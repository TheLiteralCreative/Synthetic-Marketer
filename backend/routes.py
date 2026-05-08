"""API routes."""
from __future__ import annotations

import asyncio
import json
import platform
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from backend import (
    __version__, audit_meta, audit_runner, job_queue, progress,
    settings as settings_mod,
)
from backend.models import PingResponse, SettingsModel, SettingsResponse

router = APIRouter(prefix="/api")

ROOT = Path(__file__).resolve().parent.parent


# ----- Liveness -------------------------------------------------------------

@router.get("/ping", response_model=PingResponse)
def ping() -> PingResponse:
    cfg = settings_mod.load()
    return PingResponse(
        status="ok", version=__version__, name="Synthetic-Marketer",
        ready=bool(cfg.get("anthropic_api_key")),
    )


# ----- Settings -------------------------------------------------------------

@router.get("/settings", response_model=SettingsResponse)
def get_settings() -> SettingsResponse:
    cfg = settings_mod.load()
    return SettingsResponse(**settings_mod.redact_for_response(cfg))


@router.put("/settings", response_model=SettingsResponse)
def put_settings(payload: SettingsModel) -> SettingsResponse:
    update = {k: v for k, v in payload.model_dump().items() if v is not None}
    merged = settings_mod.save(update)
    return SettingsResponse(**settings_mod.redact_for_response(merged))


# ----- Audits ---------------------------------------------------------------

class CreateAuditRequest(BaseModel):
    url: str
    brand: Optional[str] = None
    model: Optional[str] = None
    skip_psi: bool = False


@router.post("/audits")
async def create_audit(payload: CreateAuditRequest) -> dict:
    cfg = settings_mod.load()
    api_key = cfg.get("anthropic_api_key", "")
    if not api_key:
        raise HTTPException(400, "Anthropic API key not configured. Set in Settings.")

    # Derive brand from URL if not provided, then sanitize.
    # Sanitization rules: keep alphanumerics + hyphens. Replace `&` with "And"
    # before stripping (so "Hewitt-Garden&Design" becomes "Hewitt-GardenAndDesign"
    # not "Hewitt-GardenDesign"). Underscores are reserved as bin-name separators.
    raw_brand = payload.brand or _derive_brand(payload.url)
    brand = raw_brand.replace("&", "And").replace("_", "-")
    brand = re.sub(r"[^A-Za-z0-9\-]+", "", brand).strip("-") or "Audit"
    date = time.strftime("%Y%m%d")
    bin_name = f"Synth-mkt_{brand}_{date}"
    output_folder = Path(cfg.get("output_folder") or ROOT)
    bin_dir = output_folder / bin_name

    job = job_queue.create(payload.url, str(bin_dir), bin_name, options={
        "model": payload.model or audit_runner.DEFAULT_MODEL,
        "skip_psi": payload.skip_psi,
    })

    async def _run():
        try:
            await audit_runner.run_audit(
                payload.url, bin_dir,
                job_id=job.job_id,
                api_key=api_key,
                model=payload.model or audit_runner.DEFAULT_MODEL,
                do_psi=not payload.skip_psi,
                brand=brand,
            )
        except Exception:
            # Errors already recorded by audit_runner via job_queue + progress
            pass

    job.task = asyncio.create_task(_run())
    return {"job_id": job.job_id, "bin_name": bin_name, "bin_dir": str(bin_dir)}


@router.get("/audits/{job_id}")
def get_audit(job_id: str) -> dict:
    job = job_queue.get(job_id)
    if not job:
        raise HTTPException(404, "job not found")
    return job.to_dict()


@router.get("/audits/{job_id}/stream")
async def stream_audit(job_id: str) -> EventSourceResponse:
    job = job_queue.get(job_id)
    if not job:
        raise HTTPException(404, "job not found")

    queue = progress.AsyncEventQueue(job_id, replay_log=True)
    progress.register(job_id, queue.callback)

    async def event_generator():
        try:
            async for event in queue:
                yield {
                    "event": event.kind,
                    "data": json.dumps(event.to_dict()),
                }
        finally:
            progress.unregister(job_id, queue.callback)

    return EventSourceResponse(event_generator())


@router.post("/audits/{job_id}/cancel")
def cancel_audit(job_id: str) -> dict:
    if not job_queue.cancel(job_id):
        raise HTTPException(409, "job not cancellable")
    return {"job_id": job_id, "status": "cancelled"}


@router.get("/audits")
def list_audits() -> dict:
    """List jobs (in-memory) + bins on disk."""
    in_memory = [j.to_dict() for j in job_queue.list_all()]
    bins = []
    cfg = settings_mod.load()
    output_folder = Path(cfg.get("output_folder") or ROOT)
    if output_folder.exists():
        for child in sorted(output_folder.glob("Synth-mkt_*"), reverse=True):
            if not child.is_dir():
                continue
            qa_path = child / "_QA-REPORT.md"
            audit_path = child / "MARKETING-AUDIT.md"
            score = None
            if audit_path.exists():
                m = re.search(r"(?:Overall.*?Score|Marketing Score)[:\s\*]+(\d+)/100",
                              audit_path.read_text(encoding="utf-8", errors="ignore"))
                if m:
                    score = int(m.group(1))
            bins.append({
                "name": child.name,
                "path": str(child),
                "score": score,
                "has_qa": qa_path.exists(),
                "has_audit": audit_path.exists(),
                "modified": child.stat().st_mtime,
            })
    return {"jobs": in_memory, "bins": bins}


# ----- Bins (project-bin metadata + file ops) -------------------------------

@router.get("/bins")
def list_bins() -> dict:
    """Lightweight list of all Synth-mkt_* bins in the configured output folder."""
    cfg = settings_mod.load()
    output_folder = Path(cfg.get("output_folder") or ROOT)
    bins = audit_meta.list_bins(output_folder)
    return {"output_folder": str(output_folder), "bins": bins}


@router.get("/bins/{bin_name}")
def get_bin(bin_name: str) -> dict:
    """Full metadata for a single bin — score, categories, findings, files."""
    bin_dir = _resolve_bin(bin_name)
    return audit_meta.parse_bin(bin_dir)


@router.get("/bins/{bin_name}/file/{filename:path}")
def serve_bin_file(bin_name: str, filename: str):
    """Serve a deliverable file (PDF, MD, JSON) from inside a bin.

    For PDFs the browser displays inline; for markdown the server sends as
    text/markdown so the browser typically downloads or shows source.
    """
    bin_dir = _resolve_bin(bin_name)
    safe = (bin_dir / filename).resolve()
    # safety: ensure resolved path stays inside the bin
    try:
        safe.relative_to(bin_dir.resolve())
    except ValueError:
        raise HTTPException(400, "path escape attempt")
    if not safe.is_file():
        raise HTTPException(404, "file not found")
    media = "application/pdf" if safe.suffix == ".pdf" else (
        "text/markdown" if safe.suffix == ".md" else "application/octet-stream"
    )
    return FileResponse(str(safe), media_type=media, filename=safe.name)


class OpenRequest(BaseModel):
    target: str = "folder"  # 'folder' or a specific filename inside the bin


@router.post("/bins/{bin_name}/open")
def open_bin(bin_name: str, payload: OpenRequest) -> dict:
    """Open the bin folder (or a specific file) in the OS default app.

    macOS uses `open`, Windows uses `start`, Linux uses `xdg-open`.
    """
    bin_dir = _resolve_bin(bin_name)
    if payload.target == "folder":
        path = bin_dir
    else:
        path = (bin_dir / payload.target).resolve()
        try:
            path.relative_to(bin_dir.resolve())
        except ValueError:
            raise HTTPException(400, "path escape attempt")
        if not path.exists():
            raise HTTPException(404, "file not found")

    system = platform.system()
    try:
        if system == "Darwin":
            subprocess.Popen(["open", str(path)])
        elif system == "Windows":
            subprocess.Popen(["cmd", "/c", "start", "", str(path)], shell=False)
        else:
            subprocess.Popen(["xdg-open", str(path)])
    except Exception as e:
        raise HTTPException(500, f"open failed: {e}")
    return {"opened": str(path)}


@router.post("/bins/{bin_name}/rerender")
async def rerender_pdfs(bin_name: str) -> dict:
    """Re-run tools/md_to_pdf.py against this bin to regenerate PDFs."""
    bin_dir = _resolve_bin(bin_name)
    script = ROOT / "tools" / "md_to_pdf.py"
    if not script.exists():
        raise HTTPException(500, "md_to_pdf.py not found")
    proc = await asyncio.create_subprocess_exec(
        sys.executable, str(script), str(bin_dir),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise HTTPException(500, f"rerender failed: {stderr.decode()[:300]}")
    return {"ok": True, "log": stdout.decode().splitlines()[-10:]}


# ----- helpers --------------------------------------------------------------

def _derive_brand(url: str) -> str:
    """Pull a clean brand token from a URL."""
    m = re.search(r"://(?:www\.)?([^/]+)", url)
    host = m.group(1) if m else url
    base = host.split(".")[0]
    return re.sub(r"[^A-Za-z0-9]+", "", base) or "Audit"


def _resolve_bin(bin_name: str) -> Path:
    """Resolve a bin name against the configured output folder. 404 if missing."""
    if not re.match(r"^Synth-mkt_[A-Za-z0-9_-]+$", bin_name):
        raise HTTPException(400, "invalid bin name")
    cfg = settings_mod.load()
    output_folder = Path(cfg.get("output_folder") or ROOT)
    bin_dir = output_folder / bin_name
    if not bin_dir.is_dir():
        raise HTTPException(404, "bin not found")
    return bin_dir

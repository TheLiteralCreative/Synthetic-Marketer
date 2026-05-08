"""API routes."""
from __future__ import annotations

import asyncio
import json
import re
import time
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from backend import __version__, audit_runner, job_queue, progress, settings as settings_mod
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

    # Derive brand and bin_dir
    brand = payload.brand or _derive_brand(payload.url)
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


# ----- helpers --------------------------------------------------------------

def _derive_brand(url: str) -> str:
    """Pull a clean brand token from a URL."""
    m = re.search(r"://(?:www\.)?([^/]+)", url)
    host = m.group(1) if m else url
    base = host.split(".")[0]
    return re.sub(r"[^A-Za-z0-9]+", "", base) or "Audit"

"""Audit pipeline runner — orchestrates all 8 phases.

Phase 1 (Discovery) and Phases 6, 8 (QA, PDFs) are pure Python — call into
tools/ directly. The LLM phases (2, 3, 4, 5, 7) use the anthropic SDK with
prompts from backend/prompts.py.

Designed to run two ways:
    1. As a CLI:          python -m backend.audit_runner <url> <bin_dir>
    2. From the GUI:      backend.audit_runner.run_audit() called by routes.py

Progress events are emitted via backend/progress.py and consumed by either
a stdout printer (CLI) or an SSE stream (GUI).
"""
from __future__ import annotations

import asyncio
import json
import re
import sys
import time
import traceback
from pathlib import Path
from typing import Any, Optional

import anthropic

# Make existing tools importable
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import discover, qa, md_to_pdf  # noqa: E402

from backend import job_queue, progress, prompts, settings as settings_mod  # noqa: E402

# ----------------------------------------------------------------------------
# Pricing — USD per 1M tokens (rough; revise as Anthropic publishes)
# ----------------------------------------------------------------------------

PRICING = {
    "claude-haiku-4-5-20251001": (1.0, 5.0),
    "claude-sonnet-4-6": (3.0, 15.0),
    "claude-opus-4-7": (15.0, 75.0),
}
DEFAULT_MODEL = "claude-haiku-4-5-20251001"


def _estimate_cost(model: str, tokens_in: int, tokens_out: int) -> float:
    in_rate, out_rate = PRICING.get(model, (3.0, 15.0))
    return (tokens_in * in_rate + tokens_out * out_rate) / 1_000_000


# ----------------------------------------------------------------------------
# anthropic helpers
# ----------------------------------------------------------------------------

async def _call_claude(
    client: anthropic.AsyncAnthropic,
    prompt: str,
    *,
    model: str,
    max_tokens: int = 8192,
    job_id: Optional[str] = None,
) -> tuple[str, int, int]:
    """Single anthropic call. Returns (text, in_tokens, out_tokens)."""
    resp = await client.messages.create(
        model=model,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    text = "".join(
        block.text for block in resp.content if getattr(block, "type", "") == "text"
    )
    in_tok = resp.usage.input_tokens
    out_tok = resp.usage.output_tokens
    if job_id:
        job_queue.add_cost(job_id, in_tok, out_tok, _estimate_cost(model, in_tok, out_tok))
        progress.cost(job_id, in_tok, out_tok, _estimate_cost(model, in_tok, out_tok))
    return text, in_tok, out_tok


# ----------------------------------------------------------------------------
# Phase implementations
# ----------------------------------------------------------------------------

async def _phase1_discovery(url: str, bin_dir: Path, job_id: str, do_psi: bool) -> str:
    """Pure Python — call discover.py. Return digest text."""
    progress.phase(job_id, 1, "running", f"Crawling {url}")
    # Run blocking discover() in a thread so we don't block the event loop
    await asyncio.to_thread(discover.discover, url, bin_dir, do_psi=do_psi)
    digest_path = bin_dir / "_DIGEST.md"
    if not digest_path.exists():
        raise RuntimeError("Discovery did not produce _DIGEST.md")
    digest = digest_path.read_text(encoding="utf-8")
    progress.phase(job_id, 1, "done", f"{len(digest)} chars")
    return digest


async def _phase2_subagents(
    client: anthropic.AsyncAnthropic,
    url: str,
    digest: str,
    job_id: str,
    model: str,
) -> dict[str, str]:
    """5 parallel subagent calls. Returns {role: markdown_output}."""
    progress.phase(job_id, 2, "running", "5 parallel analysts")

    async def run_one(role: str, brief: str) -> tuple[str, str]:
        progress.subagent(job_id, role, "running")
        prompt = brief.format(url=url, digest=digest)
        text, _in, _out = await _call_claude(
            client, prompt, model=model, max_tokens=4096, job_id=job_id
        )
        progress.subagent(job_id, role, "done", f"{len(text)} chars")
        return role, text

    tasks = [run_one(role, brief) for role, brief in prompts.SUBAGENT_BRIEFS.items()]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    outputs: dict[str, str] = {}
    for r in results:
        if isinstance(r, Exception):
            raise r
        role, text = r
        outputs[role] = text

    progress.phase(job_id, 2, "done", f"{len(outputs)} subagent outputs")
    return outputs


async def _phase3_aggregate(
    client: anthropic.AsyncAnthropic,
    url: str,
    digest: str,
    subagent_outputs: dict[str, str],
    bin_dir: Path,
    job_id: str,
    model: str,
) -> str:
    """Aggregate the 5 subagent outputs into MARKETING-AUDIT.md."""
    progress.phase(job_id, 3, "running", "Synthesizing audit")
    combined = "\n\n---\n\n".join(
        f"### Subagent: {role}\n\n{text}" for role, text in subagent_outputs.items()
    )
    prompt = prompts.AGGREGATE_AUDIT.format(
        url=url, subagent_outputs=combined, digest=digest[:8000],
    )
    audit_text, _, _ = await _call_claude(
        client, prompt, model=model, max_tokens=8192, job_id=job_id
    )
    audit_path = bin_dir / "MARKETING-AUDIT.md"
    audit_path.write_text(audit_text, encoding="utf-8")
    progress.phase(job_id, 3, "done", f"{audit_path.name} written")
    return audit_text


async def _phase4_companions(
    client: anthropic.AsyncAnthropic,
    url: str,
    audit_text: str,
    bin_dir: Path,
    brand: str,
    job_id: str,
    model: str,
) -> None:
    """Run COMPETITOR-REPORT and ADS-AUDIENCE in parallel."""
    progress.phase(job_id, 4, "running", "Competitor + audience reports")
    excerpt = audit_text[:6000]

    async def write_competitor():
        prompt = prompts.COMPETITOR_REPORT.format(
            url=url, brand=brand, audit_excerpt=excerpt,
        )
        text, _, _ = await _call_claude(
            client, prompt, model=model, max_tokens=8192, job_id=job_id
        )
        (bin_dir / "COMPETITOR-REPORT.md").write_text(text, encoding="utf-8")

    async def write_audience():
        prompt = prompts.AUDIENCE_REPORT.format(url=url, audit_excerpt=excerpt)
        text, _, _ = await _call_claude(
            client, prompt, model=model, max_tokens=8192, job_id=job_id
        )
        (bin_dir / "ADS-AUDIENCE.md").write_text(text, encoding="utf-8")

    await asyncio.gather(write_competitor(), write_audience())
    progress.phase(job_id, 4, "done", "2 reports written")


async def _phase5_standard(
    client: anthropic.AsyncAnthropic,
    audit_text: str,
    bin_dir: Path,
    job_id: str,
    model: str,
) -> None:
    """Run 4 standard deliverables in parallel."""
    progress.phase(job_id, 5, "running", "4 standard deliverables")

    async def write(filename: str, prompt_template: str, var: str = "audit_text"):
        prompt = prompt_template.format(**{var: audit_text})
        text, _, _ = await _call_claude(
            client, prompt, model=model, max_tokens=4096, job_id=job_id
        )
        (bin_dir / filename).write_text(text, encoding="utf-8")

    await asyncio.gather(
        write("EXECUTIVE-BRIEF.md", prompts.EXECUTIVE_BRIEF),
        write("WALKTHROUGH.md", prompts.WALKTHROUGH),
        write("IMPLEMENTATION-ROADMAP.md", prompts.IMPLEMENTATION_ROADMAP),
        write("GLOSSARY.md", prompts.GLOSSARY, var="audit_excerpt"),
    )
    progress.phase(job_id, 5, "done", "4 deliverables written")


async def _phase6_qa(bin_dir: Path, job_id: str) -> dict[str, Any]:
    """Pure Python — call qa.py."""
    progress.phase(job_id, 6, "running", "QA checks")
    results, exit_code = await asyncio.to_thread(qa.run_qa, bin_dir)
    await asyncio.to_thread(qa.write_report, bin_dir, results, exit_code)
    status = {0: "ready to ship", 1: "warnings", 2: "critical"}[exit_code]
    progress.phase(job_id, 6, "done", f"QA: {status}")
    return {"exit_code": exit_code, "status": status}


async def _phase7_dashboard_pdf(
    audit_text: str, bin_dir: Path, brand: str, url: str, job_id: str,
) -> None:
    """Generate the dashboard PDF using the existing reportlab script.

    Builds the JSON payload directly from MARKETING-AUDIT.md (no LLM needed).
    """
    progress.phase(job_id, 7, "running", "Dashboard PDF")
    # Find the script
    script_path = Path.home() / ".claude/skills/market/scripts/generate_pdf_report.py"
    if not script_path.exists():
        progress.phase(job_id, 7, "done", "Skipped — generate_pdf_report.py not found")
        return
    payload = _extract_dashboard_payload(audit_text, brand, url)
    json_path = bin_dir / "_dashboard_data.json"
    json_path.write_text(json.dumps(payload), encoding="utf-8")
    domain = re.sub(r"^https?://(www\.)?", "", url).rstrip("/").replace(".", "-")
    pdf_name = f"MARKETING-REPORT-{domain}.pdf"
    proc = await asyncio.create_subprocess_exec(
        sys.executable, str(script_path), str(json_path), pdf_name,
        cwd=str(bin_dir),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()
    json_path.unlink(missing_ok=True)
    if proc.returncode != 0:
        raise RuntimeError(f"Dashboard PDF script failed: {stderr.decode()[:200]}")
    progress.phase(job_id, 7, "done", pdf_name)


async def _phase8_pdfs(bin_dir: Path, job_id: str) -> None:
    """Pure Python — call md_to_pdf.py via subprocess for isolation."""
    progress.phase(job_id, 8, "running", "Rendering markdowns to PDF")
    proc = await asyncio.create_subprocess_exec(
        sys.executable, str(ROOT / "tools" / "md_to_pdf.py"), str(bin_dir),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(f"PDF rendering failed: {stderr.decode()[:300]}")
    progress.phase(job_id, 8, "done", "PDFs rendered + bundled")


# ----------------------------------------------------------------------------
# MARKETING-AUDIT.md → dashboard JSON
# ----------------------------------------------------------------------------

def _extract_dashboard_payload(audit_text: str, brand: str, url: str) -> dict:
    """Parse MARKETING-AUDIT.md to build the dashboard JSON the script expects."""
    overall = _extract_int(r"(?:Overall(?:\s+Marketing)?\s+Score|Marketing\s+Score)[:\s\*]+(\d+)\s*(?:/\s*100)?\b", audit_text) or 0

    cat_re = re.compile(
        r"\|\s*(?:\*\*)?(Content & Messaging|Conversion Optimization|"
        r"SEO & Discoverability|Competitive Positioning|Brand & Trust|"
        r"Growth & Strategy)(?:\*\*)?\s*\|\s*(\d+)/100",
        re.IGNORECASE,
    )
    cats = {m.group(1): int(m.group(2)) for m in cat_re.finditer(audit_text)}
    weights = {
        "Content & Messaging": "25%",
        "Conversion Optimization": "20%",
        "SEO & Discoverability": "20%",
        "Competitive Positioning": "15%",
        "Brand & Trust": "10%",
        "Growth & Strategy": "10%",
    }
    categories = {
        name: {"score": cats.get(name, 0), "weight": weights[name]}
        for name in weights
    }

    # Findings: scrape lines that start with severity tags
    findings = []
    for sev in ("Critical", "High", "Medium", "Low"):
        for m in re.finditer(rf"\b{sev}\b\s*[—\-:]+\s*([^\n]+)", audit_text):
            text = m.group(1).strip().strip("*").strip()
            if 30 < len(text) < 400:
                findings.append({"severity": sev, "finding": text})
            if len(findings) >= 14:
                break
        if len(findings) >= 14:
            break

    quick_wins = _extract_numbered_list(audit_text, "Quick Wins") or []
    medium = _extract_numbered_list(audit_text, "Strategic Recommendations") or []
    strategic = _extract_numbered_list(audit_text, "Long-Term Initiatives") or []

    summary = _extract_section(audit_text, "Executive Summary") or ""
    summary = re.sub(r"\s+", " ", summary).strip()[:1500]

    return {
        "url": url,
        "date": time.strftime("%B %d, %Y"),
        "brand_name": brand,
        "overall_score": overall,
        "executive_summary": summary,
        "categories": categories,
        "findings": findings[:14],
        "quick_wins": quick_wins[:12],
        "medium_term": medium[:10],
        "strategic": strategic[:7],
    }


def _extract_int(pattern: str, text: str) -> Optional[int]:
    m = re.search(pattern, text, re.IGNORECASE)
    return int(m.group(1)) if m else None


def _extract_section(text: str, header: str) -> Optional[str]:
    m = re.search(rf"##\s+{re.escape(header)}\s*\n+([\s\S]*?)(?=\n##\s+|\Z)", text, re.IGNORECASE)
    return m.group(1).strip() if m else None


def _extract_numbered_list(text: str, heading_substring: str) -> list[str]:
    section = re.search(
        rf"##\s+[^\n]*{re.escape(heading_substring)}[^\n]*\n+([\s\S]*?)(?=\n##\s+|\Z)",
        text, re.IGNORECASE,
    )
    if not section:
        return []
    items = re.findall(r"^\s*\d+\.\s+([^\n]+(?:\n {3,}[^\n]+)*)", section.group(1), re.MULTILINE)
    cleaned = [re.sub(r"\s+", " ", x).strip() for x in items]
    return [x for x in cleaned if 20 < len(x) < 600]


# ----------------------------------------------------------------------------
# Orchestrator
# ----------------------------------------------------------------------------

async def run_audit(
    url: str,
    bin_dir: Path,
    *,
    job_id: str,
    api_key: str,
    model: str = DEFAULT_MODEL,
    do_psi: bool = True,
    brand: Optional[str] = None,
) -> dict[str, Any]:
    """Run the full 8-phase pipeline. Returns metadata dict."""
    bin_dir = Path(bin_dir).resolve()
    bin_dir.mkdir(parents=True, exist_ok=True)
    if brand is None:
        brand = bin_dir.name.split("_")[1] if "_" in bin_dir.name else url

    client = anthropic.AsyncAnthropic(api_key=api_key)
    job_queue.mark_started(job_id)
    progress.log(job_id, f"Starting audit of {url} (model={model})")

    try:
        digest = await _phase1_discovery(url, bin_dir, job_id, do_psi)
        subagents = await _phase2_subagents(client, url, digest, job_id, model)
        audit_text = await _phase3_aggregate(client, url, digest, subagents, bin_dir, job_id, model)
        await _phase4_companions(client, url, audit_text, bin_dir, brand, job_id, model)
        await _phase5_standard(client, audit_text, bin_dir, job_id, model)
        qa_result = await _phase6_qa(bin_dir, job_id)
        await _phase7_dashboard_pdf(audit_text, bin_dir, brand, url, job_id)
        await _phase8_pdfs(bin_dir, job_id)

        # Final score from MARKETING-AUDIT.md
        score = _extract_int(r"(?:Overall(?:\s+Marketing)?\s+Score|Marketing\s+Score)[:\s\*]+(\d+)\s*(?:/\s*100)?\b", audit_text)
        job_queue.mark_done(job_id, score=score)
        progress.done(job_id, score=score)
        return {
            "score": score,
            "qa": qa_result,
            "bin_dir": str(bin_dir),
        }
    except asyncio.CancelledError:
        job_queue.mark_cancelled(job_id)
        progress.error(job_id, "cancelled")
        raise
    except Exception as e:
        tb = traceback.format_exc()
        job_queue.mark_failed(job_id, str(e))
        progress.error(job_id, f"{type(e).__name__}: {e}")
        progress.log(job_id, tb[:1000])
        raise


# ----------------------------------------------------------------------------
# CLI entrypoint
# ----------------------------------------------------------------------------

def _cli_progress_printer(event: progress.ProgressEvent) -> None:
    """Stdout consumer for events when running from CLI."""
    if event.kind == "phase":
        icon = {"running": "▶", "done": "✓", "failed": "✗"}.get(event.status or "", "·")
        detail = f" — {event.detail}" if event.detail else ""
        print(f"  {icon} Phase {event.phase}: {event.phase_name}{detail}")
    elif event.kind == "subagent":
        icon = {"running": "  ⏳", "done": "  ✓"}.get(event.status or "", "  ·")
        print(f"{icon}  subagent: {event.subagent_id}{(' — ' + event.detail) if event.detail else ''}")
    elif event.kind == "cost":
        # noisy if printed every call — keep as a running total at end
        pass
    elif event.kind == "log":
        if event.detail and event.detail != "heartbeat":
            print(f"  · {event.detail[:200]}")
    elif event.kind == "error":
        print(f"  ✗ ERROR: {event.error}")
    elif event.kind == "done":
        print(f"  ✅ Audit complete. Score: {event.score}/100")


async def _cli_main(args) -> int:
    cfg = settings_mod.load()
    api_key = args.api_key or cfg.get("anthropic_api_key") or ""
    if not api_key:
        print("error: no API key. Set ANTHROPIC_API_KEY or run from the GUI Settings.", file=sys.stderr)
        return 2

    bin_dir = Path(args.bin_dir).resolve()
    job = job_queue.create(args.url, str(bin_dir), bin_dir.name)
    progress.register(job.job_id, _cli_progress_printer)

    print(f"[runner] {args.url} → {bin_dir}")
    print(f"[runner] model: {args.model}")
    print(f"[runner] job_id: {job.job_id}")
    print()

    try:
        result = await run_audit(
            args.url, bin_dir,
            job_id=job.job_id,
            api_key=api_key,
            model=args.model,
            do_psi=not args.no_psi,
        )
        j = job_queue.get(job.job_id)
        print()
        print(f"[runner] cost: ${j.cost_usd:.4f} ({j.cost_tokens_in:,} in, {j.cost_tokens_out:,} out)")
        print(f"[runner] bin: {result['bin_dir']}")
        return 0
    except Exception as e:
        print(f"[runner] FAILED: {e}", file=sys.stderr)
        return 1


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("url", help="Target site URL")
    ap.add_argument("bin_dir", help="Project bin folder (created if missing)")
    ap.add_argument("--model", default=DEFAULT_MODEL,
                    help=f"Anthropic model (default: {DEFAULT_MODEL})")
    ap.add_argument("--api-key", help="Override API key (else uses settings.json)")
    ap.add_argument("--no-psi", action="store_true", help="Skip PageSpeed Insights")
    args = ap.parse_args()
    return asyncio.run(_cli_main(args))


if __name__ == "__main__":
    sys.exit(main())

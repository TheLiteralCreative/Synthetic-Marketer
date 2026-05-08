"""In-memory job queue.

For B2 the job queue is in-memory only — process restart drops all jobs.
B5 will optionally persist to SQLite. For a single-user local tool, in-memory
is correct: audits run inside the same process anyway.
"""
from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field, asdict
from typing import Any, Optional


@dataclass
class Job:
    job_id: str
    url: str
    bin_dir: str
    bin_name: str
    status: str = "queued"  # queued | running | done | failed | cancelled
    started_at: Optional[float] = None
    finished_at: Optional[float] = None
    error: Optional[str] = None
    score: Optional[int] = None
    cost_usd: float = 0.0
    cost_tokens_in: int = 0
    cost_tokens_out: int = 0
    options: dict[str, Any] = field(default_factory=dict)
    cancel_event: Optional[asyncio.Event] = None
    task: Optional[asyncio.Task] = None

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d.pop("cancel_event", None)
        d.pop("task", None)
        return d


_jobs: dict[str, Job] = {}


def create(url: str, bin_dir: str, bin_name: str, options: dict[str, Any] | None = None) -> Job:
    job_id = uuid.uuid4().hex[:12]
    job = Job(
        job_id=job_id,
        url=url,
        bin_dir=bin_dir,
        bin_name=bin_name,
        options=options or {},
        cancel_event=asyncio.Event(),
    )
    _jobs[job_id] = job
    return job


def get(job_id: str) -> Optional[Job]:
    return _jobs.get(job_id)


def list_all() -> list[Job]:
    return sorted(_jobs.values(), key=lambda j: j.started_at or 0, reverse=True)


def mark_started(job_id: str) -> None:
    job = _jobs.get(job_id)
    if job:
        job.status = "running"
        job.started_at = time.time()


def mark_done(job_id: str, score: Optional[int] = None) -> None:
    job = _jobs.get(job_id)
    if job:
        job.status = "done"
        job.finished_at = time.time()
        if score is not None:
            job.score = score


def mark_failed(job_id: str, error: str) -> None:
    job = _jobs.get(job_id)
    if job:
        job.status = "failed"
        job.finished_at = time.time()
        job.error = error


def mark_cancelled(job_id: str) -> None:
    job = _jobs.get(job_id)
    if job:
        job.status = "cancelled"
        job.finished_at = time.time()


def add_cost(job_id: str, tokens_in: int, tokens_out: int, usd: float) -> None:
    job = _jobs.get(job_id)
    if job:
        job.cost_tokens_in += tokens_in
        job.cost_tokens_out += tokens_out
        job.cost_usd += usd


def cancel(job_id: str) -> bool:
    job = _jobs.get(job_id)
    if not job or job.status not in ("queued", "running"):
        return False
    if job.cancel_event:
        job.cancel_event.set()
    if job.task and not job.task.done():
        job.task.cancel()
    mark_cancelled(job_id)
    return True

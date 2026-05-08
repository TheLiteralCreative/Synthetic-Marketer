"""Progress event types + per-job callback registry.

The audit pipeline emits ProgressEvent objects throughout its run. The runner
calls `register(job_id, callback)` to subscribe; events are pushed to all
registered callbacks. SSE endpoint (in routes.py) subscribes a queue and
serializes events as Server-Sent Events to the browser.
"""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field, asdict
from typing import Any, Callable, Optional

# 8 phases as named in AUDIT-PROCESS.md
PHASES = [
    (1, "Discovery"),
    (2, "5 audit subagents"),
    (3, "Aggregate audit"),
    (4, "Companion reports"),
    (5, "Standard deliverables"),
    (6, "QA pass"),
    (7, "Dashboard PDF"),
    (8, "Human-friendly PDFs"),
]


@dataclass
class ProgressEvent:
    """A single progress update emitted by the runner."""
    job_id: str
    timestamp: float = field(default_factory=time.time)
    kind: str = "phase"  # 'phase' | 'subagent' | 'log' | 'error' | 'cost' | 'done'
    phase: Optional[int] = None
    phase_name: Optional[str] = None
    status: Optional[str] = None  # 'running' | 'done' | 'failed' | 'cancelled'
    detail: Optional[str] = None
    subagent_id: Optional[str] = None  # for kind='subagent'
    cost_usd: Optional[float] = None  # for kind='cost'
    cost_tokens_in: Optional[int] = None
    cost_tokens_out: Optional[int] = None
    score: Optional[int] = None  # for kind='done'
    error: Optional[str] = None  # for kind='error'

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        return {k: v for k, v in d.items() if v is not None}


# Per-job callback registry. Multiple callbacks per job are supported (e.g.,
# CLI logger + SSE stream simultaneously).
_callbacks: dict[str, list[Callable[[ProgressEvent], None]]] = {}
# Per-job event log — append-only, used by SSE late-joiners to catch up.
_event_log: dict[str, list[ProgressEvent]] = {}


def register(job_id: str, callback: Callable[[ProgressEvent], None]) -> None:
    """Subscribe a callback to a job's progress events."""
    _callbacks.setdefault(job_id, []).append(callback)


def unregister(job_id: str, callback: Callable[[ProgressEvent], None]) -> None:
    if job_id in _callbacks and callback in _callbacks[job_id]:
        _callbacks[job_id].remove(callback)


def emit(event: ProgressEvent) -> None:
    """Push an event to all registered callbacks for its job. Also persist."""
    _event_log.setdefault(event.job_id, []).append(event)
    for cb in list(_callbacks.get(event.job_id, [])):
        try:
            cb(event)
        except Exception:  # callbacks must not break the runner
            pass


def get_log(job_id: str) -> list[ProgressEvent]:
    """Return the full event log for a job (for late-joining SSE clients)."""
    return list(_event_log.get(job_id, []))


def clear_job(job_id: str) -> None:
    """Drop all state for a finished job (caller decides retention)."""
    _callbacks.pop(job_id, None)
    _event_log.pop(job_id, None)


# ----------------------------------------------------------------------------
# Convenience emitters used by the runner
# ----------------------------------------------------------------------------

def phase(job_id: str, phase_num: int, status: str, detail: str = "") -> None:
    name = next((n for p, n in PHASES if p == phase_num), f"Phase {phase_num}")
    emit(ProgressEvent(
        job_id=job_id, kind="phase", phase=phase_num, phase_name=name,
        status=status, detail=detail or None,
    ))


def subagent(job_id: str, subagent_id: str, status: str, detail: str = "") -> None:
    emit(ProgressEvent(
        job_id=job_id, kind="subagent", subagent_id=subagent_id,
        status=status, detail=detail or None,
    ))


def log(job_id: str, message: str) -> None:
    emit(ProgressEvent(job_id=job_id, kind="log", detail=message))


def cost(job_id: str, tokens_in: int, tokens_out: int, usd: float) -> None:
    emit(ProgressEvent(
        job_id=job_id, kind="cost",
        cost_tokens_in=tokens_in, cost_tokens_out=tokens_out, cost_usd=usd,
    ))


def done(job_id: str, score: Optional[int] = None) -> None:
    emit(ProgressEvent(job_id=job_id, kind="done", status="done", score=score))


def error(job_id: str, message: str) -> None:
    emit(ProgressEvent(job_id=job_id, kind="error", error=message))


# ----------------------------------------------------------------------------
# Async helper for SSE
# ----------------------------------------------------------------------------

class AsyncEventQueue:
    """Bridge sync emit() calls to an async iterator for SSE streaming."""

    def __init__(self, job_id: str, replay_log: bool = True):
        self.job_id = job_id
        self.queue: asyncio.Queue = asyncio.Queue()
        self._loop = asyncio.get_event_loop()
        self._closed = False
        if replay_log:
            for ev in get_log(job_id):
                self.queue.put_nowait(ev)

    def callback(self, event: ProgressEvent) -> None:
        """Sync callback registered with progress.register()."""
        if self._closed:
            return
        try:
            self._loop.call_soon_threadsafe(self.queue.put_nowait, event)
        except RuntimeError:
            pass  # loop closed

    async def __aiter__(self):
        while not self._closed:
            try:
                event = await asyncio.wait_for(self.queue.get(), timeout=30.0)
            except asyncio.TimeoutError:
                # heartbeat — keeps the SSE connection alive through proxies
                yield ProgressEvent(job_id=self.job_id, kind="log", detail="heartbeat")
                continue
            yield event
            if event.kind in ("done", "error") and event.status in ("done", "failed", "cancelled", None):
                self._closed = True

    def close(self) -> None:
        self._closed = True

"""Tiny background-job registry: long work (older games, engine analysis) runs in a thread while the user keeps exploring.

Streamlit-free. Jobs are keyed by what they compute (player, settings), so a second visitor looking at the same
player shares the result instead of repeating the work. The page polls ``get`` and merges finished results.
"""
from __future__ import annotations

import threading
from typing import Callable, Dict, Optional


class Job:
    def __init__(self) -> None:
        self.status = "running"      # running | done | error
        self.done = 0
        self.total = 0
        self.result: object = None
        self.error = ""

    @property
    def fraction(self) -> float:
        return self.done / self.total if self.total else 0.0


_JOBS: Dict[str, Job] = {}
_LOCK = threading.Lock()


def start(key: str, fn: Callable[[Callable[[int, int], None]], object]) -> Job:
    """Run ``fn(progress)`` in a thread unless a job with this key already runs or finished. Returns the job."""
    with _LOCK:
        job = _JOBS.get(key)
        if job is not None and job.status in ("running", "done"):
            return job
        job = Job()
        _JOBS[key] = job

    def progress(done: int, total: int) -> None:
        job.done, job.total = done, total

    def run() -> None:
        try:
            job.result = fn(progress)
        except Exception as exc:  # noqa: BLE001 - a failed background job must never break the page
            job.error = f"{type(exc).__name__}: {exc}"
            job.status = "error"
        else:
            job.status = "done"

    threading.Thread(target=run, daemon=True, name=f"klimate-{key[:40]}").start()
    return job


def running(prefix: str = "") -> int:
    """How many jobs whose key starts with ``prefix`` are running right now (used to cap concurrent engine work)."""
    with _LOCK:
        return sum(1 for k, j in _JOBS.items() if k.startswith(prefix) and j.status == "running")


def get(key: str) -> Optional[Job]:
    with _LOCK:
        return _JOBS.get(key)


def clear() -> None:
    with _LOCK:
        _JOBS.clear()

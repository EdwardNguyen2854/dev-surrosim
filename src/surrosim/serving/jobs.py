"""In-process background jobs for long-running engineering operations.

The API runs solver cases, GNN inference and optimization in a small thread
pool so HTTP requests never block on a multi-second (or minute) computation.
Jobs live in memory, stream a bounded log and report progress; durable
artifacts are written to ``outputs/jobs/<id>`` by the workers themselves.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timezone
import multiprocessing
import queue
from threading import Lock
import time
from typing import Any, Callable
from uuid import uuid4

MAX_LOG_ENTRIES = 400


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(moment: datetime | None) -> str | None:
    return moment.isoformat(timespec="seconds") if moment else None


@dataclass
class Job:
    """A single background operation; the worker receives it as its context."""

    id: str
    kind: str
    status: str = "queued"
    stage: str = "queued"
    progress: float | None = None
    created: datetime = field(default_factory=_now)
    started: datetime | None = None
    finished: datetime | None = None
    logs: list[dict[str, Any]] = field(default_factory=list)
    result: dict[str, Any] | None = None
    error: str | None = None
    artifacts: dict[str, str] = field(default_factory=dict)

    def log(self, message: str, level: str = "info") -> None:
        self.logs.append({"time": _iso(_now()), "level": level, "message": message})
        if len(self.logs) > MAX_LOG_ENTRIES:
            del self.logs[: len(self.logs) - MAX_LOG_ENTRIES]

    def set_progress(self, fraction: float | None, stage: str | None = None) -> None:
        self.progress = (
            None if fraction is None else max(0.0, min(1.0, float(fraction)))
        )
        if stage:
            self.stage = stage

    def to_dict(self) -> dict[str, Any]:
        elapsed = (
            ((self.finished or _now()) - self.started).total_seconds()
            if self.started
            else 0.0
        )
        return {
            "id": self.id,
            "kind": self.kind,
            "status": self.status,
            "stage": self.stage,
            "progress": self.progress,
            "created_utc": _iso(self.created),
            "started_utc": _iso(self.started),
            "finished_utc": _iso(self.finished),
            "elapsed_seconds": round(elapsed, 2),
            "logs": list(self.logs),
            "result": self.result,
            "error": self.error,
        }


class JobManager:
    def __init__(self, max_workers: int = 2) -> None:
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers, thread_name_prefix="surrosim-job"
        )
        self._jobs: dict[str, Job] = {}
        self._lock = Lock()

    def submit(self, kind: str, worker: Callable[[Job], dict[str, Any]]) -> Job:
        job = Job(id=uuid4().hex[:12], kind=kind)
        with self._lock:
            self._jobs[job.id] = job
        self._executor.submit(self._execute, job, worker)
        return job

    def _execute(self, job: Job, worker: Callable[[Job], dict[str, Any]]) -> None:
        job.status = "running"
        job.started = _now()
        job.stage = "running"
        job.log("job accepted")
        try:
            result = worker(job)
        except Exception as exc:  # noqa: BLE001 - reported through job status
            job.status = "failed"
            job.error = f"{type(exc).__name__}: {exc}"
            job.log(job.error, level="error")
        else:
            job.result = result
            job.status = "succeeded"
            job.progress = 1.0
            job.stage = "done"
            job.log("job completed")
        finally:
            job.finished = _now()

    def get(self, job_id: str) -> Job | None:
        with self._lock:
            return self._jobs.get(job_id)

    def list(self, limit: int = 20) -> list[Job]:
        with self._lock:
            jobs = list(self._jobs.values())
        jobs.sort(key=lambda item: item.created, reverse=True)
        return jobs[:limit]


def run_in_process(
    entry: Callable[[dict[str, Any], Any], None],
    payload: dict[str, Any],
    job: Job,
    timeout_seconds: float = 900.0,
) -> dict[str, Any]:
    """Run a spawned worker process, forwarding its stream to the job record.

    Spawned processes keep main-thread-only libraries (Gmsh installs a SIGINT
    handler) usable and isolate solver crashes from the API server.
    """
    context = multiprocessing.get_context("spawn")
    message_queue = context.Queue()
    process = context.Process(target=entry, args=(payload, message_queue), daemon=True)
    process.start()
    outcome: dict[str, Any] = {"result": None, "error": None}
    deadline = time.monotonic() + timeout_seconds
    try:
        while True:
            try:
                message = message_queue.get(timeout=0.25)
            except queue.Empty:
                message = None
            if message is not None:
                _handle_message(job, message, outcome)
                continue
            if not process.is_alive():
                while True:
                    try:
                        message = message_queue.get_nowait()
                    except queue.Empty:
                        break
                    _handle_message(job, message, outcome)
                break
            if time.monotonic() > deadline:
                process.terminate()
                process.join(timeout=10)
                raise TimeoutError(
                    f"worker process exceeded {timeout_seconds:.0f} s"
                )
    finally:
        if process.is_alive():
            process.join(timeout=5)
    if outcome["error"] is not None:
        raise RuntimeError(outcome["error"])
    if outcome["result"] is None:
        raise RuntimeError("worker process exited without producing a result")
    return outcome["result"]


def _handle_message(
    job: Job, message: dict[str, Any], outcome: dict[str, Any]
) -> None:
    kind = message.get("kind")
    if kind == "log":
        job.log(message.get("message", ""), message.get("level", "info"))
    elif kind == "stage":
        job.set_progress(message.get("progress"), message.get("stage"))
    elif kind == "result":
        outcome["result"] = message.get("result")
    elif kind == "error":
        outcome["error"] = message.get("error")

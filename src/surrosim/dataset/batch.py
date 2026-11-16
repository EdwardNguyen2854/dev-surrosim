"""Parallel, resumable batch execution of FEA design cases."""

from concurrent.futures import ProcessPoolExecutor, as_completed
from concurrent.futures.process import BrokenProcessPool
from dataclasses import dataclass
from pathlib import Path
import csv
import json
import os
import time

from ..mesh_policy import DEFAULT_POLICY, MeshPolicy
from ..plate import Plate
from .cases import run_case


@dataclass(frozen=True)
class DesignRow:
    case_id: str
    split: str
    tag: str
    plate: Plate

    def as_dict(self) -> dict:
        return {
            "case_id": self.case_id,
            "split": self.split,
            "tag": self.tag,
            **self.plate.as_dict(),
        }


def load_designs(path: str | Path) -> list[DesignRow]:
    rows = []
    with Path(path).open(encoding="utf-8") as handle:
        for raw in csv.DictReader(handle):
            plate = Plate.from_mapping(raw)
            plate.validate()
            rows.append(
                DesignRow(
                    case_id=raw["case_id"],
                    split=raw.get("split", "unsplit"),
                    tag=raw.get("tag", ""),
                    plate=plate,
                )
            )
    if not rows:
        raise ValueError(f"No design rows found in {path}")
    return rows


def _run_worker(payload: tuple) -> dict:
    case_id, plate, runs_root, ccx, timeout, force, retries, policy = payload
    last: dict = {}
    for attempt in range(retries + 1):
        try:
            result = run_case(
                case_id, plate, runs_root, ccx, timeout,
                force=force and attempt == 0, policy=policy,
            )
        except Exception as exc:  # noqa: BLE001 - one bad case must not kill the batch
            result = {
                "case_id": case_id,
                "status": "WORKER_ERROR",
                "error": f"{type(exc).__name__}: {exc}",
                "runtime_seconds": None,
            }
        if result["status"] in ("SUCCESS", "CACHED"):
            if attempt:
                result["attempts"] = attempt + 1
            return result
        last = result
        if attempt < retries:
            time.sleep(2.0 * (attempt + 1))
    last["attempts"] = retries + 1
    return last


def run_batch(
    designs_path: str | Path,
    runs_root: str | Path,
    ccx_executable: str = "ccx",
    jobs: int = 4,
    timeout_seconds: float = 600.0,
    limit: int | None = None,
    force: bool = False,
    retries: int = 1,
    policy: MeshPolicy | None = None,
) -> dict:
    """Run every design case, resuming cached successes.

    Workers are long-lived (meshing state is released at the end of every
    case by the pipeline itself). If a worker dies abruptly (e.g. a
    solver/library crash), the pool is rebuilt and the remaining cases are
    retried; cases that exhaust the pool restarts are reported as failures
    instead of aborting the whole batch.
    """
    policy = policy or DEFAULT_POLICY
    rows = load_designs(designs_path)
    if limit is not None:
        rows = rows[:limit]
    runs_root = Path(runs_root)
    runs_root.mkdir(parents=True, exist_ok=True)

    started = time.perf_counter()
    jobs = max(1, jobs)
    results: dict[str, dict] = {}
    pending = list(rows)
    pool_attempts = 0
    max_pool_attempts = 3
    while pending and pool_attempts < max_pool_attempts:
        pool_attempts += 1
        payloads = [
            (
                row.case_id, row.plate, str(runs_root), ccx_executable,
                timeout_seconds, force, retries, policy,
            )
            for row in pending
        ]
        progressed = False
        try:
            with ProcessPoolExecutor(max_workers=jobs) as pool:
                futures = [pool.submit(_run_worker, payload) for payload in payloads]
                for future in as_completed(futures):
                    result = future.result()
                    results[result["case_id"]] = result
                    progressed = True
                    runtime = result.get("runtime_seconds")
                    runtime_text = (
                        f"{runtime:.1f}s" if runtime is not None else "n/a"
                    )
                    error = f" ({result['error']})" if result.get("error") else ""
                    attempts = result.get("attempts")
                    retry_text = (
                        f" after {attempts} attempts"
                        if attempts and attempts > 1
                        else ""
                    )
                    print(
                        f"[{len(results)}/{len(rows)}] {result['case_id']}: "
                        f"{result['status']} [{runtime_text}]{error}{retry_text}",
                        flush=True,
                    )
        except BrokenProcessPool as exc:
            print(
                f"  worker pool crashed ({exc}); "
                f"retrying {len(pending)} remaining cases with a fresh pool",
                flush=True,
            )
        pending = [row for row in pending if row.case_id not in results]
        if not progressed:
            break
    for row in pending:
        results[row.case_id] = {
            "case_id": row.case_id,
            "status": "WORKER_POOL_CRASH",
            "error": "worker pool restarts exhausted",
            "runtime_seconds": None,
        }
    ordered = [results[row.case_id] for row in rows]
    elapsed = time.perf_counter() - started
    status_counts: dict[str, int] = {}
    for result in ordered:
        status_counts[result["status"]] = status_counts.get(result["status"], 0) + 1
    summary = {
        "designs_file": str(designs_path),
        "runs_root": str(runs_root),
        "cases_requested": len(ordered),
        "status_counts": status_counts,
        "wall_seconds": elapsed,
        "solver_seconds": sum(
            result.get("runtime_seconds") or 0.0 for result in ordered
        ),
        "jobs": jobs,
        "retries": retries,
        "pool_restarts": pool_attempts - 1,
        "mesh_policy": policy.as_dict(),
        "high_order_optimize": os.environ.get("SURROSIM_HIGH_ORDER_OPTIMIZE"),
        "ccx_executable": ccx_executable,
        "failed_cases": [
            {
                "case_id": result["case_id"],
                "status": result["status"],
                "error": result.get("error"),
            }
            for result in ordered
            if result["status"] not in ("SUCCESS", "CACHED")
        ],
        "results": sorted(ordered, key=lambda item: item["case_id"]),
    }
    (runs_root / "batch_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    return summary

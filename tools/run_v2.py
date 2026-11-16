"""Resumable, single-instance v2 regeneration and training.

Run from the repository root with its Python environment. Each small FEA
chunk uses a fresh process, bounding accumulation of native mesher state.
Candidate models stay outside the serving registry until reviewed.
Requires psutil for FEA memory monitoring.
"""

import argparse
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
import csv
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import psutil


ROOT = Path(__file__).resolve().parents[1]


class MemoryPressure(RuntimeError):
    pass


def run_fea(command, *, cwd, env):
    """Stop only this batch's process tree if available RAM falls below 4 GiB."""
    process = subprocess.Popen(command, cwd=cwd, env=env)
    minimum_free = psutil.virtual_memory().available
    while process.poll() is None:
        free = psutil.virtual_memory().available
        minimum_free = min(minimum_free, free)
        if free < 4 * 1024**3:
            try:
                parent = psutil.Process(process.pid)
                children = parent.children(recursive=True)
                # Stop the submitter first, then its existing workers/solvers.
                for child in [parent, *children]:
                    try:
                        child.kill()
                    except psutil.NoSuchProcess:
                        pass
                psutil.wait_procs([parent, *children], timeout=10)
            except psutil.NoSuchProcess:
                pass
            process.wait()
            raise MemoryPressure("Available RAM fell below 4 GiB")
        time.sleep(0.5)
    print(f"Minimum available RAM during batch: {minimum_free / 1024**3:.1f} GiB", flush=True)
    return subprocess.CompletedProcess(command, process.returncode)


@contextmanager
def instance_lock(path):
    with path.open("a+b") as handle:
        handle.seek(0, 2)
        if handle.tell() == 0:
            handle.write(b"0")
            handle.flush()
        handle.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise RuntimeError("A v2 pipeline launcher is already running") from exc
        try:
            yield
        finally:
            if os.name == "nt":
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def write_table(path, rows, columns):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def run_pipeline(args, state_dir):
    from surrosim.dataset.batch import load_designs
    from surrosim.plate import Plate

    designs_path = ROOT / "data/designs_v2.csv"
    base_path = ROOT / "data/dataset_v1/dataset.csv"
    designs = load_designs(designs_path)
    with designs_path.open(encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        columns = reader.fieldnames
        rows = list(reader)
    with base_path.open(encoding="utf-8") as handle:
        base = {row["case_id"]: row for row in csv.DictReader(handle)}
    if len({row.case_id for row in designs}) != len(designs):
        raise ValueError("Duplicate design IDs")
    if not set(base).issubset({row.case_id for row in designs}):
        raise ValueError("Base dataset contains designs outside the v2 table")
    for row in designs:
        if row.case_id in base:
            previous = base[row.case_id]
            if (Plate.from_mapping(previous) != row.plate
                    or previous["split"] != row.split):
                raise ValueError(f"Base label inputs/split differ: {row.case_id}")

    env = os.environ.copy()
    for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
                 "NUMEXPR_NUM_THREADS"):
        env[name] = "1"
    env["PYTHONUNBUFFERED"] = "1"

    def status(stage, **extra):
        payload = {"stage": stage, "pid": os.getpid(),
                   "updated_utc": datetime.now(timezone.utc).isoformat(), **extra}
        temporary = state_dir / "status.tmp"
        temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        temporary.replace(state_dir / "status.json")

    worker_limit = args.jobs

    def command(stage, *arguments):
        nonlocal worker_limit
        arguments = list(arguments)
        while True:
            status(stage, command=arguments)
            print(f"\n{stage}: {' '.join(arguments)}", flush=True)
            runner = run_fea if arguments[:2] == ["dataset", "run"] else subprocess.run
            try:
                result = runner(
                    [sys.executable, "-m", "surrosim", *arguments], cwd=ROOT, env=env,
                )
                break
            except MemoryPressure:
                index = arguments.index("--jobs") + 1
                jobs = int(arguments[index])
                if jobs == 1:
                    raise
                arguments[index] = str(max(1, jobs // 2))
                worker_limit = min(worker_limit, int(arguments[index]))
                print(f"Memory pressure: resuming this chunk with {arguments[index]} workers", flush=True)
        if result.returncode:
            raise RuntimeError(f"{stage} failed with exit code {result.returncode}")

    scalar_future = None

    def train_scalar():
        scalar_env = env.copy()
        # Bound sklearn/joblib and OpenMP pools while graph FEA is active.
        scalar_env["LOKY_MAX_CPU_COUNT"] = "2"
        scalar_env["OMP_THREAD_LIMIT"] = "2"
        with (state_dir / "scalar.log").open("a", encoding="utf-8") as log:
            result = subprocess.run(
                [sys.executable, "-m", "surrosim", "train", "scalar",
                 "--out", "models/scalar/v2_candidate",
                 "--report", "reports/v2.0_scalar_candidate.md"],
                cwd=ROOT, env=scalar_env, stdout=log, stderr=subprocess.STDOUT,
            )
        if result.returncode:
            raise RuntimeError(f"Scalar training failed with exit code {result.returncode}; see scalar.log")

    try:
        with ThreadPoolExecutor(max_workers=1) as training:
            for profile, selected, runs in (
                ("production", [row for row in rows if row["case_id"] not in base],
                 "data/runs_v2"),
                ("graph", rows, "data/runs_v2_graph"),
            ):
                for start in range(0, len(selected), args.chunk_size):
                    if scalar_future is not None and scalar_future.done():
                        scalar_future.result()
                    scalar_active = scalar_future is not None and not scalar_future.done()
                    jobs = 1 if scalar_active else worker_limit
                    chunk = state_dir / f"{profile}_{start:04d}.csv"
                    write_table(chunk, selected[start:start + args.chunk_size], columns)
                    command(f"{profile} {start + 1}-{min(start + args.chunk_size, len(selected))}/{len(selected)}",
                            "dataset", "run", "--designs", str(chunk), "--out", runs,
                            "--ccx", args.ccx, "--jobs", str(jobs), "--mesh-profile", profile,
                            "--timeout", str(args.timeout))
                if profile == "production":
                    command("build gated dataset", "dataset", "build", "--designs", str(designs_path),
                            "--runs", "data/runs_v2", "--base", str(base_path), "--out", "data/dataset_v2")
                    manifest = json.loads((ROOT / "data/dataset_v2/manifest.json").read_text())
                    if manifest["cases_failed"] or manifest["cases_in_dataset"] != len(rows):
                        raise RuntimeError("Production dataset is incomplete after gating")
                    if getattr(args, "reuse_scalar", False):
                        from surrosim.serving.predictor import ScalarPredictor
                        candidate = ScalarPredictor(ROOT / "models/scalar/v2_candidate")
                        if candidate.metadata["dataset_sha256"] != manifest["dataset_sha256"]:
                            raise RuntimeError("Scalar candidate does not match the gated dataset")
                        del candidate
                        print("Reusing loadable scalar candidate with matching dataset hash", flush=True)
                    else:
                        print("Starting scalar training alongside graph FEA; see scalar.log", flush=True)
                        scalar_future = training.submit(train_scalar)
            status("waiting for scalar training")
            if scalar_future is not None:
                scalar_future.result()
        command("export graphs", "graph", "export", "--designs", str(designs_path),
                "--runs", "data/runs_v2_graph", "--out", "data/graphs_v2")
        manifest = json.loads((ROOT / "data/graphs_v2/manifest.json").read_text())
        if manifest["skipped"] or manifest["graphs"] != len(rows):
            raise RuntimeError("Graph dataset is incomplete after export")
        command("train GNN candidate", "train", "gnn", "--out", "models/gnn/v2_candidate",
                "--report", "reports/v2.0_gnn_candidate.md", "--target-scaling", "nominal_v1")
        status("awaiting_model_review", designs=len(rows))
    except BaseException as exc:
        status("failed", error=f"{type(exc).__name__}: {exc}")
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ccx", default=str(ROOT / "tools/calculix/ccx.exe"))
    parser.add_argument("--chunk-size", type=int, default=20)
    parser.add_argument("--timeout", type=float, default=600)
    parser.add_argument("--jobs", type=int, choices=(1, 2, 3, 4), default=1)
    parser.add_argument("--reuse-scalar", action="store_true",
                        help="Reuse a loadable scalar candidate if its dataset hash matches")
    args = parser.parse_args()
    if args.chunk_size < 1 or args.timeout <= 0:
        parser.error("chunk-size and timeout must be positive")
    state_dir = ROOT / "outputs/v2_pipeline"
    state_dir.mkdir(parents=True, exist_ok=True)
    with instance_lock(state_dir / "launcher.lock"):
        run_pipeline(args, state_dir)


if __name__ == "__main__":
    main()

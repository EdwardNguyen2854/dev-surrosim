"""Compare fresh 1/2-worker FEA runs. Requires psutil for memory monitoring."""

import argparse
import csv
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import psutil

from run_v2 import ROOT, instance_lock, write_table


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jobs", type=int, nargs="+", choices=(1, 2, 3, 4), default=[1, 2])
    parser.add_argument("--solver-threads", type=int, choices=(1, 2), default=1)
    args = parser.parse_args()
    state = ROOT / "outputs/v2_pipeline"
    state.mkdir(parents=True, exist_ok=True)
    with instance_lock(state / "launcher.lock"):
        output = state / f"benchmark_{time.strftime('%Y%m%d_%H%M%S')}"
        output.mkdir()
        with (ROOT / "data/designs_v2.csv").open(encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            columns = reader.fieldnames
            rows = list(reader)
        selected = []
        for shape in sorted({row["shape"] for row in rows} - {"plate"}):
            family = [row for row in rows if row["shape"] == shape]
            # Two deterministic designs per family, with different dimensions.
            selected.extend([family[0], family[len(family) // 2]])
        designs = output / "designs.csv"
        write_table(designs, selected, columns)
        env = os.environ.copy()
        for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
                     "NUMEXPR_NUM_THREADS"):
            env[name] = "1"
        env["OMP_NUM_THREADS"] = str(args.solver_threads)
        results = []
        for jobs in args.jobs:
            runs = output / f"runs_{jobs}"
            log_path = output / f"jobs_{jobs}.log"
            start = time.perf_counter()
            minimum_free = psutil.virtual_memory().available
            peak_rss = 0
            cpu_samples = []
            psutil.cpu_percent()
            with log_path.open("w", encoding="utf-8") as log:
                process = subprocess.Popen(
                    [sys.executable, "-m", "surrosim", "dataset", "run",
                     "--designs", str(designs), "--out", str(runs), "--jobs", str(jobs),
                     "--ccx", str(ROOT / "tools/calculix/ccx.exe"), "--retries", "0"],
                    cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT,
                )
                while process.poll() is None:
                    cpu_samples.append(psutil.cpu_percent())
                    free = psutil.virtual_memory().available
                    minimum_free = min(minimum_free, free)
                    try:
                        parent = psutil.Process(process.pid)
                        tree = [parent, *parent.children(recursive=True)]
                        rss = 0
                        for child in tree:
                            try:
                                rss += child.memory_info().rss
                            except psutil.NoSuchProcess:
                                pass
                        peak_rss = max(peak_rss, rss)
                        if free < 4 * 1024**3:
                            for child in reversed(tree):
                                try:
                                    child.kill()
                                except psutil.NoSuchProcess:
                                    pass
                            process.wait()
                            raise RuntimeError("Benchmark stopped: less than 4 GiB RAM available")
                    except psutil.NoSuchProcess:
                        pass
                    time.sleep(0.5)
            summary = json.loads((runs / "batch_summary.json").read_text())
            result = {"jobs": jobs, "wall_seconds": time.perf_counter() - start,
                      "solver_threads": args.solver_threads,
                      "min_available_gib": minimum_free / 1024**3,
                      "peak_tree_rss_gib": peak_rss / 1024**3,
                      "mean_system_cpu_pct": sum(cpu_samples) / max(1, len(cpu_samples)),
                      "status_counts": summary["status_counts"],
                      "pool_restarts": summary["pool_restarts"],
                      "return_code": process.returncode}
            results.append(result)
            (output / "results.json").write_text(json.dumps(results, indent=2) + "\n")
            print(json.dumps(result, indent=2), flush=True)
            if process.returncode or summary["status_counts"].get("SUCCESS") != len(selected):
                raise RuntimeError(f"Benchmark failed; inspect {log_path}")
        if len(results) > 1:
            print(f"Speedup: {results[0]['wall_seconds'] / results[-1]['wall_seconds']:.2f}x")
        print(f"Results: {output}")


if __name__ == "__main__":
    main()

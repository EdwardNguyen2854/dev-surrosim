"""One-command reproduction of the SurroSim pipeline.

Profiles:

* ``quick`` — a CI-sized end-to-end run: sample a handful of designs, run the
  real CalculiX cases, gate them into a dataset and train a small surrogate.
  Takes a few minutes.
* ``full`` — the complete v1.0 pipeline: the 644-case production dataset, the
  coarse graph dataset, the scalar ensemble suite and the MeshGraphNet field
  model. Takes hours on a 6-core laptop.

Every stage is invoked through the same functions the CLI uses, so the
reproduction path cannot drift from the product path.
"""

from pathlib import Path
import json
import time

from . import shapes
from .dataset import build_dataset, run_batch
from .gnn.export import export_graphs
from .gnn.train import train_gnn
from .mesh_policy import GRAPH_POLICY, PRODUCTION_POLICY
from .ml.train import train_scalar_suite
from .sampling import export_designs_v2


def _stage(name: str, function, *args, **kwargs):
    print(f"\n=== {name} ===", flush=True)
    started = time.perf_counter()
    result = function(*args, **kwargs)
    print(f"--- {name} finished in {time.perf_counter() - started:.1f} s", flush=True)
    return result


def reproduce(
    profile: str = "quick",
    ccx_executable: str = "ccx",
    jobs: int = 4,
    seed: int = 42,
    root: str | Path | None = None,
) -> dict:
    if profile not in ("quick", "full"):
        raise ValueError("profile must be 'quick' or 'full'")
    root = Path(root) if root else Path("outputs") / f"reproduce_{profile}"
    root.mkdir(parents=True, exist_ok=True)
    designs = root / "designs.csv"
    runs = root / "runs"
    dataset = root / "dataset"
    models = root / "models"

    if profile == "quick":
        per_shape, challenge_per_shape = 3, 1
        plate_count, plate_challenge = 8, 2
        sampled_shapes = (shapes.PLATE, shapes.TAPER)
        scalar_models = ("ridge",)
        graph_steps = False
    else:
        per_shape, challenge_per_shape = 380, 48
        plate_count, plate_challenge = 560, 72
        sampled_shapes = shapes.SHAPE_KINDS
        scalar_models = ("ridge", "random_forest", "xgboost", "mlp", "gaussian_process", "ensemble")
        graph_steps = True

    _stage(
        "sample designs", export_designs_v2, designs,
        seed=seed, per_shape=per_shape,
        challenge_per_shape=challenge_per_shape,
        plate_count=plate_count, plate_challenge=plate_challenge,
        method="sobol", no_hole_fraction=0.05,
        shapes_to_sample=sampled_shapes,
    )
    run_summary = _stage(
        "production FEA batch", run_batch, designs, runs, ccx_executable,
        jobs=jobs, timeout_seconds=900.0, retries=1,
        policy=PRODUCTION_POLICY, force=False,
    )
    failing = [
        status for status, number in run_summary["status_counts"].items()
        if status not in ("SUCCESS", "CACHED") and number
    ]
    if failing:
        print(f"WARNING: {failing} cases did not solve", flush=True)
    manifest = _stage("build dataset", build_dataset, designs, runs, dataset)
    metadata = _stage(
        "train scalar surrogates", train_scalar_suite,
        dataset / "dataset.csv", models, seed=seed, model_names=scalar_models,
        report_path=root / "scalar_comparison.md",
        figure_dir=root / "figures",
    )

    gnn_metadata = None
    if graph_steps:
        graph_runs = root / "runs_graph"
        graphs = root / "graphs"
        gnn_models = root / "gnn"
        _stage(
            "graph-profile FEA batch", run_batch, designs, graph_runs,
            ccx_executable, jobs=jobs, timeout_seconds=900.0, retries=1,
            policy=GRAPH_POLICY, force=False,
        )
        _stage("export mesh graphs", export_graphs, designs, graph_runs, graphs)
        gnn_metadata = _stage(
            "train field model", train_gnn, graphs, graph_runs, gnn_models,
            report_path=root / "gnn_report.md", figure_dir=root / "figures",
            seed=seed, epochs=150, patience=30,
        )

    summary = {
        "profile": profile,
        "root": str(root),
        "cases_in_dataset": manifest["cases_in_dataset"],
        "cases_failed": manifest["cases_failed"],
        "dataset_sha256": manifest["dataset_sha256"],
        "scalar_best_models": metadata["best_models"],
        "gnn_best_model": gnn_metadata["best_model"] if gnn_metadata else None,
        "ccx": ccx_executable,
        "seed": seed,
    }
    (root / "reproduction_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    print("\n=== reproduction summary ===")
    print(json.dumps(summary, indent=2))
    return summary

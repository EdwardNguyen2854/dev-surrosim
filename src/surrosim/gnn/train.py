"""Train and evaluate field-prediction models on the mesh-graph dataset."""

from pathlib import Path
from datetime import datetime, timezone
import json
import math
import time

import numpy as np
import torch

from .. import shapes
from ..plate import Plate
from ..provenance import git_info, sha256, tool_versions
from .device import resolve_device
from .features import EDGE_FEATURES, NODE_FEATURES, TARGET_COMPONENTS, von_mises
from .models import build_model
from .normalisation import decode_targets, target_scales

EVALUATED_SPLITS = ("val", "test", "challenge")


def _format_metric(value):
    return "n/a" if value is None else f"{value:.2f}"


def _select_model(models: dict) -> str:
    """Choose using validation only; held-out scores cannot change the choice."""
    return min(models, key=lambda name: models[name]["evaluation"]["val"]["global_max_vm"]["mape"])


def _load_index(graph_dir: Path) -> list[dict]:
    return json.loads((graph_dir / "index.json").read_text(encoding="utf-8"))


def _load_graph(graph_dir: Path, case_id: str) -> dict:
    return torch.load(graph_dir / f"{case_id}.pt", map_location="cpu", weights_only=False)


def _compute_normalisation(graph_dir: Path, train_ids: list[str], target_scaling: str = "none") -> dict:
    count = 0
    x_sum = np.zeros(len(NODE_FEATURES))
    x_sq = np.zeros(len(NODE_FEATURES))
    y_sum = np.zeros(len(TARGET_COMPONENTS))
    y_sq = np.zeros(len(TARGET_COMPONENTS))
    for case_id in train_ids:
        sample = _load_graph(graph_dir, case_id)
        x = sample["x"].numpy().astype(np.float64)
        y = sample["y"].numpy().astype(np.float64)
        y = y / target_scales(sample["params"], target_scaling)
        count += x.shape[0]
        x_sum += x.sum(axis=0)
        x_sq += (x**2).sum(axis=0)
        y_sum += y.sum(axis=0)
        y_sq += (y**2).sum(axis=0)
    x_mean = x_sum / count
    y_mean = y_sum / count
    x_std = np.sqrt(np.maximum(x_sq / count - x_mean**2, 1e-12))
    y_std = np.sqrt(np.maximum(y_sq / count - y_mean**2, 1e-12))
    return {
        "x_mean": x_mean.tolist(),
        "x_std": x_std.tolist(),
        "y_mean": y_mean.tolist(),
        "y_std": y_std.tolist(),
        "nodes": int(count),
        "target_scaling": target_scaling,
    }


def _forward(model, sample, normalisation, device):
    x = sample["x"].to(device)
    mean = torch.tensor(normalisation["x_mean"], device=device)
    std = torch.tensor(normalisation["x_std"], device=device)
    return model(
        (x - mean) / std,
        sample["edge_index"].to(device),
        sample["edge_attr"].to(device),
    )


def _train_one_model(
    graph_dir: Path,
    model_name: str,
    splits: dict[str, list[str]],
    normalisation: dict,
    config: dict,
    device: torch.device,
) -> tuple[object, dict]:
    torch.manual_seed(config["seed"])
    model = build_model(
        model_name,
        len(NODE_FEATURES),
        len(EDGE_FEATURES),
        hidden=config["hidden"] if model_name == "meshgraphnet" else 128,
        layers=config["layers"] if model_name == "meshgraphnet" else 3,
    ).to(device)
    optimiser = torch.optim.AdamW(
        model.parameters(), lr=config["learning_rate"], weight_decay=1e-5
    )
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
        optimiser, T_max=config["epochs"]
    )
    criterion = torch.nn.MSELoss()
    y_mean = torch.tensor(normalisation["y_mean"], device=device)
    y_std = torch.tensor(normalisation["y_std"], device=device)

    train_ids = splits["train"]
    val_ids = splits["val"]
    best_state = None
    best_val = float("inf")
    waited = 0
    history = []
    generator = torch.Generator().manual_seed(config["seed"])
    for epoch in range(1, config["epochs"] + 1):
        model.train()
        order = torch.randperm(len(train_ids), generator=generator).tolist()
        optimiser.zero_grad()
        epoch_loss = 0.0
        for step, position in enumerate(order):
            sample = _load_graph(graph_dir, train_ids[position])
            prediction = _forward(model, sample, normalisation, device)
            scale = torch.tensor(target_scales(sample["params"], normalisation.get("target_scaling", "none")), device=device, dtype=torch.float32)
            target = (sample["y"].to(device) / scale - y_mean) / y_std
            loss = criterion(prediction, target) / config["grad_accumulation"]
            loss.backward()
            epoch_loss += float(loss) * config["grad_accumulation"]
            if (step + 1) % config["grad_accumulation"] == 0:
                torch.nn.utils.clip_grad_norm_(model.parameters(), 5.0)
                optimiser.step()
                optimiser.zero_grad()
        model.eval()
        val_loss = 0.0
        with torch.no_grad():
            for case_id in val_ids:
                sample = _load_graph(graph_dir, case_id)
                prediction = _forward(model, sample, normalisation, device)
                scale = torch.tensor(target_scales(sample["params"], normalisation.get("target_scaling", "none")), device=device, dtype=torch.float32)
                target = (sample["y"].to(device) / scale - y_mean) / y_std
                val_loss += float(criterion(prediction, target))
        val_loss /= max(len(val_ids), 1)
        history.append(
            {
                "epoch": epoch,
                "train_loss": epoch_loss / len(train_ids),
                "val_loss": val_loss,
            }
        )
        scheduler.step()
        improved = val_loss < best_val - 1e-6
        if improved:
            best_val = val_loss
            best_state = {
                key: value.detach().clone() for key, value in model.state_dict().items()
            }
            waited = 0
        else:
            waited += 1
        print(
            f"  epoch {epoch:3d} train {epoch_loss / len(train_ids):.5f} "
            f"val {val_loss:.5f}{' *' if improved else ''}",
            flush=True,
        )
        if waited >= config["patience"]:
            break
    if best_state is not None:
        model.load_state_dict(best_state)
    return model, {"best_val_loss": best_val, "epochs_run": len(history), "history": history}


def _evaluate(
    model,
    graph_dir: Path,
    case_ids: list[str],
    normalisation: dict,
    runs_root: Path,
    device: torch.device,
) -> dict:
    model.eval()
    rows = []
    with torch.no_grad():
        for case_id in case_ids:
            sample = _load_graph(graph_dir, case_id)
            prediction = _forward(model, sample, normalisation, device).cpu().numpy()
            prediction = decode_targets(prediction, sample["params"], normalisation)
            truth = sample["y"].numpy().astype(np.float64)
            params = sample["params"]

            displacement_pred = np.linalg.norm(prediction[:, :3], axis=1)
            displacement_fea = np.linalg.norm(truth[:, :3], axis=1)
            vm_pred = von_mises(prediction[:, 3:])
            vm_fea = von_mises(truth[:, 3:])
            coordinates = sample["coordinates"].numpy().astype(np.float64)
            roi_mask = shapes.roi_mask(coordinates, Plate.from_mapping(params))

            displacement_scale = max(displacement_fea.max(), 1e-9)
            stress_scale = max(vm_fea.max(), 1e-9)
            row = {
                "case_id": case_id,
                "shape": params.get("shape", "plate"),
                "split": sample["split"],
                "nodes": int(truth.shape[0]),
                "disp_error_median_pct": float(
                    100.0 * np.median(np.abs(displacement_pred - displacement_fea))
                    / displacement_scale
                ),
                "vm_error_median_pct": float(
                    100.0 * np.median(np.abs(vm_pred - vm_fea)) / stress_scale
                ),
                "vm_error_worst_pct": float(
                    100.0 * np.max(np.abs(vm_pred - vm_fea)) / stress_scale
                ),
                "true_max_displacement_mm": float(displacement_fea.max()),
                "pred_max_displacement_mm": float(displacement_pred.max()),
                "true_global_max_vm_mpa": float(vm_fea.max()),
                "pred_global_max_vm_mpa": float(vm_pred.max()),
                "true_roi_max_vm_mpa": (
                    float(vm_fea[roi_mask].max()) if roi_mask.any() else None
                ),
                "pred_roi_max_vm_mpa": (
                    float(vm_pred[roi_mask].max()) if roi_mask.any() else None
                ),
            }
            rows.append(row)
    result = _aggregate_evaluation(rows)
    result["by_shape"] = {
        shape: _aggregate_evaluation([row for row in rows if row["shape"] == shape])
        for shape in sorted({row["shape"] for row in rows})
    }
    return result


def _relative_error(predicted, truth) -> float:
    if truth is None or predicted is None or truth == 0:
        return float("nan")
    return 100.0 * abs(predicted - truth) / truth


def _aggregate_evaluation(rows: list[dict]) -> dict:
    if not rows:
        return {"cases": 0}

    def _mean(key):
        values = [row[key] for row in rows if row.get(key) is not None]
        return float(np.mean(values)) if values else None

    def _median(key):
        values = [row[key] for row in rows if row.get(key) is not None]
        return float(np.median(values)) if values else None

    def _percentile(key, percentile):
        values = [row[key] for row in rows if row.get(key) is not None]
        return float(np.percentile(values, percentile)) if values else None

    displacement_errors = [
        _relative_error(row["pred_max_displacement_mm"], row["true_max_displacement_mm"])
        for row in rows
    ]
    global_errors = [
        _relative_error(row["pred_global_max_vm_mpa"], row["true_global_max_vm_mpa"])
        for row in rows
    ]
    roi_errors = [
        _relative_error(row["pred_roi_max_vm_mpa"], row["true_roi_max_vm_mpa"])
        for row in rows
    ]

    def _stats(values):
        array = np.array([value for value in values if not math.isnan(value)])
        if array.size == 0:
            return {"mape": None, "worst": None}
        return {"mape": float(array.mean()), "worst": float(array.max())}

    return {
        "cases": len(rows),
        "nodes_mean": _mean("nodes"),
        "field_disp_error_median_pct": _median("disp_error_median_pct"),
        "field_vm_error_median_pct": _median("vm_error_median_pct"),
        "field_vm_error_p95_pct": _percentile("vm_error_worst_pct", 95),
        "max_displacement": _stats(displacement_errors),
        "global_max_vm": _stats(global_errors),
        "roi_max_vm": _stats(roi_errors),
        "rows": rows,
    }


def train_gnn(
    graph_dir: str | Path = "data/graphs_v1",
    runs_root: str | Path = "data/runs_graph",
    out_dir: str | Path = "models/gnn/v1",
    report_path: str | Path = "reports/v0.6_gnn_field_prediction.md",
    figure_dir: str | Path = "reports/figures/v0.6",
    seed: int = 42,
    epochs: int = 60,
    patience: int = 12,
    hidden: int = 80,
    layers: int = 8,
    learning_rate: float = 1e-3,
    grad_accumulation: int = 4,
    models: tuple[str, ...] = ("node_mlp", "meshgraphnet"),
    max_graphs_per_split: int | None = None,
    target_scaling: str = "none",
    validation_only: bool = False,
) -> dict:
    graph_dir = Path(graph_dir)
    runs_root = Path(runs_root)
    output = Path(out_dir)
    output.mkdir(parents=True, exist_ok=True)
    index = _load_index(graph_dir)
    splits: dict[str, list[str]] = {}
    for entry in index:
        splits.setdefault(entry["split"], []).append(entry["case_id"])
    if max_graphs_per_split:
        from itertools import zip_longest

        for split, ids in splits.items():
            groups: dict[str, list[str]] = {}
            for case_id in sorted(ids):
                shape = _load_graph(graph_dir, case_id)["params"].get("shape", "plate")
                groups.setdefault(shape, []).append(case_id)
            generator = np.random.default_rng(seed)
            for group in groups.values():
                generator.shuffle(group)
            balanced = [case_id for group in zip_longest(*groups.values()) for case_id in group if case_id is not None]
            splits[split] = balanced[:max_graphs_per_split]
    if not splits.get("train") or not splits.get("val"):
        raise ValueError("Graph dataset needs train and val splits")

    device = resolve_device()
    normalisation = _compute_normalisation(graph_dir, splits["train"], target_scaling)
    config = {
        "seed": seed,
        "epochs": epochs,
        "patience": patience,
        "hidden": hidden,
        "layers": layers,
        "learning_rate": learning_rate,
        "grad_accumulation": grad_accumulation,
        "target_scaling": target_scaling,
    }
    metadata: dict = {
        "schema_version": "0.8.0",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "graph_dataset": graph_dir.as_posix(),
        "graph_index_sha256": sha256(graph_dir / "index.json"),
        "node_features": NODE_FEATURES,
        "edge_features": EDGE_FEATURES,
        "targets": TARGET_COMPONENTS,
        "normalisation": normalisation,
        "config": config,
        "device": str(device),
        "split_counts": {split: len(ids) for split, ids in splits.items()},
        "selected_case_ids": splits,
        "selection_split": "val",
        "models": {},
        "tool_versions": tool_versions(),
        "git": git_info(),
    }

    for model_name in models:
        print(f"Training {model_name} on {len(splits['train'])} graphs...", flush=True)
        started = time.perf_counter()
        model, training = _train_one_model(
            graph_dir, model_name, splits, normalisation, config, device
        )
        runtime = time.perf_counter() - started
        model_path = output / f"{model_name}.pt"
        torch.save(
            {
                "state_dict": model.state_dict(),
                "model_name": model_name,
                "config": config,
                "node_features": NODE_FEATURES,
                "edge_features": EDGE_FEATURES,
            },
            model_path,
        )
        evaluation = {}
        for split in (("val",) if validation_only else EVALUATED_SPLITS):
            if splits.get(split):
                evaluation[split] = _evaluate(
                    model, graph_dir, sorted(splits[split]), normalisation,
                    runs_root, device,
                )
        metadata["models"][model_name] = {
            "path": model_path.as_posix(),
            "train_seconds": runtime,
            "epochs_run": training["epochs_run"],
            "best_val_loss": training["best_val_loss"],
            "history": training["history"],
            "evaluation": evaluation,
        }
        for split, result in evaluation.items():
            print(
                f"  {split}: disp MAPE {result['max_displacement']['mape']:.2f}% "
                f"global VM {result['global_max_vm']['mape']:.2f}% "
                f"ROI VM {_format_metric(result['roi_max_vm']['mape'])}%",
                flush=True,
            )

    best_model = _select_model(metadata["models"])
    metadata["best_model"] = best_model
    (output / "metadata.json").write_text(
        json.dumps(metadata, indent=2) + "\n", encoding="utf-8"
    )
    _parity_figures(metadata, Path(figure_dir))
    if not validation_only:
        _field_snapshot(
            graph_dir, runs_root, metadata, output,
            Path(figure_dir),
        )
    Path(report_path).parent.mkdir(parents=True, exist_ok=True)
    Path(report_path).write_text(_report(metadata), encoding="utf-8")
    return metadata


def _parity_figures(metadata: dict, figure_dir: Path) -> None:
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return
    figure_dir.mkdir(parents=True, exist_ok=True)
    best = metadata["best_model"]
    evaluation = metadata["models"][best]["evaluation"]
    quantities = [
        ("true_max_displacement_mm", "pred_max_displacement_mm", "max displacement (mm)"),
        ("true_global_max_vm_mpa", "pred_global_max_vm_mpa", "global max VM (MPa)"),
        ("true_roi_max_vm_mpa", "pred_roi_max_vm_mpa", "ROI max VM (MPa)"),
    ]
    figure, axes = plt.subplots(1, 3, figsize=(14, 4.2))
    for axis, (true_key, pred_key, label) in zip(axes, quantities):
        for split, colour in (("val", "tab:green"), ("test", "tab:blue"), ("challenge", "tab:red")):
            split_result = evaluation.get(split)
            rows = (
                [row for row in split_result["rows"] if row.get(true_key)]
                if split_result
                else []
            )
            if not rows:
                continue
            truth = [row[true_key] for row in rows]
            predicted = [row[pred_key] for row in rows]
            axis.scatter(truth, predicted, s=16, alpha=0.7, label=split, color=colour)
        axis.set_xlabel(f"FEA {label}")
        axis.set_ylabel("GNN field reduction")
        axis.set_title(label)
        axis.grid(True, alpha=0.3)
        axis.legend()
        if label.startswith("max disp"):
            axis.set_xscale("log")
            axis.set_yscale("log")
    figure.suptitle(f"Field-model scalar reductions ({best})")
    figure.tight_layout()
    figure.savefig(figure_dir / "gnn_scalar_parity.png", dpi=150)
    plt.close(figure)


def _field_snapshot(
    graph_dir: Path,
    runs_root: Path,
    metadata: dict,
    output: Path,
    figure_dir: Path,
) -> None:
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return
    best = metadata["best_model"]
    test_ids = sorted(
        entry["case_id"]
        for entry in _load_index(graph_dir)
        if entry["split"] == "test"
    )
    if not test_ids:
        return
    case_id = test_ids[0]
    sample = _load_graph(graph_dir, case_id)
    normalisation = metadata["normalisation"]
    device = resolve_device()
    model = build_model(
        best, len(NODE_FEATURES), len(EDGE_FEATURES),
        hidden=metadata["config"]["hidden"] if best == "meshgraphnet" else 128,
        layers=metadata["config"]["layers"] if best == "meshgraphnet" else 3,
    ).to(device)
    model.load_state_dict(
        torch.load(output / f"{best}.pt", map_location=device, weights_only=False)[
            "state_dict"
        ]
    )
    model.eval()
    with torch.no_grad():
        prediction = _forward(model, sample, normalisation, device).cpu().numpy()
    prediction = decode_targets(prediction, sample["params"], normalisation)
    truth = sample["y"].numpy().astype(np.float64)
    coordinates = sample["coordinates"].numpy().astype(np.float64)
    vm_true = von_mises(truth[:, 3:])
    vm_pred = von_mises(prediction[:, 3:])
    absolute_error = np.abs(vm_pred - vm_true)

    figure, axes = plt.subplots(1, 3, figsize=(16, 4.2))
    for axis, values, title in (
        (axes[0], vm_true, "FEA Von Mises (MPa)"),
        (axes[1], vm_pred, f"{best} prediction (MPa)"),
        (axes[2], absolute_error, "absolute error (MPa)"),
    ):
        scatter = axis.scatter(
            coordinates[:, 0], coordinates[:, 1], c=values, s=6, cmap="jet"
        )
        axis.set_title(f"{title}\n{case_id}")
        axis.set_xlabel("x (mm)")
        axis.set_ylabel("y (mm)")
        axis.set_aspect("equal")
        figure.colorbar(scatter, ax=axis, fraction=0.046)
    figure.tight_layout()
    figure_dir.mkdir(parents=True, exist_ok=True)
    figure.savefig(figure_dir / f"field_snapshot_{case_id}.png", dpi=150)
    plt.close(figure)


def _report(metadata: dict) -> str:
    lines = [
        "# GNN field prediction",
        "",
        f"- Graph dataset: `{metadata['graph_dataset']}` "
        f"(index sha `{metadata['graph_index_sha256'][:12]}...`), "
        f"splits {metadata['split_counts']}",
        f"- Device: `{metadata['device']}`, config {metadata['config']}",
        f"- Node features: {len(metadata['node_features'])}; targets: "
        f"{len(metadata['targets'])} components (displacement + stress tensor)",
        f"- Best model by validation global-VM MAPE: "
        f"**{metadata['best_model']}**",
        "",
        "Scalar values are obtained by reducing the predicted field exactly like",
        "the FEA labels are reduced (global max, and the shape's stress-riser",
        "ROI definition). Field errors are node-wise errors relative to the",
        "per-case peak value.",
        "",
    ]
    for model_name, model_data in metadata["models"].items():
        lines += [
            f"## {model_name}",
            "",
            f"Training: {model_data['train_seconds']:.1f} s, "
            f"{model_data['epochs_run']} epochs, best val loss "
            f"{model_data['best_val_loss']:.5f}.",
            "",
            "| split | cases | max disp MAPE % | global max VM MAPE % | "
            "ROI max VM MAPE % | field VM med. err % | field VM p95 err % |",
            "| --- | --- | --- | --- | --- | --- | --- |",
        ]
        for split, result in model_data["evaluation"].items():
            lines.append(
                f"| {split} | {result['cases']} | "
                f"{result['max_displacement']['mape']:.2f} | "
                f"{result['global_max_vm']['mape']:.2f} | "
                f"{_format_metric(result['roi_max_vm']['mape'])} | "
                f"{result['field_vm_error_median_pct']:.2f} | "
                f"{result['field_vm_error_p95_pct']:.2f} |"
            )
        lines.append("")
        lines += [
            "| split | shape | cases | displacement MAPE % | global VM MAPE % | ROI VM MAPE % |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
        for split, result in model_data["evaluation"].items():
            for shape, metrics in result.get("by_shape", {}).items():
                lines.append(
                    f"| {split} | {shape} | {metrics['cases']} | "
                    f"{_format_metric(metrics['max_displacement']['mape'])} | "
                    f"{_format_metric(metrics['global_max_vm']['mape'])} | "
                    f"{_format_metric(metrics['roi_max_vm']['mape'])} |"
                )
        lines.append("")
    lines += [
        "## Notes and limitations",
        "",
        "- The GNN is trained on the coarse `graph` mesh profile; labels are FEA",
        "  solutions of those same meshes (consistent field supervision).",
        "- Field accuracy is measured against the FEA peak per case; local values",
        "  near zero stress have large relative error but small absolute error.",
        "- The challenge split (corner-of-design-space) is never used for fitting",
        "  or model selection.",
        "- Candidate metrics require per-shape review before production use.",
        "",
    ]
    return "\n".join(lines)

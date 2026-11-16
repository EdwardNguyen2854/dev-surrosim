"""Train and compare scalar surrogate models on a versioned dataset.

All models learn ``log(target)``; metrics are reported after exponentiation
in the engineering units. Evaluation covers the random test split and the
held-out challenge split (corner-of-design-space extrapolation). A model
comparison report and parity figures are written for the portfolio.
"""

from pathlib import Path
from datetime import datetime, timezone
import json
import math
import time

import numpy as np

from ..provenance import git_info, sha256, tool_versions
from ..sampling import shape_param_bounds
from .baselines import euler_bernoulli, euler_bernoulli_net_section
from .data import FEATURE_COLUMNS, TARGETS, TARGET_UNITS, load_dataset, target_subset
from .models import MODEL_NAMES, make_model, model_suffix

EVALUATED_SPLITS = ("val", "test", "challenge")


def _empty_metrics() -> dict:
    return {
        "n": 0,
        "mae": None,
        "rmse": None,
        "mape_pct": None,
        "r2": None,
        "max_abs_error": None,
        "max_rel_error_pct": None,
    }


def _metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    if y_true.size == 0:
        return _empty_metrics()
    residual = y_pred - y_true
    absolute = np.abs(residual)
    relative = absolute / np.maximum(np.abs(y_true), 1e-12)
    ss_res = float(np.sum(residual**2))
    ss_tot = float(np.sum((y_true - y_true.mean()) ** 2))
    return {
        "n": int(y_true.size),
        "mae": float(absolute.mean()),
        "rmse": float(math.sqrt(np.mean(residual**2))),
        "mape_pct": float(100.0 * relative.mean()),
        "r2": float(1.0 - ss_res / ss_tot) if ss_tot > 0 else None,
        "max_abs_error": float(absolute.max()),
        "max_rel_error_pct": float(100.0 * relative.max()),
    }


def _latency_ms_per_1k(model, X: np.ndarray, repeats: int = 20) -> float:
    X = np.asarray(X, dtype=float)
    if len(X) == 0:
        return float("nan")
    times = []
    for _ in range(repeats):
        start = time.perf_counter()
        model.predict(X)
        times.append(time.perf_counter() - start)
    return float(np.median(times) / len(X) * 1000.0 * 1000.0)


def _selection_key(item) -> tuple:
    entry = item[1]
    worst = entry["val"]["max_rel_error_pct"] or 0.0
    blows_up = worst > 100.0
    val_rmse = entry["val"]["rmse"]
    return (blows_up, val_rmse if val_rmse is not None else float("inf"))


def _split_arrays(frame, target: str, split: str) -> tuple[np.ndarray, np.ndarray]:
    subset = frame[frame["split"] == split]
    return (
        subset[FEATURE_COLUMNS].to_numpy(dtype=float),
        subset[target].to_numpy(dtype=float),
    )


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def train_scalar_suite(
    dataset_path: str | Path,
    out_dir: str | Path,
    seed: int = 42,
    model_names: tuple[str, ...] = MODEL_NAMES,
    report_path: str | Path = "reports/v0.4_scalar_comparison.md",
    figure_dir: str | Path = "reports/figures/v0.4",
) -> dict:
    dataset_path = Path(dataset_path)
    output = Path(out_dir)
    figure_path = Path(figure_dir)
    frame = load_dataset(dataset_path)

    metadata: dict = {
        "schema_version": "0.4.0",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "seed": seed,
        "dataset": dataset_path.as_posix(),
        "dataset_sha256": sha256(dataset_path),
        "features": FEATURE_COLUMNS,
        "target_transform": "log",
        "targets": {},
        "baselines": {},
        "best_models": {},
        "tool_versions": tool_versions(),
        "git": git_info(),
    }
    metadata["fea_runtime_median_seconds"] = (
        float(frame["runtime_seconds"].median())
        if "runtime_seconds" in frame.columns
        else None
    )
    if "shape" in frame.columns:
        metadata["design_spaces"] = {
            kind: shape_param_bounds(kind)
            for kind in sorted(set(frame["shape"]))
        }
        metadata["shape_counts"] = {
            kind: int((frame["shape"] == kind).sum())
            for kind in sorted(set(frame["shape"]))
        }

    for target, label in TARGETS.items():
        subset = target_subset(frame, target)
        arrays = {
            split: _split_arrays(subset, target, split) for split in EVALUATED_SPLITS
        }
        X_train, y_train = _split_arrays(subset, target, "train")
        X_val, y_val = _split_arrays(subset, target, "val")
        y_train_log = np.log(y_train)
        y_val_log = np.log(y_val)

        target_results: dict = {"models": {}, "units": TARGET_UNITS[target]}
        for name in model_names:
            model = make_model(name, seed=seed)
            model.fit(X_train, y_train_log, X_val, y_val_log)
            metrics = {}
            for split in EVALUATED_SPLITS:
                X, y = arrays[split]
                if y.size == 0:
                    metrics[split] = _empty_metrics()
                    continue
                predicted = np.exp(model.predict(X))
                metrics[split] = _metrics(y, predicted)
                if split in ("test", "challenge") and "shape" in subset.columns:
                    split_rows = subset[subset["split"] == split]
                    by_shape = {}
                    for shape_name in sorted(set(split_rows["shape"])):
                        mask = (split_rows["shape"] == shape_name).to_numpy()
                        if mask.any():
                            by_shape[shape_name] = _metrics(
                                y[mask], predicted[mask]
                            )
                    metrics[split]["by_shape"] = by_shape
            path = output / "models" / f"{label}__{name}{model_suffix(name)}"
            model.save(path)
            entry = {
                "path": path.as_posix(),
                "latency_ms_per_1k": _latency_ms_per_1k(model, arrays["test"][0]),
                **metrics,
            }
            target_results["models"][name] = entry

        baseline_metrics = {}
        if target != "max_von_mises_roi_mpa":
            for baseline_name, baseline_fn in (
                ("euler_bernoulli", euler_bernoulli),
                ("euler_bernoulli_net_section", euler_bernoulli_net_section),
            ):
                predictions = baseline_fn(subset)
                if label not in predictions:
                    continue
                split_flags = subset["split"].to_numpy()
                baseline_metrics[baseline_name] = {
                    split: _metrics(
                        arrays[split][1], predictions[label][split_flags == split]
                    )
                    for split in ("test", "challenge")
                }
        target_results["baselines"] = baseline_metrics

        ranked = sorted(
            target_results["models"].items(), key=_selection_key
        )
        target_results["best_model"] = ranked[0][0]
        target_results["selection_rule"] = (
            "validation worst-case error <= 100% preferred, then lowest validation RMSE; "
            "test and challenge are not used for selection"
        )
        metadata["targets"][target] = target_results
        metadata["best_models"][target] = ranked[0][0]

        _parity_figure(
            subset, target, label, target_results, figure_path / f"parity_{label}.png"
        )

    _comparison_figure(metadata, figure_path / "model_comparison.png")
    _write_json(output / "metadata.json", metadata)
    Path(report_path).parent.mkdir(parents=True, exist_ok=True)
    Path(report_path).write_text(
        _comparison_markdown(metadata), encoding="utf-8"
    )
    return metadata


def _parity_figure(subset, target: str, label: str, results: dict, path: Path) -> None:
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return
    from .models import load_model

    best = results["best_model"]
    model = load_model(Path(results["models"][best]["path"]), best)
    figure, axes = plt.subplots(1, 3, figsize=(13, 4.2))
    for axis, split in zip(axes, ("val", "test", "challenge")):
        rows = subset[subset["split"] == split]
        if rows.empty:
            axis.axis("off")
            continue
        X = rows[FEATURE_COLUMNS].to_numpy(dtype=float)
        y = rows[target].to_numpy(dtype=float)
        predicted = np.exp(model.predict(X))
        axis.scatter(y, predicted, s=14, alpha=0.75)
        low = min(y.min(), predicted.min()) * 0.95
        high = max(y.max(), predicted.max()) * 1.05
        axis.plot([low, high], [low, high], "k--", linewidth=1)
        axis.set_xscale("log")
        axis.set_yscale("log")
        axis.set_xlim(low, high)
        axis.set_ylim(low, high)
        axis.set_title(f"{split} ({best})")
        axis.set_xlabel(f"FEA {label}")
        axis.set_ylabel("surrogate")
        axis.grid(True, alpha=0.3)
    figure.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(path, dpi=150)
    plt.close(figure)


def _comparison_figure(metadata: dict, path: Path) -> None:
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return
    labels = list(metadata["targets"].keys())
    figure, axes = plt.subplots(1, len(labels), figsize=(5 * len(labels), 4))
    if len(labels) == 1:
        axes = [axes]
    for axis, target in zip(axes, labels):
        models = metadata["targets"][target]["models"]
        names = list(models.keys())
        mape = [models[name]["test"]["mape_pct"] for name in names]
        worst = [models[name]["test"]["max_rel_error_pct"] for name in names]
        positions = np.arange(len(names))
        axis.bar(positions - 0.2, mape, width=0.4, label="MAPE (mean)")
        axis.bar(positions + 0.2, worst, width=0.4, label="worst-case rel.")
        axis.set_xticks(positions)
        axis.set_xticklabels(names, rotation=30, ha="right")
        axis.set_title(target)
        axis.set_ylabel("relative error (%)")
        axis.legend()
        axis.grid(True, axis="y", alpha=0.3)
    figure.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(path, dpi=150)
    plt.close(figure)


def _num(value, spec: str = ".4g") -> str:
    return "n/a" if value is None else format(value, spec)


def _comparison_markdown(metadata: dict) -> str:
    lines = [
        "# v0.4 scalar surrogate comparison",
        "",
        f"- Dataset: `{metadata['dataset']}` "
        f"(sha256 `{metadata['dataset_sha256'][:16]}...`)",
        f"- Models: {sorted(metadata['targets'][list(metadata['targets'])[0]]['models'])}",
        f"- Target transform: `log` (predictions exponentiated before metrics)",
        (
            f"- Median FEA solve time in dataset: "
            f"{metadata['fea_runtime_median_seconds']:.2f} s"
            if metadata["fea_runtime_median_seconds"] is not None
            else "- Median FEA solve time: not recorded in dataset"
        ),
        "",
        "Metrics below use the random **test** split and the held-out",
        "**challenge** split (corner-of-design-space cases excluded from training).",
        "",
    ]
    for target, results in metadata["targets"].items():
        units = results["units"]
        lines += [
            f"## {target}",
            "",
            f"Selected model: **{results['best_model']}** "
            f"({results['selection_rule']}).",
            "",
            "| model | test MAE | test RMSE | test MAPE % | test R² | test worst % "
            "| challenge MAPE % | challenge worst % | µs / 1k |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
        for name, entry in sorted(
            results["models"].items(),
            key=lambda item: (
                item[1]["test"]["mape_pct"]
                if item[1]["test"]["mape_pct"] is not None
                else float("inf")
            ),
        ):
            test = entry["test"]
            challenge = entry["challenge"]
            lines.append(
                f"| {name} | {_num(test['mae'])} | {_num(test['rmse'])} | "
                f"{_num(test['mape_pct'], '.2f')} | {_num(test['r2'], '.4f')} | "
                f"{_num(test['max_rel_error_pct'], '.1f')} | "
                f"{_num(challenge['mape_pct'], '.2f')} | "
                f"{_num(challenge['max_rel_error_pct'], '.1f')} | "
                f"{_num(entry['latency_ms_per_1k'] * 1000, '.0f')} |"
            )
        for baseline, splits in results["baselines"].items():
            test = splits["test"]
            challenge = splits["challenge"]
            lines.append(
                f"| {baseline} (baseline) | {_num(test['mae'])} | {_num(test['rmse'])} | "
                f"{_num(test['mape_pct'], '.2f')} | {_num(test['r2'], '.4f')} | "
                f"{_num(test['max_rel_error_pct'], '.1f')} | "
                f"{_num(challenge['mape_pct'], '.2f')} | "
                f"{_num(challenge['max_rel_error_pct'], '.1f')} | n/a |"
            )
        lines += [
            "",
            f"Units: {units}. Worst % is the maximum absolute relative error.",
            f"Parity figure: `reports/figures/v0.4/parity_"
            f"{TARGETS[target]}.png`",
            "",
        ]
    lines += [
        "## Notes",
        "",
        "- Baselines are Euler-Bernoulli prismatic-beam formulas; they ignore the",
        "  hole, so they are reference points, not labels.",
        "- The challenge split must never be used for model selection.",
        "- Inference latency is measured on the test feature matrix in Python;",
        "  compare with the median FEA solve time above (excluding meshing).",
        "",
    ]
    return "\n".join(lines)

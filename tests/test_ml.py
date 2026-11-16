import csv
import json
from pathlib import Path

import numpy as np
import pytest

from surrosim.ml.baselines import euler_bernoulli, euler_bernoulli_net_section
from surrosim.ml.data import FEATURE_COLUMNS, TARGETS, add_features, load_dataset
from surrosim.ml.models import EnsembleModel, TorchMLP, make_model, model_suffix
from surrosim.ml.train import train_scalar_suite


def _synthetic_dataset(path: Path, count: int = 48) -> Path:
    rng = np.random.default_rng(7)
    rows = []
    for index in range(count):
        length = 100 + 60 * rng.random()
        width = 30 + 30 * rng.random()
        thickness = 4 + 6 * rng.random()
        diameter = width * (0.2 + 0.25 * rng.random())
        hole_x = length * (0.35 + 0.3 * rng.random())
        force = 100 + 700 * rng.random()
        inertia = width * thickness**3 / 12.0
        displacement = force * length**3 / (3 * 210_000 * inertia)
        stress = force * length * thickness / (2 * inertia)
        split = (
            "train" if index < count - 12 else "val" if index < count - 6 else "test"
        )
        rows.append(
            {
                "case_id": f"case_{index:04d}",
                "split": split,
                "tag": "synthetic",
                "length_mm": length,
                "width_mm": width,
                "thickness_mm": thickness,
                "hole_diameter_mm": diameter,
                "hole_x_mm": hole_x,
                "force_n": force,
                "youngs_modulus_mpa": 210_000.0,
                "poisson_ratio": 0.3,
                "mesh_size_mm": 2.0,
                "max_displacement_mm": displacement * 0.97,
                "global_max_von_mises_mpa": stress * 1.1,
                "max_von_mises_roi_mpa": stress * 1.3,
            }
        )
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    return path


def test_load_dataset_adds_engineered_features(tmp_path):
    frame = load_dataset(_synthetic_dataset(tmp_path / "dataset.csv"))
    for column in FEATURE_COLUMNS:
        assert column in frame.columns
    assert np.allclose(
        frame["hole_width_ratio"], frame.hole_diameter_mm / frame.width_mm
    )
    assert frame["load_parameter"].gt(0).all()


def test_euler_bernoulli_matches_closed_form():
    import pandas as pd

    frame = pd.DataFrame(
        [
            {
                "width_mm": 20.0, "thickness_mm": 5.0, "length_mm": 100.0,
                "force_n": 100.0, "youngs_modulus_mpa": 200_000.0,
                "hole_diameter_mm": 0.0, "hole_x_mm": 50.0,
            }
        ]
    )
    result = euler_bernoulli(frame)
    assert result["displacement"][0] == pytest.approx(4 * 100 * 100**3 / (200_000 * 20 * 5**3))
    net = euler_bernoulli_net_section(frame)
    assert net["stress_global"][0] > 0


def test_mlp_trains_and_ensemble_roundtrip(tmp_path):
    pytest.importorskip("torch")
    rng = np.random.default_rng(3)
    X = rng.normal(size=(60, 6))
    y = X[:, 0] * 0.5 + np.log(2.0)
    mlp = TorchMLP(hidden=(16,), epochs=40, patience=10, seed=1)
    mlp.fit(X[:40], y[:40], X[40:], y[40:])
    predictions = mlp.predict(X)
    assert predictions.shape == (60,)
    path = tmp_path / "mlp.pt"
    mlp.save(path)
    reloaded = TorchMLP.load(path)
    assert np.allclose(reloaded.predict(X), predictions, atol=1e-5)

    ensemble = EnsembleModel([mlp, make_model("ridge", seed=1)])
    ensemble.fit(X[:40], y[:40])
    folder = tmp_path / "ensemble"
    ensemble.save(folder)
    loaded = EnsembleModel.load(folder)
    assert np.allclose(loaded.predict(X), ensemble.predict(X), atol=1e-5)


def test_train_suite_writes_registry_and_report(tmp_path):
    dataset = _synthetic_dataset(tmp_path / "dataset.csv")
    metadata = train_scalar_suite(
        dataset,
        tmp_path / "models",
        seed=5,
        model_names=("ridge",),
        report_path=tmp_path / "report.md",
        figure_dir=tmp_path / "figures",
    )
    assert set(metadata["targets"]) == set(TARGETS)
    for target, results in metadata["targets"].items():
        entry = results["models"]["ridge"]
        assert entry["test"]["n"] == 6
        assert entry["val"]["n"] == 6
        model_path = Path(entry["path"])
        assert model_path.exists()
        assert results["best_model"] == "ridge"
    assert (tmp_path / "models" / "metadata.json").exists()
    report = (tmp_path / "report.md").read_text(encoding="utf-8")
    assert "scalar surrogate comparison" in report
    manifest = json.loads((tmp_path / "models" / "metadata.json").read_text())
    assert manifest["dataset_sha256"]
    assert manifest["target_transform"] == "log"


def test_model_suffix_for_ensemble():
    assert model_suffix("ensemble") == ""
    assert model_suffix("mlp") == ".pt"
    assert model_suffix("xgboost") == ".joblib"
def test_scalar_selection_does_not_consult_held_out_metrics():
    from surrosim.ml.train import _selection_key

    better = ("better", {"val": {"max_rel_error_pct": 10, "rmse": 1},
                          "challenge": {"max_rel_error_pct": 1000}})
    worse = ("worse", {"val": {"max_rel_error_pct": 10, "rmse": 2},
                        "challenge": {"max_rel_error_pct": 1}})
    assert _selection_key(better) < _selection_key(worse)

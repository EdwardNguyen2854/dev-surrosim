"""Surrogate inference with explicit domain and confidence reporting.

The predictor never returns a bare number: every response carries the model
and dataset versions, a design-space bounds check, a distance-to-training
OOD score, ensemble member disagreement and an action recommendation
("trust", "caution" or "run_fea").

Model registries record their own feature list (``metadata["features"]``), so
v1 plate-only registries keep working unchanged while v2 registries add the
shape one-hot and shape-specific descriptors.
"""

from pathlib import Path
import json
import math
import time

import numpy as np
import pandas as pd

from .. import shapes
from ..ml.data import FEATURE_COLUMNS, TARGETS, add_features, load_dataset
from ..ml.models import load_model
from ..plate import Plate
from ..sampling import DesignSpace, shape_param_bounds

IN_DOMAIN = "in_domain"
CAUTION = "caution"
OUT_OF_DOMAIN = "out_of_domain"

TRUST = "trust"
RUN_FEA = "run_fea"


class ScalarPredictor:
    def __init__(
        self,
        registry_dir: str | Path,
        dataset_path: str | Path | None = None,
        neighbors: int = 5,
    ) -> None:
        self.registry_dir = Path(registry_dir)
        metadata_path = self.registry_dir / "metadata.json"
        if not metadata_path.exists():
            raise FileNotFoundError(f"No model registry metadata at {metadata_path}")
        self.metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        self.features = list(self.metadata.get("features") or FEATURE_COLUMNS)
        self.neighbors = neighbors
        self.models: dict[str, object] = {}
        for target, results in self.metadata["targets"].items():
            name = results["best_model"]
            self.models[target] = load_model(
                Path(results["models"][name]["path"]), name
            )
        self.dataset_path = Path(dataset_path) if dataset_path else Path(
            self.metadata["dataset"]
        )
        frame = load_dataset(self.dataset_path)
        self._prepare_domain(frame)
        self.design_spaces = self._prepare_design_spaces(frame)
        self.space = DesignSpace()

    @classmethod
    def load(cls, registry_dir="models/scalar/v1", dataset_path=None) -> "ScalarPredictor":
        return cls(registry_dir, dataset_path)

    def _prepare_domain(self, frame: pd.DataFrame) -> None:
        training = frame[frame["split"] == "train"]
        self.feature_mean = training[self.features].to_numpy(dtype=float).mean(axis=0)
        scale = training[self.features].to_numpy(dtype=float).std(axis=0)
        self.feature_std = np.where(scale > 1e-12, scale, 1.0)
        standardised = (
            training[self.features].to_numpy(dtype=float) - self.feature_mean
        ) / self.feature_std
        self.training_standardised = standardised
        distances = np.linalg.norm(
            standardised[:, None, :] - standardised[None, :, :], axis=2
        )
        np.fill_diagonal(distances, np.inf)
        kth = np.sort(distances, axis=1)[:, min(self.neighbors - 1, len(distances) - 1)]
        self.ood_reference = float(np.percentile(kth, 95))
        self.training_runtime = (
            float(frame["runtime_seconds"].median())
            if "runtime_seconds" in frame.columns
            else None
        )

    def _prepare_design_spaces(self, frame: pd.DataFrame) -> dict:
        recorded = self.metadata.get("design_spaces")
        if recorded:
            return {key: dict(value) for key, value in recorded.items()}
        kinds = sorted(set(frame.get("shape", pd.Series(["plate"]))))
        return {kind: shape_param_bounds(kind) for kind in kinds}

    def design_space_bounds(self) -> dict:
        """Plate-family bounds (v1-compatible view used by older clients)."""
        space = self.space
        return {
            "length_mm": [space.length_mm.low, space.length_mm.high],
            "width_mm": [space.width_mm.low, space.width_mm.high],
            "thickness_mm": [space.thickness_mm.low, space.thickness_mm.high],
            "force_n": [space.force_n.low, space.force_n.high],
            "hole_diameter_mm": [
                0.0,
                space.width_mm.high * space.diameter_width_fraction.high,
            ],
            "hole_position_fraction": [
                space.hole_x_length_fraction.low,
                space.hole_x_length_fraction.high,
            ],
        }

    def shape_design_spaces(self) -> dict:
        return self.design_spaces

    def _bounds_violations(self, design: Plate) -> list[str]:
        violations: list[str] = []
        try:
            design.validate()
        except ValueError as exc:
            violations.append(str(exc))
        bounds = self.design_spaces.get(design.shape)
        if not bounds:
            return violations
        for name, (low, high) in bounds.items():
            if name not in Plate.field_names():
                continue
            value = float(getattr(design, name))
            if not low - 1e-9 <= value <= high + 1e-9:
                violations.append(
                    f"{name}={value:.4g} outside [{low:.4g}, {high:.4g}]"
                )
        return violations

    def _feature_row(self, design: Plate) -> pd.DataFrame:
        values = design.as_dict()
        if not shapes.shape_holes(design):
            values["hole_x_mm"] = design.length_mm / 2.0
        frame = pd.DataFrame([values])
        return add_features(frame)

    def _ood_ratio(self, features: pd.DataFrame) -> float:
        row = features[self.features].to_numpy(dtype=float)
        standardised = (row - self.feature_mean) / self.feature_std
        distances = np.linalg.norm(self.training_standardised - standardised, axis=1)
        kth = np.sort(distances)[min(self.neighbors - 1, len(distances) - 1)]
        return float(kth / max(self.ood_reference, 1e-12))

    def predict(self, design: dict) -> dict:
        start = time.perf_counter()
        plate = Plate.from_mapping(design)
        features = self._feature_row(plate)
        X = features[self.features].to_numpy(dtype=float)
        has_roi = bool(shapes.shape_holes(plate)) or shapes.fillet_radius(plate) > 0
        predictions: dict[str, dict] = {}
        spreads = []
        for target, model in self.models.items():
            if target == "max_von_mises_roi_mpa" and not has_roi:
                predictions[target] = {
                    "value": None,
                    "reason": "ROI stress is defined only for stress-riser designs",
                }
                continue
            log_prediction = float(np.asarray(model.predict(X)).reshape(-1)[0])
            value = float(math.exp(log_prediction))
            entry = {"value": value}
            if hasattr(model, "member_predictions"):
                member_logs = np.asarray(model.member_predictions(X)).reshape(-1)
                spread = (math.exp(float(np.std(member_logs))) - 1.0) * 100.0
                entry["member_spread_pct"] = spread
                spreads.append(spread)
            predictions[target] = entry

        violations = self._bounds_violations(plate)
        ood_ratio = self._ood_ratio(features)
        if violations or ood_ratio > 2.5:
            ood_level = OUT_OF_DOMAIN
        elif ood_ratio > 1.5:
            ood_level = CAUTION
        else:
            ood_level = IN_DOMAIN

        max_spread = max(spreads) if spreads else 0.0
        reasons = list(violations)
        if ood_ratio > 2.5:
            reasons.append(f"design is far from training data (distance ratio {ood_ratio:.2f})")
        elif ood_ratio > 1.5:
            reasons.append(f"design is outside the dense training region (ratio {ood_ratio:.2f})")
        if max_spread > 15.0:
            reasons.append(f"ensemble members disagree by up to {max_spread:.1f}%")

        if violations or ood_ratio > 2.5:
            recommendation = RUN_FEA
        elif ood_ratio > 1.5 or max_spread > 15.0:
            recommendation = CAUTION
        else:
            recommendation = TRUST

        latency_ms = (time.perf_counter() - start) * 1000.0
        try:
            nominal = plate.nominal_baseline()
        except ValueError:
            nominal = None
        return {
            "inputs": plate.as_dict(),
            "predictions": predictions,
            "nominal_beam_baseline": nominal,
            "confidence": {
                "bounds_ok": not violations,
                "bound_violations": violations,
                "ood_ratio": ood_ratio,
                "ood_level": ood_level,
                "max_member_spread_pct": max_spread,
                "recommendation": recommendation,
                "reasons": reasons,
            },
            "model": {
                "registry": self.registry_dir.as_posix(),
                "dataset_sha256": self.metadata["dataset_sha256"],
                "dataset": self.metadata["dataset"],
                "created_utc": self.metadata["created_utc"],
                "targets": self.metadata.get("best_models", {}),
                "git_commit": (self.metadata.get("git") or {}).get("commit"),
            },
            "fea_reference": {
                "median_solve_seconds": self.training_runtime,
            },
            "latency_ms": latency_ms,
        }

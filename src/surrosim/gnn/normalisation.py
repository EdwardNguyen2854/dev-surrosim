"""Invertible target scaling using only geometry, material and load inputs."""

import numpy as np

from ..plate import Plate


def target_scales(params: dict, mode: str = "none") -> np.ndarray:
    if mode == "none":
        return np.ones(9, dtype=np.float64)
    if mode != "nominal_v1":
        raise ValueError(f"Unknown field target scaling: {mode}")
    reference = Plate.from_mapping(params).nominal_baseline()
    displacement = max(abs(reference["nominal_tip_displacement_mm"]), 1e-12)
    stress = max(abs(reference["nominal_root_bending_stress_mpa"]), 1e-12)
    return np.array([displacement] * 3 + [stress] * 6)


def decode_targets(prediction: np.ndarray, params: dict, normalisation: dict) -> np.ndarray:
    dimensionless = prediction * np.array(normalisation["y_std"]) + np.array(normalisation["y_mean"])
    return dimensionless * target_scales(params, normalisation.get("target_scaling", "none"))

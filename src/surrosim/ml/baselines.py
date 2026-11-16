"""Transparent engineering baselines used as independent references.

These are Euler-Bernoulli prismatic-beam formulas applied to the perforated
plate. They ignore the hole and therefore must not be treated as labels —
their purpose is to show how much the learned models add over classical
closed-form engineering estimates.
"""

import numpy as np
import pandas as pd


def euler_bernoulli(frame: pd.DataFrame) -> dict[str, np.ndarray]:
    inertia = frame.width_mm * frame.thickness_mm**3 / 12.0
    displacement = (
        frame.force_n * frame.length_mm**3
        / (3.0 * frame.youngs_modulus_mpa * inertia)
    )
    root_stress = (
        frame.force_n * frame.length_mm * (frame.thickness_mm / 2.0) / inertia
    )
    return {
        "displacement": displacement.to_numpy(dtype=float),
        "stress_global": root_stress.to_numpy(dtype=float),
    }


def euler_bernoulli_net_section(frame: pd.DataFrame) -> dict[str, np.ndarray]:
    """Root bending stress using the net section at the hole."""
    inertia = frame.width_mm * frame.thickness_mm**3 / 12.0
    hole_cut = frame.hole_diameter_mm * frame.thickness_mm**3 / 12.0
    net = np.clip(inertia - hole_cut, 1e-12, None)
    moment_at_hole = frame.force_n * (frame.length_mm - frame.hole_x_mm)
    stress = moment_at_hole * (frame.thickness_mm / 2.0) / net
    return {"stress_global": stress.to_numpy(dtype=float)}

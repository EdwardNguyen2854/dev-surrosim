"""Deterministic Latin-hypercube design sampler; NO simulation results."""

import csv
import random
from pathlib import Path

from .plate import Plate


def sample_designs(count: int, seed: int = 42) -> list[Plate]:
    """Sample a feasible plate family with six independent input factors.

    Hole diameter and location are sampled as *fractions* of width/length,
    keeping samples valid while providing varied physical dimensions.
    """
    if count < 1:
        raise ValueError("count must be >= 1")
    rng = random.Random(seed)
    columns = []
    for _ in range(6):
        column = [(i + rng.random()) / count for i in range(count)]
        rng.shuffle(column)
        columns.append(column)
    designs = []
    for u in zip(*columns):
        length = 100 + 60 * u[0]
        width = 30 + 30 * u[1]
        thickness = 4 + 6 * u[2]
        diameter = width * (0.20 + 0.25 * u[3])
        hole_x = length * (0.35 + 0.30 * u[4])
        force = 100 + 700 * u[5]
        plate = Plate(
            length_mm=length, width_mm=width, thickness_mm=thickness,
            hole_diameter_mm=diameter, hole_x_mm=hole_x, force_n=force,
            mesh_size_mm=min(2.0, thickness / 3),
        )
        plate.validate()
        designs.append(plate)
    return designs


def export_designs(path: str | Path, count: int, seed: int = 42) -> int:
    """Write *inputs only*. Baseline and FEA outputs must not be conflated."""
    designs = sample_designs(count, seed)
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["case_id", *designs[0].as_dict().keys()]
    with destination.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for idx, design in enumerate(designs, start=1):
            writer.writerow({"case_id": f"plate_{idx:04d}", **design.as_dict()})
    return len(designs)

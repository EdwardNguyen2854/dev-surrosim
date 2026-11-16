"""Dataset loading, feature engineering and target definitions.

Features are deliberately physical and dimensionless where possible so the
models stay interpretable and the same feature code serves the scalar
surrogates, the application and the field models.

The v2 feature vector adds the geometry-family one-hot block and the
shape-specific dimensionless descriptors produced by :mod:`surrosim.shapes`.
Rows from the v1 dataset (no ``shape`` column, missing v2 parameters) are
backfilled with shape defaults so old artifacts keep loading.
"""

from pathlib import Path

import pandas as pd

from .. import shapes
from ..plate import Plate

INPUT_FEATURES = [
    "length_mm",
    "width_mm",
    "thickness_mm",
    "hole_diameter_mm",
    "hole_x_mm",
    "hole2_diameter_mm",
    "hole2_x_mm",
    "tip_width_mm",
    "step_x_mm",
    "step_thickness_mm",
    "fillet_radius_mm",
    "flange_width_mm",
    "beam_depth_mm",
    "flange_thickness_mm",
    "web_thickness_mm",
    "height_mm",
    "force_n",
]
SHAPE_FEATURES = [f"shape_is_{kind}" for kind in shapes.SHAPE_KINDS]
ENGINEERED_FEATURES = [
    "hole_width_ratio",
    "hole_position_ratio",
    "hole_thickness_ratio",
    "hole2_width_ratio",
    "hole2_position_ratio",
    "taper_ratio",
    "step_thickness_ratio",
    "step_position_ratio",
    "fillet_radius_ratio",
    "beam_depth_ratio",
    "flange_thickness_ratio",
    "web_thickness_ratio",
    "bracket_height_ratio",
    "slenderness",
    "width_thickness_ratio",
    "load_parameter",
    "mass_parameter",
]
FEATURE_COLUMNS = INPUT_FEATURES + ENGINEERED_FEATURES + SHAPE_FEATURES

TARGETS = {
    "max_displacement_mm": "displacement",
    "global_max_von_mises_mpa": "stress_global",
    "max_von_mises_roi_mpa": "stress_roi",
}
TARGET_UNITS = {
    "max_displacement_mm": "mm",
    "global_max_von_mises_mpa": "MPa",
    "max_von_mises_roi_mpa": "MPa",
}
SPLITS = ("train", "val", "test", "challenge")


def add_features(frame: pd.DataFrame) -> pd.DataFrame:
    data = frame.copy()
    source = data.copy()
    if "shape" not in source.columns:
        source["shape"] = shapes.PLATE
    recomputed = [
        column
        for column in INPUT_FEATURES + ENGINEERED_FEATURES + SHAPE_FEATURES + ["shape"]
        if column in data.columns
    ]
    data = data.drop(columns=recomputed)
    records = []
    for raw in source.to_dict(orient="records"):
        design = Plate.from_mapping(raw)
        record = design.as_dict()
        record.update(shapes.engineered_features(design))
        for kind in shapes.SHAPE_KINDS:
            record[f"shape_is_{kind}"] = 1.0 if design.shape == kind else 0.0
        records.append(record)
    features = pd.DataFrame.from_records(
        [
            {
                name: record[name]
                for name in INPUT_FEATURES
                + ENGINEERED_FEATURES
                + SHAPE_FEATURES
                + ["shape"]
            }
            for record in records
        ],
        index=data.index,
    )
    return pd.concat([data, features], axis=1)


def load_dataset(path: str | Path) -> pd.DataFrame:
    frame = pd.read_csv(path)
    required = {"case_id", "split", *TARGETS}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Dataset is missing required columns: {sorted(missing)}")
    unknown = set(frame["split"]) - set(SPLITS)
    if unknown:
        raise ValueError(f"Dataset contains unknown splits: {sorted(unknown)}")
    return add_features(frame)


def target_subset(frame: pd.DataFrame, target: str) -> pd.DataFrame:
    """Rows where the target is defined (ROI stress is null for no-hole cases)."""
    return frame[frame[target].notna()].reset_index(drop=True)


def split_xy(
    frame: pd.DataFrame, target: str, split: str
) -> tuple[pd.DataFrame, pd.Series]:
    subset = frame[frame["split"] == split]
    return subset[FEATURE_COLUMNS], subset[target]

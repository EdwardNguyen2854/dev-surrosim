import csv
from pathlib import Path

import numpy as np
import pytest

from surrosim import shapes
from surrosim.plate import Plate
from surrosim.sampling import build_design_table_v2, shape_param_bounds, shape_space

ROOT = Path(__file__).resolve().parents[1]


def _representative(kind: str) -> Plate:
    if kind == shapes.PLATE:
        return Plate()
    space = shape_space(kind)
    return space.design_from_unit(tuple(0.5 for _ in range(space.dimensions())))


def test_representative_designs_validate_for_every_shape():
    for kind in shapes.SHAPE_KINDS:
        design = _representative(kind)
        design.validate()
        assert design.mass_g() > 0


INVALID = [
    (shapes.PLATE, {"hole_diameter_mm": 41}),
    (shapes.PLATE, {"hole_x_mm": 2}),
    (shapes.MULTI_HOLE, {"hole_diameter_mm": 15, "hole_x_mm": 45,
                         "hole2_diameter_mm": 15, "hole2_x_mm": 52}),
    (shapes.TAPER, {"tip_width_mm": 50, "width_mm": 40}),
    (shapes.TAPER, {"width_mm": 40, "tip_width_mm": 10,
                    "hole_diameter_mm": 30, "hole_x_mm": 100}),
    (shapes.STEPPED, {"thickness_mm": 8, "step_thickness_mm": 8}),
    (shapes.STEPPED, {"thickness_mm": 8, "step_thickness_mm": 4,
                      "fillet_radius_mm": 5}),
    (shapes.I_BEAM, {"flange_thickness_mm": 25, "beam_depth_mm": 40}),
    (shapes.I_BEAM, {"web_thickness_mm": 60, "flange_width_mm": 40}),
    (shapes.L_BRACKET, {"height_mm": 4, "thickness_mm": 5}),
    (shapes.L_BRACKET, {"fillet_radius_mm": 0.0}),
]


@pytest.mark.parametrize("kind,changes", INVALID)
def test_invalid_designs_rejected(kind, changes):
    base = _representative(kind).as_dict()
    design = Plate(**{**base, **changes})
    with pytest.raises(ValueError):
        design.validate()


def test_plate_mass_matches_closed_form():
    design = Plate()
    expected = (
        design.length_mm * design.width_mm * design.thickness_mm
        - np.pi * (design.hole_diameter_mm / 2) ** 2 * design.thickness_mm
    )
    assert shapes.mass_mm3(design) == pytest.approx(expected)


def test_l_bracket_mass_matches_profile_area():
    design = Plate(
        shape=shapes.L_BRACKET, length_mm=80, height_mm=90, width_mm=30,
        thickness_mm=8, fillet_radius_mm=2,
    )
    area = 80 * 8 + 8 * (90 - 4) + 2**2 * (1 - np.pi / 4)
    assert shapes.mass_mm3(design) == pytest.approx(area * 30)


def test_engineered_features_are_shape_conditioned():
    plate = Plate()
    taper = Plate(shape=shapes.TAPER, tip_width_mm=20)
    beam = Plate(
        shape=shapes.I_BEAM, beam_depth_mm=50, flange_width_mm=40,
        flange_thickness_mm=8, web_thickness_mm=6, fillet_radius_mm=2,
    )
    plate_features = shapes.engineered_features(plate)
    taper_features = shapes.engineered_features(taper)
    beam_features = shapes.engineered_features(beam)
    assert taper_features["taper_ratio"] == pytest.approx(0.5)
    assert plate_features["taper_ratio"] == 0.0
    assert beam_features["beam_depth_ratio"] > 0
    assert beam_features["hole_width_ratio"] == 0.0
    assert plate_features["hole_width_ratio"] == pytest.approx(12 / 40)


def test_v2_design_table_has_ids_splits_and_valid_designs(tmp_path):
    destination = tmp_path / "designs_v2.csv"
    from surrosim.sampling import export_designs_v2

    total = export_designs_v2(
        destination, per_shape=12, challenge_per_shape=3,
        plate_count=10, plate_challenge=2, seed=5,
    )
    rows = list(csv.DictReader(destination.open(encoding="utf-8")))
    assert total == len(rows) == 10 + 2 + 12 + 5 * (12 + 3 + 5)
    by_shape: dict[str, int] = {}
    for row in rows:
        by_shape[row["shape"]] = by_shape.get(row["shape"], 0) + 1
        design = Plate.from_mapping(row)
        design.validate()
    assert set(by_shape) == set(shapes.SHAPE_KINDS)
    splits = {row["split"] for row in rows if row["tag"] == "main"}
    assert splits == {"train", "val", "test"}
    assert any(row["split"] == "challenge" for row in rows)


def test_shape_param_bounds_are_ordered_and_wide():
    for kind in shapes.SHAPE_KINDS:
        bounds = shape_param_bounds(kind, samples=64)
        assert bounds, kind
        for low, high in bounds.values():
            assert low < high


def test_case_id_is_filesystem_safe():
    for kind in shapes.SHAPE_KINDS:
        identifier = shapes.case_id("verify", _representative(kind))
        assert identifier.startswith("verify_")
        assert all(character.isalnum() or character in "_-=." for character in identifier)
        assert "/" not in identifier and "\\" not in identifier


def test_dataset_v2_merges_base_rows(tmp_path):
    base = tmp_path / "base.csv"
    base_row = {
        "case_id": "plate_0001", "split": "train", "tag": "main",
        "length_mm": 120.0, "width_mm": 40.0, "thickness_mm": 6.0,
        "hole_diameter_mm": 12.0, "hole_x_mm": 60.0,
        "force_n": 500.0, "youngs_modulus_mpa": 210_000.0,
        "poisson_ratio": 0.3, "mesh_size_mm": 3.0,
        "max_displacement_mm": 1.9, "global_max_von_mises_mpa": 250.0,
        "max_von_mises_roi_mpa": 260.0,
    }
    with base.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(base_row))
        writer.writeheader()
        writer.writerow(base_row)

    designs = tmp_path / "designs.csv"
    with designs.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(base_row))
        writer.writeheader()
        writer.writerow(base_row)

    from surrosim.dataset.build import build_dataset

    manifest = build_dataset(
        designs, tmp_path / "runs", tmp_path / "dataset", base_datasets=[base]
    )
    assert manifest["schema_version"] == "2.0.0"
    assert manifest["cases_in_dataset"] == 1
    assert manifest["cases_failed"] == 0
    assert manifest["cases_from_base"] == 1
    assert manifest["shape_counts"] == {"plate": 1}
    row = next(
        csv.DictReader((tmp_path / "dataset" / "dataset.csv").open(encoding="utf-8"))
    )
    assert row["shape"] == "plate"
    assert row["max_displacement_mm"] == "1.9"


def test_gnn_features_encode_shape():
    from surrosim.gnn.features import NODE_FEATURES, build_geometry_tensors
    from surrosim.simulation.msh2 import GmshMesh, MeshElement

    mesh = GmshMesh(
        nodes={1: (0.0, 0.0, 0.0), 2: (1.0, 0.0, 0.0),
               3: (0.0, 1.0, 0.0), 4: (0.0, 0.0, 1.0)},
        physical_names={},
        elements=(MeshElement(element_id=1, element_type=4,
                              physical_tag=1, nodes=(1, 2, 3, 4)),),
    )
    row = _representative(shapes.I_BEAM).as_dict()
    tensors = build_geometry_tensors(row, mesh)
    one_hot = tensors["x"][0, NODE_FEATURES.index("shape_is_i_beam")].item()
    assert one_hot == pytest.approx(1.0)
    assert tensors["x"].shape[1] == len(NODE_FEATURES)

import csv
from dataclasses import replace
import json
from pathlib import Path

import numpy as np
import pytest

from surrosim.dataset.batch import load_designs
from surrosim.dataset.build import build_dataset
from surrosim.dataset.cases import fields_csv_to_npz
from surrosim.sampling import export_designs
from surrosim.mesh_policy import GRAPH_POLICY, PRODUCTION_POLICY

FIELDS_CSV = """node_id,x_mm,y_mm,z_mm,ux_mm,uy_mm,uz_mm,displacement_mm,sxx_mpa,syy_mpa,szz_mpa,sxy_mpa,syz_mpa,szx_mpa,von_mises_mpa
1,0.0,0.0,0.0,0.0,0.0,0.0,0.0,10.0,0.0,0.0,0.0,0.0,0.0,10.0
2,1.0,0.0,0.0,0.0,0.0,0.5,0.5,20.0,0.0,0.0,0.0,0.0,0.0,20.0
"""


def test_mesh_profiles_produce_valid_sizes_for_all_v2_designs():
    designs = Path(__file__).resolve().parents[1] / "data/designs_v2.csv"
    for row in load_designs(designs):
        for policy in (PRODUCTION_POLICY, GRAPH_POLICY):
            replace(row.plate, mesh_size_mm=policy.global_size_mm(row.plate)).validate()


def test_fields_csv_to_npz_roundtrip(tmp_path):
    csv_path = tmp_path / "fields.csv"
    csv_path.write_text(FIELDS_CSV, encoding="utf-8")
    npz_path = tmp_path / "fields.npz"
    assert fields_csv_to_npz(csv_path, npz_path) == 2
    with np.load(npz_path) as data:
        assert data["node_id"].tolist() == [1, 2]
        assert data["x_mm"].dtype == np.float32
        assert data["von_mises_mpa"].tolist() == pytest.approx([10.0, 20.0])


def _write_designs(tmp_path: Path) -> Path:
    path = tmp_path / "designs.csv"
    export_designs(path, count=40, seed=11, challenge_count=0)
    return path


def test_load_designs_builds_valid_plates(tmp_path):
    rows = load_designs(_write_designs(tmp_path))
    assert len(rows) == 52
    assert all(row.plate.validate() is None for row in rows)
    assert {row.split for row in rows} >= {"train", "val", "test"}


def _fake_success(case_dir: Path, plate_row: dict) -> None:
    case_dir.mkdir(parents=True, exist_ok=True)
    (case_dir / "fields.npz").write_bytes(b"fake")
    summary = {
        "status": "SUCCESS",
        "geometry": {
            "mesh_nodes": 1234,
            "mesh_volume_elements": 5678,
            "hole_refinement_mm": 1.2,
        },
        "deck": {
            "element_type": "C3D10",
            "element_order": 2,
            "total_applied_force_n": -float(plate_row["force_n"]),
        },
        "solver": {
            "runtime_seconds": 3.5,
            "stdout": "CalculiX Version 2.23, Copyright(C) 1998-2025",
        },
        "results": {
            "max_displacement_mm": 0.5,
            "global_max_von_mises_mpa": 120.0,
            "max_von_mises_roi_mpa": 90.0,
        },
    }
    (case_dir / "run.json").write_text(json.dumps(summary), encoding="utf-8")


def test_build_dataset_gates_and_reports(tmp_path):
    designs = _write_designs(tmp_path)
    rows = list(csv.DictReader(designs.open(encoding="utf-8")))
    runs = tmp_path / "runs"
    _fake_success(runs / rows[0]["case_id"], rows[0])

    failed_dir = runs / rows[1]["case_id"]
    failed_dir.mkdir(parents=True)
    (failed_dir / "run.json").write_text(
        json.dumps({"status": "SOLVER_FAILED"}), encoding="utf-8"
    )

    manifest = build_dataset(designs, runs, tmp_path / "dataset")
    assert manifest["cases_in_dataset"] == 1
    assert manifest["cases_failed"] == 51
    dataset_rows = list(
        csv.DictReader((tmp_path / "dataset" / "dataset.csv").open(encoding="utf-8"))
    )
    assert dataset_rows[0]["max_displacement_mm"] == "0.5"
    assert dataset_rows[0]["solver_version"] == "2.23"
    failures = list(
        csv.DictReader((tmp_path / "dataset" / "failures.csv").open(encoding="utf-8"))
    )
    failure_map = {row["case_id"]: row["failure"] for row in failures}
    assert failure_map[rows[1]["case_id"]] == "SOLVER_FAILED"
    assert failure_map[rows[2]["case_id"]] == "MISSING_RUN_JSON"
    assert (tmp_path / "dataset" / "manifest.json").exists()
    card = (tmp_path / "dataset" / "dataset_card.md").read_text(encoding="utf-8")
    assert "simulation dataset card" in card


def test_build_dataset_rejects_force_mismatch(tmp_path):
    designs = _write_designs(tmp_path)
    rows = list(csv.DictReader(designs.open(encoding="utf-8")))
    runs = tmp_path / "runs"
    case_dir = runs / rows[0]["case_id"]
    _fake_success(case_dir, rows[0])
    summary = json.loads((case_dir / "run.json").read_text(encoding="utf-8"))
    summary["deck"]["total_applied_force_n"] = 1.0
    (case_dir / "run.json").write_text(json.dumps(summary), encoding="utf-8")
    manifest = build_dataset(designs, runs, tmp_path / "dataset")
    assert manifest["cases_in_dataset"] == 0
    failures = list(
        csv.DictReader((tmp_path / "dataset" / "failures.csv").open(encoding="utf-8"))
    )
    assert failures[0]["failure"] == "FORCE_GATE"

"""Single-case execution plus artifact compaction for the dataset factory."""

from dataclasses import replace
from pathlib import Path
import csv
import json

import numpy as np

from ..mesh_policy import DEFAULT_POLICY, MeshPolicy
from ..plate import Plate
from ..simulation.pipeline import simulate_case

PRUNED_SUFFIXES = (".frd", ".dat", ".sta", ".cvg")


def fields_csv_to_npz(csv_path: str | Path, npz_path: str | Path) -> int:
    """Convert the verbose nodal CSV into a compact float32 archive."""
    source = Path(csv_path)
    destination = Path(npz_path)
    with source.open(encoding="utf-8") as handle:
        reader = csv.reader(handle)
        header = next(reader)
        rows = list(reader)
    if not rows:
        raise ValueError(f"fields CSV has no data rows: {source}")
    data = np.array(rows, dtype=np.float64)
    index = {name: position for position, name in enumerate(header)}
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(destination.name + ".tmp.npz")
    np.savez_compressed(
        temporary,
        node_id=data[:, index["node_id"]].astype(np.int64),
        x_mm=data[:, index["x_mm"]].astype(np.float32),
        y_mm=data[:, index["y_mm"]].astype(np.float32),
        z_mm=data[:, index["z_mm"]].astype(np.float32),
        ux_mm=data[:, index["ux_mm"]].astype(np.float32),
        uy_mm=data[:, index["uy_mm"]].astype(np.float32),
        uz_mm=data[:, index["uz_mm"]].astype(np.float32),
        displacement_mm=data[:, index["displacement_mm"]].astype(np.float32),
        sxx_mpa=data[:, index["sxx_mpa"]].astype(np.float32),
        syy_mpa=data[:, index["syy_mpa"]].astype(np.float32),
        szz_mpa=data[:, index["szz_mpa"]].astype(np.float32),
        sxy_mpa=data[:, index["sxy_mpa"]].astype(np.float32),
        syz_mpa=data[:, index["syz_mpa"]].astype(np.float32),
        szx_mpa=data[:, index["szx_mpa"]].astype(np.float32),
        von_mises_mpa=data[:, index["von_mises_mpa"]].astype(np.float32),
    )
    temporary.replace(destination)
    return len(rows)


def run_case(
    case_id: str,
    plate: Plate,
    runs_root: str | Path,
    ccx_executable: str = "ccx",
    timeout_seconds: float = 600.0,
    element_order: int | None = None,
    hole_refinement_mm: float | None = None,
    force: bool = False,
    policy: MeshPolicy | None = None,
) -> dict:
    """Run one FEA case, compact its fields and prune bulky solver artifacts.

    Existing successful cases are reused unless ``force`` is set, which makes
    long dataset generations resumable after an interruption. When a
    ``policy`` is given the case is meshed with that policy regardless of the
    mesh size stored in the design row.
    """
    case_dir = Path(runs_root) / case_id
    run_json = case_dir / "run.json"
    fields_npz = case_dir / "fields.npz"
    if not force and run_json.exists() and fields_npz.exists():
        cached = json.loads(run_json.read_text(encoding="utf-8"))
        if cached.get("status") == "SUCCESS":
            return {
                "case_id": case_id,
                "status": "CACHED",
                "runtime_seconds": 0.0,
                "case_dir": str(case_dir),
            }

    policy = policy or DEFAULT_POLICY
    plate = replace(plate, mesh_size_mm=policy.global_size_mm(plate))
    order = policy.element_order if element_order is None else element_order
    refinement = (
        policy.hole_refinement_mm(plate)
        if hole_refinement_mm is None
        else hole_refinement_mm
    )
    summary = simulate_case(
        plate, case_dir, ccx_executable, timeout_seconds,
        element_order=order, hole_refinement_mm=refinement, quiet_mesh=True,
    )
    result = {
        "case_id": case_id,
        "status": summary["status"],
        "runtime_seconds": (summary.get("solver") or {}).get("runtime_seconds"),
        "case_dir": str(case_dir),
    }
    if summary["status"] == "SUCCESS":
        fields_csv = case_dir / "fields.csv"
        node_count = fields_csv_to_npz(fields_csv, fields_npz)
        fields_csv.unlink()
        for suffix in PRUNED_SUFFIXES:
            artifact = (case_dir / "model").with_suffix(suffix)
            if artifact.exists():
                artifact.unlink()
        result["field_nodes"] = node_count
    return result

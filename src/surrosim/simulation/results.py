"""Parse CalculiX FRD nodal fields and derive engineering summaries."""

from dataclasses import dataclass
from math import sqrt
from pathlib import Path
import csv
import re

import numpy as np

from .. import shapes
from ..plate import Plate
from .msh2 import GmshMesh, read_msh2

_FLOAT = re.compile(r"[-+]?\d+(?:\.\d*)?(?:[Ee][-+]?\d+)?")


@dataclass(frozen=True)
class FrdFields:
    displacement: dict[int, tuple[float, float, float]]
    stress: dict[int, tuple[float, float, float, float, float, float]]


def parse_frd(path: str | Path) -> FrdFields:
    """Read the last DISP and STRESS nodal datasets from an ASCII FRD file.

    CalculiX stress order in FRD is SXX, SYY, SZZ, SXY, SYZ, SZX.
    """
    source = Path(path)
    displacement: dict[int, tuple[float, float, float]] = {}
    stress: dict[int, tuple[float, float, float, float, float, float]] = {}
    current: str | None = None

    for raw in source.read_text(encoding="utf-8", errors="replace").splitlines():
        stripped = raw.strip()
        if stripped.startswith("-4"):
            parts = stripped.split()
            current = parts[1].upper() if len(parts) > 1 else None
            if current == "DISP":
                displacement = {}
            elif current == "STRESS":
                stress = {}
            continue
        if stripped.startswith("-3"):
            current = None
            continue
        if current not in {"DISP", "STRESS"} or not stripped.startswith("-1"):
            continue
        numbers = _FLOAT.findall(raw)
        expected = 5 if current == "DISP" else 8
        if len(numbers) < expected:
            raise ValueError(f"Malformed {current} FRD record: {raw!r}")
        node_id = int(numbers[1])
        values = tuple(float(value) for value in numbers[2:expected])
        if current == "DISP":
            displacement[node_id] = values  # type: ignore[assignment]
        else:
            stress[node_id] = values  # type: ignore[assignment]

    if not displacement:
        raise ValueError("FRD does not contain a DISP nodal result block")
    if not stress:
        raise ValueError("FRD does not contain a STRESS nodal result block")
    return FrdFields(displacement=displacement, stress=stress)


def von_mises(components: tuple[float, float, float, float, float, float]) -> float:
    """Von Mises stress from (SXX,SYY,SZZ,SXY,SYZ,SZX)."""
    sxx, syy, szz, sxy, syz, szx = components
    return sqrt(
        0.5 * ((sxx - syy) ** 2 + (syy - szz) ** 2 + (szz - sxx) ** 2)
        + 3.0 * (sxy**2 + syz**2 + szx**2)
    )


def summarize_fields(fields: FrdFields, mesh: GmshMesh, plate: Plate) -> dict:
    disp_mag = {
        node: sqrt(ux * ux + uy * uy + uz * uz)
        for node, (ux, uy, uz) in fields.displacement.items()
    }
    mises = {node: von_mises(values) for node, values in fields.stress.items()}
    if not disp_mag or not mises:
        raise ValueError("Empty displacement or stress result")

    max_disp_node = max(disp_mag, key=disp_mag.get)
    global_stress_node = max(mises, key=mises.get)
    node_ids = [node for node in mesh.nodes if node in mises]
    coordinates = np.array([mesh.nodes[node] for node in node_ids], dtype=float)
    mask = (
        shapes.roi_mask(coordinates, plate)
        if node_ids
        else np.zeros(0, dtype=bool)
    )
    roi_nodes = [node for node, flag in zip(node_ids, mask) if flag]
    roi_stress_node = max(roi_nodes, key=mises.get) if roi_nodes else None

    return {
        "max_displacement_mm": disp_mag[max_disp_node],
        "max_displacement_node": max_disp_node,
        "global_max_von_mises_mpa": mises[global_stress_node],
        "global_max_von_mises_node": global_stress_node,
        "max_von_mises_roi_mpa": mises[roi_stress_node] if roi_stress_node else None,
        "max_von_mises_roi_node": roi_stress_node,
        "roi_definition": {
            **shapes.area_of_interest_definition(plate),
            "node_count": len(roi_nodes),
        },
    }


def parse_and_summarize(
    frd_path: str | Path,
    mesh_path: str | Path,
    plate: Plate,
    fields_csv: str | Path | None = None,
) -> dict:
    fields = parse_frd(frd_path)
    mesh = read_msh2(mesh_path)
    summary = summarize_fields(fields, mesh, plate)
    if fields_csv is not None:
        write_fields_csv(fields_csv, fields, mesh)
    return summary


def write_fields_csv(path: str | Path, fields: FrdFields, mesh: GmshMesh) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    columns = [
        "node_id", "x_mm", "y_mm", "z_mm", "ux_mm", "uy_mm", "uz_mm",
        "displacement_mm", "sxx_mpa", "syy_mpa", "szz_mpa", "sxy_mpa",
        "syz_mpa", "szx_mpa", "von_mises_mpa",
    ]
    common = sorted(set(mesh.nodes) & set(fields.displacement) & set(fields.stress))
    with destination.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for node in common:
            x, y, z = mesh.nodes[node]
            ux, uy, uz = fields.displacement[node]
            sxx, syy, szz, sxy, syz, szx = fields.stress[node]
            writer.writerow({
                "node_id": node, "x_mm": x, "y_mm": y, "z_mm": z,
                "ux_mm": ux, "uy_mm": uy, "uz_mm": uz,
                "displacement_mm": sqrt(ux * ux + uy * uy + uz * uz),
                "sxx_mpa": sxx, "syy_mpa": syy, "szz_mpa": szz,
                "sxy_mpa": sxy, "syz_mpa": syz, "szx_mpa": szx,
                "von_mises_mpa": von_mises(fields.stress[node]),
            })

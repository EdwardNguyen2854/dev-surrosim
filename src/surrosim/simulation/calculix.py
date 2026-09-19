"""Create a CalculiX static-structural input deck from a SurroSim Gmsh mesh."""

from collections import defaultdict
from dataclasses import dataclass
from math import sqrt
from pathlib import Path

from ..plate import Plate
from .msh2 import GmshMesh, MeshElement, read_msh2, unique_nodes


@dataclass(frozen=True)
class DeckSummary:
    path: Path
    nodes: int
    volume_elements: int
    fixed_nodes: int
    load_nodes: int
    total_applied_force_n: float


def _triangle_area(mesh: GmshMesh, element: MeshElement) -> float:
    a, b, c = (mesh.nodes[node] for node in element.nodes)
    ab = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
    ac = (c[0] - a[0], c[1] - a[1], c[2] - a[2])
    cross = (
        ab[1] * ac[2] - ab[2] * ac[1],
        ab[2] * ac[0] - ab[0] * ac[2],
        ab[0] * ac[1] - ab[1] * ac[0],
    )
    return 0.5 * sqrt(sum(value * value for value in cross))


def _area_weighted_nodal_loads(
    mesh: GmshMesh, surface_elements: tuple[MeshElement, ...], total_force_n: float
) -> dict[int, float]:
    """Equivalent linear-triangle nodal forces for uniform end-face traction."""
    weights: dict[int, float] = defaultdict(float)
    for element in surface_elements:
        if element.element_type != 2:
            raise ValueError("v0.2 supports first-order triangular load faces only")
        area = _triangle_area(mesh, element)
        if area <= 0:
            raise ValueError(f"Degenerate load-face element {element.element_id}")
        for node in element.nodes:
            weights[node] += area / 3.0
    total_area_weight = sum(weights.values())
    if total_area_weight <= 0:
        raise ValueError("LOAD_FACE has zero area")
    return {
        node: -abs(total_force_n) * weight / total_area_weight
        for node, weight in weights.items()
    }


def _write_ids(handle, ids: tuple[int, ...], per_line: int = 16) -> None:
    for start in range(0, len(ids), per_line):
        handle.write(", ".join(str(value) for value in ids[start : start + per_line]) + "\n")


def build_calculix_deck(
    mesh_path: str | Path,
    plate: Plate,
    output_path: str | Path | None = None,
) -> DeckSummary:
    """Write a linear-tetra CalculiX deck with an exact total -Z end load.

    The load is distributed to LOAD_FACE nodes by tributary triangle area. This
    keeps the requested total force invariant as the surface mesh is refined.
    """
    plate.validate()
    mesh = read_msh2(mesh_path)
    volumes = mesh.elements_in_group(3, "SOLID")
    fixed_surface = mesh.elements_in_group(2, "FIXED_FACE")
    load_surface = mesh.elements_in_group(2, "LOAD_FACE")
    if not volumes:
        raise ValueError("SOLID contains no first-order tetrahedra")
    if not fixed_surface or not load_surface:
        raise ValueError("FIXED_FACE and LOAD_FACE must contain surface triangles")
    if any(element.element_type != 4 for element in volumes):
        raise ValueError("SurroSim v0.2 currently supports C3D4 tetrahedra only")

    fixed_nodes = unique_nodes(fixed_surface)
    load_nodes = unique_nodes(load_surface)
    loads = _area_weighted_nodal_loads(mesh, load_surface, plate.force_n)
    applied = sum(loads.values())
    if abs(applied + abs(plate.force_n)) > max(1e-9, abs(plate.force_n) * 1e-12):
        raise RuntimeError("Distributed nodal load does not sum to requested force")

    destination = Path(output_path) if output_path else Path(mesh_path).with_name("model.inp")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("*HEADING\nSurroSim v0.2 static structural case\n")
        handle.write("** Units: mm, N, MPa. Total transverse load is -Z.\n")
        handle.write("*NODE\n")
        for node_id in sorted(mesh.nodes):
            x, y, z = mesh.nodes[node_id]
            handle.write(f"{node_id}, {x:.12g}, {y:.12g}, {z:.12g}\n")
        handle.write("*ELEMENT, TYPE=C3D4, ELSET=SOLID\n")
        for element in volumes:
            handle.write(f"{element.element_id}, " + ", ".join(map(str, element.nodes)) + "\n")
        handle.write("*NSET, NSET=ALL_NODES\n")
        _write_ids(handle, tuple(sorted(mesh.nodes)))
        handle.write("*NSET, NSET=FIXED_FACE\n")
        _write_ids(handle, fixed_nodes)
        handle.write("*NSET, NSET=LOAD_FACE\n")
        _write_ids(handle, load_nodes)
        handle.write("*MATERIAL, NAME=STEEL\n*ELASTIC\n")
        handle.write(f"{plate.youngs_modulus_mpa:.12g}, {plate.poisson_ratio:.12g}\n")
        handle.write("*SOLID SECTION, ELSET=SOLID, MATERIAL=STEEL\n")
        handle.write("*BOUNDARY\nFIXED_FACE, 1, 3, 0.0\n")
        handle.write("*STEP\n*STATIC\n")
        handle.write("*CLOAD\n")
        for node_id in sorted(loads):
            handle.write(f"{node_id}, 3, {loads[node_id]:.12g}\n")
        handle.write("*NODE FILE\nU\n")
        handle.write("*EL FILE\nS\n")
        handle.write("*END STEP\n")

    return DeckSummary(
        path=destination,
        nodes=len(mesh.nodes),
        volume_elements=len(volumes),
        fixed_nodes=len(fixed_nodes),
        load_nodes=len(load_nodes),
        total_applied_force_n=applied,
    )

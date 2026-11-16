"""Create a CalculiX static-structural input deck from a SurroSim Gmsh mesh."""

from collections import defaultdict
from dataclasses import dataclass
from math import sqrt
from pathlib import Path

from .. import shapes
from ..plate import Plate
from .msh2 import GmshMesh, MeshElement, read_msh2, unique_nodes


# Gmsh MSH 2.2 tet10 slots 5..10 are edges (1,2),(2,3),(1,3),(1,4),(3,4),(2,4);
# CalculiX C3D10 expects (1,2),(2,3),(3,1),(1,4),(2,4),(3,4).
CALCULIX_TET10_ORDER = (0, 1, 2, 3, 4, 5, 6, 7, 9, 8)


@dataclass(frozen=True)
class DeckSummary:
    path: Path
    nodes: int
    volume_elements: int
    fixed_nodes: int
    load_nodes: int
    total_applied_force_n: float
    element_type: str
    element_order: int
    load_dof: int = 3


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


def _corner_triangle(mesh: GmshMesh, element: MeshElement) -> MeshElement:
    if element.element_type == 2:
        return element
    if element.element_type == 9:
        return MeshElement(
            element_id=element.element_id,
            element_type=2,
            physical_tag=element.physical_tag,
            nodes=element.nodes[:3],
        )
    raise ValueError(f"Unsupported load-face element type {element.element_type}")


def _area_weighted_nodal_loads(
    mesh: GmshMesh, surface_elements: tuple[MeshElement, ...], total_force_n: float
) -> dict[int, float]:
    """Consistent nodal force weights for a uniform traction on the end face.

    For a straight-sided quadratic triangle the consistent uniform-traction
    load vector puts zero force on corner nodes and area/3 on each midside
    node; linear triangles put area/3 on every node. Weights are unsigned; the
    caller applies the shape's load direction.
    """
    weights: dict[int, float] = defaultdict(float)
    for element in surface_elements:
        if element.element_type not in (2, 9):
            raise ValueError(f"Unsupported load-face element type {element.element_type}")
        area = _triangle_area(mesh, _corner_triangle(mesh, element))
        if area <= 0:
            raise ValueError(f"Degenerate load-face element {element.element_id}")
        if element.element_type == 2:
            for node in element.nodes:
                weights[node] += area / 3.0
        else:
            for node in element.nodes[3:6]:
                weights[node] += area / 3.0
    total_area_weight = sum(weights.values())
    if total_area_weight <= 0:
        raise ValueError("LOAD_FACE has zero area")
    return {
        node: abs(total_force_n) * weight / total_area_weight
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
    """Write a linear-tetra CalculiX deck with an exact total end load.

    The load is distributed to LOAD_FACE nodes by tributary triangle area. This
    keeps the requested total force invariant as the surface mesh is refined.
    The load direction (DOF and sign) comes from the shape registry.
    """
    plate.validate()
    spec = shapes.spec(plate.shape)
    mesh = read_msh2(mesh_path)
    volumes = mesh.elements_in_group(3, "SOLID")
    fixed_surface = mesh.elements_in_group(2, "FIXED_FACE")
    load_surface = mesh.elements_in_group(2, "LOAD_FACE")
    if not volumes:
        raise ValueError("SOLID contains no tetrahedra")
    if not fixed_surface or not load_surface:
        raise ValueError("FIXED_FACE and LOAD_FACE must contain surface triangles")

    volume_types = {element.element_type for element in volumes}
    if volume_types == {4}:
        element_type, element_order = "C3D4", 1
    elif volume_types == {11}:
        element_type, element_order = "C3D10", 2
    else:
        raise ValueError(f"Unsupported or mixed SOLID element types: {sorted(volume_types)}")
    surface_types = {element.element_type for element in fixed_surface + load_surface}
    if not surface_types <= ({2} if element_order == 1 else {9}):
        raise ValueError(
            f"Surface element types {sorted(surface_types)} do not match "
            f"{element_type} volume elements"
        )

    fixed_nodes = unique_nodes(fixed_surface)
    load_nodes = unique_nodes(load_surface)
    weights = _area_weighted_nodal_loads(mesh, load_surface, plate.force_n)
    loads = {node: spec.load_sign * weight for node, weight in weights.items()}
    applied = sum(loads.values())
    if abs(applied - spec.load_sign * abs(plate.force_n)) > max(
        1e-9, abs(plate.force_n) * 1e-12
    ):
        raise RuntimeError("Distributed nodal load does not sum to requested force")

    destination = Path(output_path) if output_path else Path(mesh_path).with_name("model.inp")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("*HEADING\nSurroSim static structural case\n")
        handle.write(
            f"** Units: mm, N, MPa. Load along DOF {spec.load_dof} "
            f"(sign {spec.load_sign:+.0f}); shape {plate.shape}.\n"
        )
        handle.write("*NODE\n")
        for node_id in sorted(mesh.nodes):
            x, y, z = mesh.nodes[node_id]
            handle.write(f"{node_id}, {x:.12g}, {y:.12g}, {z:.12g}\n")
        handle.write(f"*ELEMENT, TYPE={element_type}, ELSET=SOLID\n")
        for element in volumes:
            nodes = element.nodes
            if element_order == 2:
                nodes = tuple(nodes[index] for index in CALCULIX_TET10_ORDER)
            handle.write(f"{element.element_id}, " + ", ".join(map(str, nodes)) + "\n")
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
            handle.write(f"{node_id}, {spec.load_dof}, {loads[node_id]:.12g}\n")
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
        element_type=element_type,
        element_order=element_order,
        load_dof=spec.load_dof,
    )

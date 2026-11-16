"""Lightweight FEA field visualisation (plotly surface meshes, no PyVista)."""

from collections import defaultdict
from pathlib import Path

import numpy as np

from ..simulation.msh2 import read_msh2

TET_CORNER_FACES = ((0, 1, 2), (0, 1, 3), (1, 2, 3), (0, 2, 3))
# (face corners, opposite corner)
TET_FACES = (
    ((0, 1, 2), 3),
    ((0, 1, 3), 2),
    ((1, 2, 3), 0),
    ((0, 2, 3), 1),
)
# Gmsh MSH 2.2 tet10 slots 5..10 are edges (1,2),(2,3),(1,3),(1,4),(3,4),(2,4)
QUADRATIC_EDGES = ((0, 1, 4), (1, 2, 5), (0, 2, 6), (0, 3, 7), (2, 3, 8), (1, 3, 9))


def _corners(element) -> tuple[int, ...] | None:
    if element.element_type == 4:
        return element.nodes
    if element.element_type == 11:
        return element.nodes[:4]
    return None


def _orient_outward(
    mesh, face: tuple[int, int, int], opposite: int
) -> tuple[int, int, int]:
    a, b, c = (mesh.nodes[node] for node in face)
    normal = (
        (b[1] - a[1]) * (c[2] - a[2]) - (b[2] - a[2]) * (c[1] - a[1]),
        (b[2] - a[2]) * (c[0] - a[0]) - (b[0] - a[0]) * (c[2] - a[2]),
        (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]),
    )
    o = mesh.nodes[opposite]
    if sum(normal[axis] * (o[axis] - a[axis]) for axis in range(3)) > 0.0:
        return (face[0], face[2], face[1])
    return face


def _split_quadratic_face(
    element, face: tuple[int, int, int]
) -> list[tuple[int, int, int]]:
    mid_of = {
        frozenset((element.nodes[i], element.nodes[j])): element.nodes[k]
        for i, j, k in QUADRATIC_EDGES
    }
    a, b, c = face
    ab = mid_of[frozenset((a, b))]
    bc = mid_of[frozenset((b, c))]
    ac = mid_of[frozenset((a, c))]
    return [(a, ab, ac), (ab, b, bc), (ac, bc, c), (ab, bc, ac)]


def boundary_triangles(
    mesh, subdivide: bool = False
) -> list[tuple[int, int, int]]:
    """Boundary faces of a tetrahedral mesh as outward-facing node triples.

    With ``subdivide`` every quadratic face is split into four sub-triangles
    through its mid-edge nodes, so the bore of the hole renders round instead
    of faceted.
    """
    counts: dict[tuple[int, int, int], int] = defaultdict(int)
    for element in mesh.elements:
        corners = _corners(element)
        if corners is None:
            continue
        for face in TET_CORNER_FACES:
            counts[tuple(sorted(corners[index] for index in face))] += 1

    triangles: list[tuple[int, int, int]] = []
    for element in mesh.elements:
        corners = _corners(element)
        if corners is None:
            continue
        for face, opposite in TET_FACES:
            key = tuple(sorted(corners[index] for index in face))
            if counts[key] != 1:
                continue
            ordered = _orient_outward(
                mesh, tuple(corners[index] for index in face), corners[opposite]
            )
            if subdivide and element.element_type == 11:
                triangles.extend(_split_quadratic_face(element, ordered))
            else:
                triangles.append(ordered)
    return triangles


def _nodal_values(mesh, node_ids, values) -> dict[int, float]:
    """Map node ids to field values, filling quadratic mid-edge nodes by
    averaging their corner endpoints when the field has no value there."""
    value_of = {int(node): float(value) for node, value in zip(node_ids, values)}
    for element in mesh.elements:
        if element.element_type != 11:
            continue
        nodes = element.nodes
        if not all(nodes[index] in value_of for index in range(4)):
            continue
        for i, j, mid in QUADRATIC_EDGES:
            if nodes[mid] not in value_of:
                value_of[nodes[mid]] = 0.5 * (value_of[nodes[i]] + value_of[nodes[j]])
    return value_of


FIELD_META = {
    "von_mises_mpa": {"label": "Von Mises stress", "unit": "MPa"},
    "displacement_mm": {"label": "Displacement magnitude", "unit": "mm"},
}


def field_payload(
    mesh_path: str | Path,
    fields_npz: str | Path,
    field: str = "von_mises_mpa",
) -> dict:
    """Compact JSON-ready smooth-shaded surface mesh payload for the viewer."""
    mesh = read_msh2(mesh_path)
    with np.load(fields_npz) as data:
        if field not in data:
            raise ValueError(f"Field {field!r} not present in {fields_npz}")
        node_ids = data["node_id"]
        values = data[field].astype(float)
    value_of = _nodal_values(mesh, node_ids, values)

    triangles = [
        face
        for face in boundary_triangles(mesh, subdivide=True)
        if all(node in value_of for node in face)
    ]
    if not triangles:
        raise ValueError("No visualisable boundary triangles with field data")

    used = sorted({node for face in triangles for node in face})
    vertex_index = {node: index for index, node in enumerate(used)}
    vertices = [
        [float(value) for value in mesh.nodes[node]] for node in used
    ]
    faces = [
        [vertex_index[node] for node in face] for face in triangles
    ]
    intensity = [value_of[node] for node in used]
    meta = FIELD_META.get(field, {"label": field, "unit": ""})
    return {
        "field": field,
        "label": meta["label"],
        "unit": meta["unit"],
        "vertices": vertices,
        "faces": faces,
        "intensity": intensity,
        "intensity_mode": "vertex",
        "min": min(intensity),
        "max": max(intensity),
    }


def field_figure(
    mesh_path: str | Path,
    fields_npz: str | Path,
    field: str = "von_mises_mpa",
    title: str | None = None,
    colorbar_title: str | None = None,
):
    """Build a plotly Mesh3d figure coloured by a nodal field."""
    import plotly.graph_objects as go

    mesh = read_msh2(mesh_path)
    with np.load(fields_npz) as data:
        if field not in data:
            raise ValueError(f"Field {field!r} not present in {fields_npz}")
        node_ids = data["node_id"]
        values = data[field].astype(float)
    value_of = _nodal_values(mesh, node_ids, values)

    triangles = [
        face
        for face in boundary_triangles(mesh, subdivide=True)
        if all(node in value_of for node in face)
    ]
    if not triangles:
        raise ValueError("No visualisable boundary triangles with field data")
    used = sorted({node for face in triangles for node in face})
    vertex_index = {node: index for index, node in enumerate(used)}
    coordinates = np.array([mesh.nodes[node] for node in used], dtype=float)
    faces = np.array(
        [[vertex_index[node] for node in face] for face in triangles], dtype=int
    )
    intensity = np.array([value_of[node] for node in used], dtype=float)

    figure = go.Figure(
        data=[
            go.Mesh3d(
                x=coordinates[:, 0],
                y=coordinates[:, 1],
                z=coordinates[:, 2],
                i=faces[:, 0],
                j=faces[:, 1],
                k=faces[:, 2],
                intensity=intensity,
                intensitymode="vertex",
                colorscale="Jet",
                colorbar={"title": colorbar_title or field},
                flatshading=False,
                lighting={"ambient": 0.55, "diffuse": 0.9, "roughness": 0.85},
            )
        ]
    )
    figure.update_layout(
        title=title or field,
        scene={
            "aspectmode": "data",
            "xaxis_title": "x (mm)",
            "yaxis_title": "y (mm)",
            "zaxis_title": "z (mm)",
        },
        margin={"l": 0, "r": 0, "t": 40, "b": 0},
    )
    return figure

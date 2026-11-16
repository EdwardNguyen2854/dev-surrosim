"""Mesh-graph feature construction shared by export and inference.

The graph uses the corner (linear) nodes of the tetrahedral mesh. Node
features combine scaled coordinates, boundary-condition flags and hole
proximity with a broadcast global design vector; edge features are relative
position vectors scaled by the shape's characteristic thickness.

Boundary flags come from the mesh physical groups when present (needed for
shapes whose loaded end is not at ``X=L``, e.g. the L-bracket) and fall back
to coordinate tests for synthetic meshes.
"""

import numpy as np
import torch

from .. import shapes
from ..plate import Plate
from ..simulation.msh2 import unique_nodes

GEOMETRY_NODE_FEATURES = [
    "x_over_L",
    "y_over_W",
    "z_over_T",
    "hole_radial_ratio",
    "is_fixed",
    "is_load",
    "is_hole_surface",
]
GLOBAL_FEATURES = [
    "global_length",
    "global_width",
    "global_thickness",
    "global_hole_ratio",
    "global_hole_position",
    "global_hole2_ratio",
    "global_hole2_position",
    "global_taper_ratio",
    "global_step_ratio",
    "global_step_position",
    "global_fillet_ratio",
    "global_flange_width_ratio",
    "global_flange_thickness_ratio",
    "global_web_thickness_ratio",
    "global_height_ratio",
    "global_force",
    "global_modulus",
    "global_poisson",
    *[f"shape_is_{kind}" for kind in shapes.SHAPE_KINDS],
]
NODE_FEATURES = GEOMETRY_NODE_FEATURES + GLOBAL_FEATURES
EDGE_FEATURES = ["dx_over_T", "dy_over_T", "dz_over_T", "length_over_T"]
TARGET_COMPONENTS = [
    "ux_mm", "uy_mm", "uz_mm",
    "sxx_mpa", "syy_mpa", "szz_mpa", "sxy_mpa", "syz_mpa", "szx_mpa",
]

PARAMETER_KEYS = (
    "length_mm", "width_mm", "thickness_mm", "hole_diameter_mm", "hole_x_mm",
    "force_n", "youngs_modulus_mpa", "poisson_ratio",
)


def von_mises(stress: np.ndarray) -> np.ndarray:
    """Von Mises stress from an (N, 6) component matrix (SXX..SZX)."""
    sxx, syy, szz, sxy, syz, szx = (stress[:, index] for index in range(6))
    return np.sqrt(
        0.5 * ((sxx - syy) ** 2 + (syy - szz) ** 2 + (szz - sxx) ** 2)
        + 3.0 * (sxy**2 + syz**2 + szx**2)
    )


def coordinate_scales(design: Plate) -> tuple[float, float, float]:
    """Feature scaling lengths ``(L, W, T)`` for a design."""
    if design.shape == shapes.I_BEAM:
        return (
            design.length_mm,
            design.flange_width_mm,
            design.beam_depth_mm,
        )
    if design.shape == shapes.L_BRACKET:
        return (design.length_mm, design.width_mm, design.height_mm)
    return (design.length_mm, design.width_mm, design.thickness_mm)


def _corner_nodes(mesh) -> list[tuple[int, ...]]:
    corners = []
    for element in mesh.elements:
        if element.element_type == 4:
            corners.append(element.nodes)
        elif element.element_type == 11:
            corners.append(element.nodes[:4])
    return corners


def _global_vector(design: Plate) -> np.ndarray:
    length, width, thickness = coordinate_scales(design)
    features = shapes.engineered_features(design)
    values = [
        length / 130.0,
        width / 45.0,
        thickness / 7.0,
        features["hole_width_ratio"],
        features["hole_position_ratio"],
        features["hole2_width_ratio"],
        features["hole2_position_ratio"],
        features["taper_ratio"],
        features["step_thickness_ratio"],
        features["step_position_ratio"],
        features["fillet_radius_ratio"],
        features["beam_depth_ratio"],
        features["flange_thickness_ratio"],
        features["web_thickness_ratio"],
        features["bracket_height_ratio"],
        design.force_n / 450.0,
        design.youngs_modulus_mpa / 210_000.0,
        design.poisson_ratio,
    ]
    values.extend(
        1.0 if design.shape == kind else 0.0 for kind in shapes.SHAPE_KINDS
    )
    return np.array(values, dtype=np.float64)


def _boundary_flags(
    mesh, node_ids: list[int], coordinates: np.ndarray, design: Plate
) -> tuple[np.ndarray, np.ndarray]:
    try:
        fixed_ids = set(unique_nodes(mesh.elements_in_group(2, "FIXED_FACE")))
        load_ids = set(unique_nodes(mesh.elements_in_group(2, "LOAD_FACE")))
    except ValueError:
        fixed_ids, load_ids = set(), set()
    if fixed_ids and load_ids:
        is_fixed = np.array(
            [1.0 if node in fixed_ids else 0.0 for node in node_ids]
        )
        is_load = np.array([1.0 if node in load_ids else 0.0 for node in node_ids])
        return is_fixed, is_load
    x = coordinates[:, 0]
    is_fixed = (np.abs(x) <= 1e-6).astype(float)
    if design.shape == shapes.L_BRACKET:
        z = coordinates[:, 2]
        is_load = (np.abs(z - design.height_mm) <= 1e-6).astype(float)
    else:
        is_load = (np.abs(x - design.length_mm) <= 1e-6).astype(float)
    return is_fixed, is_load


def build_geometry_tensors(row: dict, mesh) -> dict:
    """Node/edge features for inference (no targets required)."""
    design = Plate.from_mapping(row)
    length, width, thickness = coordinate_scales(design)
    holes = shapes.shape_holes(design)

    corners = _corner_nodes(mesh)
    if not corners:
        raise ValueError("mesh has no tetrahedra")
    node_ids = sorted({node for element in corners for node in element})
    index_of = {node_id: index for index, node_id in enumerate(node_ids)}
    count = len(node_ids)

    coordinates = np.array([mesh.nodes[node] for node in node_ids], dtype=np.float64)
    x = coordinates[:, 0]
    y = coordinates[:, 1]
    z = coordinates[:, 2]

    radial_ratio = np.ones(count, dtype=np.float64)
    on_hole = np.zeros(count, dtype=np.float64)
    for hole_x, hole_y, diameter in holes:
        radius = diameter / 2.0
        radial = np.sqrt((x - hole_x) ** 2 + (y - hole_y) ** 2)
        ratio = np.clip(radial / max(radius, 1e-9), 0.0, 3.0) / 3.0
        radial_ratio = np.minimum(radial_ratio, ratio)
        tolerance = max(0.03 * radius, 0.15)
        on_hole = np.maximum(
            on_hole,
            (
                (np.abs(radial - radius) <= tolerance)
                & (np.abs(z) <= thickness / 2 + 1e-6)
            ).astype(float),
        )

    is_fixed, is_load = _boundary_flags(mesh, node_ids, coordinates, design)
    global_vector = _global_vector(design)
    globals_broadcast = np.tile(global_vector, (count, 1))
    node_matrix = np.column_stack(
        [x / length, y / width, z / thickness, radial_ratio, is_fixed, is_load, on_hole]
    )
    node_features = np.concatenate([node_matrix, globals_broadcast], axis=1)

    edge_pairs: set[tuple[int, int]] = set()
    for element in corners:
        for a in range(4):
            for b in range(a + 1, 4):
                first, second = sorted((index_of[element[a]], index_of[element[b]]))
                edge_pairs.add((first, second))
    edge_index = np.array(sorted(edge_pairs), dtype=np.int64).T
    deltas = coordinates[edge_index[0]] - coordinates[edge_index[1]]
    edge_attr = np.column_stack(
        [deltas / thickness, np.linalg.norm(deltas, axis=1) / thickness]
    )

    return {
        "x": torch.tensor(node_features, dtype=torch.float32),
        "edge_index": torch.tensor(edge_index, dtype=torch.long),
        "edge_attr": torch.tensor(edge_attr, dtype=torch.float32),
        "node_ids": torch.tensor(node_ids, dtype=torch.long),
        "coordinates": torch.tensor(coordinates, dtype=torch.float64),
    }


def attach_targets(tensors: dict, fields: dict) -> dict:
    node_ids = tensors["node_ids"].tolist()
    fields_by_node = {
        int(node_id): index
        for index, node_id in enumerate(np.asarray(fields["node_id"]).ravel())
    }
    missing = [node for node in node_ids if node not in fields_by_node]
    if missing:
        raise ValueError(f"{len(missing)} corner nodes missing from fields")
    field_index = np.array([fields_by_node[node] for node in node_ids])
    displacement = np.stack(
        [
            np.asarray(fields["ux_mm"])[field_index],
            np.asarray(fields["uy_mm"])[field_index],
            np.asarray(fields["uz_mm"])[field_index],
        ],
        axis=1,
    )
    stress = np.stack(
        [
            np.asarray(fields[f"{name}_mpa"])[field_index]
            for name in ("sxx", "syy", "szz", "sxy", "syz", "szx")
        ],
        axis=1,
    )
    targets = np.concatenate([displacement, stress], axis=1)
    return {**tensors, "y": torch.tensor(targets, dtype=torch.float32)}


def build_graph_tensors(row: dict, mesh, fields: dict) -> dict:
    return attach_targets(build_geometry_tensors(row, mesh), fields)

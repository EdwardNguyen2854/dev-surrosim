"""Generate and tag 3-D cantilever designs with Gmsh OCC.

Coordinate frame shared by every shape: the structure is fixed at ``X=0`` and
loaded at its free end; the load is a single transverse force whose direction
is declared by the shape registry (``load_dof`` / ``load_sign``).  Physical
groups ``FIXED_FACE`` and ``LOAD_FACE`` are written explicitly per shape so the
CalculiX deck never has to guess boundary conditions from bounding boxes.

This module is the single geometry entry point: :func:`generate_design`
dispatches on ``design.shape`` and :func:`generate_plate` is kept as the
backwards-compatible name used by the v1 pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable
import json
import os

from . import shapes
from .plate import Plate

TOLERANCE = 1e-6

# Bound inside :func:`generate_design` when the meshing stack is available so
# the geometry helpers can use it without importing gmsh at module import time.
gmsh = None


@dataclass(frozen=True)
class BuiltGeometry:
    volume: int
    fixed_faces: tuple[int, ...]
    load_faces: tuple[int, ...]
    refine_faces: tuple[int, ...]
    refine_distances: tuple[float, ...]
    hole_faces: tuple[int, ...]
    note: str = ""


def _flat(result):
    if isinstance(result, tuple):
        return result[0]
    return result


def _bbox(dim: int, tag: int) -> tuple[float, float, float, float, float, float]:
    values = gmsh.model.getBoundingBox(dim, tag)
    return tuple(float(value) for value in values)


def _near(a: float, b: float, tol: float = TOLERANCE) -> bool:
    return abs(a - b) <= tol * max(1.0, abs(a), abs(b))


def _faces_of(volume: int) -> list[int]:
    gmsh.model.occ.synchronize()
    return [tag for dim, tag in gmsh.model.getBoundary(
        [(3, volume)], oriented=False, recursive=False
    ) if dim == 2]


def _edges_of(volume: int) -> list[int]:
    gmsh.model.occ.synchronize()
    edges: set[int] = set()
    for face in _faces_of(volume):
        for dim, tag in gmsh.model.getBoundary(
            [(2, face)], oriented=False, recursive=False
        ):
            if dim == 1:
                edges.add(tag)
    return sorted(edges)


def _select_faces(volume: int, predicate: Callable) -> list[int]:
    return [tag for tag in _faces_of(volume) if predicate(_bbox(2, tag))]


def _select_edges(volume: int, predicate: Callable) -> list[int]:
    return [tag for tag in _edges_of(volume) if predicate(_bbox(1, tag))]


def _latest_volume() -> int:
    gmsh.model.occ.synchronize()
    volumes = [tag for _dim, tag in gmsh.model.getEntities(3)]
    if not volumes:
        raise RuntimeError("OCC produced no solid volume")
    return volumes[-1]


def _build_profile(occ, points, extrude, translate) -> int:
    tags = [occ.addPoint(*point) for point in points]
    lines = [
        occ.addLine(tags[index], tags[(index + 1) % len(tags)])
        for index in range(len(tags))
    ]
    surface = occ.addPlaneSurface([occ.addCurveLoop(lines)])
    out = _flat(occ.extrude([(2, surface)], *extrude))
    volume = [tag for dim, tag in out if dim == 3][0]
    if translate != (0.0, 0.0, 0.0):
        occ.translate([(3, volume)], *translate)
    return volume


def _cut_holes(occ, volume: int, design: Plate) -> tuple[int, list[int]]:
    """Cut every through-hole along Z and return the hole surface tags."""
    hole_faces: list[int] = []
    thickness = _hole_cut_depth(design)
    for x, y, diameter in shapes.shape_holes(design):
        cutter = occ.addCylinder(x, y, -thickness, 0, 0, 2.0 * thickness, diameter / 2)
        out = _flat(occ.cut([(3, volume)], [(3, cutter)],
                            removeObject=True, removeTool=True))
        volume = [tag for dim, tag in out if dim == 3][0]
        gmsh.model.occ.synchronize()
        radius = diameter / 2.0
        hole_faces.extend(
            _select_faces(
                volume,
                lambda bb, cx=x, rr=radius: (
                    _near(bb[3] - bb[0], 2 * rr)
                    and _near(bb[4] - bb[1], 2 * rr)
                    and _near((bb[0] + bb[3]) / 2.0, cx)
                ),
            )
        )
    return volume, hole_faces


def _hole_cut_depth(design: Plate) -> float:
    if design.shape == shapes.I_BEAM:
        return design.beam_depth_mm
    if design.shape == shapes.L_BRACKET:
        return design.height_mm
    return design.thickness_mm


def _fillet(occ, volume: int, edges: list[int], radius: float, label: str) -> int:
    if not edges:
        raise RuntimeError(f"{label}: no edges matched the fillet selection")
    _flat(occ.fillet([int(volume)], [int(edge) for edge in edges], [float(radius)]))
    return _latest_volume()


def _base_faces(volume: int, length: float) -> tuple[list[int], list[int]]:
    fixed = _select_faces(volume, lambda bb: _near(bb[0], 0.0) and _near(bb[3], 0.0))
    load = _select_faces(
        volume, lambda bb: _near(bb[0], length) and _near(bb[3], length)
    )
    return fixed, load


def build_plate(occ, design: Plate) -> BuiltGeometry:
    length, width, thickness = design.length_mm, design.width_mm, design.thickness_mm
    volume = occ.addBox(0, -width / 2, -thickness / 2, length, width, thickness)
    volume, hole_faces = _cut_holes(occ, volume, design)
    fixed, load = _base_faces(volume, length)
    distances = tuple(
        1.5 * diameter for _x, _y, diameter in shapes.shape_holes(design)
    )
    return BuiltGeometry(volume, tuple(fixed), tuple(load), tuple(hole_faces),
                         distances, tuple(hole_faces))


def build_multi_hole(occ, design: Plate) -> BuiltGeometry:
    return build_plate(occ, design)


def build_taper(occ, design: Plate) -> BuiltGeometry:
    length, width, thickness = design.length_mm, design.width_mm, design.thickness_mm
    tip = design.tip_width_mm
    volume = _build_profile(
        occ,
        [(0, -width / 2, 0), (length, -tip / 2, 0), (length, tip / 2, 0), (0, width / 2, 0)],
        (0, 0, thickness),
        (0, 0, -thickness / 2),
    )
    volume, hole_faces = _cut_holes(occ, volume, design)
    fixed, load = _base_faces(volume, length)
    distances = tuple(
        1.5 * diameter for _x, _y, diameter in shapes.shape_holes(design)
    )
    return BuiltGeometry(volume, tuple(fixed), tuple(load), tuple(hole_faces),
                         distances, tuple(hole_faces))


def build_stepped(occ, design: Plate) -> BuiltGeometry:
    length, width = design.length_mm, design.width_mm
    root, tip = design.thickness_mm, design.step_thickness_mm
    step, radius = design.step_x_mm, design.fillet_radius_mm
    thick = occ.addBox(0, -width / 2, -root / 2, step, width, root)
    thin = occ.addBox(step, -width / 2, -tip / 2, length - step, width, tip)
    out = _flat(occ.fuse([(3, thick)], [(3, thin)],
                         removeObject=True, removeTool=True))
    volume = [tag for dim, tag in out if dim == 3][0]
    gmsh.model.occ.synchronize()

    corners = _select_edges(
        volume,
        lambda bb: (
            _near(bb[0], step)
            and _near(bb[3], step)
            and _near(bb[5] - bb[2], 0.0)
            and _near(abs((bb[2] + bb[5]) / 2.0), tip / 2)
        ),
    )
    volume = _fillet(occ, volume, corners, radius, "stepped plate")
    fixed, load = _base_faces(volume, length)
    refine = _select_faces(
        volume,
        lambda bb: (
            bb[0] >= step - radius - TOLERANCE
            and bb[3] <= step + TOLERANCE
            and abs((bb[2] + bb[5]) / 2.0) >= tip / 2.0 - TOLERANCE
        ),
    )
    return BuiltGeometry(volume, tuple(fixed), tuple(load), tuple(refine),
                         (1.5 * radius,) * len(refine), (), "filleted step")


def build_i_beam(occ, design: Plate) -> BuiltGeometry:
    length = design.length_mm
    depth, flange = design.beam_depth_mm, design.flange_width_mm
    tf, tw = design.flange_thickness_mm, design.web_thickness_mm
    radius = design.fillet_radius_mm
    y, z = flange / 2.0, depth / 2.0
    points = [
        (0, -y, -z), (0, y, -z), (0, y, -z + tf), (0, tw / 2, -z + tf),
        (0, tw / 2, z - tf), (0, y, z - tf), (0, y, z), (0, -y, z),
        (0, -y, z - tf), (0, -tw / 2, z - tf), (0, -tw / 2, -z + tf),
        (0, -y, -z + tf),
    ]
    volume = _build_profile(occ, points, (length, 0, 0), (0.0, 0.0, 0.0))
    gmsh.model.occ.synchronize()

    corners = _select_edges(
        volume,
        lambda bb: (
            _near(bb[3] - bb[0], length)
            and _near(bb[5] - bb[2], 0.0)
            and _near(bb[4] - bb[1], 0.0)
            and _near(abs((bb[1] + bb[4]) / 2.0), tw / 2)
            and _near(abs((bb[2] + bb[5]) / 2.0), z - tf)
        ),
    )
    volume = _fillet(occ, volume, corners, radius, "i-beam web/flange junctions")
    fixed, load = _base_faces(volume, length)
    refine = _select_faces(
        volume,
        lambda bb: (
            abs((bb[1] + bb[4]) / 2.0) <= tw / 2.0 + radius + TOLERANCE
            and abs((bb[2] + bb[5]) / 2.0) >= z - tf - TOLERANCE
            and abs(bb[1]) >= tw / 2.0 - TOLERANCE
        ),
    )
    return BuiltGeometry(volume, tuple(fixed), tuple(load), tuple(refine),
                         (1.5 * radius,) * len(refine), (), "filleted i-section")


def build_l_bracket(occ, design: Plate) -> BuiltGeometry:
    length, height, width = design.length_mm, design.height_mm, design.width_mm
    thickness, radius = design.thickness_mm, design.fillet_radius_mm
    points = [
        (0, 0, -thickness / 2),
        (length, 0, -thickness / 2),
        (length, 0, height),
        (length - thickness, 0, height),
        (length - thickness, 0, thickness / 2),
        (0, 0, thickness / 2),
    ]
    volume = _build_profile(occ, points, (0, width, 0), (0, -width / 2, 0))
    gmsh.model.occ.synchronize()

    inner = _select_edges(
        volume,
        lambda bb: (
            _near(bb[0], length - thickness)
            and _near(bb[3], length - thickness)
            and _near(bb[2], thickness / 2)
            and _near(bb[5], thickness / 2)
        ),
    )
    volume = _fillet(occ, volume, inner, radius, "l-bracket inner corner")
    fixed = _select_faces(volume, lambda bb: _near(bb[0], 0.0) and _near(bb[3], 0.0))
    load = _select_faces(volume, lambda bb: _near(bb[2], height) and _near(bb[5], height))
    refine = _select_faces(
        volume,
        lambda bb: (
            bb[0] >= length - thickness - TOLERANCE
            and bb[0] <= length - thickness + radius + TOLERANCE
            and abs((bb[2] + bb[5]) / 2.0) <= thickness / 2.0 + radius + TOLERANCE
            and abs((bb[2] + bb[5]) / 2.0) >= thickness / 2.0 - TOLERANCE
        ),
    )
    return BuiltGeometry(volume, tuple(fixed), tuple(load), tuple(refine),
                         (1.5 * radius,) * len(refine), (), "filleted l-corner")


BUILDERS: dict[str, Callable] = {
    shapes.PLATE: build_plate,
    shapes.MULTI_HOLE: build_multi_hole,
    shapes.TAPER: build_taper,
    shapes.STEPPED: build_stepped,
    shapes.I_BEAM: build_i_beam,
    shapes.L_BRACKET: build_l_bracket,
}


def _apply_refinement(
    built: BuiltGeometry, mesh_size: float, refinement_mm: float, quiet: bool
) -> bool:
    if refinement_mm <= 0 or not built.refine_faces or refinement_mm >= mesh_size:
        return False
    fields: list[int] = []
    for face, distance in zip(built.refine_faces, built.refine_distances):
        distance_field = gmsh.model.mesh.field.add("Distance")
        gmsh.model.mesh.field.setNumbers(distance_field, "SurfacesList", [face])
        threshold = gmsh.model.mesh.field.add("Threshold")
        gmsh.model.mesh.field.setNumber(threshold, "InField", distance_field)
        gmsh.model.mesh.field.setNumber(threshold, "SizeMin", refinement_mm)
        gmsh.model.mesh.field.setNumber(threshold, "SizeMax", mesh_size)
        gmsh.model.mesh.field.setNumber(threshold, "DistMin", 0.0)
        gmsh.model.mesh.field.setNumber(threshold, "DistMax", float(distance))
        fields.append(threshold)
    if len(fields) == 1:
        gmsh.model.mesh.field.setAsBackgroundMesh(fields[0])
    else:
        minimum = gmsh.model.mesh.field.add("Min")
        gmsh.model.mesh.field.setNumbers(minimum, "FieldsList", fields)
        gmsh.model.mesh.field.setAsBackgroundMesh(minimum)
    return True


def generate_design(
    design: Plate,
    output_dir: str | Path,
    element_order: int = 2,
    hole_refinement_mm: float = 0.0,
    quiet: bool = False,
) -> dict:
    """Export STEP geometry, Gmsh MSH v2 mesh and descriptive JSON metadata.

    ``hole_refinement_mm`` is the target element size on stress-raisers (holes
    and fillets); it is ignored when it is zero or not smaller than the global
    mesh size.  This function does NOT perform FEA.
    """
    design.validate()
    if element_order not in (1, 2):
        raise ValueError("element_order must be 1 (C3D4) or 2 (C3D10)")
    if hole_refinement_mm < 0:
        raise ValueError("hole_refinement_mm must be non-negative")
    if 0 < hole_refinement_mm >= design.mesh_size_mm:
        raise ValueError("hole_refinement_mm must be smaller than mesh_size_mm")
    try:
        global gmsh
        import gmsh  # noqa: PLC0415 - deferred so the module imports without a mesh stack
    except ImportError as exc:
        raise RuntimeError(
            "Gmsh is required for mesh generation: pip install -e '.[mesh]'"
        ) from exc

    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    initialized = False
    try:
        gmsh.initialize()
        initialized = True
        gmsh.option.setNumber("General.Terminal", 0 if quiet else 1)
        gmsh.model.add(f"surrosim_{design.shape}")
        occ = gmsh.model.occ
        builder = BUILDERS[design.shape]
        built = builder(occ, design)
        gmsh.model.occ.synchronize()
        if not built.fixed_faces or not built.load_faces:
            raise RuntimeError(
                f"{design.shape}: cannot identify fixed/load faces "
                f"(fixed={built.fixed_faces}, load={built.load_faces})"
            )

        groups = (
            (3, [built.volume], "SOLID"),
            (2, list(built.fixed_faces), "FIXED_FACE"),
            (2, list(built.load_faces), "LOAD_FACE"),
        )
        for dim, tags, name in groups:
            group = gmsh.model.addPhysicalGroup(dim, tags)
            gmsh.model.setPhysicalName(dim, group, name)

        gmsh.write(str(output / "geometry.step"))
        gmsh.option.setNumber("Mesh.MshFileVersion", 2.2)
        gmsh.option.setNumber("Mesh.ElementOrder", element_order)
        if element_order == 2:
            optimize = int(os.environ.get("SURROSIM_HIGH_ORDER_OPTIMIZE", "2"))
            gmsh.option.setNumber("Mesh.HighOrderOptimize", optimize)
        gmsh.model.mesh.setSize(gmsh.model.getEntities(0), design.mesh_size_mm)
        refined = _apply_refinement(
            built, design.mesh_size_mm, hole_refinement_mm, quiet
        )
        gmsh.model.mesh.generate(3)
        gmsh.write(str(output / "mesh.msh"))
        nodes, _, _ = gmsh.model.mesh.getNodes()
        _types, element_tags, _ = gmsh.model.mesh.getElements(3)
        volume_elements = sum(len(tags) for tags in element_tags)
        min_sicn = None
        try:
            qualities = [
                min(gmsh.model.mesh.getElementQualities(tags, "minSICN"))
                for tags in element_tags
                if len(tags)
            ]
            if qualities:
                min_sicn = round(float(min(qualities)), 6)
        except Exception:  # noqa: BLE001 - quality is informational provenance
            min_sicn = None

        spec = shapes.spec(design.shape)
        metadata = {
            "geometry": design.as_dict(),
            "shape": design.shape,
            "shape_label": spec.label,
            "units": {"length": "mm", "force": "N", "stress": "MPa"},
            "coordinate_frame": (
                "fixed X=0; transverse load at the free end; "
                f"load along DOF {spec.load_dof} (sign {spec.load_sign:+.0f})"
            ),
            "physical_groups": ["SOLID", "FIXED_FACE", "LOAD_FACE"],
            "mesh_nodes": len(nodes),
            "mesh_volume_elements": volume_elements,
            "mesh_min_sicn": min_sicn,
            "element_order": element_order,
            "hole_refinement_mm": hole_refinement_mm if refined else None,
            "mass_g": design.mass_g(),
            "area_of_interest": shapes.area_of_interest_definition(design),
            "nominal_beam_baseline_not_fea": design.nominal_baseline(),
            "fea_status": "not_run",
        }
        (output / "metadata.json").write_text(
            json.dumps(metadata, indent=2) + "\n", encoding="utf-8"
        )
        return metadata
    finally:
        if initialized:
            gmsh.finalize()


def generate_plate(
    plate: Plate,
    output_dir: str | Path,
    element_order: int = 2,
    hole_refinement_mm: float = 0.0,
    quiet: bool = False,
) -> dict:
    """Backwards-compatible alias for :func:`generate_design`."""
    return generate_design(
        plate, output_dir, element_order=element_order,
        hole_refinement_mm=hole_refinement_mm, quiet=quiet,
    )

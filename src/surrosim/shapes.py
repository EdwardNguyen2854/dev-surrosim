"""Shape registry for parametric cantilever designs.

SurroSim started with a single geometry family: a rectangular cantilever plate
with an optional through-hole.  This module makes the shape explicit so the
same sampling, FEA, dataset and model code can serve several families that
share one operating principle -- fixed at ``X=0``, a single transverse tip
load, linear elasticity.

Every shape exposes the same contract:

* active parameters with defaults, labels and design-space ranges,
* ``validate`` rules that keep designs manufacturable and meshable,
* an analytic ``mass_mm3``,
* a transparent beam-theory ``nominal_baseline`` (reference only, never a
  label),
* dimensionless ``engineered_features`` used by the surrogates,
* a ``roi_mask`` locating the stress-raisers that the ROI target tracks,
* the load direction expressed as a CalculiX DOF and sign.

The gmsh/OCC geometry builders live in :mod:`surrosim.geometry` so that this
module stays importable without a meshing stack.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
import re
from typing import TYPE_CHECKING, Callable

import numpy as np

if TYPE_CHECKING:  # pragma: no cover - typing only
    from .plate import Plate

PLATE = "plate"
MULTI_HOLE = "multi_hole"
TAPER = "taper"
STEPPED = "stepped"
I_BEAM = "i_beam"
L_BRACKET = "l_bracket"

SHAPE_KINDS: tuple[str, ...] = (
    PLATE, MULTI_HOLE, TAPER, STEPPED, I_BEAM, L_BRACKET,
)


@dataclass(frozen=True)
class Param:
    """A user-facing design parameter with a design-space range."""

    name: str
    label: str
    unit: str = "mm"
    low: float | None = None
    high: float | None = None
    sampled: bool = True

    def bounds(self) -> tuple[float, float] | None:
        if self.low is None or self.high is None:
            return None
        return (self.low, self.high)


def _finite(value: float) -> bool:
    return isinstance(value, (int, float)) and math.isfinite(value)


def _plate_like_params() -> tuple[Param, ...]:
    return (
        Param("length_mm", "Length", low=100.0, high=160.0),
        Param("width_mm", "Width", low=30.0, high=60.0),
        Param("thickness_mm", "Thickness", low=4.0, high=10.0),
        Param("hole_diameter_mm", "Hole diameter", low=0.0, high=27.0),
        Param("hole_x_mm", "Hole position", low=35.0, high=104.0),
        Param("force_n", "Tip force", unit="N", low=100.0, high=800.0),
    )


@dataclass(frozen=True)
class ShapeSpec:
    kind: str
    label: str
    summary: str
    params: tuple[Param, ...]
    load_dof: int
    load_sign: float
    has_hole: bool
    has_fillet: bool

    def param(self, name: str) -> Param | None:
        for entry in self.params:
            if entry.name == name:
                return entry
        return None


SPECS: dict[str, ShapeSpec] = {
    PLATE: ShapeSpec(
        kind=PLATE,
        label="Plate with hole",
        summary=(
            "Rectangular cantilever plate with an optional circular through-hole "
            "(the v1 geometry family)."
        ),
        params=_plate_like_params(),
        load_dof=3,
        load_sign=-1.0,
        has_hole=True,
        has_fillet=False,
    ),
    MULTI_HOLE: ShapeSpec(
        kind=MULTI_HOLE,
        label="Two-hole plate",
        summary=(
            "Rectangular cantilever plate with two circular through-holes along "
            "the beam axis."
        ),
        params=_plate_like_params()
        + (
            Param("hole2_diameter_mm", "Second hole diameter", low=0.0, high=20.0),
            Param("hole2_x_mm", "Second hole position", low=55.0, high=130.0),
        ),
        load_dof=3,
        load_sign=-1.0,
        has_hole=True,
        has_fillet=False,
    ),
    TAPER: ShapeSpec(
        kind=TAPER,
        label="Tapered plate",
        summary=(
            "Cantilever plate whose width tapers linearly from the clamp to the "
            "tip, with an optional circular through-hole."
        ),
        params=_plate_like_params()
        + (Param("tip_width_mm", "Tip width", low=10.0, high=60.0),),
        load_dof=3,
        load_sign=-1.0,
        has_hole=True,
        has_fillet=False,
    ),
    STEPPED: ShapeSpec(
        kind=STEPPED,
        label="Stepped plate",
        summary=(
            "Cantilever plate with a thickness step, filleted at the re-entrant "
            "corner to keep the stress concentration finite."
        ),
        params=(
            Param("length_mm", "Length", low=100.0, high=160.0),
            Param("width_mm", "Width", low=30.0, high=60.0),
            Param("thickness_mm", "Root thickness", low=6.0, high=12.0),
            Param("step_x_mm", "Step position", low=30.0, high=96.0),
            Param("step_thickness_mm", "Tip thickness", low=2.4, high=9.0),
            Param("fillet_radius_mm", "Fillet radius", low=0.4, high=3.0),
            Param("force_n", "Tip force", unit="N", low=100.0, high=800.0),
        ),
        load_dof=3,
        load_sign=-1.0,
        has_hole=False,
        has_fillet=True,
    ),
    I_BEAM: ShapeSpec(
        kind=I_BEAM,
        label="I-beam",
        summary=(
            "Cantilever with a parametric I-section profile; the four web/flange "
            "junctions are filleted."
        ),
        params=(
            Param("length_mm", "Length", low=100.0, high=160.0),
            Param("beam_depth_mm", "Depth", low=30.0, high=60.0),
            Param("flange_width_mm", "Flange width", low=25.0, high=60.0),
            Param("flange_thickness_mm", "Flange thickness", low=3.5, high=12.0),
            Param("web_thickness_mm", "Web thickness", low=3.0, high=12.0),
            Param("fillet_radius_mm", "Fillet radius", low=0.8, high=3.0),
            Param("force_n", "Tip force", unit="N", low=100.0, high=800.0),
        ),
        load_dof=3,
        load_sign=-1.0,
        has_hole=False,
        has_fillet=True,
    ),
    L_BRACKET: ShapeSpec(
        kind=L_BRACKET,
        label="L-bracket",
        summary=(
            "L-shaped cantilever bracket loaded sideways at the top of the "
            "vertical leg; the inner corner is filleted."
        ),
        params=(
            Param("length_mm", "Base length", low=60.0, high=120.0),
            Param("height_mm", "Height", low=60.0, high=140.0),
            Param("width_mm", "Width", low=20.0, high=45.0),
            Param("thickness_mm", "Leg thickness", low=5.0, high=12.0),
            Param("fillet_radius_mm", "Fillet radius", low=0.6, high=3.5),
            Param("force_n", "Tip force", unit="N", low=100.0, high=800.0),
        ),
        load_dof=1,
        load_sign=-1.0,
        has_hole=False,
        has_fillet=True,
    ),
}


def spec(kind: str) -> ShapeSpec:
    try:
        return SPECS[kind]
    except KeyError as exc:
        raise ValueError(
            f"Unknown shape {kind!r}; available: {sorted(SPECS)}"
        ) from exc


def shape_of(design: "Plate") -> str:
    return getattr(design, "shape", PLATE) or PLATE


def case_id(prefix: str, design: "Plate") -> str:
    """Filesystem-safe case identifier for a design."""
    parts = [prefix, shape_of(design)]
    parts.extend(
        f"{name}={float(value):.4g}"
        for name, value in design.active_params().items()
    )
    return re.sub(r"[^0-9A-Za-z_=.-]+", "p", "_".join(parts))


def shape_holes(design: "Plate") -> list[tuple[float, float, float]]:
    """Active through-holes as ``(x_mm, y_mm, diameter_mm)``."""
    holes: list[tuple[float, float, float]] = []
    if shape_of(design) in (PLATE, MULTI_HOLE, TAPER):
        if design.hole_diameter_mm > 0:
            holes.append((design.hole_x_mm, 0.0, design.hole_diameter_mm))
    if shape_of(design) == MULTI_HOLE and design.hole2_diameter_mm > 0:
        holes.append((design.hole2_x_mm, 0.0, design.hole2_diameter_mm))
    return holes


def fillet_radius(design: "Plate") -> float:
    kind = shape_of(design)
    if kind in (STEPPED, I_BEAM, L_BRACKET):
        return float(design.fillet_radius_mm)
    return 0.0


def characteristic_thickness(design: "Plate") -> float:
    kind = shape_of(design)
    if kind == STEPPED:
        return min(design.thickness_mm, design.step_thickness_mm)
    if kind == I_BEAM:
        return min(design.flange_thickness_mm, design.web_thickness_mm)
    return design.thickness_mm


def characteristic_width(design: "Plate") -> float:
    kind = shape_of(design)
    if kind == I_BEAM:
        return design.flange_width_mm
    return design.width_mm


def _tiny(design: "Plate") -> float:
    return 1e-6 * max(1.0, design.length_mm)


def _validate_plate_like(design: "Plate") -> None:
    if design.hole_diameter_mm < 0:
        raise ValueError("hole_diameter_mm must be non-negative")
    if design.hole_diameter_mm >= design.width_mm:
        raise ValueError("hole must fit inside the width")
    if design.hole_diameter_mm > 0:
        radius = design.hole_diameter_mm / 2
        if not radius < design.hole_x_mm < design.length_mm - radius:
            raise ValueError("hole must not intersect the clamped or loaded end")


def validate_plate(design: "Plate") -> None:
    _validate_plate_like(design)


def validate_multi_hole(design: "Plate") -> None:
    _validate_plate_like(design)
    if design.hole2_diameter_mm < 0:
        raise ValueError("hole2_diameter_mm must be non-negative")
    if design.hole2_diameter_mm >= design.width_mm:
        raise ValueError("second hole must fit inside the width")
    if design.hole2_diameter_mm > 0:
        radius = design.hole2_diameter_mm / 2
        if not radius < design.hole2_x_mm < design.length_mm - radius:
            raise ValueError("second hole must not intersect the ends")
    if design.hole_diameter_mm > 0 and design.hole2_diameter_mm > 0:
        gap = abs(design.hole2_x_mm - design.hole_x_mm)
        required = 0.5 * (design.hole_diameter_mm + design.hole2_diameter_mm) + 1.0
        if gap < required:
            raise ValueError("holes must be separated by at least 1 mm of material")


def validate_taper(design: "Plate") -> None:
    if design.tip_width_mm <= 0:
        raise ValueError("tip_width_mm must be positive")
    if design.tip_width_mm > design.width_mm:
        raise ValueError("tip_width_mm must not exceed the root width")
    if design.hole_diameter_mm < 0:
        raise ValueError("hole_diameter_mm must be non-negative")
    if design.hole_diameter_mm > 0:
        radius = design.hole_diameter_mm / 2
        if not radius < design.hole_x_mm < design.length_mm - radius:
            raise ValueError("hole must not intersect the clamped or loaded end")
        local_width = design.width_mm + (
            design.tip_width_mm - design.width_mm
        ) * design.hole_x_mm / design.length_mm
        if design.hole_diameter_mm >= local_width:
            raise ValueError("hole must fit inside the local tapered width")


def validate_stepped(design: "Plate") -> None:
    if not 0 < design.step_x_mm < design.length_mm:
        raise ValueError("step_x_mm must lie strictly inside the length")
    if not 0 < design.step_thickness_mm < design.thickness_mm:
        raise ValueError("step_thickness_mm must be smaller than the root thickness")
    if design.fillet_radius_mm <= 0:
        raise ValueError("fillet_radius_mm must be positive for a stepped plate")
    max_radius = 0.9 * 0.5 * (design.thickness_mm - design.step_thickness_mm)
    if design.fillet_radius_mm > max_radius:
        raise ValueError(
            "fillet_radius_mm is too large for the step height "
            f"(max {max_radius:.3g} mm)"
        )
    if design.fillet_radius_mm > 0.5 * (design.length_mm - design.step_x_mm):
        raise ValueError("fillet_radius_mm is too large for the remaining length")


def validate_i_beam(design: "Plate") -> None:
    if design.flange_width_mm <= 0 or design.beam_depth_mm <= 0:
        raise ValueError("beam depth and flange width must be positive")
    if not 0 < design.flange_thickness_mm < 0.5 * design.beam_depth_mm:
        raise ValueError("flange_thickness_mm must be smaller than half the depth")
    if not 0 < design.web_thickness_mm < design.flange_width_mm:
        raise ValueError("web_thickness_mm must be smaller than the flange width")
    if design.fillet_radius_mm <= 0:
        raise ValueError("fillet_radius_mm must be positive for an I-beam")
    max_radius = 0.8 * min(
        design.flange_thickness_mm,
        0.5 * (design.flange_width_mm - design.web_thickness_mm),
        0.5 * design.beam_depth_mm - design.flange_thickness_mm,
    )
    if design.fillet_radius_mm > max_radius:
        raise ValueError(
            f"fillet_radius_mm is too large for this section (max {max_radius:.3g} mm)"
        )


def validate_l_bracket(design: "Plate") -> None:
    if design.height_mm <= design.thickness_mm:
        raise ValueError("height_mm must exceed the leg thickness")
    if design.fillet_radius_mm <= 0:
        raise ValueError("fillet_radius_mm must be positive for an L-bracket")
    max_radius = 0.8 * min(
        design.thickness_mm,
        design.height_mm - design.thickness_mm,
        design.length_mm - design.thickness_mm,
    )
    if design.fillet_radius_mm > max_radius:
        raise ValueError(
            f"fillet_radius_mm is too large for this bracket (max {max_radius:.3g} mm)"
        )


VALIDATORS: dict[str, Callable[["Plate"], None]] = {
    PLATE: validate_plate,
    MULTI_HOLE: validate_multi_hole,
    TAPER: validate_taper,
    STEPPED: validate_stepped,
    I_BEAM: validate_i_beam,
    L_BRACKET: validate_l_bracket,
}


def mass_mm3(design: "Plate") -> float:
    kind = shape_of(design)
    if kind in (PLATE, MULTI_HOLE):
        volume = design.length_mm * design.width_mm * design.thickness_mm
    elif kind == TAPER:
        volume = (
            0.5
            * (design.width_mm + design.tip_width_mm)
            * design.length_mm
            * design.thickness_mm
        )
    elif kind == STEPPED:
        volume = (
            design.step_x_mm * design.width_mm * design.thickness_mm
            + (design.length_mm - design.step_x_mm)
            * design.width_mm
            * design.step_thickness_mm
        )
        volume += (
            2.0
            * design.fillet_radius_mm**2
            * (1.0 - math.pi / 4.0)
            * design.width_mm
        )
    elif kind == I_BEAM:
        area = (
            2.0 * design.flange_width_mm * design.flange_thickness_mm
            + (design.beam_depth_mm - 2.0 * design.flange_thickness_mm)
            * design.web_thickness_mm
        )
        area += 4.0 * design.fillet_radius_mm**2 * (1.0 - math.pi / 4.0)
        volume = area * design.length_mm
    elif kind == L_BRACKET:
        area = (
            design.length_mm * design.thickness_mm
            + design.thickness_mm * (design.height_mm - 0.5 * design.thickness_mm)
        )
        area += design.fillet_radius_mm**2 * (1.0 - math.pi / 4.0)
        volume = area * design.width_mm
    else:  # pragma: no cover - guarded by spec()
        raise ValueError(f"Unknown shape {kind!r}")
    for _x, _y, diameter in shape_holes(design):
        radius = diameter / 2.0
        volume -= math.pi * radius**2 * characteristic_thickness(design)
    return volume


def _trapezoid(values: np.ndarray, xs: np.ndarray) -> float:
    return float(np.sum(0.5 * (values[:-1] + values[1:]) * np.diff(xs)))


def nominal_baseline(design: "Plate") -> dict[str, float]:
    kind = shape_of(design)
    length = design.length_mm
    force = abs(design.force_n)
    modulus = design.youngs_modulus_mpa
    if kind == PLATE:
        inertia = design.width_mm * design.thickness_mm**3 / 12.0
        return {
            "nominal_root_bending_stress_mpa": (
                force * length * design.thickness_mm / (2.0 * inertia)
            ),
            "nominal_tip_displacement_mm": (
                force * length**3 / (3.0 * modulus * inertia)
            ),
        }
    if kind == MULTI_HOLE:
        inertia = design.width_mm * design.thickness_mm**3 / 12.0
        return {
            "nominal_root_bending_stress_mpa": (
                force * length * design.thickness_mm / (2.0 * inertia)
            ),
            "nominal_tip_displacement_mm": (
                force * length**3 / (3.0 * modulus * inertia)
            ),
        }
    if kind == TAPER:
        width, tip = design.width_mm, design.tip_width_mm
        thickness = design.thickness_mm
        xs = np.linspace(0.0, length, 256)
        widths = width + (tip - width) * xs / length
        inertia = widths * thickness**3 / 12.0
        root_inertia = width * thickness**3 / 12.0
        integrand = (length - xs) ** 2 / (modulus * inertia)
        displacement = force * _trapezoid(integrand, xs)
        return {
            "nominal_root_bending_stress_mpa": (
                force * length * thickness / (2.0 * root_inertia)
            ),
            "nominal_tip_displacement_mm": displacement,
        }
    if kind == STEPPED:
        thickness, tip_thickness = design.thickness_mm, design.step_thickness_mm
        step = design.step_x_mm
        inertia_root = design.width_mm * thickness**3 / 12.0
        inertia_tip = design.width_mm * tip_thickness**3 / 12.0

        def inertia_at(x):
            return np.where(x <= step, inertia_root, inertia_tip)

        xs = np.linspace(0.0, length, 256)
        integrand = (length - xs) ** 2 / (modulus * inertia_at(xs))
        displacement = force * _trapezoid(integrand, xs)
        return {
            "nominal_root_bending_stress_mpa": (
                force * length * thickness / (2.0 * inertia_root)
            ),
            "nominal_tip_displacement_mm": displacement,
        }
    if kind == I_BEAM:
        depth, flange, tf, tw = (
            design.beam_depth_mm,
            design.flange_width_mm,
            design.flange_thickness_mm,
            design.web_thickness_mm,
        )
        inertia = (
            flange * depth**3 - (flange - tw) * (depth - 2.0 * tf) ** 3
        ) / 12.0
        return {
            "nominal_root_bending_stress_mpa": (
                force * length * (depth / 2.0) / inertia
            ),
            "nominal_tip_displacement_mm": (
                force * length**3 / (3.0 * modulus * inertia)
            ),
        }
    if kind == L_BRACKET:
        # The vertical leg behaves as a cantilever of length height - T/2,
        # loaded at its free end; the fillet is not represented.
        arm = design.height_mm - 0.5 * design.thickness_mm
        inertia = design.width_mm * design.thickness_mm**3 / 12.0
        return {
            "nominal_root_bending_stress_mpa": (
                force * arm * (design.thickness_mm / 2.0) / inertia
            ),
            "nominal_tip_displacement_mm": (
                force * arm**3 / (3.0 * modulus * inertia)
            ),
        }
    raise ValueError(f"Unknown shape {kind!r}")  # pragma: no cover


def _local_taper_width(design: "Plate", x: float) -> float:
    return design.width_mm + (design.tip_width_mm - design.width_mm) * (
        x / design.length_mm
    )


def engineered_features(design: "Plate") -> dict[str, float]:
    """Dimensionless descriptors shared by every shape (0 when not applicable)."""
    kind = shape_of(design)
    thickness = characteristic_thickness(design)
    width = characteristic_width(design)
    length = design.length_mm
    features = {
        "hole_width_ratio": 0.0,
        "hole_position_ratio": 0.0,
        "hole_thickness_ratio": 0.0,
        "hole2_width_ratio": 0.0,
        "hole2_position_ratio": 0.0,
        "taper_ratio": 0.0,
        "step_thickness_ratio": 0.0,
        "step_position_ratio": 0.0,
        "fillet_radius_ratio": 0.0,
        "beam_depth_ratio": 0.0,
        "flange_thickness_ratio": 0.0,
        "web_thickness_ratio": 0.0,
        "bracket_height_ratio": 0.0,
        "slenderness": length / max(thickness, 1e-9),
        "width_thickness_ratio": width / max(thickness, 1e-9),
        "load_parameter": abs(design.force_n)
        / max(design.youngs_modulus_mpa * width * thickness, 1e-9),
        "mass_parameter": mass_mm3(design)
        / max(length * width * thickness, 1e-9),
    }
    if kind in (PLATE, MULTI_HOLE, TAPER):
        reference = (
            _local_taper_width(design, design.hole_x_mm)
            if kind == TAPER
            else design.width_mm
        )
        if design.hole_diameter_mm > 0:
            features["hole_width_ratio"] = design.hole_diameter_mm / reference
            features["hole_thickness_ratio"] = design.hole_diameter_mm / thickness
        features["hole_position_ratio"] = design.hole_x_mm / length
    if kind == MULTI_HOLE:
        if design.hole2_diameter_mm > 0:
            features["hole2_width_ratio"] = (
                design.hole2_diameter_mm / design.width_mm
            )
        features["hole2_position_ratio"] = design.hole2_x_mm / length
    if kind == TAPER:
        features["taper_ratio"] = design.tip_width_mm / design.width_mm
    if kind == STEPPED:
        features["step_thickness_ratio"] = (
            design.step_thickness_mm / design.thickness_mm
        )
        features["step_position_ratio"] = design.step_x_mm / length
        features["fillet_radius_ratio"] = design.fillet_radius_mm / thickness
    if kind == I_BEAM:
        features["beam_depth_ratio"] = design.beam_depth_mm / length
        features["flange_thickness_ratio"] = (
            design.flange_thickness_mm / design.beam_depth_mm
        )
        features["web_thickness_ratio"] = (
            design.web_thickness_mm / design.flange_width_mm
        )
        features["fillet_radius_ratio"] = (
            design.fillet_radius_mm / design.flange_thickness_mm
        )
    if kind == L_BRACKET:
        features["fillet_radius_ratio"] = design.fillet_radius_mm / design.thickness_mm
        features["bracket_height_ratio"] = design.height_mm / length
    return features


def roi_mask(coordinates: np.ndarray, design: "Plate") -> np.ndarray:
    """Boolean mask of nodes inside the shape's stress-riser region of interest."""
    coordinates = np.asarray(coordinates, dtype=float)
    count = coordinates.shape[0]
    mask = np.zeros(count, dtype=bool)
    kind = shape_of(design)
    hole_mask = np.zeros(count, dtype=bool)
    for x, y, diameter in shape_holes(design):
        radius = 1.5 * diameter
        distance = np.sqrt((coordinates[:, 0] - x) ** 2 + coordinates[:, 1] ** 2)
        hole_mask |= distance <= radius
    hole_mask &= coordinates[:, 0] >= 0.1 * design.length_mm
    if kind in (PLATE, MULTI_HOLE, TAPER):
        mask |= hole_mask
    elif kind == STEPPED:
        radius = max(design.fillet_radius_mm, _tiny(design))
        surface = design.step_thickness_mm / 2.0
        distance = np.sqrt(
            (coordinates[:, 0] - design.step_x_mm) ** 2
            + (np.abs(coordinates[:, 2]) - surface) ** 2
        )
        mask |= (distance <= 2.5 * radius) & (
            coordinates[:, 0] >= 0.1 * design.length_mm
        )
    elif kind == I_BEAM:
        radius = max(design.fillet_radius_mm, _tiny(design))
        web = design.web_thickness_mm / 2.0
        flange = design.beam_depth_mm / 2.0 - design.flange_thickness_mm
        near_web = np.abs(np.abs(coordinates[:, 1]) - web) <= 3.0 * radius
        near_flange = np.abs(np.abs(coordinates[:, 2]) - flange) <= 3.0 * radius
        mask |= (near_web & near_flange) & (
            coordinates[:, 0] >= 0.1 * design.length_mm
        )
    elif kind == L_BRACKET:
        radius = max(design.fillet_radius_mm, _tiny(design))
        distance = np.sqrt(
            (coordinates[:, 0] - (design.length_mm - design.thickness_mm)) ** 2
            + (coordinates[:, 2] - design.thickness_mm / 2.0) ** 2
        )
        mask |= distance <= 2.5 * radius
    return mask


def area_of_interest_definition(design: "Plate") -> dict:
    kind = shape_of(design)
    holes = shape_holes(design)
    if kind in (PLATE, MULTI_HOLE, TAPER):
        return {
            "enabled": bool(holes),
            "kind": "hole_cylinder",
            "holes": [{"x_mm": x, "y_mm": y, "diameter_mm": d} for x, y, d in holes],
            "radius_factor": 1.5,
            "clamp_exclusion_x_mm": 0.1 * design.length_mm,
        }
    if kind == STEPPED:
        return {
            "enabled": True,
            "kind": "reentrant_fillet",
            "x_mm": design.step_x_mm,
            "z_mm": design.step_thickness_mm / 2.0,
            "peak_radius_mm": 2.5 * design.fillet_radius_mm,
        }
    if kind == I_BEAM:
        return {
            "enabled": True,
            "kind": "web_flange_fillets",
            "radius_mm": 3.0 * design.fillet_radius_mm,
            "web_half_mm": design.web_thickness_mm / 2.0,
            "flange_offset_mm": (
                design.beam_depth_mm / 2.0 - design.flange_thickness_mm
            ),
        }
    if kind == L_BRACKET:
        return {
            "enabled": True,
            "kind": "reentrant_fillet",
            "x_mm": design.length_mm - design.thickness_mm,
            "z_mm": design.thickness_mm / 2.0,
            "peak_radius_mm": 2.5 * design.fillet_radius_mm,
        }
    return {"enabled": False, "kind": "none"}

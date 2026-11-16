"""Parametric design record plus a transparent *nominal* beam benchmark.

SurroSim designs are flat, immutable records.  The original v1 record was a
rectangular cantilever plate with an optional through-hole; the same record
now carries a ``shape`` discriminator and a superset of parameters for the
supported geometry families (see :mod:`surrosim.shapes`).  Parameters that are
inactive for a shape keep neutral values, so old datasets, model registries
and API clients continue to work unchanged.

Units throughout: mm, N, MPa (= N/mm^2).  The nominal formulas ignore holes,
steps, shear deformation and local clamp/load effects; they are NOT FEA
labels.
"""

from dataclasses import asdict, dataclass, fields
import math
from typing import Mapping

from . import shapes


@dataclass(frozen=True)
class Plate:
    shape: str = shapes.PLATE
    length_mm: float = 120.0
    width_mm: float = 40.0
    thickness_mm: float = 6.0
    hole_diameter_mm: float = 12.0
    hole_x_mm: float = 60.0
    hole2_diameter_mm: float = 0.0
    hole2_x_mm: float = 0.0
    tip_width_mm: float = 40.0
    step_x_mm: float = 60.0
    step_thickness_mm: float = 6.0
    fillet_radius_mm: float = 0.0
    flange_width_mm: float = 40.0
    beam_depth_mm: float = 40.0
    flange_thickness_mm: float = 6.0
    web_thickness_mm: float = 5.0
    height_mm: float = 90.0
    force_n: float = 500.0
    youngs_modulus_mpa: float = 210_000.0
    poisson_ratio: float = 0.3
    mesh_size_mm: float = 3.0

    @classmethod
    def field_names(cls) -> tuple[str, ...]:
        return tuple(field.name for field in fields(cls))

    @classmethod
    def from_mapping(cls, values: Mapping) -> "Plate":
        """Build a design from a mapping, filling defaults and coercing floats."""
        payload: dict = {}
        for name in cls.field_names():
            if name not in values:
                continue
            raw = values[name]
            if raw is None or raw == "":
                continue
            if isinstance(raw, float) and math.isnan(raw):
                continue
            if name == "shape":
                payload[name] = str(raw)
            else:
                payload[name] = float(raw)
        return cls(**payload)

    def validate(self) -> None:
        if self.shape not in shapes.SHAPE_KINDS:
            raise ValueError(
                f"Unknown shape {self.shape!r}; available: {sorted(shapes.SHAPE_KINDS)}"
            )
        values = asdict(self)
        for name, value in values.items():
            if name == "shape":
                continue
            if not math.isfinite(value):
                raise ValueError(f"{name} must be finite")
        for name in (
            "length_mm", "width_mm", "thickness_mm",
            "youngs_modulus_mpa", "mesh_size_mm",
        ):
            if values[name] <= 0:
                raise ValueError(f"{name} must be positive")
        if not -1.0 < self.poisson_ratio < 0.5:
            raise ValueError("poisson_ratio must lie strictly between -1 and 0.5")
        shapes.VALIDATORS[self.shape](self)
        if self.shape != shapes.PLATE and (
            self.mesh_size_mm >= shapes.characteristic_thickness(self)
        ):
            raise ValueError(
                "mesh_size_mm must be smaller than the smallest outer dimension"
            )

    def mass_g(self) -> float:
        return shapes.mass_mm3(self) * 7.85e-6 * 1000.0

    def nominal_baseline(self) -> dict[str, float]:
        """Transparent cantilever reference; not an FEA label."""
        self.validate()
        return shapes.nominal_baseline(self)

    def as_dict(self) -> dict:
        return asdict(self)

    def active_params(self) -> dict:
        """Only the parameters that matter for this shape."""
        spec = shapes.spec(self.shape)
        names = {param.name for param in spec.params}
        values = self.as_dict()
        return {name: values[name] for name in names if name in values}

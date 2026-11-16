"""Constrained mass-minimisation problem for parametric cantilever designs.

For the plate family the design variables stay the v1 set (width, thickness,
hole-diameter ratio, hole-position ratio). Other shapes optimise the unit-cube
factors of their design space, which keeps the same mapping used for dataset
sampling, so every point the optimizer visits is a valid, meshable design.
Constraints are the surrogate-predicted global and stress-riser Von Mises
stresses and the maximum displacement. Mass is computed analytically from the
geometry.
"""

from dataclasses import dataclass, field, replace

import numpy as np

from .. import shapes
from ..mesh_policy import DEFAULT_POLICY
from ..plate import Plate
from ..sampling import shape_space

STEEL_DENSITY_KG_PER_MM3 = 7.85e-6  # 7850 kg/m^3


@dataclass(frozen=True)
class OptimizationProblem:
    shape: str = shapes.PLATE
    length_mm: float = 120.0
    force_n: float = 500.0
    youngs_modulus_mpa: float = 210_000.0
    poisson_ratio: float = 0.3
    sigma_allow_mpa: float = 180.0
    displacement_limit_mm: float = 1.5
    width_bounds: tuple[float, float] = (30.0, 60.0)
    thickness_bounds: tuple[float, float] = (4.0, 10.0)
    diameter_ratio_bounds: tuple[float, float] = (0.0, 0.45)
    hole_x_ratio_bounds: tuple[float, float] = (0.35, 0.65)
    density_kg_per_mm3: float = STEEL_DENSITY_KG_PER_MM3
    parameter_names: tuple[str, ...] = field(init=False)

    def __post_init__(self) -> None:
        shapes.spec(self.shape)
        if self.shape == shapes.PLATE:
            object.__setattr__(
                self,
                "parameter_names",
                ("width_mm", "thickness_mm", "diameter_ratio", "hole_x_ratio"),
            )
        else:
            object.__setattr__(
                self,
                "parameter_names",
                tuple(shape_space(self.shape).factors),
            )

    @property
    def bounds(self) -> list[tuple[float, float]]:
        if self.shape == shapes.PLATE:
            return [
                self.width_bounds,
                self.thickness_bounds,
                self.diameter_ratio_bounds,
                self.hole_x_ratio_bounds,
            ]
        return [(0.0, 1.0)] * shape_space(self.shape).dimensions()

    def design_from_vector(self, u: np.ndarray) -> dict:
        if self.shape == shapes.PLATE:
            width, thickness, diameter_ratio, hole_x_ratio = (
                float(value) for value in u
            )
            design = Plate(
                shape=shapes.PLATE,
                length_mm=self.length_mm,
                width_mm=width,
                thickness_mm=thickness,
                hole_diameter_mm=diameter_ratio * width,
                hole_x_mm=hole_x_ratio * self.length_mm,
                force_n=self.force_n,
                youngs_modulus_mpa=self.youngs_modulus_mpa,
                poisson_ratio=self.poisson_ratio,
            )
            design.validate()
            return design.as_dict()
        space = shape_space(self.shape)
        design = space.design_from_unit(tuple(float(value) for value in u))
        design = replace(
            design,
            length_mm=self.length_mm,
            force_n=self.force_n,
            youngs_modulus_mpa=self.youngs_modulus_mpa,
            poisson_ratio=self.poisson_ratio,
        )
        design.validate()
        return design.as_dict()

    def plate(self, design: dict) -> Plate:
        return Plate.from_mapping(design)

    def mass_g(self, design: dict) -> float:
        return (
            shapes.mass_mm3(Plate.from_mapping(design))
            * self.density_kg_per_mm3
            * 1000.0
        )

    def violations(self, design: dict, stress_mpa: float, displacement_mm: float) -> dict:
        return {
            "stress_ratio": stress_mpa / self.sigma_allow_mpa,
            "displacement_ratio": displacement_mm / self.displacement_limit_mm,
        }

    def feasible(self, design: dict, stress_mpa: float, displacement_mm: float) -> bool:
        ratios = self.violations(design, stress_mpa, displacement_mm)
        return ratios["stress_ratio"] <= 1.0 and ratios["displacement_ratio"] <= 1.0

    def as_dict(self) -> dict:
        return {
            "shape": self.shape,
            "length_mm": self.length_mm,
            "force_n": self.force_n,
            "sigma_allow_mpa": self.sigma_allow_mpa,
            "displacement_limit_mm": self.displacement_limit_mm,
            "parameter_names": list(self.parameter_names),
            "bounds": [list(entry) for entry in self.bounds],
            "width_bounds": list(self.width_bounds),
            "thickness_bounds": list(self.thickness_bounds),
            "diameter_ratio_bounds": list(self.diameter_ratio_bounds),
            "hole_x_ratio_bounds": list(self.hole_x_ratio_bounds),
            "density_kg_per_mm3": self.density_kg_per_mm3,
            "mesh_policy": DEFAULT_POLICY.as_dict(),
        }

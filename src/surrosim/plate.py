"""Plate dimensions and a transparent *nominal* beam-theory benchmark.

Units throughout: mm, N, MPa (= N/mm^2). These formulas ignore the hole,
shear deformation, and local clamp/load effects; they are NOT FEA labels.
"""

from dataclasses import asdict, dataclass
import math


@dataclass(frozen=True)
class Plate:
    length_mm: float = 120.0
    width_mm: float = 40.0
    thickness_mm: float = 6.0
    hole_diameter_mm: float = 12.0
    hole_x_mm: float = 60.0
    force_n: float = 500.0
    youngs_modulus_mpa: float = 210_000.0
    poisson_ratio: float = 0.3
    mesh_size_mm: float = 3.0

    def validate(self) -> None:
        values = asdict(self)
        for name, value in values.items():
            if not math.isfinite(value):
                raise ValueError(f"{name} must be finite")
        for name in (
            "length_mm", "width_mm", "thickness_mm", "hole_diameter_mm",
            "youngs_modulus_mpa", "mesh_size_mm",
        ):
            if values[name] <= 0:
                raise ValueError(f"{name} must be positive")
        if not -1.0 < self.poisson_ratio < 0.5:
            raise ValueError("poisson_ratio must lie strictly between -1 and 0.5")
        if self.hole_diameter_mm >= self.width_mm:
            raise ValueError("hole must fit inside the width")
        radius = self.hole_diameter_mm / 2
        if not radius < self.hole_x_mm < self.length_mm - radius:
            raise ValueError("hole must not intersect the clamped or loaded end")
        if self.mesh_size_mm >= min(self.length_mm, self.width_mm, self.thickness_mm):
            raise ValueError("mesh_size_mm must be smaller than the smallest outer dimension")

    def nominal_baseline(self) -> dict[str, float]:
        """Euler-Bernoulli cantilever reference (unperforated rectangle).

        Force is applied in the negative Z direction at X=length; plate
        thickness is along Z. The quoted stress is root bending stress,
        not Von Mises stress around the hole.
        """
        self.validate()
        i_mm4 = self.width_mm * self.thickness_mm**3 / 12.0
        return {
            "nominal_root_bending_stress_mpa": (
                abs(self.force_n) * self.length_mm * self.thickness_mm
                / (2.0 * i_mm4)
            ),
            "nominal_tip_displacement_mm": (
                abs(self.force_n) * self.length_mm**3
                / (3.0 * self.youngs_modulus_mpa * i_mm4)
            ),
        }

    def as_dict(self) -> dict[str, float]:
        return asdict(self)

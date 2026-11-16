"""Production mesh policies for dataset generation.

Two profiles are defined:

* ``production`` — second-order tetrahedra with global size
  ``min(3.0 mm, t_char / 2)`` where ``t_char`` is the shape's characteristic
  thickness, and stress-raisers (holes, fillets) graded to
  ``min(0.6 x global, feature / 10)``. This is the policy validated in
  ``reports/validation/`` for trustworthy scalar labels.
* ``graph`` — a coarser profile for geometric-deep-learning field prediction:
   global size ``clamp(t_char / 1.5, 2.5, 4.0)`` (the floor is waived
   when it would reach/exceed a non-plate section thickness) and raisers graded to
  ``min(0.6 x global, feature / 6)``. Coarse meshes keep message-passing
  training affordable on consumer GPUs; scalar labels for the accurate
  surrogate pipeline still come from the production profile.

Both profiles are recorded per case in ``metadata.json`` / ``run.json`` so
every artifact stays reproducible.
"""

from dataclasses import dataclass

from . import shapes
from .plate import Plate

PRODUCTION_ELEMENT_ORDER = 2


@dataclass(frozen=True)
class MeshPolicy:
    name: str = "production"
    element_order: int = PRODUCTION_ELEMENT_ORDER
    global_size_factor: float = 2.0
    global_size_cap_mm: float = 3.0
    global_size_floor_mm: float = 0.0
    hole_size_fraction: float = 0.10
    hole_grading_fraction: float = 0.60
    fillet_size_fraction: float = 0.60

    def global_size_mm(self, design: Plate) -> float:
        thickness = shapes.characteristic_thickness(design)
        size = min(self.global_size_cap_mm, thickness / self.global_size_factor)
        floored = round(max(self.global_size_floor_mm, size), 6)
        if design.shape != shapes.PLATE and floored >= thickness:
            return round(size, 6)
        return floored

    def refinement_mm(self, design: Plate) -> float:
        global_size = self.global_size_mm(design)
        candidates: list[float] = []
        for _x, _y, diameter in shapes.shape_holes(design):
            candidates.append(diameter * self.hole_size_fraction)
        radius = shapes.fillet_radius(design)
        if radius > 0:
            candidates.append(radius * self.fillet_size_fraction)
        if not candidates:
            return 0.0
        return round(
            min(self.hole_grading_fraction * global_size, *candidates), 6
        )

    def hole_refinement_mm(self, design: Plate) -> float:
        """Backwards-compatible alias for the stress-raiser refinement size."""
        return self.refinement_mm(design)

    def as_dict(self) -> dict:
        return {
            "name": self.name,
            "element_order": self.element_order,
            "global_size_factor": self.global_size_factor,
            "global_size_cap_mm": self.global_size_cap_mm,
            "global_size_floor_mm": self.global_size_floor_mm,
            "hole_size_fraction": self.hole_size_fraction,
            "hole_grading_fraction": self.hole_grading_fraction,
            "fillet_size_fraction": self.fillet_size_fraction,
        }


PRODUCTION_POLICY = MeshPolicy()
GRAPH_POLICY = MeshPolicy(
    name="graph",
    element_order=2,
    global_size_factor=1.5,
    global_size_cap_mm=4.0,
    global_size_floor_mm=2.5,
    hole_size_fraction=1.0 / 6.0,
    hole_grading_fraction=0.60,
    fillet_size_fraction=0.60,
)

POLICIES = {
    "production": PRODUCTION_POLICY,
    "graph": GRAPH_POLICY,
}
DEFAULT_POLICY = PRODUCTION_POLICY


def get_policy(name: str) -> MeshPolicy:
    try:
        return POLICIES[name]
    except KeyError as exc:
        raise ValueError(
            f"Unknown mesh profile {name!r}; available: {sorted(POLICIES)}"
        ) from exc

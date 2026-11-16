"""Reproducible design-space sampling (inputs only; NO simulation results).

Sampling is defined by an explicit :class:`DesignSpace`. Samples are drawn
with space-filling quasi-random sequences (scrambled Sobol by default,
Latin hypercube optional) and mapped to feasible :class:`Plate` designs.
Every case row carries its split assignment and a tag describing how it was
generated, so datasets remain auditable.
"""

from dataclasses import asdict, dataclass, replace
import csv
from pathlib import Path
import random
from typing import Callable, Mapping, Sequence

from . import shapes
from .mesh_policy import DEFAULT_POLICY
from .plate import Plate


@dataclass(frozen=True)
class Factor:
    low: float
    high: float

    def validate(self, name: str) -> None:
        if not self.low < self.high:
            raise ValueError(f"Factor {name} requires low < high")


@dataclass(frozen=True)
class DesignSpace:
    length_mm: Factor = Factor(100.0, 160.0)
    width_mm: Factor = Factor(30.0, 60.0)
    thickness_mm: Factor = Factor(4.0, 10.0)
    diameter_width_fraction: Factor = Factor(0.20, 0.45)
    hole_x_length_fraction: Factor = Factor(0.35, 0.65)
    force_n: Factor = Factor(100.0, 800.0)
    youngs_modulus_mpa: float = 210_000.0
    poisson_ratio: float = 0.3

    def validate(self) -> None:
        for name, factor in self.factors().items():
            factor.validate(name)
        if self.youngs_modulus_mpa <= 0:
            raise ValueError("youngs_modulus_mpa must be positive")
        if not -1.0 < self.poisson_ratio < 0.5:
            raise ValueError("poisson_ratio must lie strictly between -1 and 0.5")

    def factors(self) -> dict[str, Factor]:
        return {
            "length_mm": self.length_mm,
            "width_mm": self.width_mm,
            "thickness_mm": self.thickness_mm,
            "diameter_width_fraction": self.diameter_width_fraction,
            "hole_x_length_fraction": self.hole_x_length_fraction,
            "force_n": self.force_n,
        }

    def as_dict(self) -> dict:
        return {
            "length_mm": asdict(self.length_mm),
            "width_mm": asdict(self.width_mm),
            "thickness_mm": asdict(self.thickness_mm),
            "diameter_width_fraction": asdict(self.diameter_width_fraction),
            "hole_x_length_fraction": asdict(self.hole_x_length_fraction),
            "force_n": asdict(self.force_n),
            "youngs_modulus_mpa": self.youngs_modulus_mpa,
            "poisson_ratio": self.poisson_ratio,
        }

    def unit_samples(
        self, count: int, seed: int = 42, method: str = "sobol"
    ) -> list[tuple[float, ...]]:
        if count < 1:
            raise ValueError("count must be >= 1")
        if method == "sobol":
            from scipy.stats import qmc

            engine = qmc.Sobol(d=6, scramble=True, seed=seed)
            raw = engine.random(count)
            return [tuple(float(value) for value in row) for row in raw]
        if method == "lhs":
            from scipy.stats import qmc

            engine = qmc.LatinHypercube(d=6, seed=seed)
            raw = engine.random(count)
            return [tuple(float(value) for value in row) for row in raw]
        raise ValueError(f"Unknown sampling method: {method}")

    def corner_samples(
        self, count: int, seed: int = 4242
    ) -> list[tuple[float, ...]]:
        """Map samples into the outer 10% band of every factor."""
        if count < 1:
            raise ValueError("count must be >= 1")
        base = self.unit_samples(count, seed=seed, method="sobol")
        return [
            tuple(
                0.1 * value if value < 0.5 else 0.9 + 0.1 * (value - 0.5)
                for value in row
            )
            for row in base
        ]

    def plate_from_unit(self, unit: tuple[float, ...]) -> Plate:
        if len(unit) != 6:
            raise ValueError("unit sample must have six components")
        length = self.length_mm.low + (self.length_mm.high - self.length_mm.low) * unit[0]
        width = self.width_mm.low + (self.width_mm.high - self.width_mm.low) * unit[1]
        thickness = (
            self.thickness_mm.low
            + (self.thickness_mm.high - self.thickness_mm.low) * unit[2]
        )
        diameter = width * (
            self.diameter_width_fraction.low
            + (
                self.diameter_width_fraction.high
                - self.diameter_width_fraction.low
            )
            * unit[3]
        )
        hole_x = length * (
            self.hole_x_length_fraction.low
            + (self.hole_x_length_fraction.high - self.hole_x_length_fraction.low)
            * unit[4]
        )
        force = self.force_n.low + (self.force_n.high - self.force_n.low) * unit[5]
        plate = Plate(
            length_mm=length,
            width_mm=width,
            thickness_mm=thickness,
            hole_diameter_mm=diameter,
            hole_x_mm=hole_x,
            force_n=force,
            youngs_modulus_mpa=self.youngs_modulus_mpa,
            poisson_ratio=self.poisson_ratio,
            mesh_size_mm=1.0,
        )
        plate = replace(plate, mesh_size_mm=DEFAULT_POLICY.global_size_mm(plate))
        plate.validate()
        return plate

    def sample_plates(
        self, count: int, seed: int = 42, method: str = "sobol"
    ) -> list[Plate]:
        return [self.plate_from_unit(unit) for unit in self.unit_samples(count, seed, method)]

    def challenge_plates(
        self, count: int, seed: int = 4242, method: str = "sobol"
    ) -> list[Plate]:
        if method == "sobol":
            units = self.corner_samples(count, seed=seed)
        else:
            base = self.unit_samples(count, seed=seed, method=method)
            units = [
                tuple(
                    0.1 * value if value < 0.5 else 0.9 + 0.1 * (value - 0.5)
                    for value in row
                )
                for row in base
            ]
        return [self.plate_from_unit(unit) for unit in units]


def edge_case_designs(space: DesignSpace | None = None) -> list[tuple[str, Plate]]:
    """Explicit boundary and degeneracy cases that random sampling may miss."""
    space = space or DesignSpace()
    defaults = Plate()
    cases: list[tuple[str, Plate]] = []

    def add(tag: str, **overrides) -> None:
        values = {**defaults.as_dict(), **overrides}
        plate = Plate(**values)
        plate = replace(
            plate, mesh_size_mm=DEFAULT_POLICY.global_size_mm(plate)
        )
        plate.validate()
        cases.append((tag, plate))

    add(
        "edge_min_all",
        length_mm=space.length_mm.low, width_mm=space.width_mm.low,
        thickness_mm=space.thickness_mm.low, force_n=space.force_n.low,
        hole_diameter_mm=space.width_mm.low * space.diameter_width_fraction.low,
        hole_x_mm=space.length_mm.low * 0.5,
    )
    add(
        "edge_max_all",
        length_mm=space.length_mm.high, width_mm=space.width_mm.high,
        thickness_mm=space.thickness_mm.high, force_n=space.force_n.high,
        hole_diameter_mm=space.width_mm.high * space.diameter_width_fraction.high,
        hole_x_mm=space.length_mm.high * 0.5,
    )
    add(
        "edge_thin_hi_force",
        thickness_mm=space.thickness_mm.low, force_n=space.force_n.high,
    )
    add(
        "edge_slender",
        length_mm=space.length_mm.high, thickness_mm=space.thickness_mm.low,
        width_mm=space.width_mm.low,
    )
    add(
        "edge_stubby",
        length_mm=space.length_mm.low, thickness_mm=space.thickness_mm.high,
        width_mm=space.width_mm.high,
    )
    add(
        "edge_big_hole_max_width",
        width_mm=space.width_mm.high,
        hole_diameter_mm=space.width_mm.high * space.diameter_width_fraction.high,
    )
    add("edge_hole_near_clamp", hole_x_mm=48.0, hole_diameter_mm=12.0)
    add("edge_hole_near_load", hole_x_mm=110.0, hole_diameter_mm=12.0)
    add("edge_no_hole_min", hole_diameter_mm=0.0,
        length_mm=space.length_mm.low, width_mm=space.width_mm.low,
        thickness_mm=space.thickness_mm.low)
    add("edge_no_hole_max", hole_diameter_mm=0.0,
        length_mm=space.length_mm.high, width_mm=space.width_mm.high,
        thickness_mm=space.thickness_mm.high, force_n=space.force_n.high)
    add("edge_no_hole_nominal", hole_diameter_mm=0.0)
    add("edge_nominal", **defaults.as_dict())
    return cases


def build_design_table(
    count: int = 560,
    challenge_count: int = 72,
    seed: int = 42,
    method: str = "sobol",
    no_hole_fraction: float = 0.05,
    space: DesignSpace | None = None,
) -> list[dict]:
    """Assemble the full case table: inputs, split and provenance tag."""
    space = space or DesignSpace()
    space.validate()
    rng = random.Random(seed + 1)

    challenge = []
    if challenge_count > 0:
        challenge = [
            (f"challenge_{index:04d}", "challenge", "challenge_corner", plate)
            for index, plate in enumerate(
                space.challenge_plates(challenge_count, seed=seed + 100), start=1
            )
        ]
    edges = [
        (f"challenge_{index:04d}", "challenge", tag, plate)
        for index, (tag, plate) in enumerate(
            edge_case_designs(space), start=len(challenge) + 1
        )
    ]

    main_plates = []
    for index, plate in enumerate(space.sample_plates(count, seed=seed, method=method), start=1):
        if plate.hole_diameter_mm > 0 and rng.random() < no_hole_fraction:
            plate = replace(plate, hole_diameter_mm=0.0, hole_x_mm=plate.length_mm / 2)
            plate.validate()
        main_plates.append((f"plate_{index:04d}", plate))

    shuffled = list(range(count))
    rng.shuffle(shuffled)
    split_of: dict[int, str] = {}
    for position, original in enumerate(shuffled):
        fraction = position / count
        split_of[original] = (
            "train" if fraction < 0.70 else "val" if fraction < 0.85 else "test"
        )

    rows = []
    for index, (case_id, plate) in enumerate(main_plates):
        rows.append(
            {
                "case_id": case_id,
                "split": split_of[index],
                "tag": "main",
                **plate.as_dict(),
            }
        )
    for case_id, split, tag, plate in challenge + edges:
        rows.append({"case_id": case_id, "split": split, "tag": tag, **plate.as_dict()})
    return rows


def sample_designs(
    count: int, seed: int = 42, method: str = "sobol", space: DesignSpace | None = None
) -> list[Plate]:
    """Backwards-compatible primitive used by tests and quick experiments."""
    return (space or DesignSpace()).sample_plates(count, seed=seed, method=method)


def export_designs(path: str | Path, count: int = 560, seed: int = 42, **kwargs) -> int:
    """Write *inputs only*. Baseline and FEA outputs must not be conflated."""
    rows = build_design_table(count=count, seed=seed, **kwargs)
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys())
    with destination.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


# ---------------------------------------------------------------------------
# v2: multi-shape design spaces
# ---------------------------------------------------------------------------


def _lerp(factor: "Factor", value: float) -> float:
    return factor.low + (factor.high - factor.low) * value


def _multi_hole_mapper(space: "ShapeSpace", unit: tuple[float, ...]) -> Plate:
    length = _lerp(space.factors["length_mm"], unit[0])
    width = _lerp(space.factors["width_mm"], unit[1])
    thickness = _lerp(space.factors["thickness_mm"], unit[2])
    diameter1 = _lerp(space.factors["diameter1_width_fraction"], unit[3]) * width
    x1 = _lerp(space.factors["hole1_x_length_fraction"], unit[4]) * length
    diameter2 = _lerp(space.factors["diameter2_width_fraction"], unit[5]) * width
    x2 = _lerp(space.factors["hole2_x_length_fraction"], unit[6]) * length
    force = _lerp(space.factors["force_n"], unit[7])
    return Plate(
        shape=shapes.MULTI_HOLE, length_mm=length, width_mm=width,
        thickness_mm=thickness, hole_diameter_mm=diameter1, hole_x_mm=x1,
        hole2_diameter_mm=diameter2, hole2_x_mm=x2, force_n=force,
        youngs_modulus_mpa=space.youngs_modulus_mpa,
        poisson_ratio=space.poisson_ratio, mesh_size_mm=1.0,
    )


def _taper_mapper(space: "ShapeSpace", unit: tuple[float, ...]) -> Plate:
    length = _lerp(space.factors["length_mm"], unit[0])
    width = _lerp(space.factors["width_mm"], unit[1])
    thickness = _lerp(space.factors["thickness_mm"], unit[2])
    tip = _lerp(space.factors["tip_width_fraction"], unit[3]) * width
    x_fraction = _lerp(space.factors["hole_x_length_fraction"], unit[5])
    local = width + (tip - width) * x_fraction
    diameter = _lerp(space.factors["diameter_width_fraction"], unit[4]) * local
    hole_x = x_fraction * length
    force = _lerp(space.factors["force_n"], unit[6])
    return Plate(
        shape=shapes.TAPER, length_mm=length, width_mm=width,
        thickness_mm=thickness, hole_diameter_mm=diameter, hole_x_mm=hole_x,
        tip_width_mm=tip, force_n=force,
        youngs_modulus_mpa=space.youngs_modulus_mpa,
        poisson_ratio=space.poisson_ratio, mesh_size_mm=1.0,
    )


def _stepped_mapper(space: "ShapeSpace", unit: tuple[float, ...]) -> Plate:
    length = _lerp(space.factors["length_mm"], unit[0])
    width = _lerp(space.factors["width_mm"], unit[1])
    thickness = _lerp(space.factors["thickness_mm"], unit[2])
    step = _lerp(space.factors["step_length_fraction"], unit[3]) * length
    tip_thickness = _lerp(space.factors["tip_thickness_fraction"], unit[4]) * thickness
    radius = (
        _lerp(space.factors["fillet_fraction"], unit[5])
        * (thickness - tip_thickness)
        / 2.0
    )
    force = _lerp(space.factors["force_n"], unit[6])
    return Plate(
        shape=shapes.STEPPED, length_mm=length, width_mm=width,
        thickness_mm=thickness, step_x_mm=step, step_thickness_mm=tip_thickness,
        fillet_radius_mm=radius, force_n=force,
        youngs_modulus_mpa=space.youngs_modulus_mpa,
        poisson_ratio=space.poisson_ratio, mesh_size_mm=1.0,
    )


def _i_beam_mapper(space: "ShapeSpace", unit: tuple[float, ...]) -> Plate:
    length = _lerp(space.factors["length_mm"], unit[0])
    depth = _lerp(space.factors["beam_depth_mm"], unit[1])
    flange = _lerp(space.factors["flange_width_mm"], unit[2])
    tf = _lerp(space.factors["flange_thickness_fraction"], unit[3]) * depth
    tw = _lerp(space.factors["web_thickness_fraction"], unit[4]) * flange
    radius = _lerp(space.factors["fillet_fraction"], unit[5]) * tf
    force = _lerp(space.factors["force_n"], unit[6])
    return Plate(
        shape=shapes.I_BEAM, length_mm=length, beam_depth_mm=depth,
        flange_width_mm=flange, flange_thickness_mm=tf, web_thickness_mm=tw,
        fillet_radius_mm=radius, force_n=force,
        youngs_modulus_mpa=space.youngs_modulus_mpa,
        poisson_ratio=space.poisson_ratio, mesh_size_mm=1.0,
    )


def _l_bracket_mapper(space: "ShapeSpace", unit: tuple[float, ...]) -> Plate:
    length = _lerp(space.factors["length_mm"], unit[0])
    height = _lerp(space.factors["height_mm"], unit[1])
    width = _lerp(space.factors["width_mm"], unit[2])
    thickness = _lerp(space.factors["thickness_mm"], unit[3])
    radius = _lerp(space.factors["fillet_fraction"], unit[4]) * thickness
    force = _lerp(space.factors["force_n"], unit[5])
    return Plate(
        shape=shapes.L_BRACKET, length_mm=length, height_mm=height,
        width_mm=width, thickness_mm=thickness, fillet_radius_mm=radius,
        force_n=force, youngs_modulus_mpa=space.youngs_modulus_mpa,
        poisson_ratio=space.poisson_ratio, mesh_size_mm=1.0,
    )


MAPPERS: dict[str, Callable[["ShapeSpace", tuple[float, ...]], Plate]] = {
    shapes.MULTI_HOLE: _multi_hole_mapper,
    shapes.TAPER: _taper_mapper,
    shapes.STEPPED: _stepped_mapper,
    shapes.I_BEAM: _i_beam_mapper,
    shapes.L_BRACKET: _l_bracket_mapper,
}


@dataclass(frozen=True)
class ShapeSpace:
    kind: str
    factors: dict[str, Factor]
    youngs_modulus_mpa: float = 210_000.0
    poisson_ratio: float = 0.3

    def dimensions(self) -> int:
        return len(self.factors)

    def unit_samples(
        self, count: int, seed: int = 42, method: str = "sobol"
    ) -> list[tuple[float, ...]]:
        if count < 1:
            raise ValueError("count must be >= 1")
        if method == "sobol":
            from scipy.stats import qmc

            engine = qmc.Sobol(d=self.dimensions(), scramble=True, seed=seed)
            raw = engine.random(count)
        elif method == "lhs":
            from scipy.stats import qmc

            engine = qmc.LatinHypercube(d=self.dimensions(), seed=seed)
            raw = engine.random(count)
        else:
            raise ValueError(f"Unknown sampling method: {method}")
        return [tuple(float(value) for value in row) for row in raw]

    def corner_samples(
        self, count: int, seed: int = 4242
    ) -> list[tuple[float, ...]]:
        base = self.unit_samples(count, seed=seed, method="sobol")
        return [
            tuple(
                0.1 * value if value < 0.5 else 0.9 + 0.1 * (value - 0.5)
                for value in row
            )
            for row in base
        ]

    def design_from_unit(self, unit: tuple[float, ...]) -> Plate:
        if len(unit) != self.dimensions():
            raise ValueError(
                f"{self.kind} unit sample must have {self.dimensions()} components"
            )
        design = MAPPERS[self.kind](self, unit)
        design = replace(
            design, mesh_size_mm=DEFAULT_POLICY.global_size_mm(design)
        )
        design.validate()
        return design

    def sample_designs(
        self, count: int, seed: int = 42, method: str = "sobol"
    ) -> list[Plate]:
        return [
            self.design_from_unit(unit)
            for unit in self.unit_samples(count, seed, method)
        ]

    def challenge_designs(
        self, count: int, seed: int = 4242, method: str = "sobol"
    ) -> list[Plate]:
        units = (
            self.corner_samples(count, seed=seed)
            if method == "sobol"
            else [
                tuple(
                    0.1 * value if value < 0.5 else 0.9 + 0.1 * (value - 0.5)
                    for value in row
                )
                for row in self.unit_samples(count, seed=seed, method=method)
            ]
        )
        return [self.design_from_unit(unit) for unit in units]


def _space(kind: str, **factors: Factor) -> ShapeSpace:
    return ShapeSpace(kind=kind, factors=factors)


SHAPE_SPACES: dict[str, ShapeSpace] = {
    shapes.MULTI_HOLE: _space(
        shapes.MULTI_HOLE,
        length_mm=Factor(100.0, 160.0),
        width_mm=Factor(30.0, 60.0),
        thickness_mm=Factor(4.0, 10.0),
        diameter1_width_fraction=Factor(0.15, 0.32),
        hole1_x_length_fraction=Factor(0.20, 0.38),
        diameter2_width_fraction=Factor(0.15, 0.32),
        hole2_x_length_fraction=Factor(0.62, 0.80),
        force_n=Factor(100.0, 800.0),
    ),
    shapes.TAPER: _space(
        shapes.TAPER,
        length_mm=Factor(100.0, 160.0),
        width_mm=Factor(30.0, 60.0),
        thickness_mm=Factor(4.0, 10.0),
        tip_width_fraction=Factor(0.35, 1.0),
        diameter_width_fraction=Factor(0.20, 0.45),
        hole_x_length_fraction=Factor(0.35, 0.65),
        force_n=Factor(100.0, 800.0),
    ),
    shapes.STEPPED: _space(
        shapes.STEPPED,
        length_mm=Factor(100.0, 160.0),
        width_mm=Factor(30.0, 60.0),
        thickness_mm=Factor(8.0, 12.0),
        step_length_fraction=Factor(0.30, 0.60),
        tip_thickness_fraction=Factor(0.30, 0.55),
        fillet_fraction=Factor(0.50, 0.80),
        force_n=Factor(100.0, 800.0),
    ),
    shapes.I_BEAM: _space(
        shapes.I_BEAM,
        length_mm=Factor(100.0, 160.0),
        beam_depth_mm=Factor(40.0, 70.0),
        flange_width_mm=Factor(35.0, 70.0),
        flange_thickness_fraction=Factor(0.14, 0.22),
        web_thickness_fraction=Factor(0.12, 0.20),
        fillet_fraction=Factor(0.25, 0.35),
        force_n=Factor(100.0, 800.0),
    ),
    shapes.L_BRACKET: _space(
        shapes.L_BRACKET,
        length_mm=Factor(60.0, 120.0),
        height_mm=Factor(60.0, 140.0),
        width_mm=Factor(20.0, 45.0),
        thickness_mm=Factor(5.0, 12.0),
        fillet_fraction=Factor(0.25, 0.60),
        force_n=Factor(100.0, 800.0),
    ),
}


def shape_space(kind: str) -> ShapeSpace:
    if kind == shapes.PLATE:
        raise ValueError("the plate family uses the v1 DesignSpace")
    try:
        return SHAPE_SPACES[kind]
    except KeyError as exc:
        raise ValueError(
            f"No v2 design space for shape {kind!r}; available: {sorted(SHAPE_SPACES)}"
        ) from exc


def shape_param_bounds(kind: str, samples: int = 512) -> dict[str, list[float]]:
    """Observed parameter ranges for a shape (used by the API and the UI).

    Includes the unit-hypercube corners so the exact design-space extremes are
    captured, then widens by 1% of each span so boundary designs are not
    reported as out of domain because of sampling noise.
    """
    from itertools import product

    if kind == shapes.PLATE:
        designs = DesignSpace().sample_plates(samples, seed=7)
        plates = [
            DesignSpace().plate_from_unit(unit)
            for unit in product((0.0, 1.0), repeat=6)
        ]
        designs = designs + plates
    else:
        space = shape_space(kind)
        designs = space.sample_designs(samples, seed=7)
        designs += [
            space.design_from_unit(unit)
            for unit in product((0.0, 1.0), repeat=space.dimensions())
        ]
    active = [param.name for param in shapes.spec(kind).params]
    bounds: dict[str, list[float]] = {}
    for name in active:
        values = [getattr(design, name) for design in designs]
        low, high = min(values), max(values)
        span = (high - low) if high > low else max(abs(high), 1.0) * 1e-6
        bounds[name] = [low - 0.01 * span, high + 0.01 * span]
    return bounds


def _zero_holes(design: Plate, rng: random.Random, fraction: float) -> Plate:
    kind = shapes.shape_of(design)
    updates: dict[str, float] = {}
    if kind in (shapes.PLATE, shapes.MULTI_HOLE, shapes.TAPER):
        if design.hole_diameter_mm > 0 and rng.random() < fraction:
            updates["hole_diameter_mm"] = 0.0
            updates.setdefault("hole_x_mm", design.length_mm / 2)
    if kind == shapes.MULTI_HOLE and design.hole2_diameter_mm > 0:
        if rng.random() < fraction:
            updates["hole2_diameter_mm"] = 0.0
    if not updates:
        return design
    updated = replace(design, **updates)
    updated.validate()
    return updated


def _split_assignments(count: int, rng: random.Random) -> list[str]:
    order = list(range(count))
    rng.shuffle(order)
    assignment = [""] * count
    for position, original in enumerate(order):
        fraction = position / count
        assignment[original] = (
            "train" if fraction < 0.70 else "val" if fraction < 0.85 else "test"
        )
    return assignment


def _edge_designs(kind: str) -> list[tuple[str, Plate]]:
    """Explicit boundary cases per shape that random sampling may miss."""
    space = shape_space(kind)

    def build(tag: str, **overrides) -> tuple[str, Plate]:
        design = Plate(shape=kind, **overrides)
        design = replace(
            design, mesh_size_mm=DEFAULT_POLICY.global_size_mm(design)
        )
        design.validate()
        return (tag, design)

    length_low, length_high = space.factors["length_mm"].low, space.factors["length_mm"].high
    width_factor = space.factors.get("width_mm") or space.factors["flange_width_mm"]
    thickness_factor = (
        space.factors.get("thickness_mm") or space.factors["flange_thickness_fraction"]
    )
    width_low, width_high = width_factor.low, width_factor.high
    thickness_low, thickness_high = thickness_factor.low, thickness_factor.high
    force_low, force_high = space.factors["force_n"].low, space.factors["force_n"].high
    cases: list[tuple[str, Plate]] = []
    if kind == shapes.MULTI_HOLE:
        cases.append(build(
            "edge_min_all", length_mm=length_low, width_mm=width_low,
            thickness_mm=thickness_low, force_n=force_low,
            hole_diameter_mm=0.15 * width_low, hole_x_mm=0.30 * length_low,
            hole2_diameter_mm=0.15 * width_low, hole2_x_mm=0.70 * length_low,
        ))
        cases.append(build(
            "edge_max_all", length_mm=length_high, width_mm=width_high,
            thickness_mm=thickness_high, force_n=force_high,
            hole_diameter_mm=0.32 * width_high, hole_x_mm=0.25 * length_high,
            hole2_diameter_mm=0.32 * width_high, hole2_x_mm=0.75 * length_high,
        ))
        cases.append(build(
            "edge_holes_near", width_mm=width_low, thickness_mm=thickness_high,
            hole_diameter_mm=0.32 * width_low, hole_x_mm=0.30 * length_low,
            hole2_diameter_mm=0.32 * width_low, hole2_x_mm=0.68 * length_low,
        ))
        cases.append(build(
            "edge_no_holes", hole_diameter_mm=0.0, hole2_diameter_mm=0.0,
        ))
        cases.append(build(
            "edge_one_hole", hole_diameter_mm=20.0, hole_x_mm=45.0,
            hole2_diameter_mm=0.0, hole2_x_mm=0.0,
        ))
    elif kind == shapes.TAPER:
        cases.append(build(
            "edge_min_all", length_mm=length_low, width_mm=width_low,
            thickness_mm=thickness_low, tip_width_mm=0.35 * width_low,
            hole_diameter_mm=0.30 * width_low, hole_x_mm=0.40 * length_low,
            force_n=force_low,
        ))
        cases.append(build(
            "edge_max_all", length_mm=length_high, width_mm=width_high,
            thickness_mm=thickness_high, tip_width_mm=width_high,
            hole_diameter_mm=0.45 * width_high, hole_x_mm=0.50 * length_high,
            force_n=force_high,
        ))
        cases.append(build("edge_prismatic", tip_width_mm=40.0))
        cases.append(build(
            "edge_strong_taper", width_mm=60.0, tip_width_mm=21.0,
            hole_diameter_mm=12.0, hole_x_mm=50.0,
        ))
        cases.append(build("edge_no_hole", hole_diameter_mm=0.0, hole_x_mm=60.0))
    elif kind == shapes.STEPPED:
        cases.append(build(
            "edge_min_all", length_mm=length_low, width_mm=width_low,
            thickness_mm=thickness_low, step_x_mm=0.35 * length_low,
            step_thickness_mm=0.45 * thickness_low,
            fillet_radius_mm=0.35 * (thickness_low - 0.45 * thickness_low) / 2,
            force_n=force_low,
        ))
        cases.append(build(
            "edge_max_all", length_mm=length_high, width_mm=width_high,
            thickness_mm=thickness_high, step_x_mm=0.55 * length_high,
            step_thickness_mm=0.70 * thickness_high,
            fillet_radius_mm=0.35 * (thickness_high - 0.70 * thickness_high) / 2,
            force_n=force_high,
        ))
        cases.append(build(
            "edge_step_near_clamp", step_x_mm=36.0, thickness_mm=10.0,
            step_thickness_mm=4.5, fillet_radius_mm=1.5,
        ))
        cases.append(build(
            "edge_step_near_tip", length_mm=120.0, step_x_mm=72.0,
            thickness_mm=10.0, step_thickness_mm=4.5, fillet_radius_mm=1.5,
        ))
        cases.append(build(
            "edge_large_fillet", thickness_mm=12.0, step_thickness_mm=6.0,
            fillet_radius_mm=2.0,
        ))
    elif kind == shapes.I_BEAM:
        cases.append(build(
            "edge_min_all", length_mm=length_low, beam_depth_mm=40.0,
            flange_width_mm=35.0, flange_thickness_mm=0.14 * 40.0,
            web_thickness_mm=0.12 * 35.0, fillet_radius_mm=0.25 * 0.14 * 40.0,
            force_n=force_low,
        ))
        cases.append(build(
            "edge_max_all", length_mm=length_high, beam_depth_mm=70.0,
            flange_width_mm=70.0, flange_thickness_mm=0.22 * 70.0,
            web_thickness_mm=0.20 * 70.0, fillet_radius_mm=0.3 * 0.22 * 70.0,
            force_n=force_high,
        ))
        cases.append(build(
            "edge_slender_web", beam_depth_mm=60.0, flange_width_mm=50.0,
            flange_thickness_mm=10.0, web_thickness_mm=6.0,
            fillet_radius_mm=2.0,
        ))
        cases.append(build(
            "edge_stocky", beam_depth_mm=40.0, flange_width_mm=60.0,
            flange_thickness_mm=8.5, web_thickness_mm=11.0,
            fillet_radius_mm=2.5,
        ))
        cases.append(build(
            "edge_small_fillet", beam_depth_mm=50.0, flange_width_mm=40.0,
            flange_thickness_mm=7.0, web_thickness_mm=6.0,
            fillet_radius_mm=1.4,
        ))
    elif kind == shapes.L_BRACKET:
        cases.append(build(
            "edge_min_all", length_mm=60.0, height_mm=60.0, width_mm=20.0,
            thickness_mm=5.0, fillet_radius_mm=1.25, force_n=force_low,
        ))
        cases.append(build(
            "edge_max_all", length_mm=120.0, height_mm=140.0, width_mm=45.0,
            thickness_mm=12.0, fillet_radius_mm=3.0, force_n=force_high,
        ))
        cases.append(build(
            "edge_tall_thin", length_mm=70.0, height_mm=140.0, width_mm=30.0,
            thickness_mm=6.0, fillet_radius_mm=1.5,
        ))
        cases.append(build(
            "edge_short_stubby", length_mm=60.0, height_mm=65.0, width_mm=45.0,
            thickness_mm=11.0, fillet_radius_mm=2.5,
        ))
        cases.append(build(
            "edge_large_fillet", length_mm=100.0, height_mm=100.0, width_mm=35.0,
            thickness_mm=10.0, fillet_radius_mm=4.0,
        ))
    else:  # pragma: no cover - plate handled by the v1 table
        raise ValueError(f"No edge cases for shape {kind!r}")
    return cases


def build_design_table_v2(
    per_shape: int = 336,
    challenge_per_shape: int = 48,
    plate_count: int = 560,
    plate_challenge: int = 72,
    seed: int = 42,
    method: str = "sobol",
    no_hole_fraction: float = 0.05,
    shapes_to_sample: Sequence[str] | None = None,
) -> list[dict]:
    """Assemble the multi-shape v2 case table (inputs and provenance only)."""
    kinds = list(shapes_to_sample or shapes.SHAPE_KINDS)
    rows: list[dict] = []
    if shapes.PLATE in kinds:
        plate_rows = build_design_table(
            count=plate_count, challenge_count=plate_challenge, seed=seed,
            method=method, no_hole_fraction=no_hole_fraction,
        )
        rows.extend({**row, "shape": shapes.PLATE} for row in plate_rows)
    for kind in kinds:
        if kind == shapes.PLATE:
            continue
        space = shape_space(kind)
        rng = random.Random(seed + 17 * (kinds.index(kind) + 1))
        main = [
            _zero_holes(design, rng, no_hole_fraction)
            for design in space.sample_designs(per_shape, seed=seed, method=method)
        ]
        splits = _split_assignments(per_shape, rng)
        for index, design in enumerate(main, start=1):
            rows.append(
                {
                    "case_id": f"{kind}_{index:04d}",
                    "split": splits[index - 1],
                    "tag": "main",
                    **design.as_dict(),
                }
            )
        challenge = space.challenge_designs(
            challenge_per_shape, seed=seed + 100
        )
        for index, design in enumerate(challenge, start=1):
            rows.append(
                {
                    "case_id": f"{kind}_challenge_{index:04d}",
                    "split": "challenge",
                    "tag": "challenge_corner",
                    **design.as_dict(),
                }
            )
        for tag, design in _edge_designs(kind):
            rows.append(
                {
                    "case_id": f"{kind}_{tag}",
                    "split": "challenge",
                    "tag": tag,
                    **design.as_dict(),
                }
            )
    return rows


def export_designs_v2(
    path: str | Path, seed: int = 42, **kwargs
) -> int:
    """Write the multi-shape input table (no FEA labels)."""
    rows = build_design_table_v2(seed=seed, **kwargs)
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys())
    with destination.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)

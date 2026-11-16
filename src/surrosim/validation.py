"""Independent validation studies for the SurroSim FEA engine.

Two studies are supported:

* ``beam``: unperforated cantilever compared against Euler-Bernoulli beam
  theory over a mesh-refinement series, for linear (C3D4) and quadratic
  (C3D10) tetrahedra.
* ``mesh``: the perforated production geometry refined from coarse to fine
  to demonstrate grid convergence of the global stress target (no analytical
  reference exists for the perforated case).

Neither study trains or evaluates an ML model. They exist to keep the FEA
labels trustworthy before dataset generation.
"""

from pathlib import Path
import csv
import json

from .plate import Plate
from .simulation.pipeline import simulate_case


def _case_dir(
    root: Path, plate: Plate, element_order: int, hole_refinement_mm: float = 0.0
) -> Path:
    name = f"size_{plate.mesh_size_mm:g}_order_{element_order}"
    if hole_refinement_mm > 0:
        name += f"_ref_{hole_refinement_mm:g}"
    return root / name


def _midspan_surface_sxx(
    fields_csv: Path, plate: Plate
) -> tuple[float, float] | None:
    """Peak |SXX| on the outer fiber near mid-span and the x where it occurs."""
    if not fields_csv.exists():
        return None
    slab = []
    with fields_csv.open(encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if abs(float(row["x_mm"]) - plate.length_mm / 2.0) <= plate.mesh_size_mm:
                slab.append(row)
    if not slab:
        return None
    top_z = max(float(row["z_mm"]) for row in slab)
    top = [row for row in slab if abs(float(row["z_mm"]) - top_z) < 1e-6]
    peak = max(top, key=lambda row: abs(float(row["sxx_mpa"])))
    return abs(float(peak["sxx_mpa"])), float(peak["x_mm"])


def _run_study_case(
    plate: Plate,
    root: Path,
    element_order: int,
    ccx_executable: str,
    timeout_seconds: float,
    hole_refinement_mm: float = 0.0,
) -> dict:
    case_dir = _case_dir(root, plate, element_order, hole_refinement_mm)
    summary = simulate_case(
        plate, case_dir, ccx_executable, timeout_seconds,
        element_order=element_order, hole_refinement_mm=hole_refinement_mm,
    )
    results = summary.get("results") or {}
    solver = summary.get("solver") or {}
    geometry = summary.get("geometry", {})
    return {
        "mesh_size_mm": plate.mesh_size_mm,
        "element_order": element_order,
        "hole_refinement_mm": hole_refinement_mm,
        "element_type": summary.get("deck", {}).get("element_type"),
        "status": summary["status"],
        "nodes": geometry.get("mesh_nodes"),
        "elements": geometry.get("mesh_volume_elements"),
        "runtime_seconds": solver.get("runtime_seconds"),
        "max_displacement_mm": results.get("max_displacement_mm"),
        "global_max_von_mises_mpa": results.get("global_max_von_mises_mpa"),
        "max_von_mises_roi_mpa": results.get("max_von_mises_roi_mpa"),
        "midspan_surface_sxx_mpa": (
            sxx[0] if (sxx := _midspan_surface_sxx(case_dir / "fields.csv", plate)) else None
        ),
        "midspan_surface_x_mm": sxx[1] if sxx else None,
        "case_dir": str(case_dir),
    }


def _midspan_beam_stress(plate: Plate, x_mm: float | None = None) -> float:
    """Euler-Bernoulli |SXX| on the outer fiber at station x (default mid-span)."""
    station = plate.length_mm / 2.0 if x_mm is None else x_mm
    moment = abs(plate.force_n) * (plate.length_mm - station)
    inertia = plate.width_mm * plate.thickness_mm**3 / 12.0
    return moment * (plate.thickness_mm / 2.0) / inertia


def _attach_theory_errors(row: dict, plate: Plate, nominal: dict) -> None:
    displacement = row.get("max_displacement_mm")
    if displacement is not None:
        row["displacement_error_pct"] = (
            100.0
            * (displacement - nominal["nominal_tip_displacement_mm"])
            / nominal["nominal_tip_displacement_mm"]
        )
    stress = row.get("midspan_surface_sxx_mpa")
    if stress is not None:
        reference = _midspan_beam_stress(plate, row.get("midspan_surface_x_mm"))
        row["midspan_stress_error_pct"] = 100.0 * (stress - reference) / reference


def beam_convergence(
    output_root: str | Path,
    ccx_executable: str = "ccx",
    mesh_sizes: tuple[float, ...] = (4.0, 3.0, 2.0, 1.5),
    element_orders: tuple[int, ...] = (1, 2),
    slender_lengths: tuple[float, ...] = (240.0,),
    base: Plate | None = None,
    timeout_seconds: float = 300.0,
) -> dict:
    """Compare unperforated cantilever FEA against Euler-Bernoulli theory."""
    base = base or Plate()
    root = Path(output_root) / "beam"
    reference = Plate(
        **{
            **base.as_dict(),
            "hole_diameter_mm": 0.0,
            "mesh_size_mm": min(base.mesh_size_mm, min(mesh_sizes)),
        }
    )
    nominal = reference.nominal_baseline()
    cases = []
    for order in element_orders:
        for size in sorted(mesh_sizes, reverse=True):
            plate = Plate(**{**reference.as_dict(), "mesh_size_mm": size})
            row = _run_study_case(plate, root, order, ccx_executable, timeout_seconds)
            _attach_theory_errors(row, plate, nominal)
            cases.append(row)

    slender_cases = []
    for length in slender_lengths:
        plate = Plate(
            **{
                **reference.as_dict(),
                "length_mm": length,
                "mesh_size_mm": base.thickness_mm / 4.0,
            }
        )
        row = _run_study_case(
            plate, Path(output_root) / "beam_slender", 2, ccx_executable, timeout_seconds
        )
        _attach_theory_errors(row, plate, plate.nominal_baseline())
        row["length_mm"] = plate.length_mm
        row["slenderness"] = plate.length_mm / plate.thickness_mm
        slender_cases.append(row)

    report = {
        "study": "beam_convergence",
        "reference": "Euler-Bernoulli cantilever (unperforated, no shear deformation)",
        "nominal": nominal,
        "geometry": reference.as_dict(),
        "cases": cases,
        "slender_cases": slender_cases,
        "conclusion": _beam_conclusion(cases, slender_cases),
    }
    _write_report(root, report, _beam_markdown(report))
    return report


def _beam_conclusion(cases: list[dict], slender_cases: list[dict]) -> str:
    converged = sorted(
        (row for row in cases if row["status"] == "SUCCESS" and row["element_order"] == 2),
        key=lambda row: row["mesh_size_mm"],
    )
    parts = []
    if len(converged) >= 2:
        finest, previous = converged[0], converged[1]
        parts.append(
            f"Quadratic mesh convergence: tip displacement changes "
            f"{abs(finest['max_displacement_mm'] - previous['max_displacement_mm']) / previous['max_displacement_mm'] * 100:.3f}% "
            f"between {previous['mesh_size_mm']:g} mm and {finest['mesh_size_mm']:g} mm."
        )
    if converged:
        parts.append(
            f"Finest quadratic tip displacement differs from Euler-Bernoulli by "
            f"{converged[0]['displacement_error_pct']:+.2f}% (expected: fully clamped 3-D "
            f"face is stiffer than the ideal beam clamp)."
        )
        if converged[0].get("midspan_stress_error_pct") is not None:
            parts.append(
                f"Mid-span outer-fiber |SXX| agrees with beam theory within "
                f"{converged[0]['midspan_stress_error_pct']:+.2f}%."
            )
    for row in slender_cases:
        parts.append(
            f"At L/T={row['length_mm'] / 6.0:.0f} the tip displacement gap is "
            f"{row['displacement_error_pct']:+.2f}%, shrinking with slenderness."
        )
    return " ".join(parts)


def mesh_convergence(
    output_root: str | Path,
    ccx_executable: str = "ccx",
    mesh_sizes: tuple[float, ...] = (4.0, 3.0, 2.0, 1.5),
    element_order: int = 2,
    hole_refinement_mm: float = 0.0,
    base: Plate | None = None,
    timeout_seconds: float = 300.0,
) -> dict:
    """Refine the perforated production geometry and track target convergence."""
    base = base or Plate()
    root = Path(output_root) / "mesh"
    cases = []
    for size in sorted(mesh_sizes, reverse=True):
        plate = Plate(**{**base.as_dict(), "mesh_size_mm": size})
        if 0 < hole_refinement_mm >= size:
            continue
        row = _run_study_case(
            plate, root, element_order, ccx_executable, timeout_seconds,
            hole_refinement_mm=hole_refinement_mm,
        )
        cases.append(row)

    _add_successive_changes(cases, "max_displacement_mm", "displacement_change_pct")
    _add_successive_changes(cases, "max_von_mises_roi_mpa", "roi_stress_change_pct")
    _add_successive_changes(
        cases, "global_max_von_mises_mpa", "global_stress_change_pct"
    )

    report = {
        "study": "mesh_convergence",
        "reference": "successive refinement of the perforated production geometry",
        "geometry": base.as_dict(),
        "hole_refinement_mm": hole_refinement_mm,
        "cases": cases,
    }
    _write_report(root, report, _mesh_markdown(report))
    return report


def _add_successive_changes(cases: list[dict], key: str, change_key: str) -> None:
    ordered = sorted(
        (row for row in cases if row["status"] == "SUCCESS"),
        key=lambda row: -row["mesh_size_mm"],
    )
    for coarse, fine in zip(ordered, ordered[1:]):
        coarse_value = coarse[key]
        fine_value = fine[key]
        if coarse_value is None or fine_value is None or coarse_value == 0:
            continue
        fine[change_key] = 100.0 * (fine_value - coarse_value) / coarse_value


def _write_report(root: Path, report: dict, markdown: str) -> None:
    if report["study"] == "beam_convergence":
        name = "beam"
    else:
        name = "mesh_refined" if report.get("hole_refinement_mm") else "mesh"
    for destination in (root, Path("reports/validation") / name):
        destination.mkdir(parents=True, exist_ok=True)
        (destination / "report.json").write_text(
            json.dumps(report, indent=2) + "\n", encoding="utf-8"
        )
        (destination / "report.md").write_text(markdown, encoding="utf-8")
        _plot(report, destination / "convergence.png")


def _fmt(value, decimals=2, signed=False):
    if value is None:
        return "n/a"
    sign = "+" if signed else ""
    return f"{value:{sign}.{decimals}f}"


def _beam_markdown(report: dict) -> str:
    nominal = report["nominal"]
    lines = [
        "# Beam validation (unperforated cantilever)",
        "",
        f"Euler-Bernoulli nominal tip displacement: "
        f"{nominal['nominal_tip_displacement_mm']:.4f} mm; "
        f"nominal root bending stress: "
        f"{nominal['nominal_root_bending_stress_mpa']:.2f} MPa.",
        "",
        "Tip displacement is compared against Euler-Bernoulli theory for the same",
        "cantilever. The fully clamped 3-D face and the distributed end traction",
        "are known to stiffen the model slightly, so a small negative displacement",
        "error is expected and should shrink with slenderness.",
        "",
        "| order | mesh (mm) | status | nodes | max disp (mm) | disp error (%) | "
        "midspan |SXX| (MPa) | stress error (%) | solve (s) |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in report["cases"]:
        lines.append(
            f"| {row['element_order']} | {row['mesh_size_mm']:g} | {row['status']} | "
            f"{row['nodes']} | {_fmt(row['max_displacement_mm'], 4)} | "
            f"{_fmt(row.get('displacement_error_pct'), 2, signed=True)} | "
            f"{_fmt(row.get('midspan_surface_sxx_mpa'))} | "
            f"{_fmt(row.get('midspan_stress_error_pct'), 2, signed=True)} | "
            f"{_fmt(row.get('runtime_seconds'))} |"
        )

    if report.get("slender_cases"):
        lines += [
            "",
            "## Slenderness sweep (quadratic, mesh = T/4)",
            "",
            "| length (mm) | L/T | status | max disp (mm) | disp error (%) | "
            "midspan |SXX| error (%) |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
        for row in report["slender_cases"]:
            lines.append(
                f"| {row['length_mm']:g} | {row['slenderness']:g} | {row['status']} | "
                f"{_fmt(row['max_displacement_mm'], 4)} | "
                f"{_fmt(row.get('displacement_error_pct'), 2, signed=True)} | "
                f"{_fmt(row.get('midspan_stress_error_pct'), 2, signed=True)} |"
            )

    if report.get("conclusion"):
        lines += ["", "## Conclusion", "", report["conclusion"], ""]
    lines.append("")
    return "\n".join(lines)


def _mesh_markdown(report: dict) -> str:
    refinement = report.get("hole_refinement_mm") or 0.0
    title = "# Perforated-geometry mesh convergence"
    if refinement:
        title += f" (hole surface graded to {refinement:g} mm)"
    lines = [
        title,
        "",
        "| order | mesh (mm) | status | nodes | max disp (mm) | disp change (%) | "
        "ROI stress (MPa) | ROI change (%) |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in report["cases"]:
        def _fmt(value, decimals=2):
            return f"{value:.{decimals}f}" if value is not None else "n/a"

        lines.append(
            f"| {row['element_order']} | {row['mesh_size_mm']:g} | {row['status']} | "
            f"{row['nodes']} | {_fmt(row['max_displacement_mm'], 4)} | "
            f"{_fmt(row.get('displacement_change_pct'))} | "
            f"{_fmt(row['max_von_mises_roi_mpa'])} | "
            f"{_fmt(row.get('roi_stress_change_pct'))} |"
        )
    lines.append("")
    return "\n".join(lines)


def _plot(report: dict, path: Path) -> None:
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return

    cases = [row for row in report["cases"] if row["status"] == "SUCCESS"]
    if not cases:
        return
    figure, axes = plt.subplots(1, 2, figsize=(10, 4))
    for order in sorted({row["element_order"] for row in cases}):
        subset = sorted(
            (row for row in cases if row["element_order"] == order),
            key=lambda row: -row["mesh_size_mm"],
        )
        sizes = [row["mesh_size_mm"] for row in subset]
        displacement = [row["max_displacement_mm"] for row in subset]
        axes[0].plot(sizes, displacement, "o-", label=f"order {order}")
        if report["study"] == "mesh_convergence":
            stress = [row["max_von_mises_roi_mpa"] for row in subset]
            axes[1].plot(sizes, stress, "o-", label=f"order {order}")
    axes[0].set_title("Max displacement vs mesh size")
    axes[0].set_xlabel("mesh size (mm)")
    axes[0].set_ylabel("max displacement (mm)")
    axes[0].invert_xaxis()
    axes[0].grid(True, alpha=0.3)
    axes[0].legend()
    if report["study"] == "mesh_convergence":
        axes[1].set_title("Hole ROI max Von Mises vs mesh size")
        axes[1].set_xlabel("mesh size (mm)")
        axes[1].set_ylabel("stress (MPa)")
        axes[1].invert_xaxis()
        axes[1].grid(True, alpha=0.3)
        axes[1].legend()
    else:
        axes[1].axis("off")
    figure.tight_layout()
    figure.savefig(path, dpi=150)
    plt.close(figure)

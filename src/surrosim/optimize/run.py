"""Run surrogate-based optimization and verify the best designs with FEA."""

from pathlib import Path
from datetime import datetime, timezone
from typing import Callable
import json
import time

import numpy as np
from scipy.optimize import differential_evolution

from .. import shapes
from ..dataset.cases import run_case
from ..mesh_policy import DEFAULT_POLICY
from ..plate import Plate
from ..provenance import git_info, tool_versions
from ..serving.predictor import ScalarPredictor
from .problem import OptimizationProblem


def optimize_design(
    problem: OptimizationProblem | None = None,
    predictor: ScalarPredictor | None = None,
    seed: int = 42,
    maxiter: int = 60,
    popsize: int = 15,
    top_k: int = 5,
    verify: bool = True,
    ccx_executable: str | None = None,
    out_dir: str | Path = "outputs/optimization",
    report_path: str | Path = "reports/v1.0_optimization.md",
    figure_dir: str | Path = "reports/figures/v1.0",
    progress_callback: Callable[[int, int], None] | None = None,
) -> dict:
    problem = problem or OptimizationProblem()
    predictor = predictor or ScalarPredictor.load()
    output = Path(out_dir)
    output.mkdir(parents=True, exist_ok=True)
    evaluations: list[dict] = []
    expected_evaluations = popsize * len(problem.bounds) * (maxiter + 1)

    def evaluate_design(design: dict) -> tuple[float, float]:
        result = predictor.predict(design)
        global_stress = result["predictions"]["global_max_von_mises_mpa"]["value"]
        roi_stress = result["predictions"]["max_von_mises_roi_mpa"]["value"]
        stress = max(global_stress, roi_stress or 0.0)
        displacement = result["predictions"]["max_displacement_mm"]["value"]
        return stress, displacement

    def objective(vector: np.ndarray) -> float:
        design = problem.design_from_vector(np.asarray(vector, dtype=float))
        stress, displacement = evaluate_design(design)
        mass = problem.mass_g(design)
        ratios = problem.violations(design, stress, displacement)
        violation = max(0.0, ratios["stress_ratio"] - 1.0) + max(
            0.0, ratios["displacement_ratio"] - 1.0
        )
        evaluations.append(
            {
                "design": design,
                "mass_g": mass,
                "stress_mpa": stress,
                "displacement_mm": displacement,
                "feasible": violation == 0.0,
                **ratios,
            }
        )
        if progress_callback is not None:
            progress_callback(len(evaluations), expected_evaluations)
        return mass + 1.0e4 * violation**2

    started = time.perf_counter()
    result = differential_evolution(
        objective,
        bounds=problem.bounds,
        seed=seed,
        maxiter=maxiter,
        popsize=popsize,
        tol=1e-8,
        polish=False,
        updating="deferred",
        workers=1,
    )
    optimizer_seconds = time.perf_counter() - started

    unique: dict[tuple, dict] = {}
    for entry in evaluations:
        if not entry["feasible"]:
            continue
        design = entry["design"]
        key = tuple(
            sorted(
                (name, round(float(value), 3))
                for name, value in problem.plate(design).active_params().items()
            )
        )
        if key not in unique or entry["mass_g"] < unique[key]["mass_g"]:
            unique[key] = entry
    candidates = sorted(unique.values(), key=lambda entry: entry["mass_g"])[:top_k]

    verification = []
    if verify and ccx_executable and candidates:
        for index, candidate in enumerate(candidates, start=1):
            verification.append(
                _verify_candidate(
                    candidate, index, problem, ccx_executable, output
                )
            )

    metadata = {
        "schema_version": "2.0.0",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "problem": problem.as_dict(),
        "optimizer": {
            "method": "scipy differential_evolution",
            "seed": seed,
            "maxiter": maxiter,
            "popsize": popsize,
            "evaluations": len(evaluations),
            "seconds": optimizer_seconds,
            "best_objective": float(result.fun),
        },
        "candidates": candidates,
        "verification": verification,
        "evaluations": {
            "mass_g": [round(entry["mass_g"], 3) for entry in evaluations],
            "stress_mpa": [round(entry["stress_mpa"], 3) for entry in evaluations],
            "displacement_mm": [
                round(entry["displacement_mm"], 5) for entry in evaluations
            ],
            "feasible": [entry["feasible"] for entry in evaluations],
        },
        "surrogate_model": predictor.metadata.get("best_models", {}),
        "dataset_sha256": predictor.metadata.get("dataset_sha256"),
        "mesh_policy": DEFAULT_POLICY.as_dict(),
        "tool_versions": tool_versions(),
        "git": git_info(),
    }
    (output / "optimization.json").write_text(
        json.dumps(metadata, indent=2) + "\n", encoding="utf-8"
    )
    _figure(evaluations, candidates, Path(figure_dir))
    Path(report_path).parent.mkdir(parents=True, exist_ok=True)
    Path(report_path).write_text(_markdown(metadata), encoding="utf-8")
    return metadata


def _verify_candidate(
    candidate: dict,
    index: int,
    problem: OptimizationProblem,
    ccx_executable: str,
    output: Path,
) -> dict:
    design = candidate["design"]
    case_id = shapes.case_id(f"opt_{index:02d}", problem.plate(design))
    plate = problem.plate(design)
    outcome = run_case(
        case_id, plate, output / "cases", ccx_executable,
        timeout_seconds=900.0, policy=DEFAULT_POLICY,
    )
    record = {"case_id": case_id, "status": outcome["status"], "design": design}
    run_json = output / "cases" / case_id / "run.json"
    if run_json.exists():
        summary = json.loads(run_json.read_text(encoding="utf-8"))
        results = summary.get("results") or {}
        fea_stress = max(
            results.get("global_max_von_mises_mpa") or 0.0,
            results.get("max_von_mises_roi_mpa") or 0.0,
        )
        fea_displacement = results.get("max_displacement_mm")
        record.update(
            {
                "fea_global_stress_mpa": results.get("global_max_von_mises_mpa"),
                "fea_roi_stress_mpa": results.get("max_von_mises_roi_mpa"),
                "fea_max_displacement_mm": fea_displacement,
                "fea_stress_error_pct": (
                    100.0
                    * (candidate["stress_mpa"] - fea_stress)
                    / fea_stress
                    if fea_stress
                    else None
                ),
                "fea_displacement_error_pct": (
                    100.0
                    * (candidate["displacement_mm"] - fea_displacement)
                    / fea_displacement
                    if fea_displacement
                    else None
                ),
                "fea_feasible": (
                    fea_stress <= problem.sigma_allow_mpa
                    and (fea_displacement or 0.0) <= problem.displacement_limit_mm
                ),
                "solver_seconds": (summary.get("solver") or {}).get(
                    "runtime_seconds"
                ),
            }
        )
    return record


def _figure(evaluations: list[dict], candidates: list[dict], figure_dir: Path) -> None:
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return
    stresses = [entry["stress_mpa"] for entry in evaluations]
    masses = [entry["mass_g"] for entry in evaluations]
    feasible = [entry["feasible"] for entry in evaluations]
    figure, axis = plt.subplots(figsize=(7.5, 5))
    axis.scatter(
        np.array(stresses)[~np.array(feasible)],
        np.array(masses)[~np.array(feasible)],
        s=14, alpha=0.35, color="tab:red", label="infeasible (surrogate)",
    )
    axis.scatter(
        np.array(stresses)[np.array(feasible)],
        np.array(masses)[np.array(feasible)],
        s=14, alpha=0.55, color="tab:blue", label="feasible (surrogate)",
    )
    if candidates:
        axis.scatter(
            [entry["stress_mpa"] for entry in candidates],
            [entry["mass_g"] for entry in candidates],
            s=70, marker="*", color="black", label="selected candidates",
        )
    axis.set_xlabel("predicted max Von Mises (MPa, global or ROI)")
    axis.set_ylabel("mass (g)")
    axis.set_title("Surrogate optimization evaluations")
    axis.grid(True, alpha=0.3)
    axis.legend()
    figure.tight_layout()
    figure_dir.mkdir(parents=True, exist_ok=True)
    figure.savefig(figure_dir / "optimization_scatter.png", dpi=150)
    plt.close(figure)


def _markdown(metadata: dict) -> str:
    problem = metadata["problem"]
    optimizer = metadata["optimizer"]
    variables = problem.get("parameter_names") or []
    lines = [
        "# SurroSim constrained design optimization",
        "",
        f"- Objective: minimise mass with "
        f"σ < {problem['sigma_allow_mpa']} MPa and "
        f"δ < {problem['displacement_limit_mm']} mm",
        f"- Shape family: **{problem.get('shape', 'plate')}**",
        f"- Fixed: L = {problem['length_mm']} mm, F = {problem['force_n']} N, "
        f"steel (E = 210 GPa, ν = 0.3, ρ = 7850 kg/m³)",
        f"- Variables: {', '.join(variables)}",
        f"- Optimizer: {optimizer['method']}, seed {optimizer['seed']}, "
        f"{optimizer['evaluations']} surrogate evaluations in "
        f"{optimizer['seconds']:.1f} s",
        f"- Surrogate models: {metadata['surrogate_model']} "
        f"(dataset sha `{str(metadata['dataset_sha256'])[:12]}...`)",
        "",
        "## Selected candidates (surrogate ranking by mass)",
        "",
        "| # | design | mass (g) | σ pred (MPa) | δ pred (mm) | σ FEA | δ FEA | "
        "σ err % | δ err % | FEA feasible |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    verification = metadata.get("verification", [])
    for index, candidate in enumerate(metadata["candidates"], start=1):
        design = candidate["design"]
        match = verification[index - 1] if index <= len(verification) else None
        design_text = ", ".join(
            f"{name}={value:.4g}"
            for name, value in Plate.from_mapping(design).active_params().items()
        )

        def _fmt(value, spec=".3g"):
            return "n/a" if value is None else format(value, spec)

        lines.append(
            f"| {index} | {design_text} | "
            f"{candidate['mass_g']:.1f} | {candidate['stress_mpa']:.1f} | "
            f"{candidate['displacement_mm']:.4f} | "
            f"{_fmt(match.get('fea_global_stress_mpa') if match else None)} | "
            f"{_fmt(match.get('fea_max_displacement_mm') if match else None, '.4f')} | "
            f"{_fmt(match.get('fea_stress_error_pct') if match else None, '+.2f')} | "
            f"{_fmt(match.get('fea_displacement_error_pct') if match else None, '+.2f')} | "
            f"{match.get('fea_feasible') if match else 'n/a'} |"
        )
    lines += [
        "",
        f"Optimization scatter: `reports/figures/v1.0/optimization_scatter.png`",
        "",
        "## Interpretation",
        "",
        "- The optimizer explores thousands of designs through the surrogate in",
        "  under a minute; only the final candidates touch the high-fidelity",
        "  solver, which is the intended division of labour.",
        "- Candidates are verified with the production mesh policy; surrogate",
        "  stress/displacement errors versus those FEA runs are shown above.",
        "- Surrogate predictions are only valid inside the sampled design space;",
        "  the app's domain checks apply to these candidates as well.",
        "",
    ]
    return "\n".join(lines)

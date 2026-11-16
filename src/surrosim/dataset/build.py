"""Validate completed FEA runs and assemble the versioned ML dataset.

Every row must pass explicit gates before it can become a training label.
Failed or ambiguous cases are written to ``failures.csv`` and never enter
``dataset.csv``. The ``manifest.json`` records provenance: design space,
mesh policy, solver version, git revision and content hashes.
"""

from pathlib import Path
import csv
import json
import math
import re
from datetime import datetime, timezone

from ..mesh_policy import DEFAULT_POLICY
from ..plate import Plate
from ..provenance import git_info, sha256, tool_versions
from .batch import load_designs

DATASET_SCHEMA_VERSION = "2.0.0"
GATE_MIN_NODES = 500

DESIGN_COLUMNS = [
    "shape",
    "length_mm", "width_mm", "thickness_mm",
    "hole_diameter_mm", "hole_x_mm",
    "hole2_diameter_mm", "hole2_x_mm",
    "tip_width_mm",
    "step_x_mm", "step_thickness_mm", "fillet_radius_mm",
    "flange_width_mm", "beam_depth_mm", "flange_thickness_mm", "web_thickness_mm",
    "height_mm",
    "force_n", "youngs_modulus_mpa", "poisson_ratio", "mesh_size_mm",
]
INPUT_COLUMNS = ["case_id", "split", "tag", *DESIGN_COLUMNS]
OUTPUT_COLUMNS = [
    "max_displacement_mm", "global_max_von_mises_mpa", "max_von_mises_roi_mpa",
]
PROVENANCE_COLUMNS = [
    "element_type", "element_order", "hole_refinement_mm",
    "mesh_nodes", "mesh_volume_elements", "runtime_seconds", "solver_version",
    "fields_npz", "case_dir",
]
DATASET_COLUMNS = INPUT_COLUMNS + OUTPUT_COLUMNS + PROVENANCE_COLUMNS

_SOLVER_VERSION = re.compile(r"CalculiX Version\s+([0-9]+\.[0-9]+)")


def _finite_positive(value) -> bool:
    return value is not None and math.isfinite(value) and value > 0


def _collect_case(row, runs_root: Path) -> tuple[dict | None, str | None]:
    case_dir = runs_root / row.case_id
    run_json = case_dir / "run.json"
    if not run_json.exists():
        return None, "MISSING_RUN_JSON"
    summary = json.loads(run_json.read_text(encoding="utf-8"))
    if summary.get("status") != "SUCCESS":
        return None, summary.get("status", "UNKNOWN_STATUS")
    geometry = summary.get("geometry") or {}
    deck = summary.get("deck") or {}
    results = summary.get("results") or {}
    if not results:
        return None, "MISSING_RESULTS"

    force = row.plate.force_n
    applied = deck.get("total_applied_force_n")
    if applied is None or abs(applied + abs(force)) > max(1e-6, abs(force) * 1e-9):
        return None, "FORCE_GATE"

    nodes = geometry.get("mesh_nodes") or 0
    if nodes < GATE_MIN_NODES:
        return None, "MESH_GATE"
    if not (case_dir / "fields.npz").exists():
        return None, "MISSING_FIELDS"

    displacement = results.get("max_displacement_mm")
    global_stress = results.get("global_max_von_mises_mpa")
    roi_stress = results.get("max_von_mises_roi_mpa")
    if not _finite_positive(displacement) or not _finite_positive(global_stress):
        return None, "OUTPUT_GATE"
    if roi_stress is not None and not _finite_positive(roi_stress):
        return None, "OUTPUT_GATE"

    solver = summary.get("solver") or {}
    match = _SOLVER_VERSION.search(solver.get("stdout", "") or "")
    return (
        {
            **row.as_dict(),
            "element_type": deck.get("element_type"),
            "element_order": deck.get("element_order"),
            "hole_refinement_mm": geometry.get("hole_refinement_mm") or 0.0,
            "mesh_nodes": nodes,
            "mesh_volume_elements": geometry.get("mesh_volume_elements"),
            "max_displacement_mm": displacement,
            "global_max_von_mises_mpa": global_stress,
            "max_von_mises_roi_mpa": roi_stress,
            "runtime_seconds": solver.get("runtime_seconds"),
            "solver_version": match.group(1) if match else None,
            "fields_npz": (case_dir / "fields.npz").as_posix(),
            "case_dir": case_dir.as_posix(),
        },
        None,
    )


def _numeric(value):
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return value


def _load_base_rows(path: Path) -> list[dict]:
    """Read a previous dataset schema and backfill new design columns."""
    rows: list[dict] = []
    with path.open(encoding="utf-8") as handle:
        for raw in csv.DictReader(handle):
            design = Plate.from_mapping(raw)
            normalized = {name: raw.get(name) for name in DATASET_COLUMNS}
            for name in DESIGN_COLUMNS:
                normalized[name] = getattr(design, name)
            for name in OUTPUT_COLUMNS + [
                "hole_refinement_mm", "mesh_nodes", "mesh_volume_elements",
                "runtime_seconds",
            ]:
                normalized[name] = _numeric(normalized.get(name))
            rows.append(normalized)
    return rows


def build_dataset(
    designs_path: str | Path,
    runs_root: str | Path,
    out_root: str | Path,
    base_datasets: list[str | Path] | tuple[str | Path, ...] = (),
) -> dict:
    rows = load_designs(designs_path)
    runs_root = Path(runs_root)
    base_rows: list[dict] = []
    base_info: list[dict] = []
    for base in base_datasets:
        base_path = Path(base)
        loaded = _load_base_rows(base_path)
        base_rows.extend(loaded)
        base_info.append(
            {
                "path": base_path.as_posix(),
                "sha256": sha256(base_path),
                "cases": len(loaded),
            }
        )
    base_ids = {row["case_id"] for row in base_rows}
    dataset_rows: list[dict] = []
    failures: list[dict] = []
    for row in rows:
        if row.case_id in base_ids:
            continue
        data, failure = _collect_case(row, runs_root)
        if data is not None:
            dataset_rows.append(data)
        else:
            failures.append({"case_id": row.case_id, "failure": failure})
    dataset_rows = base_rows + dataset_rows
    dataset_rows.sort(key=lambda item: item["case_id"])

    output = Path(out_root)
    output.mkdir(parents=True, exist_ok=True)
    dataset_path = output / "dataset.csv"
    with dataset_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=DATASET_COLUMNS)
        writer.writeheader()
        for row in dataset_rows:
            writer.writerow({name: row.get(name) for name in DATASET_COLUMNS})
    failures_path = output / "failures.csv"
    with failures_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["case_id", "failure"])
        writer.writeheader()
        writer.writerows(failures)

    split_counts: dict[str, int] = {}
    shape_counts: dict[str, int] = {}
    for row in dataset_rows:
        split_counts[row["split"]] = split_counts.get(row["split"], 0) + 1
        shape = row.get("shape") or "plate"
        shape_counts[shape] = shape_counts.get(shape, 0) + 1
    solver_versions = sorted(
        {row["solver_version"] for row in dataset_rows if row["solver_version"]}
    )
    runtimes = [row["runtime_seconds"] for row in dataset_rows if row["runtime_seconds"]]
    manifest = {
        "schema_version": DATASET_SCHEMA_VERSION,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "designs_file": str(designs_path),
        "designs_sha256": sha256(Path(designs_path)),
        "dataset_file": dataset_path.name,
        "dataset_sha256": sha256(dataset_path),
        "runs_root": str(runs_root),
        "base_datasets": base_info,
        "cases_in_designs": len(rows),
        "cases_from_base": len(base_rows),
        "cases_in_dataset": len(dataset_rows),
        "cases_failed": len(failures),
        "split_counts": split_counts,
        "shape_counts": shape_counts,
        "mesh_policy": DEFAULT_POLICY.as_dict(),
        "solver": {
            "versions": solver_versions or None,
            "total_solver_seconds": sum(runtimes) if runtimes else None,
        },
        "environment": tool_versions(),
        "git": git_info(),
        "gates": [
            "solver status == SUCCESS",
            "deck total force matches requested force",
            f"mesh nodes >= {GATE_MIN_NODES}",
            "fields.npz present",
            "displacement and global stress finite and positive",
            "ROI stress finite and positive when defined",
        ],
    }
    (output / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    (output / "dataset_card.md").write_text(
        _dataset_card(manifest, dataset_rows, failures), encoding="utf-8"
    )
    return manifest


def _column_stats(rows: list[dict], name: str) -> tuple[float, float, float, float] | None:
    values = [row[name] for row in rows if row.get(name) is not None]
    if not values:
        return None
    return (
        min(values),
        sum(values) / len(values),
        max(values),
        max(values) - min(values),
    )


def _dataset_card(
    manifest: dict, rows: list[dict], failures: list[dict]
) -> str:
    lines = [
        "# SurroSim simulation dataset card",
        "",
        f"- Schema version: `{manifest['schema_version']}`",
        f"- Created: {manifest['created_utc']}",
        f"- Cases in dataset: **{manifest['cases_in_dataset']}** "
        f"(failed/excluded: {manifest['cases_failed']})",
        f"- Splits: {manifest['split_counts']}",
        f"- Shapes: {manifest['shape_counts']}",
        f"- Solver: CalculiX {manifest['solver']['versions']}",
        f"- Git: `{manifest['git']['commit']}` (dirty={manifest['git']['dirty']})",
        f"- Dataset sha256: `{manifest['dataset_sha256'][:16]}...`",
        "",
        "## Shape families",
        "",
        "| shape | cases |",
        "| --- | --- |",
    ]
    for shape, count in sorted(manifest["shape_counts"].items()):
        lines.append(f"| {shape} | {count} |")
    lines += [
        "",
        "## Design variables (observed range, all shapes pooled)",
        "",
        "| variable | min | mean | max | range |",
        "| --- | --- | --- | --- | --- |",
    ]
    for name in DESIGN_COLUMNS:
        if name == "shape":
            continue
        stats = _column_stats(rows, name)
        if stats:
            lines.append(
                f"| {name} | {stats[0]:.4g} | {stats[1]:.4g} | {stats[2]:.4g} | "
                f"{stats[3]:.4g} |"
            )
    lines += [
        "",
        "## Targets (observed range, successful cases)",
        "",
        "| target | min | mean | max |",
        "| --- | --- | --- | --- |",
    ]
    for name in OUTPUT_COLUMNS:
        stats = _column_stats(rows, name)
        if stats:
            lines.append(f"| {name} | {stats[0]:.4g} | {stats[1]:.4g} | {stats[2]:.4g} |")
    lines += [
        "",
        "## Labels and provenance",
        "",
        "- Every label comes from a completed CalculiX C3D10 static solve; failed",
        "  or gated cases are excluded and listed in `failures.csv`.",
        "- Mesh policy: " + json.dumps(manifest["mesh_policy"]),
        "- `fields_npz` stores nodal coordinates, displacement, stress components",
        "  and Von Mises stress as float32 for field-learning experiments.",
        "- The ROI target tracks the shape's stress riser: hole cylinders for the",
        "  plate-like families, re-entrant fillets for stepped/bracket shapes, and",
        "  web/flange fillets for the I-beam; no-hole plates carry",
        "  `max_von_mises_roi_mpa = null`.",
        "- Parameters that are inactive for a shape carry neutral constants, so",
        "  models must condition on the `shape` column.",
        "",
        "## Engineering caveats",
        "",
        "- Labels carry the discretization uncertainty quantified in",
        "  `reports/validation/` (~0.5% on stress, smaller on displacement).",
        "- Linear elasticity and small strain only; no contact, plasticity,",
        "  dynamics or thermal effects.",
        "- The ROI stress is a nodal peak; use with the documented mesh policy.",
        "",
    ]
    if failures:
        lines += [
            f"## Excluded cases ({len(failures)})",
            "",
            "| case_id | failure |",
            "| --- | --- |",
        ]
        for failure in failures:
            lines.append(f"| {failure['case_id']} | {failure['failure']} |")
        lines.append("")
    return "\n".join(lines)

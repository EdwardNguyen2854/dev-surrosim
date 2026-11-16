"""FastAPI inference, job and report service for SurroSim.

Run with::

    uvicorn surrosim.serving.api:create_app --factory --port 8003

The JSON API lives under ``/api``; when a production build of the React app
exists at ``apps/web/dist`` it is served from ``/`` with client-side routing.
Long-running operations (CalculiX verification, GNN field prediction,
surrogate optimization) are queued as background jobs whose progress and log
stream are exposed through ``/api/jobs``.
"""

from __future__ import annotations

from pathlib import Path
import csv
import json
import math
import os
import shutil
import statistics

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .. import shapes
from ..mesh_policy import DEFAULT_POLICY
from ..optimize.problem import OptimizationProblem
from ..plate import Plate
from ..sampling import shape_space
from ..serving.viz import FIELD_META, field_payload
from .jobs import Job, JobManager, run_in_process
from .predictor import ScalarPredictor
from .worker_process import fea_verify_entry, field_predict_entry

REPO_ROOT = Path(__file__).resolve().parents[3]
FIELD_FILES = ("von_mises_mpa", "displacement_mm")
DEFAULT_REGISTRY = "models/scalar/v2"
DEFAULT_FIELD_MODEL = "models/gnn/v2"


def representative_design(kind: str) -> Plate:
    """A valid default design for a shape (mid-point of its design space)."""
    if kind == shapes.PLATE:
        return Plate()
    space = shape_space(kind)
    return space.design_from_unit(
        tuple(0.5 for _ in range(space.dimensions()))
    )


class DesignRequest(BaseModel):
    shape: str = shapes.PLATE
    length_mm: float = Field(120.0, gt=0)
    width_mm: float = Field(40.0, gt=0)
    thickness_mm: float = Field(6.0, gt=0)
    hole_diameter_mm: float = Field(12.0, ge=0)
    hole_x_mm: float = Field(60.0, ge=0)
    hole2_diameter_mm: float = Field(0.0, ge=0)
    hole2_x_mm: float = Field(0.0, ge=0)
    tip_width_mm: float = Field(40.0, gt=0)
    step_x_mm: float = Field(60.0, gt=0)
    step_thickness_mm: float = Field(6.0, gt=0)
    fillet_radius_mm: float = Field(0.0, ge=0)
    flange_width_mm: float = Field(40.0, gt=0)
    beam_depth_mm: float = Field(40.0, gt=0)
    flange_thickness_mm: float = Field(6.0, gt=0)
    web_thickness_mm: float = Field(5.0, gt=0)
    height_mm: float = Field(90.0, gt=0)
    force_n: float = Field(500.0)
    youngs_modulus_mpa: float = Field(210_000.0, gt=0)
    poisson_ratio: float = Field(0.3, gt=-1.0, lt=0.5)

    def as_plate(self) -> dict:
        return self.model_dump()


class FeaVerifyRequest(DesignRequest):
    force: bool = False


class OptimizeRequest(BaseModel):
    shape: str = shapes.PLATE
    length_mm: float = Field(120.0, ge=80.0, le=200.0)
    force_n: float = Field(500.0, ge=10.0, le=2000.0)
    sigma_allow_mpa: float = Field(180.0, gt=0)
    displacement_limit_mm: float = Field(1.5, gt=0)
    seed: int = 42
    maxiter: int = Field(60, ge=5, le=200)
    verify_candidates: bool = False


def find_ccx(repo_root: Path, override: str | None = None) -> str | None:
    candidates = [
        override,
        os.environ.get("SURROSIM_CCX"),
        str(repo_root / "tools" / "calculix" / "ccx.exe"),
        str(repo_root / "tools" / "calculix" / "ccx"),
        "C:/Program Files/CalculiX/ccx.exe",
        shutil.which("ccx"),
    ]
    for candidate in candidates:
        if candidate and (Path(candidate).exists() or shutil.which(candidate)):
            return candidate
    return None


def _resolve(repo_root: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else repo_root / path


def _plate_from_design(design: dict) -> Plate:
    return Plate.from_mapping(design)


def _case_id(prefix: str, design: Plate) -> str:
    return shapes.case_id(prefix, design)


def _read_text(path: Path) -> str | None:
    return path.read_text(encoding="utf-8") if path.exists() else None


def _read_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _relative_posix(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except (OSError, ValueError):
        return path.as_posix()


DESIGN_COLUMNS = (
    "length_mm",
    "width_mm",
    "thickness_mm",
    "hole_diameter_mm",
    "hole_x_mm",
    "hole2_diameter_mm",
    "hole2_x_mm",
    "tip_width_mm",
    "step_x_mm",
    "step_thickness_mm",
    "fillet_radius_mm",
    "flange_width_mm",
    "beam_depth_mm",
    "flange_thickness_mm",
    "web_thickness_mm",
    "height_mm",
    "force_n",
    "youngs_modulus_mpa",
    "poisson_ratio",
    "mesh_size_mm",
)
TARGET_COLUMNS = (
    "max_displacement_mm",
    "global_max_von_mises_mpa",
    "max_von_mises_roi_mpa",
)

_DATASET_STATS_CACHE: dict[tuple[str, int], dict] = {}


def _dataset_stats(path: Path | None) -> dict:
    """Range, count and cost summary computed from a dataset CSV.

    The result is cached per (path, mtime) so page reloads do not re-read the
    file. Missing columns are skipped, which keeps v1 plate-only datasets
    working with the same endpoint.
    """
    empty = {
        "row_count": None,
        "split_counts": {},
        "shape_counts": {},
        "design_ranges": [],
        "target_ranges": [],
        "median_runtime_seconds": None,
        "mesh": {
            "median_nodes": None,
            "median_elements": None,
            "element_type": None,
        },
    }
    if path is None or not path.exists():
        return empty
    try:
        stamp = path.stat().st_mtime_ns
    except OSError:
        return empty
    cache_key = (str(path), stamp)
    cached = _DATASET_STATS_CACHE.get(cache_key)
    if cached is not None:
        return cached

    tracked = DESIGN_COLUMNS + TARGET_COLUMNS
    acc = {
        name: {"n": 0, "sum": 0.0, "min": math.inf, "max": -math.inf}
        for name in tracked
    }
    split_counts: dict[str, int] = {}
    shape_counts: dict[str, int] = {}
    runtimes: list[float] = []
    nodes: list[float] = []
    elements: list[float] = []
    element_types: set[str] = set()
    rows = 0
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            rows += 1
            split = (row.get("split") or "").strip()
            if split:
                split_counts[split] = split_counts.get(split, 0) + 1
            shape = (row.get("shape") or "").strip()
            if shape:
                shape_counts[shape] = shape_counts.get(shape, 0) + 1
            for name in tracked:
                raw = row.get(name)
                if raw in (None, ""):
                    continue
                try:
                    value = float(raw)
                except ValueError:
                    continue
                if not math.isfinite(value):
                    continue
                slot = acc[name]
                slot["n"] += 1
                slot["sum"] += value
                slot["min"] = min(slot["min"], value)
                slot["max"] = max(slot["max"], value)
            for key, bucket in (
                ("runtime_seconds", runtimes),
                ("mesh_nodes", nodes),
                ("mesh_volume_elements", elements),
            ):
                raw = row.get(key)
                if raw in (None, ""):
                    continue
                try:
                    value = float(raw)
                except ValueError:
                    continue
                if math.isfinite(value):
                    bucket.append(value)
            element = (row.get("element_type") or "").strip()
            if element:
                element_types.add(element)

    def build(names: tuple[str, ...]) -> list[dict]:
        summary = []
        for name in names:
            slot = acc[name]
            if not slot["n"]:
                continue
            summary.append(
                {
                    "name": name,
                    "min": slot["min"],
                    "mean": slot["sum"] / slot["n"],
                    "max": slot["max"],
                }
            )
        return summary

    stats = {
        "row_count": rows,
        "split_counts": split_counts,
        "shape_counts": shape_counts,
        "design_ranges": build(DESIGN_COLUMNS),
        "target_ranges": build(TARGET_COLUMNS),
        "median_runtime_seconds": statistics.median(runtimes) if runtimes else None,
        "mesh": {
            "median_nodes": statistics.median(nodes) if nodes else None,
            "median_elements": statistics.median(elements) if elements else None,
            "element_type": sorted(element_types)[0] if element_types else None,
        },
    }
    _DATASET_STATS_CACHE.clear()
    _DATASET_STATS_CACHE[cache_key] = stats
    return stats


def _field_model_summary(field_dir: Path, root: Path) -> dict:
    """Structured view of the field (GNN) model registry for the report API."""
    meta = _read_json(field_dir / "metadata.json")
    if meta is None:
        return {"present": False, "path": _relative_posix(field_dir, root)}
    held = _read_json(field_dir / "held_out_evaluation.json") or {}
    best = held.get("best_model")
    model_entry = (held.get("models") or {}).get(best) or {}
    evaluation: dict[str, dict] = {}
    for split, entry in (model_entry.get("evaluation") or {}).items():
        evaluation[split] = {
            "cases": entry.get("cases"),
            "max_displacement": entry.get("max_displacement"),
            "global_max_vm": entry.get("global_max_vm"),
            "roi_max_vm": entry.get("roi_max_vm"),
            "field_vm_error_median_pct": entry.get("field_vm_error_median_pct"),
            "field_vm_error_p95_pct": entry.get("field_vm_error_p95_pct"),
        }
    normalisation = meta.get("normalisation") or {}
    return {
        "present": True,
        "path": _relative_posix(field_dir, root),
        "schema_version": meta.get("schema_version"),
        "created_utc": meta.get("created_utc"),
        "device": meta.get("device"),
        "config": meta.get("config"),
        "split_counts": meta.get("split_counts"),
        "node_features": meta.get("node_features") or [],
        "edge_features": meta.get("edge_features") or [],
        "targets": meta.get("targets") or [],
        "normalisation": {
            "nodes": normalisation.get("nodes"),
            "target_scaling": normalisation.get("target_scaling"),
        },
        "training": {
            "seconds": model_entry.get("train_seconds"),
            "epochs_run": model_entry.get("epochs_run"),
            "best_val_loss": model_entry.get("best_val_loss"),
        },
        "evaluation": evaluation,
    }


def create_app(
    registry_dir: str | Path | None = None,
    dataset_path: str | Path | None = None,
    repo_root: str | Path | None = None,
    field_model_dir: str | Path | None = None,
    ccx_executable: str | None = None,
    web_dist: str | Path | None = None,
    max_job_workers: int | None = None,
) -> FastAPI:
    root = Path(repo_root) if repo_root else REPO_ROOT
    registry = _resolve(root, str(registry_dir or os.environ.get("SURROSIM_SCALAR_REGISTRY", DEFAULT_REGISTRY)))
    dataset = _resolve(root, str(dataset_path)) if dataset_path else None
    field_dir = (
        _resolve(root, str(field_model_dir))
        if field_model_dir
        else _resolve(root, os.environ.get("SURROSIM_FIELD_MODEL", DEFAULT_FIELD_MODEL))
    )
    dist = _resolve(root, str(web_dist)) if web_dist else root / "apps" / "web" / "dist"
    job_root = root / "outputs" / "jobs"
    reports_dir = root / "reports"
    docs_dir = root / "docs"
    dataset_card = root / "data" / "dataset_v2" / "dataset_card.md"
    if not dataset_card.exists():
        dataset_card = root / "data" / "dataset_v1" / "dataset_card.md"

    workers = max_job_workers or int(os.environ.get("SURROSIM_JOB_WORKERS", "2"))
    jobs = JobManager(max_workers=workers)

    app = FastAPI(
        title="SurroSim service",
        version="2.0.0",
        description=(
            "Surrogate predictions, FEA verification jobs, field prediction, "
            "optimization and model reports for parametric cantilever designs "
            "(plate, multi-hole, tapered, stepped, I-beam, L-bracket). "
            "Predictions carry domain/confidence metadata and are not a "
            "replacement for physics-based verification."
        ),
    )
    app.state.repo_root = root
    app.state.jobs = jobs
    app.state.predictor = ScalarPredictor.load(registry, dataset)
    app.state.field_model_dir = field_dir
    app.state.ccx = ccx_executable
    app.state.job_root = job_root

    origins = os.environ.get(
        "SURROSIM_CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[origin.strip() for origin in origins.split(",") if origin],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(GZipMiddleware, minimum_size=1024)

    @app.get("/api/health")
    def health() -> dict:
        return {
            "status": "ok",
            "registry": registry.as_posix(),
            "field_model": field_dir.exists(),
            "calculix": find_ccx(root, ccx_executable),
        }

    @app.get("/api/config")
    def config() -> dict:
        predictor: ScalarPredictor = app.state.predictor
        problem = OptimizationProblem()
        shape_bounds = predictor.shape_design_spaces()
        shape_entries = []
        for kind in shapes.SHAPE_KINDS:
            spec = shapes.spec(kind)
            default = representative_design(kind)
            bounds = shape_bounds.get(kind, {})
            shape_entries.append(
                {
                    "kind": kind,
                    "label": spec.label,
                    "summary": spec.summary,
                    "has_hole": spec.has_hole,
                    "has_fillet": spec.has_fillet,
                    "load_dof": spec.load_dof,
                    "defaults": default.as_dict(),
                    "bounds": bounds,
                    "params": [
                        {
                            "name": param.name,
                            "label": param.label,
                            "unit": param.unit,
                            "default": float(getattr(default, param.name)),
                            "bounds": bounds.get(param.name),
                        }
                        for param in spec.params
                        if hasattr(default, param.name)
                    ],
                }
            )
        return {
            "design_defaults": Plate().as_dict(),
            "design_bounds": predictor.design_space_bounds(),
            "shapes": shape_entries,
            "optimizer_defaults": {
                "length_mm": problem.length_mm,
                "force_n": problem.force_n,
                "sigma_allow_mpa": problem.sigma_allow_mpa,
                "displacement_limit_mm": problem.displacement_limit_mm,
            },
            "optimizer_bounds": {
                "width_mm": list(problem.width_bounds),
                "thickness_mm": list(problem.thickness_bounds),
                "diameter_ratio": list(problem.diameter_ratio_bounds),
                "hole_x_ratio": list(problem.hole_x_ratio_bounds),
            },
            "mesh_policy": DEFAULT_POLICY.as_dict(),
            "capabilities": {
                "calculix": find_ccx(root, ccx_executable) is not None,
                "field_model": field_dir.exists(),
                "max_job_workers": workers,
            },
        }

    @app.get("/api/model")
    def model_info() -> dict:
        predictor: ScalarPredictor = app.state.predictor
        return {
            "registry": predictor.registry_dir.as_posix(),
            "dataset_sha256": predictor.metadata["dataset_sha256"],
            "created_utc": predictor.metadata["created_utc"],
            "targets": predictor.metadata.get("best_models", {}),
            "git_commit": (predictor.metadata.get("git") or {}).get("commit"),
        }

    @app.get("/api/domain")
    def domain() -> dict:
        predictor: ScalarPredictor = app.state.predictor
        return {
            "bounds": predictor.design_space_bounds(),
            "shape_bounds": predictor.shape_design_spaces(),
            "notes": [
                "Bounds are the sampled design space of the active dataset.",
                "material defaults: E = 210000 MPa, nu = 0.3 (steel).",
            ],
        }

    @app.post("/api/predict")
    def predict(request: DesignRequest) -> dict:
        predictor: ScalarPredictor = app.state.predictor
        try:
            return predictor.predict(request.as_plate())
        except (ValueError, RuntimeError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.get("/api/reports/model")
    def model_report() -> dict:
        predictor: ScalarPredictor = app.state.predictor
        metadata = predictor.metadata
        targets = []
        for target, results in metadata["targets"].items():
            rows = []
            for name, entry in sorted(
                results["models"].items(),
                key=lambda item: item[1]["test"]["mape_pct"],
            ):
                rows.append(
                    {
                        "model": name,
                        "params": entry.get("params"),
                        "val_mape_pct": (entry.get("val") or {}).get("mape_pct"),
                        "test_mape_pct": entry["test"]["mape_pct"],
                        "test_worst_pct": entry["test"]["max_rel_error_pct"],
                        "test_rmse": entry["test"].get("rmse"),
                        "test_r2": entry["test"].get("r2"),
                        "challenge_mape_pct": entry["challenge"]["mape_pct"],
                        "challenge_worst_pct": entry["challenge"][
                            "max_rel_error_pct"
                        ],
                        "latency_ms_per_1k": entry.get("latency_ms_per_1k"),
                        "path": entry.get("path"),
                    }
                )
            baselines = [
                {
                    "name": name,
                    "test_mape_pct": (entry.get("test") or {}).get("mape_pct"),
                    "test_worst_pct": (entry.get("test") or {}).get(
                        "max_rel_error_pct"
                    ),
                    "test_rmse": (entry.get("test") or {}).get("rmse"),
                }
                for name, entry in (results.get("baselines") or {}).items()
            ]
            targets.append(
                {
                    "target": target,
                    "best_model": results["best_model"],
                    "selection_rule": results.get("selection_rule"),
                    "models": rows,
                    "baselines": baselines,
                }
            )

        figures = []
        figures_dir = reports_dir / "figures"
        if figures_dir.exists():
            for figure in sorted(figures_dir.rglob("*.png")):
                figures.append(
                    {
                        "name": figure.stem,
                        "group": figure.parent.name,
                        "url": "/files/figures/"
                        + figure.relative_to(figures_dir).as_posix(),
                    }
                )

        cards = {
            "model_card": _read_text(docs_dir / "model_card_scalar.md"),
            "dataset_card": _read_text(dataset_card),
            "scalar_comparison": _read_text(registry / "report.md") or _read_text(
                reports_dir / "v2.0_scalar_comparison.md"
            )
            or _read_text(reports_dir / "v0.4_scalar_comparison.md"),
            "gnn_report": _read_text(field_dir / "report.md") or _read_text(reports_dir / "v2.0_gnn_field_prediction.md")
            or _read_text(reports_dir / "v0.6_gnn_field_prediction.md"),
            "optimization_report": _read_text(reports_dir / "v1.0_optimization.md"),
            "field_model_card": _read_text(docs_dir / "model_card_gnn.md"),
        }

        dataset = {
            "path": str(metadata.get("dataset")),
            "sha256": metadata.get("dataset_sha256"),
            "created_utc": metadata.get("created_utc"),
            "row_count": metadata.get("row_count"),
            "split_counts": metadata.get("split_counts"),
        }
        registry_meta = {
            "schema_version": metadata.get("schema_version"),
            "seed": metadata.get("seed"),
            "created_utc": metadata.get("created_utc"),
            "dataset": metadata.get("dataset"),
            "target_transform": metadata.get("target_transform"),
            "features": metadata.get("features") or [],
            "selections": {
                target: {
                    "best_model": results.get("best_model"),
                    "selection_rule": results.get("selection_rule"),
                }
                for target, results in metadata["targets"].items()
            },
        }
        return {
            "registry": predictor.registry_dir.as_posix(),
            "created_utc": metadata.get("created_utc"),
            "git": metadata.get("git"),
            "dataset": dataset,
            "targets": targets,
            "figures": figures,
            "cards": cards,
            "registry_meta": registry_meta,
            "field_model": _field_model_summary(field_dir, root),
        }

    @app.get("/api/reports/dataset")
    def dataset_report() -> dict:
        predictor: ScalarPredictor = app.state.predictor
        metadata = predictor.metadata
        dataset_file = predictor.dataset_path
        manifest = (
            _read_json(dataset_file.parent / "manifest.json")
            if dataset_file is not None
            else None
        )
        stats = _dataset_stats(dataset_file)
        manifest = manifest or {}
        split_counts = stats["split_counts"] or manifest.get("split_counts") or {}
        shape_counts = stats["shape_counts"] or manifest.get("shape_counts") or {}
        row_count = stats["row_count"] or manifest.get("cases_in_dataset")
        card = (
            _read_text(dataset_file.parent / "dataset_card.md")
            if dataset_file is not None
            else None
        ) or _read_text(dataset_card)
        return {
            "path": (
                _relative_posix(dataset_file, root)
                if dataset_file is not None
                else str(metadata.get("dataset"))
            ),
            "sha256": metadata.get("dataset_sha256"),
            "created_utc": manifest.get("created_utc") or metadata.get("created_utc"),
            "row_count": row_count,
            "split_counts": split_counts,
            "shape_counts": shape_counts,
            "manifest": {
                "schema_version": manifest.get("schema_version"),
                "designs_file": manifest.get("designs_file"),
                "designs_sha256": manifest.get("designs_sha256"),
                "cases_in_designs": manifest.get("cases_in_designs"),
                "cases_from_base": manifest.get("cases_from_base"),
                "cases_in_dataset": manifest.get("cases_in_dataset"),
                "cases_failed": manifest.get("cases_failed"),
                "solver": manifest.get("solver"),
                "environment": manifest.get("environment"),
                "git": manifest.get("git"),
                "gates": manifest.get("gates") or [],
                "mesh_policy": manifest.get("mesh_policy"),
                "base_datasets": manifest.get("base_datasets") or [],
            }
            if manifest
            else None,
            "design_ranges": stats["design_ranges"],
            "target_ranges": stats["target_ranges"],
            "median_runtime_seconds": stats["median_runtime_seconds"],
            "mesh": stats["mesh"],
            "card": card,
        }

    def submit(kind: str, worker) -> dict:
        job = jobs.submit(kind, worker)
        return {"job": job.to_dict()}

    @app.post("/api/jobs/fea-verify", status_code=202)
    def fea_verify(request: FeaVerifyRequest) -> dict:
        ccx = find_ccx(root, ccx_executable)
        if ccx is None:
            raise HTTPException(
                status_code=409,
                detail=(
                    "CalculiX executable not found. Place ccx in "
                    "tools/calculix/, install it on PATH or set SURROSIM_CCX."
                ),
            )
        design = request.as_plate()

        def worker(job: Job) -> dict:
            predictor: ScalarPredictor = app.state.predictor
            plate = _plate_from_design(design)
            case_id = _case_id("verify", plate)
            job.log(f"sending case {case_id} to a solver worker process")
            result = run_in_process(
                fea_verify_entry,
                {
                    "case_id": case_id,
                    "design": design,
                    "runs_root": str(job_root / job.id),
                    "ccx": ccx,
                    "timeout_seconds": 900.0,
                    "force": request.force,
                },
                job,
                timeout_seconds=1080.0,
            )
            job.set_progress(None, "comparing")
            surrogate = predictor.predict(design)
            fea = result["fea"]
            comparison = []
            for target, (label, unit) in (
                ("max_displacement_mm", ("Max displacement", "mm")),
                (
                    "global_max_von_mises_mpa",
                    ("Global max Von Mises", "MPa"),
                ),
                ("max_von_mises_roi_mpa", ("Stress-riser ROI max Von Mises", "MPa")),
            ):
                entry = surrogate["predictions"].get(target) or {}
                predicted = entry.get("value")
                reference = fea.get(target)
                error_pct = (
                    100.0 * (predicted - reference) / reference
                    if predicted is not None and reference
                    else None
                )
                comparison.append(
                    {
                        "target": target,
                        "label": label,
                        "unit": unit,
                        "surrogate": predicted,
                        "fea": reference,
                        "error_pct": error_pct,
                    }
                )
            case_dir = Path(result["case_dir"])
            job.artifacts = {
                "mesh": str(case_dir / "mesh.msh"),
                "fields": str(case_dir / "fields.npz"),
            }
            job.log("verification comparison ready")
            return {
                "case_id": case_id,
                "status": result["status"],
                "cached": result["status"] == "CACHED",
                "design": design,
                "mesh_policy": DEFAULT_POLICY.as_dict(),
                "deck": result.get("deck"),
                "solver": result.get("solver"),
                "fea": fea,
                "surrogate": surrogate["predictions"],
                "confidence": surrogate["confidence"],
                "surrogate_latency_ms": surrogate["latency_ms"],
                "comparison": comparison,
                "available_fields": list(FIELD_FILES),
            }

        return submit("fea_verify", worker)

    @app.post("/api/jobs/field-predict", status_code=202)
    def field_predict(request: DesignRequest) -> dict:
        if not field_dir.exists():
            raise HTTPException(
                status_code=409,
                detail=(
                    "No trained field model found in models/gnn/v1. Train one "
                    "with `surrosim train gnn` first."
                ),
            )
        design = request.as_plate()

        def worker(job: Job) -> dict:
            job.log("sending field prediction to a worker process")
            result = run_in_process(
                field_predict_entry,
                {
                    "design": design,
                    "model_dir": str(field_dir),
                    "workdir": str(job_root / job.id / "field"),
                },
                job,
                timeout_seconds=900.0,
            )
            job.artifacts = {
                "mesh": result["mesh_path"],
                "fields": result["fields_npz"],
            }
            return {
                "design": design,
                "model": result["model"],
                "graph_nodes": result["graph_nodes"],
                "runtime_ms": result["runtime_ms"],
                "scalars": result["scalars"],
                "available_fields": list(FIELD_FILES),
            }

        return submit("field_predict", worker)

    @app.post("/api/jobs/optimize", status_code=202)
    def optimize(request: OptimizeRequest) -> dict:
        ccx = find_ccx(root, ccx_executable)
        if request.verify_candidates and ccx is None:
            raise HTTPException(
                status_code=409,
                detail="FEA verification of candidates requires CalculiX.",
            )

        def worker(job: Job) -> dict:
            from ..optimize import optimize_design

            predictor: ScalarPredictor = app.state.predictor
            out_dir = job_root / job.id / "optimization"
            problem = OptimizationProblem(
                shape=request.shape,
                length_mm=request.length_mm,
                force_n=request.force_n,
                sigma_allow_mpa=request.sigma_allow_mpa,
                displacement_limit_mm=request.displacement_limit_mm,
            )

            def progress(completed: int, expected: int) -> None:
                job.set_progress(
                    completed / expected if expected else None,
                    f"{completed} surrogate evaluations",
                )

            job.log(
                f"minimising mass at L={request.length_mm:g} mm, "
                f"F={request.force_n:g} N, sigma<={request.sigma_allow_mpa:g} MPa, "
                f"delta<={request.displacement_limit_mm:g} mm"
            )
            metadata = optimize_design(
                problem=problem,
                predictor=predictor,
                seed=request.seed,
                maxiter=request.maxiter,
                verify=request.verify_candidates and ccx is not None,
                ccx_executable=ccx,
                out_dir=out_dir,
                report_path=out_dir / "report.md",
                figure_dir=out_dir / "figures",
                progress_callback=progress,
            )
            optimizer = metadata["optimizer"]
            job.log(
                f"{optimizer['evaluations']} evaluations in "
                f"{optimizer['seconds']:.1f} s; "
                f"{len(metadata['candidates'])} feasible candidates"
            )
            return metadata

        return submit("optimize", worker)

    @app.get("/api/jobs")
    def list_jobs(limit: int = 20) -> dict:
        return {"jobs": [job.to_dict() for job in jobs.list(limit=limit)]}

    @app.get("/api/jobs/{job_id}")
    def get_job(job_id: str) -> dict:
        job = jobs.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Unknown job id")
        return job.to_dict()

    @app.get("/api/fields/{job_id}")
    def get_field(job_id: str, field: str = "von_mises_mpa") -> dict:
        job = jobs.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Unknown job id")
        meta = FIELD_META.get(field)
        if meta is None:
            raise HTTPException(
                status_code=404,
                detail=f"Unknown field {field!r}; expected one of {sorted(FIELD_META)}",
            )
        mesh = job.artifacts.get("mesh")
        fields = job.artifacts.get("fields")
        if not mesh or not fields:
            raise HTTPException(
                status_code=404,
                detail="Job has no field artifacts (not finished or not a field job)",
            )
        try:
            return field_payload(mesh, fields, field)
        except (OSError, ValueError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    if reports_dir.exists():
        app.mount(
            "/files/figures",
            StaticFiles(directory=reports_dir / "figures"),
            name="figures",
        )

    if dist.exists() and (dist / "index.html").exists():
        assets = dist / "assets"
        if assets.exists():
            app.mount("/assets", StaticFiles(directory=assets), name="assets")

        @app.get("/{full_path:path}", include_in_schema=False)
        def spa(full_path: str):
            if full_path.startswith(
                ("api/", "files/", "docs", "redoc", "openapi.json")
            ):
                raise HTTPException(status_code=404, detail="Not found")
            candidate = dist / full_path
            if full_path and candidate.is_file():
                return FileResponse(candidate)
            return FileResponse(dist / "index.html")

    return app


if __name__ == "__main__":  # pragma: no cover - convenience runner
    import uvicorn

    uvicorn.run(create_app(), host="127.0.0.1", port=8003)

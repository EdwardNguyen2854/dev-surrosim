"""Spawned-process entry points for jobs that require the main thread.

Gmsh installs a SIGINT handler in ``initialize()``, which Python only allows
on the main thread of the main interpreter. Background jobs therefore run the
meshing pipelines (FEA cases, field prediction) in a dedicated spawned process
and stream stages, logs and results back through a multiprocessing queue.
"""

from __future__ import annotations

import json
import traceback
from pathlib import Path
from typing import Any

Message = dict[str, Any]


def _send(queue, message: Message) -> None:
    queue.put(message)


def _stage(queue, stage: str, progress: float | None = None) -> None:
    _send(queue, {"kind": "stage", "stage": stage, "progress": progress})


def _log(queue, message: str, level: str = "info") -> None:
    _send(queue, {"kind": "log", "level": level, "message": message})


def fea_verify_entry(payload: dict, queue) -> None:
    try:
        from ..dataset.cases import run_case
        from ..plate import Plate

        design = payload["design"]
        plate = Plate.from_mapping(design)
        _stage(queue, "meshing")
        _log(queue, "generating mesh and CalculiX deck")
        _stage(queue, "solving")
        _log(queue, f"running solver {payload['ccx']}")
        outcome = run_case(
            payload["case_id"],
            plate,
            payload["runs_root"],
            payload["ccx"],
            timeout_seconds=payload["timeout_seconds"],
            force=payload["force"],
        )
        _log(queue, f"solver status {outcome['status']}")
        if outcome["status"] not in ("SUCCESS", "CACHED"):
            raise RuntimeError(f"FEA case finished with status {outcome['status']}")
        _stage(queue, "extracting")
        case_dir = Path(payload["runs_root"]) / payload["case_id"]
        summary = json.loads((case_dir / "run.json").read_text(encoding="utf-8"))
        _stage(queue, "done", 1.0)
        _send(
            queue,
            {
                "kind": "result",
                "result": {
                    "case_dir": str(case_dir),
                    "status": outcome["status"],
                    "deck": summary.get("deck"),
                    "solver": summary.get("solver"),
                    "fea": summary.get("results") or {},
                },
            },
        )
    except Exception:  # noqa: BLE001 - forwarded to the job as an error
        _send(queue, {"kind": "error", "error": traceback.format_exc(limit=10)})


def field_predict_entry(payload: dict, queue) -> None:
    try:
        from .field_predictor import FieldPredictor

        _stage(queue, "loading model")
        _log(queue, "loading MeshGraphNet checkpoint")
        predictor = FieldPredictor(payload["model_dir"])
        _stage(queue, "meshing")
        _log(queue, "generating coarse graph mesh")
        _stage(queue, "inference")
        _log(queue, "running message-passing inference")
        result = predictor.predict(payload["design"], payload["workdir"])
        _log(
            queue,
            f"predicted fields on {result['graph_nodes']} nodes in "
            f"{result['runtime_ms'] / 1000:.2f} s",
        )
        _stage(queue, "done", 1.0)
        _send(
            queue,
            {
                "kind": "result",
                "result": {
                    "scalars": result["scalars"],
                    "model": result["model"],
                    "graph_nodes": result["graph_nodes"],
                    "runtime_ms": result["runtime_ms"],
                    "mesh_path": str(result["mesh_path"]),
                    "fields_npz": str(result["fields_npz"]),
                },
            },
        )
    except Exception:  # noqa: BLE001 - forwarded to the job as an error
        _send(queue, {"kind": "error", "error": traceback.format_exc(limit=10)})


def probe_entry(payload: dict, queue) -> None:
    """Minimal entry point used by the job-process test."""
    _stage(queue, "probing", 0.25)
    _log(queue, f"probing {payload.get('value')}")
    _stage(queue, "done", 1.0)
    _send(queue, {"kind": "result", "result": {"value": payload.get("value")}})

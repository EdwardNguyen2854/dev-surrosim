"""Export completed FEA cases as mesh graphs for geometric deep learning.

Each graph covers the corner nodes of the tetrahedral mesh (the linear
geometry), with edge connectivity derived from the corner tetrahedra.
Node/edge features are physics-aware (boundary flags, hole proximity,
normalised coordinates and global design parameters); targets are the nodal
displacement and stress components from the CalculiX solution.
"""

from pathlib import Path
import csv
import json

import numpy as np
import torch

from ..plate import Plate
from ..provenance import git_info, sha256, tool_versions
from ..simulation.msh2 import read_msh2
from .features import NODE_FEATURES, EDGE_FEATURES, TARGET_COMPONENTS, build_graph_tensors


def _load_designs(path: str | Path) -> list[dict]:
    with Path(path).open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def export_graphs(
    designs_path: str | Path,
    runs_root: str | Path,
    out_root: str | Path,
    min_nodes: int = 200,
) -> dict:
    designs = _load_designs(designs_path)
    runs_root = Path(runs_root)
    output = Path(out_root)
    output.mkdir(parents=True, exist_ok=True)

    exported: list[dict] = []
    skipped: list[dict] = []
    for row in designs:
        case_id = row["case_id"]
        case_dir = runs_root / case_id
        run_json = case_dir / "run.json"
        mesh_path = case_dir / "mesh.msh"
        fields_path = case_dir / "fields.npz"
        if not (run_json.exists() and mesh_path.exists() and fields_path.exists()):
            skipped.append({"case_id": case_id, "reason": "MISSING_ARTIFACTS"})
            continue
        summary = json.loads(run_json.read_text(encoding="utf-8"))
        if summary.get("status") != "SUCCESS":
            skipped.append({"case_id": case_id, "reason": summary.get("status")})
            continue
        min_sicn = (summary.get("geometry") or {}).get("mesh_min_sicn")
        if min_sicn is not None and min_sicn <= 0:
            skipped.append({"case_id": case_id, "reason": "DEGENERATE_MESH"})
            continue

        mesh = read_msh2(mesh_path)
        with np.load(fields_path) as data:
            fields = {key: data[key] for key in data.files}
        try:
            tensors = build_graph_tensors(row, mesh, fields)
        except ValueError as exc:
            skipped.append({"case_id": case_id, "reason": f"GRAPH_ERROR: {exc}"})
            continue
        if tensors["x"].shape[0] < min_nodes:
            skipped.append({"case_id": case_id, "reason": "TOO_FEW_NODES"})
            continue

        graph = {
            **tensors,
            "case_id": case_id,
            "split": row["split"],
            "tag": row["tag"],
            "params": Plate.from_mapping(row).as_dict(),
        }
        torch.save(graph, output / f"{case_id}.pt")
        exported.append(
            {
                "case_id": case_id,
                "split": row["split"],
                "nodes": int(tensors["x"].shape[0]),
                "edges": int(tensors["edge_index"].shape[1]),
            }
        )

    split_counts: dict[str, int] = {}
    for entry in exported:
        split_counts[entry["split"]] = split_counts.get(entry["split"], 0) + 1
    manifest = {
        "schema_version": "1.0.0",
        "graphs": len(exported),
        "skipped": len(skipped),
        "split_counts": split_counts,
        "node_features": NODE_FEATURES,
        "edge_features": EDGE_FEATURES,
        "targets": TARGET_COMPONENTS,
        "total_nodes": sum(entry["nodes"] for entry in exported),
        "total_edges": sum(entry["edges"] for entry in exported),
        "mean_nodes": (
            sum(entry["nodes"] for entry in exported) / len(exported)
            if exported else None
        ),
        "designs_file": str(designs_path),
        "designs_sha256": sha256(designs_path),
        "runs_root": str(runs_root),
        "skipped_cases": skipped,
        "tool_versions": tool_versions(),
        "git": git_info(),
    }
    (output / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    (output / "index.json").write_text(
        json.dumps(exported, indent=2) + "\n", encoding="utf-8"
    )
    return manifest

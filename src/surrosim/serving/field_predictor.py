"""On-demand field prediction: coarse mesh generation + GNN inference.

Used by the engineering app to visualise predicted displacement and stress
fields. The same coarse ``graph`` mesh policy as the training data is used so
the graph statistics match what the GNN was trained on.
"""

from dataclasses import replace
from pathlib import Path
import json
import shutil
import time

import numpy as np
import torch

from .. import shapes
from ..geometry import generate_design
from ..gnn.device import resolve_device
from ..gnn.features import build_geometry_tensors, von_mises
from ..gnn.models import build_model
from ..gnn.normalisation import decode_targets
from ..mesh_policy import GRAPH_POLICY
from ..plate import Plate
from ..simulation.msh2 import read_msh2


class FieldPredictor:
    def __init__(self, model_dir: str | Path = "models/gnn/v2") -> None:
        self.model_dir = Path(model_dir)
        metadata_path = self.model_dir / "metadata.json"
        if not metadata_path.exists():
            raise FileNotFoundError(f"No field-model metadata at {metadata_path}")
        self.metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        self.model_name = self.metadata["best_model"]
        checkpoint = torch.load(
            self.model_dir / f"{self.model_name}.pt",
            map_location="cpu",
            weights_only=False,
        )
        config = checkpoint["config"]
        self.device = resolve_device()
        self.model = build_model(
            self.model_name,
            len(checkpoint["node_features"]),
            len(checkpoint["edge_features"]),
            hidden=config["hidden"] if self.model_name == "meshgraphnet" else 128,
            layers=config["layers"] if self.model_name == "meshgraphnet" else 3,
        ).to(self.device)
        self.model.load_state_dict(checkpoint["state_dict"])
        self.model.eval()
        normalisation = self.metadata["normalisation"]
        self.normalisation = normalisation
        self.x_mean = torch.tensor(normalisation["x_mean"], device=self.device)
        self.x_std = torch.tensor(normalisation["x_std"], device=self.device)
        self.y_mean = np.array(normalisation["y_mean"])
        self.y_std = np.array(normalisation["y_std"])

    def predict(self, design: dict, workdir: str | Path) -> dict:
        start = time.perf_counter()
        workdir = Path(workdir)
        if workdir.exists():
            shutil.rmtree(workdir)
        plate = Plate.from_mapping(design)
        mesh_design = replace(
            plate, mesh_size_mm=GRAPH_POLICY.global_size_mm(plate)
        )
        generate_design(
            mesh_design, workdir, element_order=GRAPH_POLICY.element_order,
            hole_refinement_mm=GRAPH_POLICY.refinement_mm(mesh_design),
            quiet=True,
        )
        mesh = read_msh2(workdir / "mesh.msh")
        tensors = build_geometry_tensors(plate.as_dict(), mesh)
        with torch.no_grad():
            prediction = self.model(
                (tensors["x"].to(self.device) - self.x_mean) / self.x_std,
                tensors["edge_index"].to(self.device),
                tensors["edge_attr"].to(self.device),
            ).cpu().numpy()
        prediction = decode_targets(prediction, plate.as_dict(), self.normalisation)
        displacement = np.linalg.norm(prediction[:, :3], axis=1)
        vm = von_mises(prediction[:, 3:])
        coordinates = tensors["coordinates"].numpy()
        node_ids = tensors["node_ids"].numpy()

        roi_mask = shapes.roi_mask(coordinates, plate)
        fields_npz = workdir / "predicted_fields.npz"
        np.savez_compressed(
            fields_npz,
            node_id=node_ids,
            von_mises_mpa=vm.astype(np.float32),
            displacement_mm=displacement.astype(np.float32),
        )
        return {
            "node_ids": node_ids,
            "coordinates": coordinates,
            "displacement_mm": displacement,
            "von_mises_mpa": vm,
            "scalars": {
                "max_displacement_mm": float(displacement.max()),
                "global_max_von_mises_mpa": float(vm.max()),
                "roi_max_von_mises_mpa": (
                    float(vm[roi_mask].max()) if roi_mask.any() else None
                ),
            },
            "mesh_path": workdir / "mesh.msh",
            "fields_npz": fields_npz,
            "model": self.model_name,
            "graph_nodes": int(tensors["x"].shape[0]),
            "runtime_ms": (time.perf_counter() - start) * 1000.0,
        }

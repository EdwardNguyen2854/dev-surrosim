import json
from pathlib import Path

import numpy as np
import pytest
import torch

from surrosim.gnn.features import (
    EDGE_FEATURES,
    NODE_FEATURES,
    TARGET_COMPONENTS,
    build_graph_tensors,
)
from surrosim.gnn.models import MeshGraphNet, NodeMLP, build_model
from surrosim.gnn.normalisation import decode_targets, target_scales
from surrosim.plate import Plate
from surrosim.sampling import shape_space
from surrosim.simulation.msh2 import GmshMesh, MeshElement

pytestmark = pytest.mark.filterwarnings("ignore::UserWarning")

ROOT = Path(__file__).resolve().parents[1]


def _single_tet_mesh() -> GmshMesh:
    nodes = {
        1: (0.0, 0.0, 0.0),
        2: (1.0, 0.0, 0.0),
        3: (0.0, 1.0, 0.0),
        4: (0.0, 0.0, 1.0),
    }
    element = MeshElement(
        element_id=1, element_type=4, physical_tag=1, nodes=(1, 2, 3, 4)
    )
    return GmshMesh(nodes=nodes, physical_names={(3, 1): "SOLID"}, elements=(element,))


def _fields() -> dict:
    return {
        "node_id": np.array([1, 2, 3, 4]),
        "ux_mm": np.array([0.0, 0.1, 0.2, 0.3]),
        "uy_mm": np.array([0.0, 0.0, 0.1, 0.2]),
        "uz_mm": np.array([0.0, 0.0, 0.0, 0.4]),
        "sxx_mpa": np.array([1.0, 2.0, 3.0, 4.0]),
        "syy_mpa": np.array([0.0, 0.5, 1.0, 1.5]),
        "szz_mpa": np.array([0.0, 0.5, 1.0, 1.5]),
        "sxy_mpa": np.zeros(4),
        "syz_mpa": np.zeros(4),
        "szx_mpa": np.zeros(4),
    }


def _row() -> dict:
    return {
        "length_mm": 1.0, "width_mm": 1.0, "thickness_mm": 1.0,
        "hole_diameter_mm": 0.0, "hole_x_mm": 0.5, "force_n": 10.0,
        "youngs_modulus_mpa": 210_000.0, "poisson_ratio": 0.3,
    }


def test_build_graph_tensors_shapes_and_flags():
    tensors = build_graph_tensors(_row(), _single_tet_mesh(), _fields())
    assert tensors["x"].shape == (4, len(NODE_FEATURES))
    assert tensors["edge_index"].shape == (2, 6)
    assert tensors["edge_attr"].shape == (6, len(EDGE_FEATURES))
    assert tensors["y"].shape == (4, len(TARGET_COMPONENTS))
    assert tensors["x"][:, NODE_FEATURES.index("is_fixed")].tolist() == [1, 0, 1, 1]
    assert tensors["x"][:, NODE_FEATURES.index("is_load")].sum() == 1
    assert tensors["y"][3, 2] == pytest.approx(0.4)


def test_build_graph_rejects_missing_field_nodes():
    fields = _fields()
    fields["node_id"] = np.array([1, 2, 3])
    with pytest.raises(ValueError, match="missing"):
        build_graph_tensors(_row(), _single_tet_mesh(), fields)


def test_models_forward_shapes():
    tensors = build_graph_tensors(_row(), _single_tet_mesh(), _fields())
    graph = MeshGraphNet(
        node_features=len(NODE_FEATURES), edge_features=len(EDGE_FEATURES),
        hidden=16, layers=2,
    )
    output = graph(tensors["x"], tensors["edge_index"], tensors["edge_attr"])
    assert output.shape == (4, len(TARGET_COMPONENTS))
    baseline = build_model("node_mlp", len(NODE_FEATURES), len(EDGE_FEATURES))
    assert baseline(tensors["x"]).shape == (4, len(TARGET_COMPONENTS))


@pytest.mark.parametrize("shape", ["plate", "taper", "multi_hole", "stepped", "i_beam", "l_bracket"])
def test_nominal_scaling_respects_load_and_elastic_modulus(shape):
    if shape == "plate":
        params = Plate().as_dict()
    else:
        space = shape_space(shape)
        params = space.design_from_unit((0.5,) * space.dimensions()).as_dict()
    scale = target_scales(params, "nominal_v1")
    doubled_load = target_scales({**params, "force_n": params["force_n"] * 2}, "nominal_v1")
    stiffer = target_scales({**params, "youngs_modulus_mpa": params["youngs_modulus_mpa"] * 2}, "nominal_v1")
    np.testing.assert_allclose(doubled_load, scale * 2)
    np.testing.assert_allclose(stiffer[:3], scale[:3] / 2)
    np.testing.assert_allclose(stiffer[3:], scale[3:])
    truth = np.arange(27, dtype=float).reshape(3, 9) - 10
    mean = np.arange(9, dtype=float) / 10
    std = np.arange(1, 10, dtype=float)
    encoded = (truth / scale - mean) / std
    restored = decode_targets(encoded, params, {
        "target_scaling": "nominal_v1", "y_mean": mean, "y_std": std,
    })
    np.testing.assert_allclose(restored, truth, atol=1e-10)


def test_legacy_target_decoding_and_unknown_mode():
    prediction = np.ones((4, 9))
    np.testing.assert_allclose(decode_targets(prediction, {}, {
        "y_mean": [1] * 9, "y_std": [2] * 9,
    }), 3)
    with pytest.raises(ValueError, match="Unknown field target scaling"):
        target_scales({}, "invalid")


def test_model_selection_ignores_test_and_challenge_scores():
    from surrosim.gnn.train import _select_model

    models = {
        "validation_winner": {"evaluation": {
            "val": {"global_max_vm": {"mape": 5}},
            "test": {"global_max_vm": {"mape": 100}},
        }},
        "test_winner": {"evaluation": {
            "val": {"global_max_vm": {"mape": 10}},
            "test": {"global_max_vm": {"mape": 0}},
            "challenge": {"global_max_vm": {"mape": 0}},
        }},
    }
    assert _select_model(models) == "validation_winner"


@pytest.mark.parametrize("target_scaling", ["none", "nominal_v1"])
def test_train_gnn_smoke_on_synthetic_graphs(tmp_path, target_scaling):
    pytest.importorskip("torch")
    from surrosim.gnn import export as export_module
    from surrosim.gnn.train import train_gnn

    graph_dir = tmp_path / "graphs"
    graph_dir.mkdir()
    index = []
    for number in range(6):
        split = "train" if number < 4 else "val"
        case_id = f"case_{number:02d}"
        row = {**_row(), "force_n": 10.0 + number}
        tensors = build_graph_tensors(row, _single_tet_mesh(), _fields())
        torch.save(
            {**tensors, "case_id": case_id, "split": split, "tag": "synthetic", "params": row},
            graph_dir / f"{case_id}.pt",
        )
        index.append(
            {"case_id": case_id, "split": split, "nodes": 4, "edges": 6}
        )
    (graph_dir / "index.json").write_text(json.dumps(index), encoding="utf-8")

    metadata = train_gnn(
        graph_dir=graph_dir,
        runs_root=tmp_path / "runs",
        out_dir=tmp_path / "models",
        report_path=tmp_path / "report.md",
        figure_dir=tmp_path / "figures",
        epochs=2,
        patience=2,
        models=("node_mlp",),
        max_graphs_per_split=None,
        target_scaling=target_scaling,
        validation_only=True,
    )
    assert "node_mlp" in metadata["models"]
    assert (tmp_path / "models" / "node_mlp.pt").exists()
    assert (tmp_path / "report.md").exists()
    report = (tmp_path / "report.md").read_text(encoding="utf-8")
    assert "GNN field prediction" in report
    assert metadata["graph_index_sha256"]
    assert metadata["selection_split"] == "val"
    assert set(metadata["models"]["node_mlp"]["evaluation"]) == {"val"}
    assert "plate" in metadata["models"]["node_mlp"]["evaluation"]["val"]["by_shape"]
    assert metadata["normalisation"]["target_scaling"] == target_scaling

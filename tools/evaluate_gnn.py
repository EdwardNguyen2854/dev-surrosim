"""Evaluate a frozen GNN candidate; never train or change model selection."""

import argparse
import json
from pathlib import Path

from surrosim.gnn.train import _evaluate, _load_index, _report
from surrosim.provenance import sha256
from surrosim.serving.field_predictor import FieldPredictor


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default="models/gnn/v2_normalized_candidate")
    parser.add_argument("--report", default="reports/v2.0_gnn_normalized_holdout.md")
    args = parser.parse_args()
    predictor = FieldPredictor(args.model)
    metadata = predictor.metadata
    graph_dir = Path(metadata["graph_dataset"])
    if sha256(graph_dir / "index.json") != metadata["graph_index_sha256"]:
        raise ValueError("Graph index changed since training")
    checkpoint = Path(args.model) / f"{predictor.model_name}.pt"
    metadata["evaluated_checkpoint_sha256"] = sha256(checkpoint)
    evaluation = metadata["models"][predictor.model_name]["evaluation"]
    index = _load_index(graph_dir)
    for split in ("test", "challenge"):
        ids = sorted(row["case_id"] for row in index if row["split"] == split)
        evaluation[split] = _evaluate(
            predictor.model, graph_dir, ids, metadata["normalisation"],
            Path("data/runs_v2_graph"), predictor.device,
        )
        print(split, json.dumps({key: value for key, value in evaluation[split].items()
                                if key not in ("rows", "by_shape")}), flush=True)
    if sha256(checkpoint) != metadata["evaluated_checkpoint_sha256"]:
        raise RuntimeError("Checkpoint changed during evaluation")
    (Path(args.model) / "held_out_evaluation.json").write_text(json.dumps(metadata, indent=2) + "\n")
    report = Path(args.report)
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(_report(metadata) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()

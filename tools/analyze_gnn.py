"""Reproduce candidate field-error summaries by shape without running inference."""

import argparse
import json
from pathlib import Path

import numpy as np

from surrosim.dataset.batch import load_designs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default="models/gnn/v2_candidate")
    parser.add_argument("--split", default="test")
    parser.add_argument("--max-displacement-mape", type=float, default=50)
    args = parser.parse_args()
    metadata = json.loads((Path(args.model) / "metadata.json").read_text())
    designs = {r.case_id: r.plate for r in load_designs("data/designs_v2.csv")}
    model = metadata["models"][metadata["best_model"]]
    evaluation = model["evaluation"][args.split]
    print("shape | n | displacement MAPE % | stress MAPE % | true displacement range mm")
    for shape in sorted({d.shape for d in designs.values()}):
        rows = [r for r in evaluation["rows"] if designs[r["case_id"]].shape == shape]
        if not rows:
            continue
        truth = np.array([r["true_max_displacement_mm"] for r in rows])
        predicted = np.array([r["pred_max_displacement_mm"] for r in rows])
        stress = np.mean([abs(r["pred_global_max_vm_mpa"] / r["true_global_max_vm_mpa"] - 1) for r in rows]) * 100
        error = np.mean(np.abs(predicted / truth - 1)) * 100
        print(f"{shape} | {len(rows)} | {error:.2f} | {stress:.2f} | {truth.min():.6g} - {truth.max():.6g}")
    print("Global target std:", metadata["normalisation"]["y_std"])
    measured = evaluation["max_displacement"]["mape"]
    print(f"Diagnostic threshold (not production acceptance): displacement MAPE {measured:.2f}% <= {args.max_displacement_mape}%")
    return 0 if measured <= args.max_displacement_mape else 1


if __name__ == "__main__":
    raise SystemExit(main())

"""Reselect existing scalar fits using validation only; preserve the original registry."""

import json
from pathlib import Path

from surrosim.ml.train import _comparison_markdown, _selection_key
from surrosim.provenance import sha256
from surrosim.serving.predictor import ScalarPredictor


def main():
    source = Path("models/scalar/v2_candidate/metadata.json")
    metadata = json.loads(source.read_text())
    if sha256(Path(metadata["dataset"])) != metadata["dataset_sha256"]:
        raise ValueError("Dataset hash differs from trained scalar candidate")
    for target, data in metadata["targets"].items():
        name, result = min(data["models"].items(), key=_selection_key)
        data["best_model"] = name
        metadata["best_models"][target] = name
        data["selection_rule"] = (
            "validation worst-case error <= 100% preferred, then lowest validation RMSE; "
            "test and challenge are not used for selection"
        )
        print(target, name, "test MAPE", result["test"]["mape_pct"], flush=True)
        for shape, scores in result["test"].get("by_shape", {}).items():
            print(" ", shape, "MAPE", round(scores["mape_pct"], 2), flush=True)
    metadata["selection_review"] = {
        "source": str(source), "source_sha256": sha256(source),
        "selection_split": "val", "refit": False,
    }
    out = Path("models/scalar/v2_reviewed_candidate")
    out.mkdir(parents=True, exist_ok=True)
    (out / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
    ScalarPredictor(out)
    report = _comparison_markdown(metadata)
    Path("reports/v2.0_scalar_reviewed_candidate.md").write_text(report, encoding="utf-8")
    (out / "report.md").write_text(report, encoding="utf-8")


if __name__ == "__main__":
    main()

"""Case preparation and solver execution for the v0.2 FEA engine."""

from pathlib import Path
import json

from ..geometry import generate_plate
from ..plate import Plate
from .calculix import build_calculix_deck
from .results import parse_and_summarize
from .runner import CalculixRunner


def _write_summary(output: Path, summary: dict) -> None:
    (output / "run.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")


def prepare_case(plate: Plate, output_dir: str | Path) -> dict:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    geometry = generate_plate(plate, output)
    deck = build_calculix_deck(output / "mesh.msh", plate, output / "model.inp")
    summary = {
        "schema_version": "0.2",
        "status": "PREPARED",
        "geometry": geometry,
        "deck": {
            "path": deck.path.name,
            "nodes": deck.nodes,
            "volume_elements": deck.volume_elements,
            "fixed_nodes": deck.fixed_nodes,
            "load_nodes": deck.load_nodes,
            "total_applied_force_n": deck.total_applied_force_n,
        },
        "solver": None,
        "results": None,
    }
    _write_summary(output, summary)
    return summary


def simulate_case(
    plate: Plate,
    output_dir: str | Path,
    ccx_executable: str = "ccx",
    timeout_seconds: float = 300.0,
) -> dict:
    output = Path(output_dir)
    summary = prepare_case(plate, output)
    run = CalculixRunner(ccx_executable).run(output / "model.inp", timeout_seconds)
    summary["status"] = run.status
    summary["solver"] = run.as_dict()
    if run.success:
        try:
            results = parse_and_summarize(
                output / "model.frd", output / "mesh.msh", plate,
                fields_csv=output / "fields.csv",
            )
        except (OSError, ValueError) as exc:
            summary["status"] = "RESULT_PARSE_FAILED"
            summary["results"] = None
            summary["result_error"] = str(exc)
        else:
            summary["results"] = results
    else:
        summary["results"] = None
    _write_summary(output, summary)
    return summary

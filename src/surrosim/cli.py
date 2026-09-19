"""SurroSim command-line entry points."""

import argparse
import json

from .plate import Plate
from .sampling import export_designs


def _plate_args(parser: argparse.ArgumentParser) -> None:
    defaults = Plate()
    for key in defaults.as_dict():
        parser.add_argument("--" + key.replace("_", "-"), type=float,
                            default=getattr(defaults, key))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="SurroSim v0.1 starter")
    sub = parser.add_subparsers(dest="command", required=True)
    baseline = sub.add_parser("baseline", help="Beam-theory check (NOT FEA)")
    _plate_args(baseline)
    generate = sub.add_parser("generate", help="Generate STEP and FE mesh using Gmsh")
    _plate_args(generate)
    generate.add_argument("--out", default="outputs/plate_0001")
    sample = sub.add_parser("sample", help="Write a reproducible design CSV (inputs only)")
    sample.add_argument("--count", type=int, default=300)
    sample.add_argument("--seed", type=int, default=42)
    sample.add_argument("--out", default="data/designs.csv")
    args = parser.parse_args(argv)
    try:
        if args.command == "sample":
            n = export_designs(args.out, args.count, args.seed)
            print(f"Wrote {n} candidate designs to {args.out} (no FEA labels)")
            return 0
        values = {key: getattr(args, key) for key in Plate().__dict__}
        plate = Plate(**values)
        if args.command == "baseline":
            result = plate.nominal_baseline()
            print(json.dumps({"geometry": plate.as_dict(),
                              "nominal_beam_baseline_not_fea": result}, indent=2))
        else:
            from .geometry import generate_plate
            result = generate_plate(plate, args.out)
            print(json.dumps({"output_dir": args.out, **result}, indent=2))
        return 0
    except (ValueError, RuntimeError) as exc:
        parser.error(str(exc))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

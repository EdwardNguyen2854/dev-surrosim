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


def _plate_from_args(args: argparse.Namespace) -> Plate:
    return Plate(**{key: getattr(args, key) for key in Plate().__dict__})


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="SurroSim engineering surrogate pipeline")
    sub = parser.add_subparsers(dest="command", required=True)

    baseline = sub.add_parser("baseline", help="Beam-theory check (NOT FEA)")
    _plate_args(baseline)

    generate = sub.add_parser("generate", help="Generate STEP and FE mesh using Gmsh")
    _plate_args(generate)
    generate.add_argument("--out", default="outputs/plate_0001")

    prepare = sub.add_parser("prepare", help="Generate mesh and CalculiX model.inp")
    _plate_args(prepare)
    prepare.add_argument("--out", default="outputs/plate_0001")

    simulate = sub.add_parser("simulate", help="Prepare and run a CalculiX case")
    _plate_args(simulate)
    simulate.add_argument("--out", default="outputs/plate_0001")
    simulate.add_argument("--ccx", default="ccx", help="Path/name of CalculiX executable")
    simulate.add_argument("--timeout", type=float, default=300.0)

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

        plate = _plate_from_args(args)
        if args.command == "baseline":
            result = plate.nominal_baseline()
            payload = {"geometry": plate.as_dict(),
                       "nominal_beam_baseline_not_fea": result}
        elif args.command == "generate":
            from .geometry import generate_plate
            payload = {"output_dir": args.out, **generate_plate(plate, args.out)}
        elif args.command == "prepare":
            from .simulation.pipeline import prepare_case
            payload = prepare_case(plate, args.out)
        else:
            from .simulation.pipeline import simulate_case
            payload = simulate_case(plate, args.out, args.ccx, args.timeout)

        print(json.dumps(payload, indent=2))
        if args.command == "simulate" and payload["status"] != "SUCCESS":
            return 2
        return 0
    except (ValueError, RuntimeError) as exc:
        parser.error(str(exc))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

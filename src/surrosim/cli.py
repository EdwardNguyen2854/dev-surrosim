"""SurroSim command-line entry points."""

import argparse
import json

from . import shapes
from .plate import Plate
from .sampling import export_designs


def _plate_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--shape", choices=shapes.SHAPE_KINDS, default=shapes.PLATE,
        help="Geometry family (default: plate with hole)",
    )
    defaults = Plate()
    for key in defaults.as_dict():
        if key == "shape":
            continue
        parser.add_argument("--" + key.replace("_", "-"), type=float,
                            default=getattr(defaults, key))


def _plate_from_args(args: argparse.Namespace) -> Plate:
    return Plate(**{key: getattr(args, key) for key in Plate.field_names()})


def _mesh_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--element-order", type=int, choices=(1, 2), default=2,
        help="1 = C3D4 linear tetrahedra, 2 = C3D10 quadratic tetrahedra (default)",
    )
    parser.add_argument(
        "--hole-refinement-mm", type=float, default=0.0,
        help="Target element size on and near the hole surface (0 = uniform mesh)",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="SurroSim engineering surrogate pipeline")
    sub = parser.add_subparsers(dest="command", required=True)

    baseline = sub.add_parser("baseline", help="Beam-theory check (NOT FEA)")
    _plate_args(baseline)

    generate = sub.add_parser("generate", help="Generate STEP and FE mesh using Gmsh")
    _plate_args(generate)
    _mesh_args(generate)
    generate.add_argument("--out", default="outputs/plate_0001")

    prepare = sub.add_parser("prepare", help="Generate mesh and CalculiX model.inp")
    _plate_args(prepare)
    _mesh_args(prepare)
    prepare.add_argument("--out", default="outputs/plate_0001")

    simulate = sub.add_parser("simulate", help="Prepare and run a CalculiX case")
    _plate_args(simulate)
    _mesh_args(simulate)
    simulate.add_argument("--out", default="outputs/plate_0001")
    simulate.add_argument("--ccx", default="ccx", help="Path/name of CalculiX executable")
    simulate.add_argument("--timeout", type=float, default=300.0)

    sample = sub.add_parser("sample", help="Write a reproducible design CSV (inputs only)")
    sample.add_argument("--count", type=int, default=300)
    sample.add_argument("--seed", type=int, default=42)
    sample.add_argument("--out", default="data/designs.csv")

    dataset = sub.add_parser("dataset", help="Batch FEA dataset factory")
    dataset_sub = dataset.add_subparsers(dest="dataset_command", required=True)
    dataset_sample = dataset_sub.add_parser(
        "sample", help="Write the reproducible design table (v2, multi-shape)"
    )
    dataset_sample.add_argument("--count", type=int, default=560)
    dataset_sample.add_argument("--challenge-count", type=int, default=72)
    dataset_sample.add_argument("--per-shape", type=int, default=380)
    dataset_sample.add_argument("--challenge-per-shape", type=int, default=48)
    dataset_sample.add_argument("--seed", type=int, default=42)
    dataset_sample.add_argument("--method", choices=("sobol", "lhs"), default="sobol")
    dataset_sample.add_argument("--no-hole-fraction", type=float, default=0.05)
    dataset_sample.add_argument(
        "--shapes", default="all",
        help="Comma-separated shape families, or 'all' (default)",
    )
    dataset_sample.add_argument(
        "--legacy", action="store_true",
        help="Write the v1 plate-only table instead",
    )
    dataset_sample.add_argument("--out", default="data/designs_v2.csv")
    dataset_run = dataset_sub.add_parser(
        "run", help="Run all design cases in parallel with CalculiX"
    )
    dataset_run.add_argument("--designs", default="data/designs_v2.csv")
    dataset_run.add_argument("--out", default="data/runs_v2")
    dataset_run.add_argument("--ccx", default="ccx")
    dataset_run.add_argument("--jobs", type=int, default=4)
    dataset_run.add_argument("--timeout", type=float, default=600.0)
    dataset_run.add_argument("--limit", type=int, default=None)
    dataset_run.add_argument("--force", action="store_true")
    dataset_run.add_argument("--retries", type=int, default=1)
    dataset_run.add_argument(
        "--mesh-profile", choices=("production", "graph"), default="production",
    )
    dataset_build = dataset_sub.add_parser(
        "build", help="Gate completed runs and assemble the dataset"
    )
    dataset_build.add_argument("--designs", default="data/designs_v2.csv")
    dataset_build.add_argument("--runs", default="data/runs_v2")
    dataset_build.add_argument(
        "--base", action="append", default=[],
        help="Earlier dataset CSV to merge (repeatable); v1 plate labels are "
        "reused this way",
    )
    dataset_build.add_argument("--out", default="data/dataset_v2")

    train = sub.add_parser("train", help="Train surrogate models on a dataset")
    train_sub = train.add_subparsers(dest="train_command", required=True)
    train_scalar = train_sub.add_parser(
        "scalar", help="Train and compare scalar regressors"
    )
    train_scalar.add_argument("--dataset", default="data/dataset_v2/dataset.csv")
    train_scalar.add_argument("--out", default="models/scalar/v2")
    train_scalar.add_argument("--seed", type=int, default=42)
    train_scalar.add_argument(
        "--models",
        default="ridge,random_forest,xgboost,mlp,gaussian_process,ensemble",
    )
    train_scalar.add_argument("--report", default="reports/v2.0_scalar_comparison.md")
    train_scalar.add_argument("--figures", default="reports/figures/v2.0")
    train_gnn = train_sub.add_parser(
        "gnn", help="Train and compare mesh-graph field models"
    )
    train_gnn.add_argument("--graphs", default="data/graphs_v2")
    train_gnn.add_argument("--runs", default="data/runs_v2_graph")
    train_gnn.add_argument("--out", default="models/gnn/v2")
    train_gnn.add_argument("--report", default="reports/v2.0_gnn_field_prediction.md")
    train_gnn.add_argument("--figures", default="reports/figures/v2.0")
    train_gnn.add_argument("--epochs", type=int, default=60)
    train_gnn.add_argument("--patience", type=int, default=12)
    train_gnn.add_argument("--hidden", type=int, default=80)
    train_gnn.add_argument("--layers", type=int, default=8)
    train_gnn.add_argument("--models", default="node_mlp,meshgraphnet")
    train_gnn.add_argument("--max-graphs", type=int, default=None)
    train_gnn.add_argument("--target-scaling", choices=("none", "nominal_v1"), default="none")
    train_gnn.add_argument("--validation-only", action="store_true")

    graph = sub.add_parser("graph", help="Mesh-graph dataset for field learning")
    graph_sub = graph.add_subparsers(dest="graph_command", required=True)
    graph_export = graph_sub.add_parser(
        "export", help="Export FEA cases as mesh graphs"
    )
    graph_export.add_argument("--designs", default="data/designs_v2.csv")
    graph_export.add_argument("--runs", default="data/runs_v2_graph")
    graph_export.add_argument("--out", default="data/graphs_v2")

    optimize = sub.add_parser(
        "optimize", help="Surrogate-based constrained mass minimization"
    )
    optimize.add_argument(
        "--shape", choices=shapes.SHAPE_KINDS, default=shapes.PLATE,
    )
    optimize.add_argument("--length-mm", type=float, default=120.0)
    optimize.add_argument("--force-n", type=float, default=500.0)
    optimize.add_argument("--sigma-allow-mpa", type=float, default=180.0)
    optimize.add_argument("--displacement-limit-mm", type=float, default=1.5)
    optimize.add_argument("--top-k", type=int, default=5)
    optimize.add_argument("--seed", type=int, default=42)
    optimize.add_argument("--maxiter", type=int, default=60)
    optimize.add_argument("--no-verify", action="store_true")
    optimize.add_argument("--ccx", default=None)
    optimize.add_argument("--out", default="outputs/optimization")
    optimize.add_argument("--report", default="reports/v1.0_optimization.md")
    optimize.add_argument("--figures", default="reports/figures/v1.0")

    reproduce = sub.add_parser(
        "reproduce", help="Run the end-to-end pipeline in one command"
    )
    reproduce.add_argument("--profile", choices=("quick", "full"), default="quick")
    reproduce.add_argument("--ccx", default="ccx")
    reproduce.add_argument("--jobs", type=int, default=4)
    reproduce.add_argument("--seed", type=int, default=42)
    reproduce.add_argument("--root", default=None)

    validate = sub.add_parser("validate", help="Independent FEA validation studies")
    validate_sub = validate.add_subparsers(dest="study", required=True)
    beam = validate_sub.add_parser("beam", help="Cantilever vs Euler-Bernoulli theory")
    beam.add_argument("--out", default="outputs/validation")
    beam.add_argument("--ccx", default="ccx")
    beam.add_argument("--mesh-sizes", default="4,3,2,1.5")
    beam.add_argument("--element-orders", default="1,2")
    beam.add_argument("--timeout", type=float, default=300.0)
    mesh = validate_sub.add_parser(
        "mesh", help="Perforated geometry mesh-convergence study"
    )
    mesh.add_argument("--out", default="outputs/validation")
    mesh.add_argument("--ccx", default="ccx")
    mesh.add_argument("--mesh-sizes", default="4,3,2,1.5")
    mesh.add_argument("--element-order", type=int, choices=(1, 2), default=2)
    mesh.add_argument("--hole-refinement-mm", type=float, default=0.0)
    mesh.add_argument("--timeout", type=float, default=300.0)

    serve = sub.add_parser(
        "serve", help="Run the API and engineering app (uvicorn)"
    )
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8003)
    serve.add_argument("--registry", default=None, help="Scalar model registry directory")
    serve.add_argument("--field-model", default=None, help="Field model directory")
    serve.add_argument(
        "--reload", action="store_true", help="Auto-reload on code changes (development)"
    )

    args = parser.parse_args(argv)
    try:
        if args.command == "serve":
            import os
            import uvicorn

            if args.registry:
                os.environ["SURROSIM_SCALAR_REGISTRY"] = args.registry
            if args.field_model:
                os.environ["SURROSIM_FIELD_MODEL"] = args.field_model

            uvicorn.run(
                "surrosim.serving.api:create_app",
                factory=True,
                host=args.host,
                port=args.port,
                reload=args.reload,
            )
            return 0

        if args.command == "sample":
            n = export_designs(args.out, args.count, args.seed)
            print(f"Wrote {n} candidate designs to {args.out} (no FEA labels)")
            return 0

        if args.command == "dataset":
            from .dataset import build_dataset, run_batch
            if args.dataset_command == "sample":
                if args.legacy:
                    n = export_designs(
                        args.out, count=args.count, seed=args.seed,
                        challenge_count=args.challenge_count, method=args.method,
                        no_hole_fraction=args.no_hole_fraction,
                    )
                else:
                    from .sampling import export_designs_v2
                    kinds = (
                        None
                        if args.shapes == "all"
                        else tuple(
                            name.strip()
                            for name in args.shapes.split(",")
                            if name.strip()
                        )
                    )
                    n = export_designs_v2(
                        args.out, seed=args.seed, per_shape=args.per_shape,
                        challenge_per_shape=args.challenge_per_shape,
                        plate_count=args.count, plate_challenge=args.challenge_count,
                        method=args.method, no_hole_fraction=args.no_hole_fraction,
                        shapes_to_sample=kinds,
                    )
                print(f"Wrote {n} design rows to {args.out} (inputs only)")
                return 0
            if args.dataset_command == "run":
                from .mesh_policy import get_policy
                summary = run_batch(
                    args.designs, args.out, args.ccx, args.jobs,
                    args.timeout, args.limit, args.force, args.retries,
                    policy=get_policy(args.mesh_profile),
                )
                print(json.dumps(
                    {key: summary[key] for key in (
                        "cases_requested", "status_counts", "wall_seconds",
                        "solver_seconds",
                    )},
                    indent=2,
                ))
                failed = sum(
                    count for status, count in summary["status_counts"].items()
                    if status not in ("SUCCESS", "CACHED")
                )
                return 2 if failed else 0
            manifest = build_dataset(
                args.designs, args.runs, args.out, base_datasets=args.base
            )
            print(json.dumps(
                {key: manifest[key] for key in (
                    "schema_version", "cases_in_dataset", "cases_failed",
                    "split_counts", "dataset_sha256",
                )},
                indent=2,
            ))
            return 0

        if args.command == "train":
            names = tuple(
                name.strip() for name in args.models.split(",") if name.strip()
            )
            if args.train_command == "scalar":
                from .ml.train import train_scalar_suite
                metadata = train_scalar_suite(
                    args.dataset, args.out, seed=args.seed, model_names=names,
                    report_path=args.report, figure_dir=args.figures,
                )
                summary = {
                    target: {
                        "best_model": metadata["targets"][target]["best_model"],
                        "test_mape_pct": metadata["targets"][target]["models"][
                            metadata["targets"][target]["best_model"]
                        ]["test"]["mape_pct"],
                    }
                    for target in metadata["targets"]
                }
            else:
                from .gnn.train import train_gnn
                metadata = train_gnn(
                    args.graphs, args.runs, args.out,
                    report_path=args.report, figure_dir=args.figures,
                    epochs=args.epochs, patience=args.patience,
                    hidden=args.hidden, layers=args.layers, models=names,
                    max_graphs_per_split=args.max_graphs,
                    target_scaling=args.target_scaling,
                    validation_only=args.validation_only,
                )
                summary = {
                    "best_model": metadata["best_model"],
                    "models": {
                        name: {
                            split: result["global_max_vm"]["mape"]
                            for split, result in data["evaluation"].items()
                        }
                        for name, data in metadata["models"].items()
                    },
                }
            print(json.dumps(summary, indent=2))
            return 0

        if args.command == "graph":
            from .gnn.export import export_graphs
            manifest = export_graphs(args.designs, args.runs, args.out)
            print(json.dumps(
                {key: manifest[key] for key in (
                    "schema_version", "graphs", "skipped", "split_counts",
                    "total_nodes", "total_edges", "mean_nodes",
                )},
                indent=2,
            ))
            return 0 if manifest["graphs"] else 2

        if args.command == "reproduce":
            from .reproduce import reproduce
            summary = reproduce(
                profile=args.profile, ccx_executable=args.ccx,
                jobs=args.jobs, seed=args.seed, root=args.root,
            )
            return 0 if summary["cases_failed"] == 0 else 2

        if args.command == "optimize":
            from .optimize import OptimizationProblem, optimize_design
            problem = OptimizationProblem(
                shape=args.shape,
                length_mm=args.length_mm,
                force_n=args.force_n,
                sigma_allow_mpa=args.sigma_allow_mpa,
                displacement_limit_mm=args.displacement_limit_mm,
            )
            metadata = optimize_design(
                problem=problem, seed=args.seed, maxiter=args.maxiter,
                top_k=args.top_k, verify=not args.no_verify,
                ccx_executable=args.ccx, out_dir=args.out,
                report_path=args.report, figure_dir=args.figures,
            )
            print(json.dumps(
                {
                    "evaluations": metadata["optimizer"]["evaluations"],
                    "seconds": round(metadata["optimizer"]["seconds"], 1),
                    "candidates": [
                        {
                            "mass_g": round(entry["mass_g"], 1),
                            "stress_mpa": round(entry["stress_mpa"], 1),
                            "displacement_mm": round(entry["displacement_mm"], 4),
                        }
                        for entry in metadata["candidates"]
                    ],
                    "verified": len(metadata.get("verification", [])),
                },
                indent=2,
            ))
            return 0

        if args.command == "validate":
            from .validation import beam_convergence, mesh_convergence
            sizes = tuple(float(value) for value in args.mesh_sizes.split(","))
            if args.study == "beam":
                orders = tuple(int(value) for value in args.element_orders.split(","))
                report = beam_convergence(
                    args.out, args.ccx, sizes, orders, timeout_seconds=args.timeout
                )
            else:
                report = mesh_convergence(
                    args.out, args.ccx, sizes, args.element_order,
                    hole_refinement_mm=args.hole_refinement_mm,
                    timeout_seconds=args.timeout,
                )
            print(json.dumps(report, indent=2))
            failed = [row for row in report["cases"] if row["status"] != "SUCCESS"]
            return 2 if failed else 0

        plate = _plate_from_args(args)
        if args.command == "baseline":
            result = plate.nominal_baseline()
            payload = {"geometry": plate.as_dict(),
                       "nominal_beam_baseline_not_fea": result}
        elif args.command == "generate":
            from .geometry import generate_plate
            payload = {"output_dir": args.out,
                       **generate_plate(plate, args.out,
                                        element_order=args.element_order,
                                        hole_refinement_mm=args.hole_refinement_mm)}
        elif args.command == "prepare":
            from .simulation.pipeline import prepare_case
            payload = prepare_case(plate, args.out, element_order=args.element_order,
                                   hole_refinement_mm=args.hole_refinement_mm)
        else:
            from .simulation.pipeline import simulate_case
            payload = simulate_case(plate, args.out, args.ccx, args.timeout,
                                    element_order=args.element_order,
                                    hole_refinement_mm=args.hole_refinement_mm)

        print(json.dumps(payload, indent=2))
        if args.command == "simulate" and payload["status"] != "SUCCESS":
            return 2
        return 0
    except (ValueError, RuntimeError) as exc:
        parser.error(str(exc))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

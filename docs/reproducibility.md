# Reproducibility

## Environment

- Python 3.11+ (developed on 3.12.10, Windows 11).
- Gmsh 4.15.2 via `pip install -e '.[mesh]'`.
- CalculiX 2.23 (`ccx_static.exe` from the official Windows distribution)
  placed at `tools/calculix/ccx.exe` or anywhere on PATH.
- Hardware used for the committed artifacts: Intel i5-12400F (6 cores),
  NVIDIA RTX 3050 4 GB, 612 GB free disk.

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -e '.[dev,mesh,ml,app,gnn]'
```

## One-command reproduction

```bash
# CI-sized end-to-end run (minutes): 32 cases, real ccx, small surrogate
python -m surrosim reproduce --profile quick --jobs 4 --ccx tools/calculix/ccx.exe

# Full v1.0 pipeline (hours): 644-case datasets, scalar suite, GNN training
python -m surrosim reproduce --profile full --jobs 6 --ccx tools/calculix/ccx.exe
```

Both write `reproduction_summary.json` with the dataset hash and selected
models. The full pipeline regenerates the same artifacts (up to solver
non-determinism at the last digit) as the committed ones.

## Stage-by-stage

| Artifact | Command | Committed reference | Notes |
| --- | --- | --- | --- |
| Beam validation | `surrosim validate beam --ccx ccx` | `reports/validation/beam/` | ~2.5 min |
| Mesh convergence | `surrosim validate mesh --ccx ccx --hole-refinement-mm 1.2` | `reports/validation/mesh_refined/` | ~1 min |
| Design table | `surrosim dataset sample --count 560 --challenge-count 72` | `data/designs_v1.csv` | seed 42, Sobol |
| Production dataset | `surrosim dataset run --mesh-profile production` then `dataset build` | `data/dataset_v1/` | ~24 min on 6 jobs |
| Scalar suite | `surrosim train scalar` | `models/scalar/v1/`, `reports/v0.4_scalar_comparison.md` | ~3 min |
| Graph dataset | `surrosim dataset run --mesh-profile graph` + `graph export` | `data/graphs_v1/` | ~10 min + ~2 min |
| Field model | `surrosim train gnn --epochs 150 --patience 30` | `models/gnn/v1/`, `reports/v0.6_gnn_field_prediction.md` | ~25 min on RTX 3050 |
| Optimization | `surrosim optimize --ccx ccx` | `reports/v1.0_optimization.md` | ~4 min incl. FEA verification |

## Determinism

- Sampling, dataset splits, model seeds and optimizer seeds are explicit
  (`--seed`, default 42); Sobol/LHS draws are seeded.
- `metadata.json`/`manifest.json` record git commit and dirty flag, dataset
  SHA-256, tool versions and configuration; every model artifact points back
  to its dataset hash.
- CalculiX is deterministic for these linear static cases; transient
  Windows crash-on-launch under parallel load (~3% of runs) is retried
  automatically and would appear in `failures.csv` if it persisted.
- Torch training uses seeded RNGs; exact bitwise reproducibility of GPU
  kernels is not guaranteed across hardware/driver versions.

## Data footprint

| Path | Size | Committed |
| --- | --- | --- |
| `data/designs_v1.csv` | ~90 KB | yes |
| `data/dataset_v1/` (scalars, manifest, card) | ~1 MB | yes |
| `data/runs/` (644 cases: mesh, deck, fields.npz) | ~4.7 GB | no (regenerable) |
| `data/runs_graph/` (coarse cases) | ~1.3 GB | no |
| `data/graphs_v1/` (644 graphs) | ~700 MB | no |
| `models/scalar/v1/` (ensemble only committed) | ~8 MB | partial |
| `models/gnn/v1/` | ~2 MB | yes |
| `reports/` | ~2 MB | yes |

## Containers

`docker compose -f docker/docker-compose.yml up --build` starts the app and
API. CPU-only torch keeps the image small; CalculiX is not bundled, so the
FEA Verify page disables itself with a clear message inside containers.

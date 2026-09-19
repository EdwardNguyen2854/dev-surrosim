# SurroSim

**SurroSim** is a personal engineering-ML project for building and validating surrogate models for structural FEA. The first target is a parametric cantilever plate with a through-hole.

> **Current status: v0.1 / M1 starter.** Parameterized geometry/mesh generation, nominal analytical reference, and reproducible design sampling are implemented in the starter. FEA, labeled datasets, trained ML models, and the interactive app are **not implemented yet**. Analytical outputs are NOT FEA results.

## Quick start (Python 3.11+)

```bash
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
python -m pip install -e '.[dev,mesh]'
python -m pytest -q
python -m surrosim baseline
python -m surrosim generate --out outputs/plate_0001
python -m surrosim sample --count 300 --seed 42 --out data/designs.csv
```

Install only `.[dev]` to run the baseline and tests without Gmsh. The `generate` command exports `geometry.step`, `mesh.msh` (MSH 2.2), and `metadata.json` with `fea_status: not_run`; `sample` exports candidate inputs only.

## v0.1 milestones

1. **M1:** parametric STEP/mesh, nominal beam reference, design sampler, tests.
2. **M2:** validated CalculiX execution, boundary conditions, mesh convergence.
3. **M3:** automatic FEA-label extraction and solver provenance.
4. **M4:** geometry-disjoint train/test evaluation with XGBoost and PyTorch MLP.
5. **M5:** measured errors, OOD limits, and inference/FEA benchmark.
6. **M6:** interactive demo.

See [engineering scope](docs/engineering_scope.md) for coordinate conventions, units, and limitations. Predictions require independent engineering verification before any safety-relevant use.

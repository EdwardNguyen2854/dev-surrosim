# SurroSim

**SurroSim** is an engineering-ML portfolio project for building and validating surrogate models for structural FEA. The first geometry family is a parametric cantilever plate with a through-hole.

> **Development status: v0.2 FEA engine.** The repository now contains the geometry/data foundation plus a CalculiX deck generator, solver runner and FRD result parser. The solver path still needs end-to-end verification with real Gmsh + CalculiX before v0.2 is tagged. No ML model has been trained yet.

## Quick start (Python 3.11+)

```bash
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
python -m pip install -e '.[dev,mesh]'
python -m pytest -q
```

Generate a geometry and mesh:

```bash
surrosim generate --out outputs/plate_0001
```

Prepare a CalculiX input deck:

```bash
surrosim prepare --out outputs/plate_0001
```

Run the complete current FEA pipeline:

```bash
surrosim simulate --out outputs/plate_0001 --ccx ccx
```

The requested `force_n` is treated as a **total** transverse force. SurroSim distributes it to the loaded end nodes using surface-triangle area weights, so a finer surface mesh does not accidentally multiply the load.

A successful solver run produces `run.json` and `fields.csv` in addition to the geometry, mesh, input deck and CalculiX files. `fields.csv` preserves nodal displacement and stress tensors for later field-surrogate/GNN experiments.

## Release path

1. **v0.1:** parametric geometry, nominal analytical reference, reproducible design sampling.
2. **v0.2:** validated CalculiX FEA engine, result extraction and mesh-convergence evidence.
3. **v0.3:** batch simulation dataset factory with failure filtering and provenance.
4. **v0.4:** scalar surrogate models (analytical baseline vs XGBoost vs PyTorch MLP).
5. **v0.5+:** field surrogate / geometric deep learning and interactive engineering demo.

See [v0.2 FEA engine status](docs/v0.2_fea_engine.md) and [engineering scope](docs/engineering_scope.md). Predictions and simulation results require independent engineering verification before safety-relevant use.

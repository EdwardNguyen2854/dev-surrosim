# AGENTS.md

SurroSim builds trustworthy surrogate models for structural finite-element
analysis (FEA): simulation automation → gated dataset → scalar and field
models → FastAPI service and React app. Python 3.11+ package in
`src/surrosim`, React + TypeScript single-page app in `apps/web`, Electron
shell in `apps/desktop`. Development happens on Windows; CI runs on Linux.

## Talking to the owner

The owner is not from a software background and learns how the system works by
reading agent sessions. Explain what you changed and why in plain language,
expand an acronym the first time you use it, and avoid unexplained jargon.
Keep the real depth — simple words, not a shallow summary.

## Commands

All Python commands use the repo virtual environment.

```powershell
# Setup (Windows PowerShell)
python -m venv .venv
.venv\Scripts\python.exe -m pip install -e ".[dev,mesh,ml,app,gnn]"

# Fast tests (84 of 85); the solver test needs Gmsh + CalculiX and skips
# itself when missing. This is the CI fast lane.
.venv\Scripts\python.exe -m pytest -q -m "not solver"

# One test by name
.venv\Scripts\python.exe -m pytest tests/test_dataset.py::test_build_dataset_gates_and_reports

# Real-solver test and end-to-end check (~4 min, bundled CalculiX)
.venv\Scripts\python.exe -m pytest -q -m "solver"
.venv\Scripts\python.exe -m surrosim reproduce --profile quick --jobs 4 --ccx tools/calculix/ccx.exe

# API + built app on http://localhost:8003
.venv\Scripts\python.exe -m surrosim serve --registry models/scalar/v2_reviewed_candidate --field-model models/gnn/v2_normalized_candidate

# Web app: typecheck + production build; Vite dev server proxies /api to :8003
cd apps/web
npm ci
npm run build   # runs tsc --noEmit, then vite build
npm run dev     # dev server on :5173
```

CI (`.github/workflows/ci.yml`) has three jobs: Python unit tests
(`-m "not solver"`), the solver test plus the quick reproduction, and the web
build. There is no Python linter/formatter config, and no frontend test runner
or ESLint; `npm run build` is the web check.

## Gotchas

- `surrosim serve` defaults to the registries `models/scalar/v2` and
  `models/gnn/v2`, which do not exist yet in this checkout — it exits with
  "No model registry metadata". Pass the candidates shown above, or the v1
  registries. The desktop shell resolves those candidates itself.
- CalculiX is bundled for Windows at `tools/calculix/ccx.exe`; the API checks
  `SURROSIM_CCX`, then PATH, then that file. Docker does not bundle it, so the
  FEA verification page is disabled there.
- `dataset run` is resumable and writes `data/runs_*`; never point two writers
  at the same output directory. `tools/run_v2.py` holds an OS-level lock — do
  not run it beside independent `dataset run` commands, and keep it importable
  (tests load it by path).
- Failed simulations never enter a dataset (six label gates); dataset and model
  artifacts record the SHA-256 of their inputs and the git commit. Changing or
  retraining a dataset invalidates the registries' hash check.
- Generated and gitignored: `data/runs_*`, `data/graphs_*`, `outputs/`,
  `apps/web/dist`, `node_modules`. Committed: `data/dataset_v1/`,
  `data/designs_v1.csv`, `data/designs_v2.csv`, v1 model registries, reports.

## Architecture

Data flows `sampling` → `geometry` (Gmsh) → `simulation` (CalculiX deck/FRD)
→ `dataset` gating → `ml` / `gnn` training → `serving` (predictor + FastAPI
background jobs) → `apps/`. `surrosim.shapes` is the single source of truth for
the six shape families (parameters, boundary conditions, load direction,
region of interest, mass); adding a shape touches shapes → sampling → geometry
→ mesh_policy → serving and the UI. The CLI's `baseline`, `generate`,
`prepare` and `simulate` commands are legacy single-case plate tools, separate
from the v2 `dataset`/`train`/`graph`/`optimize`/`reproduce` pipeline.

- The FastAPI service serves the built SPA from `apps/web/dist`; build the web
  app before reviewing it through the API.
- `apps/desktop` is an Electron window that spawns `python -m surrosim serve`
  and picks the model registry automatically; see `apps/desktop/README.md`.
- Web UI work follows `apps/web/DESIGN.md`: `src/tokens.css` holds the design
  values, components use Tailwind role names (never raw hex), and icons come
  from the vendored sprite via `Icon.tsx` (lucide was removed).
- Environment overrides: `SURROSIM_CCX`, `SURROSIM_SCALAR_REGISTRY`,
  `SURROSIM_FIELD_MODEL`, `SURROSIM_DEVICE` (`cpu`/`cuda`),
  `SURROSIM_JOB_WORKERS`, `SURROSIM_CORS_ORIGINS`,
  `SURROSIM_HIGH_ORDER_OPTIMIZE`.

## Where to read more

`docs/architecture.md` (module map, provenance chain) ·
`docs/reproducibility.md` (environment, stage-by-stage commands) ·
`docs/v2_pipeline_operations.md` (resumable multi-shape run, monitoring) ·
`docs/validation_report.md` (measured accuracy and limits) ·
`apps/desktop/README.md` (desktop env vars, registry resolution).

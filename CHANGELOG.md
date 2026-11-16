# Changelog

All notable changes to SurroSim, one entry per released version.

The public release history begins at **v0.1.0**. Everything before that was
developed in a private repository under its own milestone numbers; those
milestones are kept under
[Pre-publication development](#pre-publication-development) for context and
are not public releases. Some documents written before publication still refer
to those internal numbers (for example `reports/v1.0_optimization.md`, the
`reports/figures/v1.0/` directory, and the title of
`docs/validation_report.md`).

## v0.1.0 — 2026-11-16

First public release. A complete, reproducible pipeline from parametric design
to served prediction, with the evidence needed to judge each number.

### Simulation and dataset platform

- Six parametric cantilever families in a single shape registry
  (`surrosim.shapes`): plate with hole, two-hole plate, tapered plate, stepped
  plate, I-beam, and L-bracket. Each family defines its parameters, boundary
  conditions, load direction, stress-riser region of interest, and mass.
- Verified CalculiX static pipeline: Gmsh OCC geometry and meshing, MSH 2.2
  parsing, deck generation, process runner with machine-readable statuses, and
  FRD result parsing. Quadratic C3D10 elements with correct Gmsh-to-CalculiX
  node ordering.
- Per-shape mesh policy, hole- and fillet-graded meshing, high-order Gmsh
  optimisation, and `mesh_min_sicn` mesh-quality provenance.
- Parallel, resumable batch execution with automatic retries, pool restart, and
  residual-case reporting.
- Sobol/LHS design sampling with challenge corners, edge cases, and
  deterministic splits. Six-gate label validation: failed simulations never
  enter a dataset and are written to `failures.csv`.
- Dataset schema 2.0.0 with base-dataset merging, so committed v1 plate labels
  are reused instead of re-solved. Committed artifacts: a 644-case v1 plate
  dataset and a 2,809-case six-shape dataset, both with zero failed cases,
  manifest, and dataset card recording exact force balance, mesh policy,
  quality, runtime, input SHA-256, and build commit.
- `surrosim reproduce --profile quick|full` runs the pipeline end to end; the
  quick profile is CI-sized.

### Models

- Scalar surrogate suite: ridge, random forest, XGBoost, MLP, Gaussian process,
  and a GP+MLP ensemble on log targets, with a selection rule that balances
  validation error and extrapolation blow-ups.
  - Single-shape evidence: 1.74-2.30% test MAPE, ~10 us inference against a
    ~10 s finite-element solve.
  - Six-shape candidates (reviewed, not yet released as validated):
    1.27% displacement, 2.29% global peak stress, 2.01% stress-riser MAPE on
    the test split.
- MeshGraphNet field surrogate over physics-aware mesh graphs.
  - Single-shape evidence: 2.63% test global peak-stress error, 0.80% median
    nodal field error, roughly 4x better than a coordinate-MLP baseline.
  - Six-shape normalised candidate: 3.24% test and 5.04% challenge
    global peak-stress MAPE, 0.79% median nodal error.
- Model selection never uses test or challenge data. Reports record the
  selection rule and the dataset SHA-256 they were trained on, so a candidate
  cannot silently borrow validity from a split it was chosen on.
- Model registries carry feature lists, design-space bounds, ensemble
  membership, and provenance; older registries stay loadable.

### Serving and application

- `ScalarPredictor` with design-space bounds, distance-based
  out-of-distribution score, ensemble disagreement, and a trust/caution/run-FEA
  recommendation.
- FastAPI service with background jobs: FEA verification, field prediction, and
  constrained optimisation stream stage, progress, and logs without blocking
  the interface. The service also serves the built single-page app.
- React + TypeScript engineering app (Vite, Tailwind): Design Explorer with
  live per-shape schematic, confidence and OOD panel; 3D Field Prediction; FEA
  Verify with a real CalculiX round trip; Optimization with candidate
  verification; Model and Dataset evidence pages; a Solver page explaining the
  finite-element engine step by step; and a multi-page plain-language manual.
- Light and Black themes, collapsible sidebar, saved preferences, visible
  keyboard focus, and reduced-motion support, all defined through a semantic
  token layer (`apps/web/src/tokens.css`).
- Electron desktop shell for Windows: one-click launcher that builds what is
  missing, starts the local service, and runs fully offline.
- Docker packaging (app and API on one port, CPU-only PyTorch). CalculiX is not
  bundled in the image, so FEA verification is disabled there.

### Licensing, packaging, and community

- Released under the **Apache License 2.0**, with a `NOTICE` file carrying the
  attribution notices the license requires, and a `CITATION.cff` for academic
  citation. Earlier private builds declared MIT in `pyproject.toml` but shipped
  no license file; that is superseded by this release.
- Package metadata completed: SPDX license expression and license files,
  author, keywords, classifiers, and project URLs. The web and desktop packages
  declare the same license.
- Project files: `CONTRIBUTING.md` (setup, evidence rules, Developer
  Certificate of Origin sign-off), `CODE_OF_CONDUCT.md`, `SECURITY.md`, two
  issue forms, an issue chooser, and a pull request template encoding the
  provenance rules.
- Repository hygiene: `.gitattributes` (LF normalisation, binary markers,
  generated lockfiles kept out of diffs), `.editorconfig`, and a `.gitignore`
  that ignores only the bundled GPL CalculiX build under `tools/` rather than
  every file in `tools/`.
- Documentation: `docs/README.md` index, a README with a verified `serve`
  command, separate tables for validated and candidate results, reuse and
  attribution rules, and citation guidance.

### Known limitations at this release

- Linear elasticity only, one load case per family, closed design space, no
  experimental correlation, and heuristic confidence signals.
- The six-shape scalar and field registries ship as reviewed **candidates**.
  Treat their metrics as provisional until per-shape review is published.
- Predictions require independent engineering verification before any
  safety-relevant use. See
  [limitations and out of scope](docs/limitations_and_out_of_scope.md).

### Publication note

The repository was re-initialised for this release, so git commit identifiers
recorded inside pre-publication dataset and model metadata refer to a private
history that is no longer reachable. Content identity is still pinned by the
SHA-256 hashes recorded alongside them; those hashes were not altered.

## Pre-publication development

Development milestones from the private repository, kept for context. These are
not public releases.

### v1.1.0 — 2026-09-20

- React + TypeScript engineering app (`apps/web`, Vite + Tailwind) replacing
  the Streamlit prototype: parametric plate schematic, confidence/OOD panel,
  3D field viewer, optimization charts and report browser.
- FastAPI service rebuilt under `/api` with background jobs: FEA
  verification, MeshGraphNet field prediction and surrogate optimization
  stream stage/progress/logs and never block the UI.
- Meshing jobs run in spawned worker processes to satisfy Gmsh's
  main-thread SIGINT constraint and to isolate solver failures.
- New endpoints: `/api/config`, `/api/reports/model`,
  `/api/jobs/*`, `/api/fields/{id}`; the service serves the built SPA
  together with the API.
- `surrosim serve` CLI command; Docker image builds the frontend and serves
  app + API on one port; CI type-checks and builds the web app.

### v1.0.0 — 2026-09-20

- Design optimization: constrained mass minimization over the surrogate with
  FEA verification of the five best designs (all feasible; stress errors
  +0.4% to +2.3%).
- One-command reproduction (`surrosim reproduce --profile quick|full`).
- Consolidated documentation: architecture, validation report,
  reproducibility, limitations; README portfolio rewrite.
- Version bump to 1.0.0 across package metadata.

### v0.6.0 — 2026-09-20

- Coarse `graph` mesh profile and 644-case graph-field dataset.
- Mesh-graph export with physics-aware node/edge features and 9-component
  targets (displacement + stress tensor).
- MeshGraphNet field surrogate: 2.63% test / 9.14% challenge global
  peak-stress MAPE, ~4x better than a coordinate-MLP baseline; 0.80% median
  field error on test designs.
- Gmsh high-order optimisation and `mesh_min_sicn` mesh-quality provenance.
- Streamlit Field Prediction page (mesh + GNN inference in ~1.2 s).

### v0.5.0 — 2026-09-20

- `ScalarPredictor` with design-space bounds, distance-based OOD score,
  ensemble disagreement and trust/caution/run-fea recommendation.
- FastAPI inference service (`/predict`, `/model`, `/domain`, `/health`).
- Streamlit engineering app: Design Explorer, Model Report and FEA Verify
  (real CalculiX round trip with 3D field rendering).
- Docker packaging for app and API; serving tests including a headless
  Streamlit smoke test.

### v0.4.0 — 2026-09-20

- Scalar surrogate suite: ridge, random forest, XGBoost, MLP, Gaussian
  process and a GP+MLP ensemble, trained on log targets.
- Selection rule balancing validation error and extrapolation blow-ups;
  held-out challenge split kept out of fitting and selection.
- Ensemble selected for all targets: 1.74-2.30% test MAPE, challenge
  5.4-6.7%; ~10 us inference versus a 10 s FEA solve.
- Model registry, comparison report and parity figures.

### v0.3.0 — 2026-09-20

- Parallel, resumable batch FEA execution with automatic retries.
- Sobol/LHS design sampling with challenge and edge-case composition and
  deterministic splits.
- Six-gate label validation; failed cases go to `failures.csv`.
- Compact `fields.npz` per case; manifest and dataset card with full
  provenance.
- 644-case dataset v1: 644/644 gated, zero failures.

### v0.2.0 — 2026-09-20

- Verified CalculiX static pipeline: MSH 2.2 parsing, deck generation,
  process runner with machine-readable statuses, FRD parsing.
- Quadratic C3D10 elements with correct Gmsh-to-CalculiX node ordering and
  consistent load distribution for both element orders.
- Hole-graded meshing; `surrosim validate beam|mesh` studies.
- Beam validation (mid-span stress within 0.7% of theory; converged tip
  displacement -2.35% with documented clamp effect) and mesh-convergence
  evidence; CI runs real Gmsh + CalculiX integration tests.

### v0.1.0 — 2026-09-19

- Parametric cantilever plate with through-hole; Gmsh geometry and mesh.
- Euler-Bernoulli analytical reference; reproducible Latin-hypercube design
  sampling; project scaffolding, tests and CI.

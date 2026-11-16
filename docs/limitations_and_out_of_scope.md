# Limitations and out of scope

SurroSim is an engineering-surrogate research platform, not a certified CAE
product. The following limitations are deliberate and documented so no
claim exceeds the evidence in `docs/validation_report.md`.

## Physics and simulation

- **Linear elasticity, small strain only.** No plasticity, contact,
  buckling, dynamics, modal or thermal analysis.
- **Labels above yield are simulation outputs, not material behaviour.**
  Many dataset cases exceed 250 MPa; they are valid linear-elastic
  solutions and nothing more.
- **One load case family**: a single total force at the free end of the
  cantilever (transverse for the beam-like shapes, sideways for the
  L-bracket). No pressure loads, gravity, moments or multi-axial loading.
- **Fixed end is a fully clamped face**, which is measurably stiffer than an
  ideal beam clamp (documented ~2% tip-displacement effect).
- **Peak stress is a discretised nodal value.** The mesh policy bounds
  sampling sensitivity to ~0.15–0.4%, but no stress-averaging or
  extrapolation scheme is applied.
- **Re-entrant corners must be filleted.** The stepped, I-beam and
  L-bracket families include a fillet radius parameter; sharp variants are
  excluded because their peak stress does not converge under refinement.
- **Symmetry and single material**: isotropic steel with fixed E and ν in
  all trained models; the design space does not vary material.

## Data and models

- **Design space is closed per shape.** Predictions outside
  `data/designs_v2.csv` parameter ranges are unsupported; the app raises
  bound violations and recommends the solver.
- **OOD detection is heuristic** (distance in standardised feature space,
  ensemble disagreement). It is not a calibrated probability and cannot
  guarantee detection of unusual geometry inside the parameter box.
- **Field model resolution**: the GNN is trained on the coarse graph mesh
  profile; field accuracy at production mesh resolution is not claimed.
- **Challenge-split degradation is real**: worst-case relative errors at the
  corners of the design space are reported per shape in the training
  metadata, with individual cases worse than the pooled means.
- **No experimental validation.** Everything is verified against beam
  theory, mesh refinement and solver self-consistency.

## Application and operations

- The app/API are **local engineering demos**: no authentication, no rate
  limiting, no multi-user persistence. Do not expose publicly as-is.
- Predictions are not design approvals. `docs/` and the UI repeatedly
  recommend FEA verification; the platform provides it, but a qualified
  engineer remains responsible for conclusions.
- Model artifacts are versioned by dataset hash, not by a formal registry
  service; concurrent multi-user deployment is out of scope.

## Explicit non-goals (from VISION.md)

- A black-box replacement for validated CAE software.
- Hiding engineering assumptions or unsupported input ranges.
- An ML benchmark disconnected from engineering workflows.
- Optimising test-set loss rather than engineering trustworthiness.

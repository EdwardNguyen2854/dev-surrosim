# SurroSim validation report (v1.0)

This document consolidates the validation evidence for every claim the
project makes. Raw reports live in `reports/`.

## 1. FEA engine verification

Source: `reports/validation/beam/report.md`,
`reports/validation/mesh/report.md`, `reports/validation/mesh_refined/report.md`.

**Unperforated cantilever versus Euler-Bernoulli (L=120 mm, W=40 mm,
T=6 mm, F=500 N, steel).**

| element | mesh (mm) | tip displacement error | mid-span |SXX| error |
| --- | --- | --- | --- |
| C3D4 | 1.5 | -19.3% | -11.1% |
| C3D10 | 4.0 | -2.57% | +0.29% |
| C3D10 | 2.0 | -2.39% | +0.24% |
| C3D10 | 1.5 | -2.35% | +0.64% |

- Linear tetrahedra are unusable for bending at practical mesh sizes;
  production uses C3D10.
- The residual tip-displacement gap is the known stiffening of a fully
  clamped 3-D face and distributed end traction: the mesh-converged change
  between 2.0 mm and 1.5 mm is 0.03%, and the gap shrinks to -1.37% at
  L/T = 40 (stress error +0.08%).
- The stress field at mid-span — the station where the hole ROI is defined —
  matches beam theory to better than 0.7%.

**Perforated mesh convergence (d = 12 mm, ROI = 1.5d around the hole).**

| policy | 4.0 mm | 3.0 mm | 2.0 mm | 1.5 mm |
| --- | --- | --- | --- | --- |
| uniform ROI stress (MPa) | 259.1 | 265.9 | 269.3 | 267.0 (oscillating) |
| hole-graded 1.2 mm ROI stress | — | 269.8 | 270.5 | 270.8 (+0.14%) |

The graded hole surface removes the ±1% nodal-sampling oscillation of the
peak stress with a modest cost increase.

## 2. Dataset integrity (v1, 644 cases)

Source: `data/dataset_v1/manifest.json`, `dataset_card.md`.

- 644/644 cases passed every gate (solver success, exact force balance,
  mesh size, field presence, finite positive outputs); zero rows in
  `failures.csv`.
- 33 unperforated cases: FEA/beam-theory tip displacement ratio 0.968–0.989,
  consistent with the clamp-face effect quantified above.
- Split isolation: the 84 challenge cases (outer 10% band of every factor)
  were never used for fitting or model selection.

## 3. Scalar surrogate accuracy

Source: `reports/v0.4_scalar_comparison.md`, `docs/model_card_scalar.md`.

Selected model: GP + MLP ensemble (log-target, 12 features).

| target | test MAPE | test worst | challenge MAPE | challenge worst |
| --- | --- | --- | --- | --- |
| max displacement | 1.85% | 9.1% | 5.39% | 29.5% |
| global max Von Mises | 2.30% | 12.4% | 6.73% | 88.2% |
| ROI max Von Mises | 1.74% | 8.9% | 6.14% | 42.8% |

- Euler-Bernoulli baseline: 3.56% / 12.6% test MAPE — the learned ensemble
  is clearly better than classical closed-form estimates.
- XGBoost and random forest sit near 10% test MAPE; tree models underperform
  on this small, smooth regression.
- Median FEA solve time 10.05 s versus ~10 µs per surrogate evaluation
  (~10⁶× speed-up per evaluation).

## 4. Field prediction (MeshGraphNet)

Source: `reports/v0.6_gnn_field_prediction.md`, `docs/model_card_gnn.md`.

| model | split | global max VM MAPE | ROI max VM MAPE | field VM median error |
| --- | --- | --- | --- | --- |
| MeshGraphNet | test | 2.63% | 3.22% | 0.80% of peak |
| MeshGraphNet | challenge | 9.14% | 8.58% | 1.47% of peak |
| per-node MLP | test | 10.47% | 12.00% | 1.73% of peak |
| per-node MLP | challenge | 28.24% | 33.79% | 3.44% of peak |

Message passing roughly halves the error of an otherwise identical
coordinate-MLP pipeline on the challenge split, which is the evidence that
geometry-aware learning adds real value.

## 5. End-to-end engineering loop

Source: `reports/v1.0_optimization.md`.

Surrogate-driven mass minimization (σ < 180 MPa, δ < 1.5 mm) over 3,660
evaluations in 17 s, followed by FEA verification of the five best designs:

| candidate | mass | σ pred | σ FEA | error | δ FEA | FEA feasible |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 223.8 g | 179.9 | 178.0 | +0.92% | 1.0066 mm | yes |
| 2 | 223.9 g | 180.0 | 178.0 | +1.29% | 1.0057 mm | yes |
| 3 | 224.0 g | 179.9 | 177.0 | +1.57% | 1.0062 mm | yes |
| 4 | 224.0 g | 179.9 | 179.0 | +0.38% | 1.0060 mm | yes |
| 5 | 224.0 g | 179.8 | 176.0 | +2.34% | 1.0039 mm | yes |

All five finalists satisfy the constraints under the high-fidelity solver;
surrogate stress errors are +0.4% to +2.3% (conservative).

## 6. What is *not* validated

- No experimental (physical test) correlation: all validation is against
  theory and self-consistency (mesh refinement, solver cross-checks).
- Linear elasticity only; labels above yield are simulation outputs, not
  material behaviour.
- The GNN field model is validated on its coarse mesh profile only.
- Confidence/OOD signals are heuristic and not calibrated probabilities.

# Engineering scope

SurroSim approximates six parametric cantilever families under one load case:
a single total force applied at the free end, with the other end fully
clamped, in linear elasticity.

| shape | parameters | stress riser (ROI) |
| --- | --- | --- |
| `plate` | rectangular plate with an optional through-hole | hole cylinder |
| `multi_hole` | plate with two holes along the beam axis | both hole cylinders |
| `taper` | width tapers linearly from the clamp to the tip, optional hole | hole cylinder |
| `stepped` | thickness step, filleted at the re-entrant corner | step fillet |
| `i_beam` | parametric I-section, filleted web/flange junctions | web/flange fillets |
| `l_bracket` | L-shaped bracket loaded sideways at the top of the vertical leg | inner corner fillet |

## Units and conventions

- Units: mm, N, MPa (= N/mm²), grams for mass.
- Coordinate frame: fixed face at X=0, length along X. Width and thickness
  axes follow the shape (plate-like: width Y, thickness Z; I-beam: flange
  width Y, depth Z; L-bracket: width Y out of plane, height Z).
- Load direction is declared per shape by the registry: −Z for the beam-like
  families, −X for the L-bracket. The CalculiX deck distributes consistent
  nodal loads whose sum is exactly the requested total force.
- Material: isotropic linear elastic steel (E = 210 GPa, ν = 0.3,
  ρ = 7850 kg/m³) throughout the trained models.

## What the platform computes

- FEA: max displacement, global max Von Mises stress, stress-riser ROI max
  Von Mises stress plus full nodal displacement/stress fields.
- Surrogates: the three scalar targets (shape-conditioned ensemble) and full
  fields on the coarse mesh profile (MeshGraphNet).
- Optimization: mass minimization subject to stress and displacement
  limits, with high-fidelity verification of finalists.

## Where the assumptions stop

Full limitations live in
[limitations and out of scope](limitations_and_out_of_scope.md). In short:
linear elasticity only, closed design space per shape, no experimental
validation, and peak stresses are discretised nodal values. Re-entrant
fillets are resolved by the mesh policy because sharp corners produce
non-convergent stress peaks. Analytical beam formulas in the codebase are
references, never labels.

## Documentation map

- [Architecture](architecture.md) — components, data flow, provenance.
- [Validation report](validation_report.md) — every claim with evidence.
- [Reproducibility](reproducibility.md) — environment and commands.
- [FEA engine](v0.2_fea_engine.md), [dataset factory](v0.3_dataset.md),
  [app](v0.5_app.md), [field prediction](v0.6_gnn.md) — milestone detail.
- Model cards: [scalar](model_card_scalar.md), [GNN](model_card_gnn.md).

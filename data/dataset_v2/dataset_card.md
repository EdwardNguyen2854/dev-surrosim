# SurroSim simulation dataset card

- Schema version: `2.0.0`
- Created: 2026-09-21T00:16:19.298480+00:00
- Cases in dataset: **2809** (failed/excluded: 0)
- Splits: {'challenge': 349, 'train': 1722, 'val': 369, 'test': 369}
- Shapes: {'plate': 644, 'i_beam': 433, 'l_bracket': 433, 'multi_hole': 433, 'stepped': 433, 'taper': 433}
- Solver: CalculiX ['2.23']
- Git: `af168644bd8eef34c0ded8dc014d69e3580122db` (dirty=True)
- Dataset sha256: `238111c799321e7a...`

## Shape families

| shape | cases |
| --- | --- |
| i_beam | 433 |
| l_bracket | 433 |
| multi_hole | 433 |
| plate | 644 |
| stepped | 433 |
| taper | 433 |

## Design variables (observed range, all shapes pooled)

| variable | min | mean | max | range |
| --- | --- | --- | --- | --- |
| length_mm | 60 | 123.6 | 160 | 100 |
| width_mm | 20 | 42.22 | 60 | 40 |
| thickness_mm | 4 | 7.523 | 12 | 8 |
| hole_diameter_mm | 0 | 12.11 | 27 | 27 |
| hole_x_mm | 20.11 | 58.51 | 110 | 89.89 |
| hole2_diameter_mm | 0 | 1.541 | 19.2 | 19.2 |
| hole2_x_mm | 0 | 14.13 | 126.4 | 126.4 |
| tip_width_mm | 10.5 | 38.5 | 60 | 49.5 |
| step_x_mm | 30.6 | 59.74 | 93.57 | 62.98 |
| step_thickness_mm | 2.44 | 5.73 | 8.4 | 5.96 |
| fillet_radius_mm | 0 | 1.294 | 6.755 | 6.755 |
| flange_width_mm | 35 | 41.91 | 70 | 35 |
| beam_depth_mm | 40 | 42.29 | 70 | 30 |
| flange_thickness_mm | 5.6 | 6.596 | 15.4 | 9.8 |
| web_thickness_mm | 4.2 | 5.519 | 14 | 9.8 |
| height_mm | 60 | 91.51 | 140 | 80 |
| force_n | 100 | 448.8 | 800 | 700 |
| youngs_modulus_mpa | 2.1e+05 | 2.1e+05 | 2.1e+05 | 0 |
| poisson_ratio | 0.3 | 0.3 | 0.3 | 0 |
| mesh_size_mm | 1.22 | 2.738 | 3 | 1.78 |

## Targets (observed range, successful cases)

| target | min | mean | max |
| --- | --- | --- | --- |
| max_displacement_mm | 0.0003284 | 1.985 | 44.35 |
| global_max_von_mises_mpa | 0.5933 | 229.2 | 2641 |
| max_von_mises_roi_mpa | 0.4971 | 224.8 | 2641 |

## Labels and provenance

- Every label comes from a completed CalculiX C3D10 static solve; failed
  or gated cases are excluded and listed in `failures.csv`.
- Mesh policy: {"name": "production", "element_order": 2, "global_size_factor": 2.0, "global_size_cap_mm": 3.0, "global_size_floor_mm": 0.0, "hole_size_fraction": 0.1, "hole_grading_fraction": 0.6, "fillet_size_fraction": 0.6}
- `fields_npz` stores nodal coordinates, displacement, stress components
  and Von Mises stress as float32 for field-learning experiments.
- The ROI target tracks the shape's stress riser: hole cylinders for the
  plate-like families, re-entrant fillets for stepped/bracket shapes, and
  web/flange fillets for the I-beam; no-hole plates carry
  `max_von_mises_roi_mpa = null`.
- Parameters that are inactive for a shape carry neutral constants, so
  models must condition on the `shape` column.

## Engineering caveats

- Labels carry the discretization uncertainty quantified in
  `reports/validation/` (~0.5% on stress, smaller on displacement).
- Linear elasticity and small strain only; no contact, plasticity,
  dynamics or thermal effects.
- The ROI stress is a nodal peak; use with the documented mesh policy.

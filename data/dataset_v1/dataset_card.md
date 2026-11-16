# SurroSim simulation dataset card

- Schema version: `1.0.0`
- Created: 2026-09-19T17:16:15.936942+00:00
- Cases in dataset: **644** (failed/excluded: 0)
- Splits: {'challenge': 84, 'train': 392, 'test': 84, 'val': 84}
- Solver: CalculiX ['2.23']
- Git: `3dfcad2b5e63ffbcaa4777e9883a7d8c823d5a2d` (dirty=False)
- Dataset sha256: `c94d884666caa38a...`

## Design variables (observed range)

| variable | min | mean | max | range |
| --- | --- | --- | --- | --- |
| length_mm | 100 | 129.7 | 160 | 60 |
| width_mm | 30 | 44.9 | 60 | 30 |
| thickness_mm | 4 | 6.971 | 10 | 6 |
| hole_diameter_mm | 0 | 13.92 | 27 | 27 |
| hole_x_mm | 35.19 | 64.9 | 110 | 74.81 |
| force_n | 100 | 449.9 | 800 | 700 |
| youngs_modulus_mpa | 2.1e+05 | 2.1e+05 | 2.1e+05 | 0 |
| poisson_ratio | 0.3 | 0.3 | 0.3 | 0 |
| mesh_size_mm | 2 | 2.797 | 3 | 1 |

## Targets (observed range, successful cases)

| target | min | mean | max |
| --- | --- | --- | --- |
| max_displacement_mm | 0.04454 | 2.279 | 27.74 |
| global_max_von_mises_mpa | 12.54 | 250.6 | 2071 |
| max_von_mises_roi_mpa | 10.7 | 239.3 | 2071 |

## Labels and provenance

- Every label comes from a completed CalculiX C3D10 static solve; failed
  or gated cases are excluded and listed in `failures.csv`.
- Mesh policy: {"element_order": 2, "global_size_factor": 2.0, "global_size_cap_mm": 3.0, "hole_size_fraction": 0.1, "hole_grading_fraction": 0.6}
- `fields_npz` stores nodal coordinates, displacement, stress components
  and Von Mises stress as float32 for field-learning experiments.
- ROI target is defined only for perforated cases (no-hole cases carry
  `max_von_mises_roi_mpa = null`).

## Engineering caveats

- Labels carry the discretization uncertainty quantified in
  `reports/validation/` (~0.5% on stress, smaller on displacement).
- Linear elasticity and small strain only; no contact, plasticity,
  dynamics or thermal effects.
- The ROI stress is a nodal peak; use with the documented mesh policy.

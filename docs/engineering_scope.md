# Engineering scope — v0.1 starter

This implementation is **M1 of v0.1**, not a trained or validated surrogate.

## Geometry and conditions

- mm, N, MPa; rectangular plate from X=0 to X=L, centered about Y=Z=0.
- Through-hole axis Z; its center is `(hole_x_mm, 0, 0)`.
- Intended next-stage FEA: clamp `FIXED_FACE` (X=0), distribute total
  transverse force `-force_n` across `LOAD_FACE` (X=L); isotropic linear
  elastic material with E and nu as given. No gravity or plasticity.
- Gmsh physical surface groups indicate *where* conditions should be
  applied; they **do not apply** a force or a clamp. The exported mesh is
  not a completed CalculiX input deck.

## Analytical baseline limitations

The Euler–Bernoulli rectangular-beam equations return *nominal* root bending
stress and end displacement for an **unperforated** prismatic beam. They do
not reproduce local hole stress, actual peak Von Mises stress, shear effects,
3-D constraints, or the influence of the finite-area end load. Do not use
these values as ground-truth FEA labels, engineering design approval, or ML
accuracy evidence.

## Next development tasks

1. Export a verified CalculiX-compatible volume element model with distinct
   boundary node sets; inspect mesh and element order against solver support.
2. Generate static load/constraint/material cards and run `ccx`; parse result
   fields, stress location/averaging and displacement consistently.
3. Validate against a simpler no-hole beam and carry out a mesh-convergence
   study before generating supervised training labels.
4. Sample designs, run/record solver status, retain held-out *geometry* IDs,
   train scalar regressors, and benchmark against independent FEA cases.

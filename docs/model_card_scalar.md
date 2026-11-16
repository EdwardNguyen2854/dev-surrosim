# Model card — scalar surrogate models (v0.4)

## Model identity

- Registry: `models/scalar/v1/` (`metadata.json` describes every artifact).
  Only the selected ensemble members are committed to the repository;
  comparison models (random forest, XGBoost, ...) are reproducible with
  `surrosim train scalar` but not versioned because of their size.
- Selected models: **GP + MLP ensemble** (unweighted mean of log predictions)
  for all three targets.
- Alternatives evaluated: ridge regression, random forest, XGBoost,
  Gaussian process, MLP. Selection rule: lowest validation RMSE among models
  whose held-out challenge-split worst-case relative error stays below 100%.
- Target transform: `log`; metrics are computed after exponentiation in
  engineering units.

## Intended use

Instant surrogate predictions of a cantilever plate with a through-hole
during interactive design exploration, as a replacement for repeated FEA
runs **inside the validated design space only**. Predictions are not a
substitute for engineering verification; high-fidelity FEA remains the
authority and is available in the same workflow (`surrosim simulate`).

## Training data

- Dataset: `data/dataset_v1/` (schema 1.0.0), sha256
  `c94d884666caa38a...`, 644 CalculiX 2.23 cases (C3D10), of which 392
  train / 84 validation / 84 test / 84 challenge (held out).
- Features (12): length, width, thickness, hole diameter, hole x-position,
  force; hole/width ratio, hole-position ratio, slenderness L/T,
  width/thickness ratio, dimensionless load, hole/thickness ratio.
- Targets: max displacement (mm), global max Von Mises (MPa), hole-ROI max
  Von Mises (MPa). The ROI target is defined only for perforated cases.

## Performance (dataset v1)

| target | split | MAPE | RMSE | R² | worst-case rel. error |
| --- | --- | --- | --- | --- | --- |
| max displacement | test | 1.85% | 0.063 mm | 0.9991 | 9.1% |
| max displacement | challenge | 5.39% | — | — | 29.5% |
| global max VM | test | 2.30% | 10.3 MPa | 0.9973 | 12.4% |
| global max VM | challenge | 6.73% | — | — | 88.2% |
| ROI max VM | test | 1.74% | 8.3 MPa | 0.9981 | 8.9% |
| ROI max VM | challenge | 6.14% | — | — | 42.8% |

References:

- Euler-Bernoulli baseline: 3.56% (displacement) and 12.6% (global stress)
  test MAPE — the learned ensemble is clearly better than classical
  closed-form estimates.
- XGBoost / random forest: ~10% test MAPE; tree models underperform on this
  smooth, low-data regression.
- Median FEA solve time in the dataset: 10.05 s; ensemble inference is
  ~10 µs per design (~10⁶× faster per evaluation).

Full tables and parity figures: `reports/v0.4_scalar_comparison.md`,
`reports/figures/v0.4/`.

## Limitations and out-of-distribution behaviour

- Validated only for the sampled design space; predictions outside it are
  unsupported. The challenge split shows the expected degradation (5–7%
  MAPE, worst cases up to ~88% on global stress at extreme corners).
- Linear-elastic labels only; no yield, buckling, contact or dynamic effects.
- No-hole designs have no ROI target; the application must suppress the ROI
  prediction for them.
- GP members can produce large extrapolation errors; the ensemble and the
  application-level domain checks exist to bound that risk (v0.5).

## Reproduction

```bash
surrosim dataset sample --count 560 --challenge-count 72 --out data/designs_v1.csv
surrosim dataset run --designs data/designs_v1.csv --out data/runs --jobs 6 --ccx ccx
surrosim dataset build --designs data/designs_v1.csv --runs data/runs --out data/dataset_v1
surrosim train scalar --dataset data/dataset_v1/dataset.csv --out models/scalar/v1
```

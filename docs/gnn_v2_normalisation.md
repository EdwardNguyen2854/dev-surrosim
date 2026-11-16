# Multi-shape GNN target-scaling investigation

## Failure reproduced

`python tools/analyze_gnn.py` reproduces the original candidate's aggregate
599.02% test displacement MAPE from its recorded per-case evaluations.
The command's 50% threshold is diagnostic, not a release acceptance criterion.

I-beams had 3,291.07% test displacement MAPE; their true displacement maxima
ranged from 0.00124 to 0.0178 mm. Brackets in the same dataset reached 19.58 mm.
Training standardized physical target components with one global mean/std.
This placed small-response designs at a disadvantage in absolute-error loss.

## Controlled experiment

Two MeshGraphNet runs used identical shape-balanced subsets (120 training,
120 validation graphs), seeds, architecture, learning schedule, and 20 epochs.
The changed variable was target scaling. Test/challenge evaluations were
disabled for these experiments.

| Scaling | Validation peak-displacement MAPE | Validation peak-VM MAPE |
| --- | --- | --- |
| Global physical-unit standardization | 1,564.28% | 71.74% |
| Input-derived nominal scaling, then standardization | 9.33% | 26.85% |

Artifacts: `outputs/gnn_normalisation_ab/{none,nominal}`. Selected case IDs
are recorded in metadata so the comparison can be reproduced.

## Implementation

`src/surrosim/gnn/normalisation.py` computes one displacement scale and one
stress scale from the shape-specific nominal analytical references. Inputs
are geometry, material, and force only; FEA labels never determine these
per-design scales. Training divides the physical target tensor by the scales
before computing training-only mean/std. Evaluation, field snapshots, and
serving share the inverse transform to recover mm and MPa.

This is preprocessing of the learned field, not substitution of an analytical
solution for it. Checkpoints remain one shared, shape-conditioned GNN.
The metadata identifies the transform as `nominal_v1`; missing metadata means
the legacy unscaled transform. Force/modulus scaling and inverse transforms
are regression-tested for all six shapes.

Additional evaluation corrections:

- Model selection now uses validation global-VM MAPE only, never test or
  challenge scores.
- Reduced-data experiments use shape-balanced selection rather than an
  alphabetical case-ID prefix that could exclude entire families.
- Metrics now include a per-shape breakdown and handle absent ROI values.
- Reports no longer claim comparison with an unrelated legacy scalar registry.

## Full retraining and frozen-checkpoint evaluation

The corrected candidate trained on 1,722 graphs for 60 epochs on CUDA,
taking 6,039.1 seconds. Its full-training run evaluated validation only.
`tools/evaluate_gnn.py` subsequently evaluated the fixed checkpoint and
recorded its SHA-256 without retraining or changing model selection.

| Split | Cases | Peak displacement MAPE | Peak VM MAPE | ROI VM MAPE |
| --- | --- | --- | --- | --- |
| Validation | 369 | 3.32% | 3.38% | 3.75% |
| Test | 369 | 3.53% | 3.24% | 3.53% |
| Challenge | 349 | 4.33% | 5.04% | 5.68% |

Test per-shape displacement MAPE ranges from 1.91% (L-bracket) to 8.37%
(I-beam); peak-VM MAPE ranges from 1.68% (plate) to 6.30% (L-bracket).
Challenge worst-case errors remain material: peak displacement 17.11%, peak
VM 38.58%, and ROI VM 88.07%. Average errors do not establish accuracy for
every design. Field results are measured against the coarse graph-mesh FEA,
not the independent production-mesh solution.

The original candidate's test scores were inspected during diagnosis, so
these are reused held-out benchmarks, not a newly collected blind test set.
They were not used for selection in the corrected training run.

Artifacts:

- `models/gnn/v2_normalized_candidate/metadata.json`: training and validation.
- `models/gnn/v2_normalized_candidate/held_out_evaluation.json`: frozen model
  hash plus test/challenge results and per-case errors.
- `reports/v2.0_gnn_normalized_holdout.md`: aggregate and per-shape tables.

App promotion, six-shape end-to-end checks, and scalar-registry review remain
separate completion steps. The candidate has not been promoted to serving.

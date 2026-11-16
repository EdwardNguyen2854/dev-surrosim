# Six-shape GNN candidate — UI testing

This registry is a candidate for interactive testing, not a production acceptance decision.
The MeshGraphNet uses input-derived nominal target scaling, 31 node features,
and 9 field components. It trained on 1,722 graphs for 60 epochs on CUDA.
Model selection used validation data only; the frozen checkpoint was subsequently evaluated.

| Split | Cases | Peak displacement MAPE | Peak stress MAPE | ROI stress MAPE |
| --- | --- | --- | --- | --- |
| Validation | 369 | 3.32% | 3.38% | 3.75% |
| Test | 369 | 3.53% | 3.24% | 3.53% |
| Challenge | 349 | 4.33% | 5.04% | 5.68% |

| Shape | Test displacement MAPE | Test peak stress MAPE |
| --- | --- | --- |
| Plate | 2.45% | 1.68% |
| Tapered plate | 3.28% | 1.69% |
| Two-hole plate | 2.53% | 2.69% |
| Filleted stepped plate | 3.18% | 4.98% |
| Filleted I-beam | 8.37% | 2.84% |
| Filleted L-bracket | 1.91% | 6.30% |

Errors are measured against coarse-mesh FEA. Challenge worst-case ROI stress error
is 88.07%; average errors do not guarantee accuracy for every design. Use FEA Verify
for an independent production-mesh calculation. Full per-case results and checkpoint
hash are recorded in `held_out_evaluation.json` alongside this report.

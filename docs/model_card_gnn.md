# Model card — MeshGraphNet field surrogate (v0.6)

## Model identity

- Registry: `models/gnn/v1/` (`metadata.json`, `meshgraphnet.pt`);
  a per-node MLP baseline (`node_mlp.pt`) is kept for comparison.
- Architecture: encoder–processor–decoder message passing (8 blocks,
  hidden 80, SiLU MLPs, residual LayerNorm), 15 node features, 4 edge
  features, 9 outputs (3 displacement + 6 stress components); implemented
  in pure PyTorch (no PyG dependency).
- Training: normalised MSE, AdamW (lr 1e-3, cosine), gradient accumulation
  4, early stopping on validation loss; seed 42; RTX 3050, ~24 min.

## Intended use

Spatial field prediction (displacement and stress distribution) over the
validated design space, for engineering visualisation and quick spatial
exploration. Scalar extremes should be taken from the v0.4 ensemble.

## Training data

- `data/graphs_v1`: 644 graphs from coarse-profile C3D10 FEA (CalculiX
  2.23), same designs and splits as `data/dataset_v1`
  (392/84/84/84 train/val/test/challenge).
- Graph mesh profile: global size clamp(t/1.5, 2.5, 4.0) mm, hole graded to
  min(0.6 × global, d/6).

## Performance (scalar reductions from predicted fields)

| split | max disp MAPE | global max VM MAPE | ROI max VM MAPE | field VM median err |
| --- | --- | --- | --- | --- |
| test (84) | 8.68% | 2.63% | 3.22% | 0.80% of peak |
| challenge (84) | 29.31% | 9.14% | 8.58% | 1.47% of peak |

Baseline comparison (per-node MLP): 10.47% test / 28.24% challenge global-VM
MAPE — message passing roughly halves the error.

## Limitations

- Coarse-mesh predictions; production-mesh accuracy is not claimed.
- Relative field errors are large where stress/displacement are near zero;
  use absolute or peak-relative error when interpreting.
- No uncertainty estimate per node yet; ensemble disagreement exists only
  for scalar targets.
- Linear elastic, quasi-static, single material; no OOD detector specific to
  geometry is implemented beyond design-space bounds.

## Reproduction

```bash
surrosim dataset run --designs data/designs_v1.csv --out data/runs_graph \
    --jobs 6 --mesh-profile graph --ccx ccx
surrosim graph export --designs data/designs_v1.csv --runs data/runs_graph --out data/graphs_v1
surrosim train gnn --graphs data/graphs_v1 --runs data/runs_graph \
    --out models/gnn/v1 --epochs 150 --patience 30
```

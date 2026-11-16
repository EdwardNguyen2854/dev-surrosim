# Multi-shape regeneration and training

The six-shape FEA datasets and candidate training completed on 2026-09-21.
The release remains pending accuracy review and app integration. Candidate
model directories are separate from the serving registries. The first GNN
candidate had poor held-out accuracy; a subsequently trained input-scaled
candidate substantially improved it. See `gnn_v2_normalisation.md` and
`../reports/v2.0_gnn_normalized_holdout.md` for measured results.

## Run and resume (Windows PowerShell)

Install the development dependencies, including `psutil` for memory monitoring.
From the repository root:

```powershell
.\.venv\Scripts\python.exe tools/run_v2.py --jobs 4
```

The launcher holds an OS-backed single-instance lock. Do not run independent
`dataset run` commands against the same output directories while it is active.
After an interruption, use the same command to reuse completed case artifacts.
Inputs and splits of reused v1 scalar labels are checked against the v2 table.
Add `--reuse-scalar` when resuming after scalar training: the launcher loads
the existing scalar candidate and requires an exact gated-dataset hash match.

The pipeline:

1. Runs 2,165 new-shape production cases in chunks of 20, using fresh processes.
2. Builds the scalar dataset with 644 existing plate labels. All 2,809 designs
   must pass the dataset completeness checks before training starts.
3. Starts scalar training concurrently with coarse graph FEA. Graph FEA uses
   one worker during scalar training; scalar joblib/OpenMP pools are bounded.
4. Returns graph FEA to the configured worker limit after scalar training.
5. Exports all 2,809 graphs and checks completeness, then trains the GNN.
6. Writes `awaiting_model_review` on successful completion.

FEA uses one numerical-library thread per worker. The launcher samples available
RAM every 0.5 seconds. Below 4 GiB, it stops its FEA process tree and resumes the
chunk with half as many workers, retaining the lower limit for later chunks.
At one worker it stops and records the failure instead. This is a reactive
guard, not a guarantee against abrupt memory spikes. Compacted field archives
are published by atomic rename so interrupted writes do not become cache hits.

Scalar training uses CPU; GNN training automatically selects CUDA when usable.
Dataset size, mesh settings, and epoch defaults are unchanged by concurrency.

## Monitoring

Files under `outputs/v2_pipeline/`:

- `status.json`: current stage, launcher PID, update time, command, or failure.
- `stdout*.log` / `stderr*.log`: logs from a background launch.
- `scalar.log`: scalar training output while graph FEA runs.
- `benchmark_*/results.json`: measured worker throughput and memory usage.

Each FEA chunk overwrites its runs directory's `batch_summary.json`; that file
describes the latest chunk, not cumulative progress. The existing stdout log
is preserved when restarting to a differently named log.

Candidate artifacts: `models/scalar/v2_candidate`, `models/gnn/v2_candidate`.
Reports: `reports/v2.0_scalar_candidate.md`, `reports/v2.0_gnn_candidate.md`.
They require accuracy and compatibility review before serving integration.

## Measured concurrency benchmark — 2026-09-20

Local machine: 6 physical cores / 12 logical CPUs, approximately 32 GiB RAM,
RTX 3050 with 6 GiB VRAM. CUDA availability was verified in PyTorch.
Each configuration solved the same 10 fresh production designs: two from
each of the five new shape families. All runs succeeded without pool restarts.

| Workers | Solver threads | Wall time | Speedup vs 1 worker | Minimum available RAM |
| --- | --- | --- | --- | --- |
| 1 | 1 | 203.5 s | 1.00x | 14.5 GiB |
| 2 | 1 | 117.5 s | 1.73x | 11.6 GiB |
| 4 | 1 | 69.4 s | 2.93x | 7.8 GiB |
| 4 | 2 | 67.8 s | 3.00x | 7.8 GiB |

Four-worker benchmarks averaged about 49% total system CPU usage. Additional
solver threads offered little improvement. Four single-threaded workers were
selected, with memory fallback. These samples establish throughput evidence,
not worst-case memory bounds or a guaranteed full-dataset speedup.

## Completed run and outstanding validation

- Production dataset: 2,809 rows, zero rejected cases; 644 plate labels reused
  and 433 designs for each new family.
- Graph export: 2,809 graphs, zero skipped cases.
- Scalar and GNN candidate training completed; launcher state is
  `awaiting_model_review`.
- GNN used CUDA; MeshGraphNet training took 6,278.7 seconds for 60 epochs.
- First GNN test aggregate errors: displacement-max MAPE 599.02%, global
  von Mises-max MAPE 45.48%, ROI-max MAPE 26.75%. These are unsatisfactory;
  field modeling/normalization and per-shape errors need investigation.
- The generated reports retain legacy headings and some legacy reference
  text; report wording and model-selection methodology need review before
  publication. Training completion is not a production acceptance decision.

The graph run initially stopped on `stepped_0202`: its 2.486 mm thin section
was smaller than the 2.5 mm graph mesh floor. The floor is now waived only
when it violates a non-plate section thickness. The original failing case
then passed a real solve. Both policies pass input validation on all 2,809
designs; previously valid mesh sizes are preserved.

To repeat a fresh benchmark while the pipeline is stopped:

```powershell
.\.venv\Scripts\python.exe tools/benchmark_v2.py --jobs 1 2 4
```

# SurroSim documentation

Start with the [README](../README.md) for the pitch and the quick start, then
pick the path that matches what you need.

Documents written before the public release refer to internal development
milestone numbers (v0.6, v1.0, v2.0). Those milestones were private; the public
release history starts at v0.1.0, and the file names are kept so that report
and figure links stay stable.

## Understand the system

| Document | What it answers |
| --- | --- |
| [Vision](../VISION.md) | Why the project exists and where it is meant to go. |
| [Architecture](architecture.md) | Module map, data flow, and the provenance chain from design record to served prediction. |
| [Engineering scope](engineering_scope.md) | What problem the project solves and what it deliberately does not. |
| [Validation report](validation_report.md) | Measured FEA and model accuracy, with the evidence behind each number. |
| [Limitations and out of scope](limitations_and_out_of_scope.md) | Where predictions stop being trustworthy. Read before using results in practice. |

## Run it

| Document | What it answers |
| --- | --- |
| [Reproducibility](reproducibility.md) | Environment, stage-by-stage commands, and what each stage writes. |
| [Multi-shape pipeline operations](v2_pipeline_operations.md) | Resumable v2 dataset runs, monitoring, and recovery. |
| [Web app and API](v0.5_app.md) | Service endpoints, background jobs, and the application pages. |

## Models

| Document | What it answers |
| --- | --- |
| [Scalar model card](model_card_scalar.md) | Targets, features, training, and measured accuracy of the scalar surrogates. |
| [GNN model card](model_card_gnn.md) | MeshGraphNet inputs, outputs, and accuracy envelope. |
| [GNN normalisation study](gnn_v2_normalisation.md) | Why v2 targets are scaled, and what it changed. |

## History

Per-milestone design notes: [v0.2 FEA engine](v0.2_fea_engine.md) ·
[v0.3 dataset factory](v0.3_dataset.md) · [v0.6 GNN](v0.6_gnn.md).
Release history lives in the [changelog](../CHANGELOG.md).

## Project process

[Contributing](../CONTRIBUTING.md) · [Code of conduct](../CODE_OF_CONDUCT.md) ·
[Security policy](../SECURITY.md) · [Agent working notes](../AGENTS.md)

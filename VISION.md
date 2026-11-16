# SurroSim Vision

## Purpose

**SurroSim** is an engineering AI project for building fast, trustworthy surrogate models that approximate expensive physics-based simulations.

The long-term goal is to let engineers explore design changes, loads, materials, and operating conditions interactively while preserving a clear link back to validated numerical simulation.

SurroSim is not intended to replace engineering judgment or high-fidelity FEA/CFD solvers. It is intended to make simulation-driven engineering faster by learning from verified simulation data and using that learned model where rapid approximation is useful.

## Problem

Traditional CAE workflows are accurate and powerful, but repeated simulation can be slow and expensive. A typical design study may require geometry creation, meshing, material/load/boundary-condition setup, solving, post-processing, and many repetitions.

For optimization, design-space exploration, uncertainty studies, or interactive engineering tools, hundreds or thousands of simulations may be required.

SurroSim aims to learn the relationship:

    Geometry + Material + Loads + Boundary Conditions
                          ↓
                  Surrogate Model
                          ↓
            Approximate Engineering Response

so previously expensive evaluations can be performed in milliseconds or seconds after training.

## Core Vision

SurroSim should evolve into a reusable engineering surrogate-modeling platform with four major capabilities:

    Simulation Automation
             ↓
       Dataset Factory
             ↓
      Surrogate Models
             ↓
     Engineering App

### 1. Simulation Automation

Automatically generate and execute trustworthy engineering simulations.

Initial focus:

- Structural FEA
- Parametric mechanical components
- Gmsh
- CalculiX

Future possibilities include thermal simulation, CFD, modal analysis, fatigue, and additional CAE solvers.

### 2. Engineering Dataset Factory

Turn simulation studies into structured, reproducible ML datasets while preserving:

- geometry parameters
- mesh information
- material properties
- loads and boundary conditions
- solver version and status
- convergence information
- scalar outputs
- nodal or field outputs
- runtime
- provenance

Failed or invalid simulations must never silently enter training datasets.

### 3. Surrogate Modeling

Support multiple surrogate strategies rather than assuming one architecture is always best:

- analytical engineering baselines
- Gaussian processes
- Random Forest
- XGBoost
- multilayer perceptrons
- graph neural networks
- MeshGraphNet-style models
- neural operators
- geometry-aware transformer models

For scalar targets:

    Design parameters
          ↓
    XGBoost / MLP
          ↓
    Stress / displacement

For field prediction:

    FE mesh
       ↓
    GNN / neural operator
       ↓
    Full engineering field

### 4. Engineering Interaction

Surrogate predictions should eventually be available through an interactive engineering application where engineers can change design parameters and immediately inspect predicted behavior.

Possible future interfaces include a web app, 3D result visualization, optimization dashboard, CAD integration, and integration with an engineering AI agent or harness.

## Initial Engineering Problem

The first SurroSim problem is intentionally constrained: a parametric cantilever plate with a through-hole.

Inputs include length, width, thickness, hole diameter, hole position, and applied force.

Outputs initially include maximum displacement, global maximum Von Mises stress, and maximum Von Mises stress in a defined region of interest.

The goal of this geometry family is not to create a universal FEA replacement. It is to establish the complete validated workflow:

    Parameters
        ↓
    Geometry
        ↓
    Mesh
        ↓
    FEA
        ↓
    Validated Results
        ↓
    Dataset
        ↓
    ML Training
        ↓
    Surrogate Prediction
        ↓
    FEA Verification

## Engineering Principles

### Physics Before Machine Learning

SurroSim should not train models on simulation results until the underlying simulation workflow has been validated.

Before generating ML labels:

- geometry must be verified
- loads must be verified
- constraints must be verified
- units must be verified
- solver execution must be reproducible
- mesh convergence must be studied
- selected cases should be compared with analytical references where possible

A surrogate can only be as trustworthy as the data used to train it.

### Ground Truth Must Be Traceable

Every ML label should be traceable back to the simulation that produced it.

    Prediction
       ↓
    Model Version
       ↓
    Dataset Version
       ↓
    Simulation Cases
       ↓
    Geometry / Mesh / Solver Configuration

Reproducibility and provenance are first-class requirements.

### Surrogate Models Approximate — They Do Not Replace Physics

Surrogate predictions are valid only within the domain represented by their training data and validation studies.

SurroSim should explicitly detect or communicate out-of-distribution inputs, unsupported geometries, extrapolation, uncertain predictions, and invalid parameter ranges.

When confidence is insufficient, the correct action may be: **run the real solver**.

### Validation Matters More Than Model Complexity

A small, well-validated XGBoost model can be more useful than a sophisticated deep neural network with poorly understood errors.

Model comparison should include analytical baselines where available, simple ML baselines, and advanced ML/DL models.

Evaluation should consider MAE, RMSE, relative engineering error, worst-case error, inference latency, simulation runtime, generalization to unseen geometries, and out-of-distribution behavior.

### Geometry-Aware Learning Is a Long-Term Goal

Scalar parameter models are useful for early versions, but engineering simulations fundamentally operate on geometry.

Long-term SurroSim should support FE meshes, point clouds, CAD-derived representations, graph representations, and field-level prediction.

## Product Direction

The long-term product concept is an **AI-assisted engineering simulation layer**.

Instead of repeatedly running a full solver for every design variation:

    Engineer
       ↓
    Design change
       ↓
    Surrogate prediction
       ↓
    Instant engineering feedback
       ↓
    Promising design?
       ↓
    High-fidelity FEA verification

The expensive solver remains part of the workflow, but is used strategically.

## Future CAD Integration

Possible workflow:

    Creo / SolidWorks / STEP
              ↓
    Geometry Extraction
              ↓
          SurroSim
              ↓
    Predicted Engineering Response
              ↓
       3D Visualization
              ↓
       FEA Verification

Potential applications include instant design feedback, parameter optimization, geometry screening, AI-assisted mechanical design, automated design studies, and CAD-agent integration.

## Design Optimization Vision

Once sufficiently accurate, a surrogate can become part of an optimization loop:

    Objective: Minimize Mass
    Constraints: Stress < Allowable, Displacement < Limit
              ↓
          Optimizer
              ↓
          Surrogate
              ↓
    Thousands of evaluations
              ↓
       Best candidates
              ↓
     Full FEA verification

## Roadmap

### v0.1 — Geometry Foundation

- parametric geometry
- Gmsh meshing
- analytical reference
- reproducible parameter sampling

### v0.2 — Validated FEA Engine

- CalculiX integration
- automatic input-deck generation
- boundary conditions and load handling
- result extraction
- stress ROI definition
- analytical beam validation
- mesh convergence

### v0.3 — Simulation Dataset Factory

- batch simulation
- Latin Hypercube / Sobol sampling
- parallel execution
- failure handling
- simulation provenance
- structured training dataset

### v0.4 — First Surrogate

- analytical baseline
- XGBoost
- PyTorch MLP
- train/validation/test workflow
- model comparison
- FEA vs surrogate benchmark

### v0.5 — Engineering Application

- interactive parameter exploration
- model inference API
- result visualization
- prediction confidence and domain checks

### v0.6+ — Geometric Deep Learning

- mesh representation
- PyTorch Geometric
- graph neural networks
- MeshGraphNet-style models
- field prediction

### v1.0 — Portfolio-Ready Surrogate Platform

A reproducible end-to-end engineering AI system demonstrating simulation automation, scientific data generation, ML/DL, geometric learning, engineering validation, deployment, and design optimization.

## Possible Future Expansion

### Structural

- brackets and mounts
- frames
- pressure-loaded parts
- deformation and stress prediction
- modal response

### Thermal

- temperature fields
- heat sinks
- electronics cooling
- thermal deformation

### CFD

- aerodynamic coefficients
- pressure and velocity fields
- internal flow
- pressure drop

### Manufacturing

- process parameter optimization
- thermal history
- distortion prediction
- residual stress

## Non-Goals

SurroSim should not become:

- a black-box replacement for validated CAE software
- a tool that hides engineering assumptions
- a system that reports predictions without supported input ranges
- an ML benchmark disconnected from real engineering workflows
- a project focused only on achieving the lowest test-set loss

Its purpose is to explore how **physics simulation, mechanical engineering, and modern machine learning can work together in a trustworthy engineering workflow**.

## Success Criteria

SurroSim succeeds if it can demonstrate that:

1. Engineering simulation data can be generated automatically and reproducibly.
2. The simulation pipeline is independently validated.
3. A surrogate can learn useful relationships from that data.
4. Prediction errors and limitations are measurable and documented.
5. Inference is substantially faster than the original simulation.
6. Engineers can use the surrogate to explore designs interactively.
7. High-fidelity solvers remain available for verification.
8. The architecture can grow from scalar prediction to geometry-aware field prediction.

## Long-Term Vision

> **Make engineering simulation fast enough to become part of the design interaction loop while keeping every prediction grounded in validated physics-based data.**

SurroSim should demonstrate how a mechanical engineer can combine **CAD + CAE + automation + machine learning + geometric deep learning + optimization** into a modern engineering AI workflow.

"""Simulation dataset factory: batch FEA cases plus validated dataset builds."""

from .batch import run_batch
from .build import build_dataset
from .cases import run_case

__all__ = ["run_batch", "build_dataset", "run_case"]

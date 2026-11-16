"""Surrogate-based constrained design optimization with FEA verification."""

from .problem import OptimizationProblem
from .run import optimize_design

__all__ = ["OptimizationProblem", "optimize_design"]

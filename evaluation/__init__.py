"""Deterministic, offline evaluation subsystem for CreditLens."""

from .evaluator import DATASET_VERSION, EVALUATION_VERSION, run_evaluation

__all__ = ["DATASET_VERSION", "EVALUATION_VERSION", "run_evaluation"]

"""
NEXUS Self-Evolution System

Automated system improvement through performance analysis, bottleneck detection,
hypothesis generation, A/B testing, and code refactoring.
"""

from .analyzer import PerformanceAnalyzer
from .hypothesis import HypothesisGenerator
from .experiments import ExperimentManager
from .refactor import CodeRefactor

__all__ = [
    "PerformanceAnalyzer",
    "HypothesisGenerator",
    "ExperimentManager",
    "CodeRefactor"
]
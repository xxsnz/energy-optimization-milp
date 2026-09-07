"""
Energy Resource Optimizer

Multi-asset scheduling optimizer for energy programs (ECON, FR, DCM).
Uses mixed-integer linear programming (Pyomo + HiGHS/GLPK) to maximize benefits
while respecting capacity limits, program constraints, and mutual exclusivity rules.
"""

from energy_optimizer.config import (
    DEFAULT_MAX_EXECUTION_TIME_SECONDS,
    DEFAULT_MIP_GAP,
    SOLUTION_FILE_SUFFIX,
    OptimizerConfig,
    SolverName,
    detect_solver,
)
from energy_optimizer.domain import (
    HOUR_SEPARATOR,
    NO_HOUR_VALUE,
    AssetType,
    OptimizationStrategy,
    ProgramType,
    parse_period_hour,
)
from energy_optimizer.extraction import ResourceConstraints, ResourceDataExtractor
from energy_optimizer.formatting import SolutionFormatter
from energy_optimizer.model import OptimizationModelBuilder
from energy_optimizer.runner import EnergyResourceOptimizer

__version__ = "1.0.0"

__all__ = [
    "DEFAULT_MAX_EXECUTION_TIME_SECONDS",
    "DEFAULT_MIP_GAP",
    "HOUR_SEPARATOR",
    "NO_HOUR_VALUE",
    "SOLUTION_FILE_SUFFIX",
    "AssetType",
    "EnergyResourceOptimizer",
    "OptimizationModelBuilder",
    "OptimizationStrategy",
    "OptimizerConfig",
    "ProgramType",
    "ResourceConstraints",
    "ResourceDataExtractor",
    "SolutionFormatter",
    "SolverName",
    "detect_solver",
    "parse_period_hour",
]

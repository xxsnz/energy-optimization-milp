"""Run configuration and MILP solver auto-detection."""

import enum
import importlib.util
import math
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from energy_optimizer.domain import OptimizationStrategy

DEFAULT_MAX_EXECUTION_TIME_SECONDS = 200
DEFAULT_MIP_GAP = 0.01
SOLUTION_FILE_SUFFIX = '_sln'


class SolverName(enum.Enum):
    """Supported MILP solvers, in auto-detection order."""
    HIGHS = 'highs'  # pip-installable (highspy), used via Pyomo APPSI
    GLPK = 'glpk'    # system binary (glpsol)


def detect_solver(preference: Optional[str] = None) -> tuple[SolverName, Optional[str]]:
    """Find an available MILP solver.

    Returns (solver_name, executable_path). The path is only set for GLPK;
    HiGHS is used through its Python bindings.
    """
    highs_available = importlib.util.find_spec('highspy') is not None
    glpk_path = shutil.which('glpsol')

    if preference == SolverName.HIGHS.value:
        if not highs_available:
            raise RuntimeError(
                "HiGHS solver requested but not installed. "
                "Install it with: pip install highspy"
            )
        return SolverName.HIGHS, None

    if preference == SolverName.GLPK.value:
        if not glpk_path:
            raise RuntimeError(
                "GLPK solver requested but glpsol was not found in PATH. "
                "Install it with: apt-get install glpk-utils (Linux) "
                "or brew install glpk (macOS)."
            )
        return SolverName.GLPK, glpk_path

    if highs_available:
        return SolverName.HIGHS, None
    if glpk_path:
        return SolverName.GLPK, glpk_path

    raise RuntimeError(
        "No MILP solver found. Install HiGHS (pip install highspy) "
        "or GLPK (apt-get install glpk-utils / brew install glpk)."
    )


@dataclass
class OptimizerConfig:
    """Configuration for the optimization run."""
    input_path: Path
    output_path: Path
    solver_name: SolverName
    solver_path: Optional[str] = None
    strategy: OptimizationStrategy = OptimizationStrategy.ASSET_LEVEL
    max_execution_time: int = DEFAULT_MAX_EXECUTION_TIME_SECONDS
    mip_gap: float = DEFAULT_MIP_GAP

    def __post_init__(self) -> None:
        if self.max_execution_time <= 0:
            raise ValueError(
                f"max_execution_time must be positive, got {self.max_execution_time}"
            )
        if not math.isfinite(self.mip_gap) or self.mip_gap < 0:
            raise ValueError(
                f"mip_gap must be a finite non-negative number, got {self.mip_gap}"
            )

    @classmethod
    def from_input_file(
        cls,
        input_file: str,
        output_file: Optional[str] = None,
        solver: Optional[str] = None,
        strategy: OptimizationStrategy = OptimizationStrategy.ASSET_LEVEL,
        max_execution_time: int = DEFAULT_MAX_EXECUTION_TIME_SECONDS,
        mip_gap: float = DEFAULT_MIP_GAP,
    ) -> 'OptimizerConfig':
        """Create config from input file path, auto-detecting a solver."""
        input_path = Path(input_file)
        if output_file:
            output_path = Path(output_file)
        else:
            output_path = input_path.with_stem(f"{input_path.stem}{SOLUTION_FILE_SUFFIX}")

        solver_name, solver_path = detect_solver(solver)

        return cls(
            input_path=input_path,
            output_path=output_path,
            solver_name=solver_name,
            solver_path=solver_path,
            strategy=strategy,
            max_execution_time=max_execution_time,
            mip_gap=mip_gap,
        )

"""Orchestration: load input, extract constraints, build, solve, format, write."""

import json
import logging
from typing import Any

import pyomo.environ as pyo

from energy_optimizer.config import OptimizerConfig, SolverName
from energy_optimizer.extraction import ResourceConstraints, ResourceDataExtractor
from energy_optimizer.formatting import SolutionFormatter
from energy_optimizer.model import OptimizationModelBuilder

logger = logging.getLogger(__name__)


class EnergyResourceOptimizer:
    """Main orchestrator for energy resource optimization."""

    # Assigned by the pipeline steps in run(), in order
    input_data: dict[str, Any]
    constraints: ResourceConstraints
    model: pyo.ConcreteModel
    solution: dict[str, Any]

    def __init__(self, config: OptimizerConfig):
        self.config = config

    def run(self) -> str:
        """Run the full optimization workflow."""
        try:
            logger.info("=" * 60)
            logger.info("Energy Resource Optimizer")
            logger.info("=" * 60)

            self._load_input_data()
            self._extract_constraints()
            self._build_model()
            self._solve_model()
            self._format_solution()
            self._write_solution()

            logger.info("=" * 60)
            logger.info("Optimization completed successfully")
            logger.info(f"Solution written to: {self.config.output_path}")
            logger.info("=" * 60)

            return str(self.config.output_path)

        except Exception as e:
            logger.error(f"Optimization failed: {e}", exc_info=True)
            raise

    def _load_input_data(self) -> None:
        """Load and validate input JSON data."""
        logger.info(f"Loading input data from: {self.config.input_path}")

        try:
            with open(self.config.input_path) as f:
                self.input_data = json.load(f)
        except FileNotFoundError as e:
            raise FileNotFoundError(
                f"Input file not found: {self.config.input_path}"
            ) from e
        except json.JSONDecodeError as e:
            raise ValueError(
                f"Invalid JSON in input file: {e}"
            ) from e

        # Validate required fields
        required_fields = ['Resources', 'MonthlyLoads', 'DcmData', 'ExcludeFirstDcmMonth']
        missing_fields = [f for f in required_fields if f not in self.input_data]

        if missing_fields:
            raise ValueError(
                f"Missing required fields in input data: {missing_fields}"
            )

        logger.info(f"Input data loaded: {len(self.input_data['Resources'])} resources")

    def _extract_constraints(self) -> None:
        """Extract resource constraints from input data."""
        extractor = ResourceDataExtractor(self.input_data)
        self.constraints = extractor.extract()

    def _build_model(self) -> None:
        """Build the optimization model."""
        builder = OptimizationModelBuilder(self.constraints, self.config.strategy)
        self.model = builder.build()

    def _solve_model(self) -> None:
        """Solve the optimization model."""
        if not self.constraints.asset_programs:
            logger.warning("No asset programs to optimize; solution will be empty")
            return

        logger.info("Solving optimization model...")

        try:
            if self.config.solver_name == SolverName.HIGHS:
                solver = pyo.SolverFactory('appsi_highs')
                solver.options['time_limit'] = self.config.max_execution_time
                solver.options['mip_rel_gap'] = self.config.mip_gap
            else:
                solver = pyo.SolverFactory('glpk', executable=self.config.solver_path)
                solver.options['tmlim'] = self.config.max_execution_time
                solver.options['mipgap'] = self.config.mip_gap

            result = solver.solve(self.model, tee=False)

            # Check the termination condition before the status: APPSI reports
            # a time-limited solve as status 'aborted' even when a feasible
            # incumbent was found and loaded.
            termination = result.solver.termination_condition
            if termination == pyo.TerminationCondition.optimal:
                logger.info("Optimal solution found")
            elif termination == pyo.TerminationCondition.maxTimeLimit:
                logger.warning("Time limit reached - solution may be suboptimal")
            elif result.solver.status == pyo.SolverStatus.ok:
                logger.warning(f"Solution status: {termination}")
            else:
                raise RuntimeError(
                    f"Solver failed with status: {result.solver.status} "
                    f"(termination: {termination})"
                )

        except RuntimeError:
            raise
        except Exception as e:
            raise RuntimeError(f"Solver execution failed: {e}") from e

    def _format_solution(self) -> None:
        """Format the solution for output."""
        formatter = SolutionFormatter(
            self.input_data,
            self.constraints,
            self.model
        )
        self.solution = formatter.format()

    def _write_solution(self) -> None:
        """Write solution to output file."""
        logger.info(f"Writing solution to: {self.config.output_path}")

        try:
            with open(self.config.output_path, 'w') as f:
                json.dump(self.solution, f, indent=2)
        except OSError as e:
            raise OSError(f"Failed to write solution file: {e}") from e

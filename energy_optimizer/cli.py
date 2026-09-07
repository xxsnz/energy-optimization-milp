"""Command-line interface for the energy resource optimizer."""

import argparse
import logging
import sys
from typing import Optional

from energy_optimizer.config import (
    DEFAULT_MAX_EXECUTION_TIME_SECONDS,
    DEFAULT_MIP_GAP,
    SOLUTION_FILE_SUFFIX,
    OptimizerConfig,
    SolverName,
)
from energy_optimizer.domain import OptimizationStrategy
from energy_optimizer.runner import EnergyResourceOptimizer

logger = logging.getLogger(__name__)


def _configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    logging.getLogger('pyomo.core').setLevel(logging.ERROR)
    logging.getLogger('pyomo.contrib.appsi').setLevel(logging.WARNING)


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        prog='energy-optimizer',
        description='MILP optimizer for scheduling energy assets across '
                    'ECON, FR, and DCM programs.'
    )
    parser.add_argument(
        'input_file',
        help='Path to the input JSON file'
    )
    parser.add_argument(
        '-o', '--output',
        help=f'Path to the solution JSON file '
             f'(default: <input>{SOLUTION_FILE_SUFFIX}.json next to the input)'
    )
    parser.add_argument(
        '--solver',
        choices=[s.value for s in SolverName],
        help='MILP solver to use (default: auto-detect, HiGHS preferred)'
    )
    parser.add_argument(
        '--strategy',
        choices=[s.name.lower() for s in OptimizationStrategy],
        default=OptimizationStrategy.ASSET_LEVEL.name.lower(),
        help='Optimization strategy (default: %(default)s)'
    )
    parser.add_argument(
        '--time-limit',
        type=int,
        default=DEFAULT_MAX_EXECUTION_TIME_SECONDS,
        help='Solver time limit in seconds (default: %(default)s)'
    )
    parser.add_argument(
        '--mip-gap',
        type=float,
        default=DEFAULT_MIP_GAP,
        help='Relative MIP optimality gap (default: %(default)s)'
    )
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> None:
    """Main entry point."""
    _configure_logging()
    args = parse_args(argv)

    try:
        config = OptimizerConfig.from_input_file(
            args.input_file,
            output_file=args.output,
            solver=args.solver,
            strategy=OptimizationStrategy[args.strategy.upper()],
            max_execution_time=args.time_limit,
            mip_gap=args.mip_gap,
        )
        optimizer = EnergyResourceOptimizer(config)
        output_path = optimizer.run()
        print(output_path)

    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()

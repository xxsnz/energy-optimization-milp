"""Domain vocabulary shared across the optimizer: programs, assets, time encoding."""

import enum

# Time periods are encoded as "{period}_{hour}" strings; "0_0" is the
# "no participation" sentinel shared by every program.
NO_HOUR_VALUE = '0_0'
HOUR_SEPARATOR = '_'


class OptimizationStrategy(enum.Enum):
    """Optimization strategy modes."""
    SIMPLE_MATH = 1
    ASSET_LEVEL = 2


class ProgramType(enum.Enum):
    """Energy program types."""
    ECON = 'econ'  # Economic demand response
    FR = 'fr'      # Frequency regulation
    DCM = 'dcm'    # Demand capacity management


class AssetType(enum.Enum):
    """Asset type classifications."""
    BATTERY = 'BT'
    GENERATOR = 'BG'
    LOAD = 'LD'


def parse_period_hour(period_hour: str) -> tuple[int, int]:
    """Parse a period_hour string into a (period, hour) tuple."""
    parts = period_hour.split(HOUR_SEPARATOR)
    return int(parts[0]), int(parts[1])

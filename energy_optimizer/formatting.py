"""Solution formatting: solver output back into the output JSON schema."""

import logging
from typing import Any, Optional

import pyomo.environ as pyo

from energy_optimizer.domain import (
    HOUR_SEPARATOR,
    AssetType,
    ProgramType,
    parse_period_hour,
)
from energy_optimizer.extraction import ResourceConstraints

logger = logging.getLogger(__name__)


class SolutionFormatter:
    """Formats optimization results into output JSON structure."""

    def __init__(
        self,
        input_data: dict[str, Any],
        constraints: ResourceConstraints,
        model: pyo.ConcreteModel
    ):
        self.input_data = input_data
        self.c = constraints
        self.model = model
        self.solution_values = model.x.extract_values()

    def format(self) -> dict[str, Any]:
        """Format the solution."""
        logger.info("Formatting solution...")

        solution = {
            'Resources': self._format_resources(),
            'Dcm': self._format_dcm_summary(),
            'DcmHrs': self._format_dcm_hours()
        }

        return solution

    def _format_resources(self) -> list[dict[str, Any]]:
        """Format per-resource results."""
        resources = []

        for resource_data in self.input_data['Resources']:
            asset_id = resource_data['ResourceId']

            resource = {
                'ResourceId': asset_id,
                'Type': resource_data['Type'],
                'ProgramAnnualParticipation': self._format_asset_programs(
                    asset_id,
                    resource_data
                )
            }

            resources.append(resource)

        return resources

    def _format_asset_programs(
        self,
        asset_id: str,
        resource_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Format program participation for one asset."""
        participation = {}

        for asset_program in self.c.asset_programs:
            if not asset_program.startswith(asset_id):
                continue

            program_name = asset_program.split('_')[1]

            # Skip DCM if chain is in use
            if program_name == ProgramType.DCM.value and self.c.dcm_chain_enabled:
                continue

            participation[program_name] = {
                'MonthParticipation': self._format_monthly_participation(
                    asset_id,
                    asset_program,
                    program_name,
                    resource_data
                )
            }

        return participation

    def _format_monthly_participation(
        self,
        asset_id: str,
        asset_program: str,
        program_name: str,
        resource_data: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Format monthly participation for one program."""
        # Sort time periods by period index
        sorted_periods = sorted(
            self.c.time_periods,
            key=lambda x: int(x.split(HOUR_SEPARATOR)[0])
        )

        monthly_data: list[dict[str, Any]] = []
        current_period_idx = -1

        for period_hour in sorted_periods:
            period_idx, hour = parse_period_hour(period_hour)

            if hour == 0:
                continue

            # Start new month if needed
            if period_idx != current_period_idx or len(monthly_data) == 0:
                monthly_data.append({
                    'ChosenHours': [],
                    'TotalHours': 0,
                    'Benefit': 0,
                    'TotalKw': 0
                })
                current_period_idx = period_idx

            # Check if this hour was chosen
            if self.solution_values[(asset_program, period_hour)] == 1:
                month_data = monthly_data[-1]
                month_data['ChosenHours'].append(hour - 1)
                month_data['TotalHours'] += 1
                month_data['Benefit'] += self.c.benefits[(asset_program, period_hour)]

                # Calculate KW
                if (resource_data['Type'] == AssetType.BATTERY.value and
                    program_name == ProgramType.DCM.value):
                    month_data['TotalKw'] += self.c.dcm_kw_range[asset_id][period_hour]
                else:
                    month_data['TotalKw'] += resource_data['Capacity']

        # Convert TotalKw to int
        for month_data in monthly_data:
            month_data['TotalKw'] = int(month_data['TotalKw'])

        return monthly_data

    def _format_dcm_summary(self) -> list[int]:
        """Format DCM summary: count per period."""
        dcm_counts = [0] * self.c.periods_count

        for (asset_program, period_hour), value in self.solution_values.items():
            if not asset_program.endswith(f'_{ProgramType.DCM.value}'):
                continue

            if value == 1:
                period_idx, _ = parse_period_hour(period_hour)
                dcm_counts[period_idx] += 1

        return dcm_counts

    def _format_dcm_hours(self) -> dict[str, list]:
        """Format DCM hours per asset per period."""
        dcm_hours: dict[str, list[Optional[list[int]]]] = {}

        for resource_data in self.input_data['Resources']:
            asset_id = resource_data['ResourceId']
            dcm_hours[asset_id] = [None] * self.c.periods_count

        for (asset_program, period_hour), value in self.solution_values.items():
            if not asset_program.endswith(f'_{ProgramType.DCM.value}'):
                continue

            if value == 1:
                asset_id = asset_program.split('_')[0]
                period_idx, hour = parse_period_hour(period_hour)

                hours = dcm_hours[asset_id][period_idx]
                if hours is None:
                    hours = []
                    dcm_hours[asset_id][period_idx] = hours

                hours.append(hour - 1)

        return dcm_hours

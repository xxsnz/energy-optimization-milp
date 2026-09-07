"""Input parsing: turns the raw input JSON into a ResourceConstraints dataclass."""

import logging
from dataclasses import dataclass, field
from typing import Any

from energy_optimizer.domain import (
    HOUR_SEPARATOR,
    NO_HOUR_VALUE,
    AssetType,
    ProgramType,
)

logger = logging.getLogger(__name__)


@dataclass
class ResourceConstraints:
    """Extracted resource data and constraints for optimization."""
    assets: list[str] = field(default_factory=list)
    asset_programs: list[str] = field(default_factory=list)
    programs: list[str] = field(default_factory=list)
    time_periods: list[str] = field(default_factory=list)

    # Benefits mapping: (asset_program, time_period) -> benefit_value
    benefits: dict[tuple[str, str], float] = field(default_factory=dict)

    # Asset properties
    capacity: dict[str, float] = field(default_factory=dict)
    usage_limits: dict[str, float] = field(default_factory=dict)
    kwh_limits: dict[str, float] = field(default_factory=dict)
    fr_percent: dict[str, float] = field(default_factory=dict)
    asset_type: dict[str, str] = field(default_factory=dict)

    # Constraint flags
    econ_fr_enabled: dict[str, bool] = field(default_factory=dict)
    econ_dcm_enabled: dict[str, bool] = field(default_factory=dict)
    site_dcm_enabled: bool = False

    # Constraint data
    econ_dominates_fr: dict[str, dict[str, int]] = field(default_factory=dict)
    fr_dominates_econ: dict[str, dict[str, int]] = field(default_factory=dict)

    # DCM specific
    dcm_chain_enabled: bool = True
    dcm_chain: dict[str, dict[str, int]] = field(default_factory=dict)
    dcm_kw_range: dict[str, dict[str, float]] = field(default_factory=dict)
    dcm_per_period: dict[str, int] = field(default_factory=dict)
    exclude_first_dcm_month: bool = False

    # Time mappings
    datetime_to_period: dict[tuple, str] = field(default_factory=dict)
    period_to_datetime: dict[tuple, str] = field(default_factory=dict)
    datetime_list: list[str] = field(default_factory=list)
    periods_count: int = 0


class ResourceDataExtractor:
    """Extracts and processes resource data from input JSON."""

    def __init__(self, data: dict[str, Any]):
        self.data = data
        self.constraints = ResourceConstraints()

    def extract(self) -> ResourceConstraints:
        """Main extraction method."""
        logger.info("Extracting resource data and constraints...")

        self._initialize_time_periods()
        self._process_resources()
        self._process_dcm_data()

        logger.info(f"Extracted {len(self.constraints.assets)} assets, "
                   f"{len(self.constraints.asset_programs)} programs")

        return self.constraints

    def _initialize_time_periods(self) -> None:
        """Initialize time period structure."""
        self.constraints.time_periods = [NO_HOUR_VALUE]
        self.constraints.periods_count = len(self.data['MonthlyLoads'])

    def _process_resources(self) -> None:
        """Process all resources and their programs."""
        for resource_data in self.data['Resources']:
            asset_id = resource_data['ResourceId']
            self.constraints.assets.append(asset_id)

            # Store asset properties
            self.constraints.capacity[asset_id] = resource_data['Capacity']
            self.constraints.kwh_limits[asset_id] = resource_data['KwhLimit']
            self.constraints.fr_percent[asset_id] = resource_data['FrPercent']
            self.constraints.asset_type[asset_id] = resource_data['Type']

            # Calculate usage limits. KwhLimit encodes the discharge budget
            # magnitude; input files use a negative sign for discharge direction.
            if resource_data['Type'] == AssetType.BATTERY.value:
                if self.constraints.capacity[asset_id] == 0:
                    raise ValueError(
                        f"Battery '{asset_id}' has zero capacity; "
                        "cannot derive its usage limit from KwhLimit"
                    )
                self.constraints.usage_limits[asset_id] = abs(
                    self.constraints.kwh_limits[asset_id] /
                    self.constraints.capacity[asset_id]
                )
            else:
                self.constraints.usage_limits[asset_id] = resource_data['HourLimit']

            # Process programs for this asset
            self._process_asset_programs(asset_id, resource_data)

            # Track DCM participation
            if f'{asset_id}_{ProgramType.DCM.value}' in self.constraints.asset_programs:
                self.constraints.site_dcm_enabled = True

            # Setup mutual exclusivity constraints
            self._setup_econ_fr_constraints(asset_id)
            self._setup_econ_dcm_constraints(asset_id)

        # Store DCM settings
        self.constraints.exclude_first_dcm_month = self.data['ExcludeFirstDcmMonth']

    def _process_asset_programs(
        self,
        asset_id: str,
        resource_data: dict[str, Any]
    ) -> None:
        """Process programs for a specific asset."""
        for program_name in resource_data['ProgramAnnualBenefits']:
            if program_name not in self.constraints.programs:
                self.constraints.programs.append(program_name)

            asset_program = f'{asset_id}_{program_name}'
            self.constraints.asset_programs.append(asset_program)

            # Set zero benefit for no-hour
            self.constraints.benefits[(asset_program, NO_HOUR_VALUE)] = 0

            # Process monthly benefits
            program_benefits = resource_data['ProgramAnnualBenefits'][program_name]
            self._process_monthly_benefits(
                asset_program,
                program_name,
                program_benefits['MonthBenefits']
            )

    def _process_monthly_benefits(
        self,
        asset_program: str,
        program_name: str,
        month_benefits: list[dict[str, Any]]
    ) -> None:
        """Process monthly benefit data."""
        for period_idx, period_benefits in enumerate(month_benefits):
            for hour_benefit in period_benefits['HourBenefits']:
                period_hour = f"{period_idx}{HOUR_SEPARATOR}{hour_benefit['Hour']}"

                # Add to time periods if new
                if period_hour not in self.constraints.time_periods:
                    self.constraints.time_periods.append(period_hour)
                    self.constraints.dcm_per_period[period_hour] = 0

                # Store benefit
                self.constraints.benefits[(asset_program, period_hour)] = (
                    hour_benefit['Benefit']
                )

                # Map datetime to period
                datetime = hour_benefit['DateTime']
                self.constraints.datetime_to_period[
                    (program_name, period_idx, datetime)
                ] = period_hour
                self.constraints.period_to_datetime[(program_name, period_hour)] = datetime

                if datetime not in self.constraints.datetime_list:
                    self.constraints.datetime_list.append(datetime)

        # Fill missing datetime mappings with NO_HOUR_VALUE
        self._fill_missing_datetime_mappings()

    def _fill_missing_datetime_mappings(self) -> None:
        """Ensure all datetime/program/period combinations are mapped."""
        for datetime in self.constraints.datetime_list:
            for program in self.constraints.programs:
                for period in range(self.constraints.periods_count):
                    key = (program, period, datetime)
                    if key not in self.constraints.datetime_to_period:
                        self.constraints.datetime_to_period[key] = NO_HOUR_VALUE

    def _setup_econ_fr_constraints(self, asset_id: str) -> None:
        """Setup ECON/FR mutual exclusivity constraints."""
        econ_program = f'{asset_id}_{ProgramType.ECON.value}'
        fr_program = f'{asset_id}_{ProgramType.FR.value}'

        if econ_program not in self.constraints.asset_programs:
            self.constraints.econ_fr_enabled[asset_id] = False
            return

        if fr_program not in self.constraints.asset_programs:
            self.constraints.econ_fr_enabled[asset_id] = False
            return

        self.constraints.econ_fr_enabled[asset_id] = True
        self.constraints.econ_dominates_fr[asset_id] = {}
        self.constraints.fr_dominates_econ[asset_id] = {}

        # Determine which program dominates at each time
        for datetime in self.constraints.datetime_list:
            for period in range(self.constraints.periods_count):
                econ_period = self.constraints.datetime_to_period[
                    (ProgramType.ECON.value, period, datetime)
                ]
                fr_period = self.constraints.datetime_to_period[
                    (ProgramType.FR.value, period, datetime)
                ]

                if econ_period == NO_HOUR_VALUE and fr_period == NO_HOUR_VALUE:
                    continue

                econ_benefit = self.constraints.benefits[(econ_program, econ_period)]
                fr_benefit = self.constraints.benefits[(fr_program, fr_period)]

                if econ_benefit > fr_benefit:
                    self.constraints.econ_dominates_fr[asset_id][econ_period] = 1
                    self.constraints.fr_dominates_econ[asset_id][fr_period] = 0
                else:
                    self.constraints.econ_dominates_fr[asset_id][econ_period] = 0
                    self.constraints.fr_dominates_econ[asset_id][fr_period] = 1

    def _setup_econ_dcm_constraints(self, asset_id: str) -> None:
        """Setup ECON/DCM mutual exclusivity."""
        econ_program = f'{asset_id}_{ProgramType.ECON.value}'
        dcm_program = f'{asset_id}_{ProgramType.DCM.value}'

        self.constraints.econ_dcm_enabled[asset_id] = (
            dcm_program in self.constraints.asset_programs and
            econ_program in self.constraints.asset_programs
        )

    def _process_dcm_data(self) -> None:
        """Process DCM chain data."""
        if len(self.data['DcmData']) != self.constraints.periods_count:
            return

        for period in range(self.constraints.periods_count):
            for dcm_entry in self.data['DcmData'][period]:
                asset_id = dcm_entry['AssetId']

                if asset_id not in self.constraints.dcm_chain:
                    self.constraints.dcm_chain[asset_id] = {}
                if asset_id not in self.constraints.dcm_kw_range:
                    self.constraints.dcm_kw_range[asset_id] = {}

                period_hour = f"{period}{HOUR_SEPARATOR}{dcm_entry['Hour']}"
                self.constraints.dcm_chain[asset_id][period_hour] = 1
                self.constraints.dcm_per_period[period_hour] += 1
                self.constraints.dcm_kw_range[asset_id][period_hour] = dcm_entry['KwRange']

        # Fill missing DCM data with zeros
        for asset_id in self.constraints.assets:
            dcm_program = f'{asset_id}_{ProgramType.DCM.value}'
            if dcm_program not in self.constraints.asset_programs:
                continue

            if asset_id not in self.constraints.dcm_chain:
                self.constraints.dcm_chain[asset_id] = {}
            if asset_id not in self.constraints.dcm_kw_range:
                self.constraints.dcm_kw_range[asset_id] = {}

            for period_hour in self.constraints.time_periods:
                if period_hour not in self.constraints.dcm_chain[asset_id]:
                    self.constraints.dcm_chain[asset_id][period_hour] = 0
                if period_hour not in self.constraints.dcm_kw_range[asset_id]:
                    self.constraints.dcm_kw_range[asset_id][period_hour] = 0

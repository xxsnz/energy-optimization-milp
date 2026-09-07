"""Pyomo MILP model construction from extracted resource constraints."""

import logging

import pyomo.environ as pyo

from energy_optimizer.domain import (
    HOUR_SEPARATOR,
    NO_HOUR_VALUE,
    AssetType,
    OptimizationStrategy,
    ProgramType,
    parse_period_hour,
)
from energy_optimizer.extraction import ResourceConstraints

logger = logging.getLogger(__name__)


class OptimizationModelBuilder:
    """Builds Pyomo optimization model from resource constraints."""

    model: pyo.ConcreteModel  # assigned in build()

    def __init__(self, constraints: ResourceConstraints, strategy: OptimizationStrategy):
        self.c = constraints
        self.strategy = strategy

    def build(self) -> pyo.ConcreteModel:
        """Build the optimization model."""
        logger.info("Building optimization model...")

        self.model = pyo.ConcreteModel(name="EnergyResourceOptimizer")

        self._create_variables()
        self._create_objective()

        # Early exit for edge case: only DCM with no KW ranges
        if self._is_trivial_dcm_only_case():
            self._create_trivial_constraints()
            return self.model

        self._create_capacity_constraints()
        self._create_strategy_specific_constraints()
        self._create_no_hour_constraints()
        self._create_econ_dcm_constraints()
        self._create_dcm_constraints()

        logger.info("Model built successfully")
        return self.model

    def _create_variables(self) -> None:
        """Create decision variables."""
        # x[asset_program, time_period]: binary - whether asset participates in program at time
        self.model.x = pyo.Var(
            self.c.asset_programs,
            self.c.time_periods,
            within=pyo.Binary
        )

        # y[time_period]: binary - DCM period activation
        self.model.y = pyo.Var(self.c.time_periods, within=pyo.Binary)

        # z[asset, time_period]: binary - FR consecutive hour tracking
        self.model.z = pyo.Var(
            self.c.assets,
            self.c.time_periods,
            within=pyo.Binary
        )

        # i[asset, time_period]: binary - ECON consecutive hour tracking
        self.model.i = pyo.Var(
            self.c.assets,
            self.c.time_periods,
            within=pyo.Binary
        )

    def _create_objective(self) -> None:
        """Create objective function: maximize total benefits."""
        self.model.obj = pyo.Objective(
            expr=sum(
                self.c.benefits[asset_program, period] * self.model.x[asset_program, period]
                for asset_program in self.c.asset_programs
                for period in self.c.time_periods
            ),
            sense=pyo.maximize
        )

    def _is_trivial_dcm_only_case(self) -> bool:
        """Check if this is DCM-only with no KW ranges."""
        if len(self.c.programs) != 1:
            return False
        if self.c.programs[0] != ProgramType.DCM.value:
            return False

        return all(
            kw == 0
            for dcm_ranges in self.c.dcm_kw_range.values()
            for kw in dcm_ranges.values()
        )

    def _create_trivial_constraints(self) -> None:
        """Create constraints for trivial DCM-only case."""
        self.model.c_trivial = pyo.ConstraintList()
        for asset_program in self.c.asset_programs:
            for period in self.c.time_periods:
                self.model.c_trivial.add(expr=self.model.x[asset_program, period] <= 0)

    def _create_capacity_constraints(self) -> None:
        """Create capacity/usage limit constraints."""
        self.model.c_capacity = pyo.ConstraintList()

        for asset_id in self.c.assets:
            usage_expr = sum(
                self._get_usage_multiplier(asset_id, asset_program, period)
                * self.model.x[asset_program, period]
                for asset_program in self.c.asset_programs
                if asset_program.startswith(asset_id)
                for period in self.c.time_periods
                if period != NO_HOUR_VALUE
            )

            self.model.c_capacity.add(
                expr=usage_expr <= max(self.c.usage_limits[asset_id], 0)
            )

    def _get_usage_multiplier(
        self,
        asset_id: str,
        asset_program: str,
        period: str
    ) -> float:
        """Calculate usage multiplier for capacity constraint."""
        if asset_program == f'{asset_id}_{ProgramType.FR.value}':
            return self.c.fr_percent[asset_id]

        if (asset_program == f'{asset_id}_{ProgramType.DCM.value}'
                and self.c.asset_type[asset_id] == AssetType.BATTERY.value):
            return (
                self.c.dcm_kw_range[asset_id][period] /
                self.c.capacity[asset_id]
            )

        return 1.0

    def _create_strategy_specific_constraints(self) -> None:
        """Create constraints based on optimization strategy."""
        if self.strategy == OptimizationStrategy.SIMPLE_MATH:
            self._create_simple_math_constraints()
        elif self.strategy == OptimizationStrategy.ASSET_LEVEL:
            self._create_asset_level_constraints()

    def _create_simple_math_constraints(self) -> None:
        """Simple mutual exclusivity: ECON and FR cannot overlap."""
        self.model.c_simple_mutex = pyo.ConstraintList()

        for asset_id in self.c.assets:
            if not self.c.econ_fr_enabled[asset_id]:
                continue

            for period in range(self.c.periods_count):
                for datetime in self.c.datetime_list:
                    econ_period = self.c.datetime_to_period[
                        (ProgramType.ECON.value, period, datetime)
                    ]
                    fr_period = self.c.datetime_to_period[
                        (ProgramType.FR.value, period, datetime)
                    ]

                    if econ_period.endswith('_0') or fr_period.endswith('_0'):
                        continue

                    self.model.c_simple_mutex.add(
                        expr=(
                            self.model.x[f'{asset_id}_{ProgramType.ECON.value}', econ_period] +
                            self.model.x[f'{asset_id}_{ProgramType.FR.value}', fr_period]
                            <= 1
                        )
                    )

    def _create_asset_level_constraints(self) -> None:
        """Asset-level constraints with benefit-based dominance."""
        self._create_econ_dominance_constraints()
        self._create_fr_dominance_constraints()
        self._create_fr_consecutive_constraints()
        self._create_econ_consecutive_constraints()

    def _create_econ_dominance_constraints(self) -> None:
        """ECON can only activate when it has higher benefit than FR."""
        self.model.c_econ_dom = pyo.ConstraintList()

        for asset_id in self.c.assets:
            if not self.c.econ_fr_enabled[asset_id]:
                continue

            for period in range(self.c.periods_count):
                for datetime in self.c.datetime_list:
                    econ_period = self.c.datetime_to_period[
                        (ProgramType.ECON.value, period, datetime)
                    ]

                    if econ_period == NO_HOUR_VALUE:
                        continue

                    self.model.c_econ_dom.add(
                        expr=(
                            self.model.x[f'{asset_id}_{ProgramType.ECON.value}', econ_period]
                            <= self.c.econ_dominates_fr[asset_id][econ_period]
                        )
                    )

    def _create_fr_dominance_constraints(self) -> None:
        """FR can only activate when it has higher benefit than ECON."""
        self.model.c_fr_dom = pyo.ConstraintList()

        for asset_id in self.c.assets:
            if not self.c.econ_fr_enabled[asset_id]:
                continue

            for period in range(self.c.periods_count):
                for datetime in self.c.datetime_list:
                    fr_period = self.c.datetime_to_period[
                        (ProgramType.FR.value, period, datetime)
                    ]

                    if fr_period == NO_HOUR_VALUE:
                        continue

                    self.model.c_fr_dom.add(
                        expr=(
                            self.model.x[f'{asset_id}_{ProgramType.FR.value}', fr_period]
                            <= self.c.fr_dominates_econ[asset_id][fr_period]
                        )
                    )

    def _create_fr_consecutive_constraints(self) -> None:
        """FR requires consecutive hours (2+ hours)."""
        self.model.c_fr_consec_1 = pyo.ConstraintList()
        self.model.c_fr_consec_2 = pyo.ConstraintList()
        self.model.c_fr_consec_3 = pyo.ConstraintList()

        for asset_id in self.c.assets:
            if not self.c.econ_fr_enabled[asset_id]:
                continue

            for period_hour in self.c.time_periods:
                period, hour = parse_period_hour(period_hour)
                if hour == 0 or hour == 1:
                    continue

                # z tracks if FR can be activated (requires FR or ECON in same datetime)
                self.model.c_fr_consec_1.add(
                    expr=(
                        self.model.z[asset_id, period_hour] <=
                        self.model.x[f'{asset_id}_{ProgramType.FR.value}', period_hour] +
                        self.model.x[
                            f'{asset_id}_{ProgramType.ECON.value}',
                            self.c.datetime_to_period[(
                                ProgramType.ECON.value,
                                period,
                                self.c.period_to_datetime[(ProgramType.FR.value, period_hour)]
                            )]
                        ]
                    )
                )

                # z requires previous hour also activated
                self.model.c_fr_consec_2.add(
                    expr=(
                        self.model.z[asset_id, period_hour] <=
                        self.model.z[asset_id, f'{period}_{hour - 1}']
                    )
                )

                # FR requires z (consecutive hours)
                self.model.c_fr_consec_3.add(
                    expr=(
                        self.model.x[f'{asset_id}_{ProgramType.FR.value}', period_hour] <=
                        self.model.z[asset_id, period_hour]
                    )
                )

    def _create_econ_consecutive_constraints(self) -> None:
        """ECON requires consecutive hours (2+ hours)."""
        self.model.c_econ_consec_1 = pyo.ConstraintList()
        self.model.c_econ_consec_2 = pyo.ConstraintList()
        self.model.c_econ_consec_3 = pyo.ConstraintList()

        for asset_id in self.c.assets:
            if not self.c.econ_fr_enabled[asset_id]:
                continue

            for period_hour in self.c.time_periods:
                period, hour = parse_period_hour(period_hour)
                if hour == 0 or hour == 1:
                    continue

                # i tracks if ECON can be activated
                self.model.c_econ_consec_1.add(
                    expr=(
                        self.model.i[asset_id, period_hour] <=
                        self.model.x[f'{asset_id}_{ProgramType.ECON.value}', period_hour] +
                        self.model.x[
                            f'{asset_id}_{ProgramType.FR.value}',
                            self.c.datetime_to_period[(
                                ProgramType.FR.value,
                                period,
                                self.c.period_to_datetime[(ProgramType.ECON.value, period_hour)]
                            )]
                        ]
                    )
                )

                # i requires previous hour also activated
                self.model.c_econ_consec_2.add(
                    expr=(
                        self.model.i[asset_id, period_hour] <=
                        self.model.i[asset_id, f'{period}_{hour - 1}']
                    )
                )

                # ECON requires i (consecutive hours)
                self.model.c_econ_consec_3.add(
                    expr=(
                        self.model.x[f'{asset_id}_{ProgramType.ECON.value}', period_hour] <=
                        self.model.i[asset_id, period_hour]
                    )
                )

    def _create_no_hour_constraints(self) -> None:
        """No program can activate at NO_HOUR_VALUE."""
        self.model.c_no_hour = pyo.ConstraintList()

        for asset_program in self.c.asset_programs:
            self.model.c_no_hour.add(
                expr=self.model.x[asset_program, NO_HOUR_VALUE] <= 0
            )

    def _create_econ_dcm_constraints(self) -> None:
        """ECON and DCM are mutually exclusive."""
        self.model.c_econ_dcm_mutex = pyo.ConstraintList()

        for asset_id in self.c.assets:
            if not self.c.econ_dcm_enabled[asset_id]:
                continue

            for period in range(self.c.periods_count):
                for datetime in self.c.datetime_list:
                    econ_period = self.c.datetime_to_period[
                        (ProgramType.ECON.value, period, datetime)
                    ]
                    dcm_period = self.c.datetime_to_period[
                        (ProgramType.DCM.value, period, datetime)
                    ]

                    if econ_period == NO_HOUR_VALUE and dcm_period == NO_HOUR_VALUE:
                        continue

                    self.model.c_econ_dcm_mutex.add(
                        expr=(
                            self.model.x[f'{asset_id}_{ProgramType.ECON.value}', econ_period] +
                            self.model.x[f'{asset_id}_{ProgramType.DCM.value}', dcm_period]
                            <= 1
                        )
                    )

    def _create_dcm_constraints(self) -> None:
        """Create DCM-specific constraints."""
        self._create_dcm_first_month_constraint()
        self._create_dcm_chain_constraints()
        self._create_dcm_site_constraints()

    def _create_dcm_first_month_constraint(self) -> None:
        """Optionally exclude first month from DCM."""
        if not self.c.exclude_first_dcm_month:
            return

        self.model.c_dcm_first_month = pyo.ConstraintList()

        for asset_id in self.c.assets:
            if f'{asset_id}_{ProgramType.DCM.value}' not in self.c.asset_programs:
                continue

            self.model.c_dcm_first_month.add(
                expr=sum(
                    self.model.x[f'{asset_id}_{ProgramType.DCM.value}', period]
                    for period in self.c.time_periods
                    if period.split(HOUR_SEPARATOR)[0] == '0'
                    and period.split(HOUR_SEPARATOR)[1] != '0'
                ) == 0
            )

    def _create_dcm_chain_constraints(self) -> None:
        """DCM chain: only allowed hours can be activated."""
        self.model.c_dcm_chain = pyo.ConstraintList()

        if self.c.dcm_chain_enabled:
            for asset_id in self.c.assets:
                dcm_program = f'{asset_id}_{ProgramType.DCM.value}'
                if dcm_program not in self.c.asset_programs:
                    continue

                for period in self.c.time_periods:
                    _, hour = parse_period_hour(period)
                    if hour == 0:
                        # Force hour 0 to be inactive
                        self.model.x[dcm_program, period].fix(0)
                        continue

                    if self.c.dcm_chain[asset_id][period] == 0:
                        self.model.c_dcm_chain.add(
                            expr=self.model.x[dcm_program, period] <= 0
                        )
        elif self.c.site_dcm_enabled:
            # If chain not enabled, only one DCM asset per hour site-wide
            for period in self.c.time_periods:
                self.model.c_dcm_chain.add(
                    expr=sum(
                        self.model.x[asset_program, period]
                        for asset_program in self.c.asset_programs
                        if asset_program.endswith(ProgramType.DCM.value)
                    ) <= 1
                )

    def _create_dcm_site_constraints(self) -> None:
        """Site-level DCM constraints."""
        if not self.c.site_dcm_enabled:
            return

        self.model.c_dcm_site_1 = pyo.ConstraintList()
        self.model.c_dcm_site_2 = pyo.ConstraintList()

        # DCM activation tracking
        for period in self.c.time_periods:
            period_idx, hour = parse_period_hour(period)
            if hour == 0:
                continue

            items = []
            for asset_id in self.c.assets:
                dcm_program = f'{asset_id}_{ProgramType.DCM.value}'
                if dcm_program not in self.c.asset_programs:
                    continue

                if self.c.dcm_chain_enabled and self.c.dcm_chain[asset_id][period] == 0:
                    continue

                items.append(self.model.x[dcm_program, period])

                # Include ECON for same datetime
                econ_program = f'{asset_id}_{ProgramType.ECON.value}'
                if econ_program in self.c.asset_programs:
                    econ_period = self.c.datetime_to_period[(
                        ProgramType.ECON.value,
                        period_idx,
                        self.c.period_to_datetime[(ProgramType.DCM.value, period)]
                    )]
                    items.append(self.model.x[econ_program, econ_period])

            if len(items) > 0:
                self.model.c_dcm_site_1.add(
                    expr=self.c.dcm_per_period[period] * self.model.y[period] <= sum(items)
                )

        # Individual DCM requires site activation
        for asset_id in self.c.assets:
            dcm_program = f'{asset_id}_{ProgramType.DCM.value}'
            if dcm_program not in self.c.asset_programs:
                continue

            for period in self.c.time_periods:
                _, hour = parse_period_hour(period)
                if hour == 0 or hour == 1:
                    continue

                self.model.c_dcm_site_2.add(
                    expr=self.model.x[dcm_program, period] <= self.model.y[period]
                )

        # DCM consecutive hours constraint
        def dcm_consecutive_rule(model, time_period):
            if time_period.endswith('_1') or time_period == NO_HOUR_VALUE:
                return pyo.Constraint.Skip

            period_num, hour_num = parse_period_hour(time_period)
            return model.y[time_period] <= model.y[f'{period_num}_{hour_num - 1}']

        self.model.c_dcm_consec = pyo.Constraint(
            self.c.time_periods,
            rule=dcm_consecutive_rule
        )

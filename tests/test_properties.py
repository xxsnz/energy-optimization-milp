"""Property-based tests: solver output must satisfy model invariants for any input."""

import json

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from energy_optimizer import EnergyResourceOptimizer, OptimizerConfig

CAPACITY_KW = 100.0
BENEFIT_VALUES = st.floats(min_value=0.0, max_value=100.0, allow_nan=False).map(
    lambda x: round(x, 2)
)


@st.composite
def battery_inputs(draw):
    """A single battery with ECON and FR benefits over one period."""
    hours_count = draw(st.integers(min_value=2, max_value=5))
    econ_benefits = draw(
        st.lists(BENEFIT_VALUES, min_size=hours_count, max_size=hours_count)
    )
    fr_benefits = draw(
        st.lists(BENEFIT_VALUES, min_size=hours_count, max_size=hours_count)
    )
    fr_percent = draw(
        st.floats(min_value=0.1, max_value=1.0, allow_nan=False).map(lambda x: round(x, 2))
    )
    budget_hours = draw(
        st.floats(min_value=0.5, max_value=4.0, allow_nan=False).map(lambda x: round(x, 2))
    )

    def hour_entries(benefits):
        return [
            {
                "Hour": h + 1,
                "Benefit": benefits[h],
                "DateTime": f"01/01/2023 0{h}:00:00",
            }
            for h in range(hours_count)
        ]

    return {
        "input": {
            "ExcludeFirstDcmMonth": False,
            "Resources": [
                {
                    "ResourceId": "prop-battery",
                    "Capacity": CAPACITY_KW,
                    "FrPercent": fr_percent,
                    "Type": "BT",
                    "HourLimit": 0,
                    "FirstPeriodHourLimit": None,
                    "KwhLimit": -CAPACITY_KW * budget_hours,
                    "FuelCost": 0.0,
                    "BtEfficiency": 0.95,
                    "BtECost": 0.0,
                    "ProgramAnnualBenefits": {
                        "econ": {"MonthBenefits": [{"HourBenefits": hour_entries(econ_benefits)}]},
                        "fr": {"MonthBenefits": [{"HourBenefits": hour_entries(fr_benefits)}]},
                    },
                }
            ],
            "MonthlyLoads": [
                {
                    "Loads": [
                        {
                            "Hour": h + 1,
                            "Kw": 50.0,
                            "UtilityRate": 0.1,
                            "DcmChargeRate": 0.0,
                            "EconLoadKw": 50.0,
                            "DateTime": f"2023-01-01T0{h}:00:00",
                        }
                        for h in range(hours_count)
                    ]
                }
            ],
            "DcmData": [[]],
        },
        "econ_benefits": econ_benefits,
        "fr_benefits": fr_benefits,
        "fr_percent": fr_percent,
        "budget_hours": budget_hours,
    }


class TestSolutionInvariants:
    """Every solution the optimizer produces must satisfy these invariants."""

    @settings(
        max_examples=20,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    @given(case=battery_inputs())
    def test_solution_invariants(self, case, tmp_path_factory):
        tmp_path = tmp_path_factory.mktemp("prop")
        input_file = tmp_path / "prop_input.json"
        input_file.write_text(json.dumps(case["input"]))

        config = OptimizerConfig.from_input_file(str(input_file))
        output_path = EnergyResourceOptimizer(config).run()

        with open(output_path) as f:
            solution = json.load(f)

        participation = solution["Resources"][0]["ProgramAnnualParticipation"]
        econ = participation["econ"]["MonthParticipation"][0]
        fr = participation["fr"]["MonthParticipation"][0]

        # 1. ECON and FR are mutually exclusive per hour
        assert not set(econ["ChosenHours"]) & set(fr["ChosenHours"])

        # 2. Weighted usage stays within the battery's energy budget
        usage = econ["TotalHours"] + case["fr_percent"] * fr["TotalHours"]
        assert usage <= case["budget_hours"] + 1e-9

        # 3. Reported benefit equals the sum of the chosen hours' input benefits
        expected_econ = sum(case["econ_benefits"][h] for h in econ["ChosenHours"])
        expected_fr = sum(case["fr_benefits"][h] for h in fr["ChosenHours"])
        assert econ["Benefit"] == pytest.approx(expected_econ)
        assert fr["Benefit"] == pytest.approx(expected_fr)

        # 4. A chosen hour's program must dominate the other program there
        for h in econ["ChosenHours"]:
            assert case["econ_benefits"][h] > case["fr_benefits"][h]
        for h in fr["ChosenHours"]:
            assert case["fr_benefits"][h] >= case["econ_benefits"][h]

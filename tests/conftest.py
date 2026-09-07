from pathlib import Path

import pytest


@pytest.fixture
def minimal_input_data():
    """Minimal valid input for basic testing"""
    return {
        "ExcludeFirstDcmMonth": False,
        "DcmOptimizationRequest": False,
        "SupportsRollingPeriods": False,
        "Resources": [
            {
                "ResourceId": "test-battery-1",
                "Capacity": 100.0,
                "FrPercent": 0.5,
                "Type": "BT",
                "HourLimit": 0,
                "FirstPeriodHourLimit": None,
                "KwhLimit": -500.0,
                "FuelCost": 0.0,
                "BtEfficiency": 0.95,
                "BtECost": 0.0,
                "ProgramAnnualBenefits": {
                    "econ": {
                        "MonthBenefits": [
                            {
                                "HourBenefits": [
                                    {"Hour": 1, "Benefit": 10.0, "DateTime": "01/01/2023 00:00:00"},
                                    {"Hour": 2, "Benefit": 15.0, "DateTime": "01/01/2023 01:00:00"},
                                    {"Hour": 3, "Benefit": 20.0, "DateTime": "01/01/2023 02:00:00"},
                                    {"Hour": 4, "Benefit": 12.0, "DateTime": "01/01/2023 03:00:00"},
                                ]
                            }
                        ]
                    },
                    "fr": {
                        "MonthBenefits": [
                            {
                                "HourBenefits": [
                                    {"Hour": 1, "Benefit": 8.0, "DateTime": "01/01/2023 00:00:00"},
                                    {"Hour": 2, "Benefit": 18.0, "DateTime": "01/01/2023 01:00:00"},
                                    {"Hour": 3, "Benefit": 16.0, "DateTime": "01/01/2023 02:00:00"},
                                    {"Hour": 4, "Benefit": 10.0, "DateTime": "01/01/2023 03:00:00"},
                                ]
                            }
                        ]
                    }
                }
            }
        ],
        "MonthlyLoads": [
            {
                "Loads": [
                    {"Hour": 1, "Kw": 50.0, "UtilityRate": 0.1, "DcmChargeRate": 0.0, "EconLoadKw": 50.0, "DateTime": "2023-01-01T00:00:00"},
                    {"Hour": 2, "Kw": 55.0, "UtilityRate": 0.12, "DcmChargeRate": 0.0, "EconLoadKw": 55.0, "DateTime": "2023-01-01T01:00:00"},
                    {"Hour": 3, "Kw": 60.0, "UtilityRate": 0.15, "DcmChargeRate": 0.0, "EconLoadKw": 60.0, "DateTime": "2023-01-01T02:00:00"},
                    {"Hour": 4, "Kw": 52.0, "UtilityRate": 0.11, "DcmChargeRate": 0.0, "EconLoadKw": 52.0, "DateTime": "2023-01-01T03:00:00"},
                ]
            }
        ],
        "DcmData": [[]]
    }


@pytest.fixture
def multi_asset_input_data():
    """Input with multiple asset types"""
    return {
        "ExcludeFirstDcmMonth": False,
        "DcmOptimizationRequest": False,
        "SupportsRollingPeriods": False,
        "Resources": [
            {
                "ResourceId": "battery-1",
                "Capacity": 100.0,
                "FrPercent": 0.5,
                "Type": "BT",
                "HourLimit": 10,
                "FirstPeriodHourLimit": None,
                "KwhLimit": -500.0,
                "FuelCost": 0.0,
                "BtEfficiency": 0.95,
                "BtECost": 0.05,
                "ProgramAnnualBenefits": {
                    "econ": {
                        "MonthBenefits": [
                            {
                                "HourBenefits": [
                                    {"Hour": 1, "Benefit": 10.0, "DateTime": "01/01/2023 00:00:00"},
                                    {"Hour": 2, "Benefit": 15.0, "DateTime": "01/01/2023 01:00:00"},
                                    {"Hour": 3, "Benefit": 20.0, "DateTime": "01/01/2023 02:00:00"},
                                ]
                            }
                        ]
                    },
                    "fr": {
                        "MonthBenefits": [
                            {
                                "HourBenefits": [
                                    {"Hour": 1, "Benefit": 8.0, "DateTime": "01/01/2023 00:00:00"},
                                    {"Hour": 2, "Benefit": 18.0, "DateTime": "01/01/2023 01:00:00"},
                                    {"Hour": 3, "Benefit": 16.0, "DateTime": "01/01/2023 02:00:00"},
                                ]
                            }
                        ]
                    }
                }
            },
            {
                "ResourceId": "generator-1",
                "Capacity": 150.0,
                "FrPercent": 0.3,
                "Type": "GN",
                "HourLimit": 20,
                "FirstPeriodHourLimit": None,
                "KwhLimit": 0,
                "FuelCost": 0.08,
                "BtEfficiency": 0.0,
                "BtECost": 0.0,
                "ProgramAnnualBenefits": {
                    "econ": {
                        "MonthBenefits": [
                            {
                                "HourBenefits": [
                                    {"Hour": 1, "Benefit": 12.0, "DateTime": "01/01/2023 00:00:00"},
                                    {"Hour": 2, "Benefit": 14.0, "DateTime": "01/01/2023 01:00:00"},
                                    {"Hour": 3, "Benefit": 22.0, "DateTime": "01/01/2023 02:00:00"},
                                ]
                            }
                        ]
                    },
                    "fr": {
                        "MonthBenefits": [
                            {
                                "HourBenefits": [
                                    {"Hour": 1, "Benefit": 9.0, "DateTime": "01/01/2023 00:00:00"},
                                    {"Hour": 2, "Benefit": 11.0, "DateTime": "01/01/2023 01:00:00"},
                                    {"Hour": 3, "Benefit": 13.0, "DateTime": "01/01/2023 02:00:00"},
                                ]
                            }
                        ]
                    }
                }
            }
        ],
        "MonthlyLoads": [
            {
                "Loads": [
                    {"Hour": 1, "Kw": 50.0, "UtilityRate": 0.1, "DcmChargeRate": 0.0, "EconLoadKw": 50.0, "DateTime": "2023-01-01T00:00:00"},
                    {"Hour": 2, "Kw": 55.0, "UtilityRate": 0.12, "DcmChargeRate": 0.0, "EconLoadKw": 55.0, "DateTime": "2023-01-01T01:00:00"},
                    {"Hour": 3, "Kw": 60.0, "UtilityRate": 0.15, "DcmChargeRate": 0.0, "EconLoadKw": 60.0, "DateTime": "2023-01-01T02:00:00"},
                ]
            }
        ],
        "DcmData": [[]]
    }


@pytest.fixture
def dcm_input_data():
    """Input with DCM optimization"""
    return {
        "ExcludeFirstDcmMonth": False,
        "DcmOptimizationRequest": True,
        "SupportsRollingPeriods": False,
        "Resources": [
            {
                "ResourceId": "battery-dcm",
                "Capacity": 200.0,
                "FrPercent": 0.0,
                "Type": "BT",
                "HourLimit": 0,
                "FirstPeriodHourLimit": None,
                "KwhLimit": -1000.0,
                "FuelCost": 0.0,
                "BtEfficiency": 0.95,
                "BtECost": 0.0,
                "ProgramAnnualBenefits": {
                    "dcm": {
                        "MonthBenefits": [
                            {
                                "HourBenefits": [
                                    {"Hour": 1, "Benefit": 50.0, "DemandLimit": 200.0, "DateTime": "01/01/2023 10:00:00"},
                                    {"Hour": 2, "Benefit": 60.0, "DemandLimit": 200.0, "DateTime": "01/01/2023 14:00:00"},
                                    {"Hour": 3, "Benefit": 45.0, "DemandLimit": 200.0, "DateTime": "01/01/2023 18:00:00"},
                                ]
                            }
                        ]
                    }
                }
            }
        ],
        "MonthlyLoads": [
            {
                "Loads": [
                    {"Hour": 1, "Kw": 180.0, "UtilityRate": 0.1, "DcmChargeRate": 0.05, "EconLoadKw": 180.0, "DateTime": "2023-01-01T10:00:00"},
                    {"Hour": 2, "Kw": 190.0, "UtilityRate": 0.12, "DcmChargeRate": 0.06, "EconLoadKw": 190.0, "DateTime": "2023-01-01T14:00:00"},
                    {"Hour": 3, "Kw": 175.0, "UtilityRate": 0.15, "DcmChargeRate": 0.04, "EconLoadKw": 175.0, "DateTime": "2023-01-01T18:00:00"},
                ]
            }
        ],
        "DcmData": [
            [
                {"AssetId": "battery-dcm", "Hour": 1, "Benefit": 50.0, "KwRange": 20.0, "Kw": 180.0},
                {"AssetId": "battery-dcm", "Hour": 2, "Benefit": 60.0, "KwRange": 25.0, "Kw": 190.0},
                {"AssetId": "battery-dcm", "Hour": 3, "Benefit": 45.0, "KwRange": 20.0, "Kw": 175.0},
            ]
        ]
    }


@pytest.fixture
def example_case1_path():
    """Path to example case1.json"""
    return Path(__file__).parent.parent / "examples" / "case1.json"


@pytest.fixture
def example_case2_path():
    """Path to example case2.json"""
    return Path(__file__).parent.parent / "examples" / "case2.json"


@pytest.fixture
def temp_output_dir(tmp_path):
    """Temporary directory for test outputs"""
    return tmp_path

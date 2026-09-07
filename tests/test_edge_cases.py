import json
from pathlib import Path

import pytest

from energy_optimizer import EnergyResourceOptimizer, OptimizerConfig


class TestEdgeCases:
    """Tests for edge cases and error handling"""

    def test_missing_input_file(self, temp_output_dir):
        """Test handling of missing input file"""
        input_file = temp_output_dir / "nonexistent.json"

        config = OptimizerConfig.from_input_file(str(input_file))
        optimizer = EnergyResourceOptimizer(config)

        # Should raise FileNotFoundError when trying to run
        with pytest.raises(FileNotFoundError):
            optimizer.run()

    def test_invalid_json(self, temp_output_dir):
        """Test handling of invalid JSON"""
        input_file = temp_output_dir / "invalid.json"
        input_file.write_text("{ invalid json }")

        config = OptimizerConfig.from_input_file(str(input_file))
        optimizer = EnergyResourceOptimizer(config)

        # Should raise ValueError wrapping JSONDecodeError
        with pytest.raises(ValueError, match="Invalid JSON"):
            optimizer.run()

    def test_empty_resources(self, temp_output_dir):
        """Test handling of empty resources list"""
        data = {
            "ExcludeFirstDcmMonth": False,
            "Resources": [],
            "MonthlyLoads": [],
            "DcmData": []
        }

        input_file = temp_output_dir / "empty_resources.json"
        with open(input_file, 'w') as f:
            json.dump(data, f)

        config = OptimizerConfig.from_input_file(str(input_file))
        optimizer = EnergyResourceOptimizer(config)

        # Should complete but produce empty solution
        output_path = optimizer.run()
        assert Path(output_path).exists()

    def test_zero_capacity_asset(self, minimal_input_data, temp_output_dir):
        """Test handling of asset with zero capacity"""
        minimal_input_data["Resources"][0]["Capacity"] = 0.0

        input_file = temp_output_dir / "zero_capacity.json"
        with open(input_file, 'w') as f:
            json.dump(minimal_input_data, f)

        config = OptimizerConfig.from_input_file(str(input_file))
        optimizer = EnergyResourceOptimizer(config)

        # Zero-capacity battery is rejected with a clear error
        with pytest.raises(ValueError, match="zero capacity"):
            optimizer.run()

    def test_zero_benefits(self, temp_output_dir):
        """Test optimization with all zero benefits"""
        data = {
            "ExcludeFirstDcmMonth": False,
            "Resources": [{
                "ResourceId": "test-1",
                "Capacity": 100.0,
                "FrPercent": 0.0,
                "Type": "BT",
                "HourLimit": 0,
                "FirstPeriodHourLimit": None,
                "KwhLimit": -500.0,
                "FuelCost": 0.0,
                "BtEfficiency": 1.0,
                "BtECost": 0.0,
                "ProgramAnnualBenefits": {
                    "econ": {"MonthBenefits": [
                        {"HourBenefits": [
                            {"Hour": 1, "Benefit": 0.0, "DateTime": "01/01/2023 00:00:00"},
                            {"Hour": 2, "Benefit": 0.0, "DateTime": "01/01/2023 01:00:00"}
                        ]}
                    ]}
                }
            }],
            "MonthlyLoads": [
                {"Loads": [
                    {"Hour": 1, "Kw": 50.0, "UtilityRate": 0.1, "DcmChargeRate": 0.0, "EconLoadKw": 50.0, "DateTime": "2023-01-01T00:00:00"},
                    {"Hour": 2, "Kw": 55.0, "UtilityRate": 0.1, "DcmChargeRate": 0.0, "EconLoadKw": 55.0, "DateTime": "2023-01-01T01:00:00"}
                ]}
            ],
            "DcmData": [[]]
        }

        input_file = temp_output_dir / "zero_benefits.json"
        with open(input_file, 'w') as f:
            json.dump(data, f)

        config = OptimizerConfig.from_input_file(str(input_file))
        optimizer = EnergyResourceOptimizer(config)

        # Should complete successfully
        output_path = optimizer.run()
        assert Path(output_path).exists()

    def test_missing_required_fields(self, temp_output_dir):
        """Test handling of missing required resource fields"""
        data = {
            "MonthlyLoads": [],
            "DcmData": []
        }

        input_file = temp_output_dir / "missing_fields.json"
        with open(input_file, 'w') as f:
            json.dump(data, f)

        config = OptimizerConfig.from_input_file(str(input_file))
        optimizer = EnergyResourceOptimizer(config)

        # Should raise ValueError for missing fields
        with pytest.raises(ValueError, match="Missing required fields"):
            optimizer.run()

    def test_single_hour_period(self, temp_output_dir):
        """Test optimization with only one hour"""
        data = {
            "ExcludeFirstDcmMonth": False,
            "Resources": [{
                "ResourceId": "test-1",
                "Capacity": 100.0,
                "FrPercent": 0.0,
                "Type": "BT",
                "HourLimit": 0,
                "FirstPeriodHourLimit": None,
                "KwhLimit": -500.0,
                "FuelCost": 0.0,
                "BtEfficiency": 1.0,
                "BtECost": 0.0,
                "ProgramAnnualBenefits": {
                    "econ": {"MonthBenefits": [
                        {"HourBenefits": [
                            {"Hour": 1, "Benefit": 10.0, "DateTime": "01/01/2023 00:00:00"}
                        ]}
                    ]}
                }
            }],
            "MonthlyLoads": [
                {"Loads": [
                    {"Hour": 1, "Kw": 50.0, "UtilityRate": 0.1, "DcmChargeRate": 0.0, "EconLoadKw": 50.0, "DateTime": "2023-01-01T00:00:00"}
                ]}
            ],
            "DcmData": [[]]
        }

        input_file = temp_output_dir / "single_hour.json"
        with open(input_file, 'w') as f:
            json.dump(data, f)

        config = OptimizerConfig.from_input_file(str(input_file))
        optimizer = EnergyResourceOptimizer(config)

        output_path = optimizer.run()
        assert Path(output_path).exists()

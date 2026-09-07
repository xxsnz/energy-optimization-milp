import json
from pathlib import Path

import pytest

from energy_optimizer import EnergyResourceOptimizer, OptimizationStrategy, OptimizerConfig


class TestIntegration:
    """Integration tests for complete optimization workflow"""

    def test_end_to_end_optimization(self, minimal_input_data, temp_output_dir):
        """Test complete optimization from input to output"""
        input_file = temp_output_dir / "test_input.json"
        with open(input_file, 'w') as f:
            json.dump(minimal_input_data, f)

        config = OptimizerConfig.from_input_file(str(input_file))
        optimizer = EnergyResourceOptimizer(config)

        output_path = optimizer.run()

        assert output_path is not None
        assert Path(output_path).exists()

        with open(output_path) as f:
            solution = json.load(f)
            assert isinstance(solution, dict)
            assert "Resources" in solution

    def test_optimization_with_example_case1(self, example_case1_path):
        """Test optimization with real example case1.json"""
        if not example_case1_path.exists():
            pytest.skip("case1.json not found")

        config = OptimizerConfig.from_input_file(str(example_case1_path))
        optimizer = EnergyResourceOptimizer(config)

        output_path = optimizer.run()

        with open(output_path) as f:
            solution = json.load(f)
            assert "Resources" in solution
            assert len(solution["Resources"]) > 0

    def test_optimization_with_example_case2(self, example_case2_path):
        """Test optimization with real example case2.json"""
        if not example_case2_path.exists():
            pytest.skip("case2.json not found")

        config = OptimizerConfig.from_input_file(str(example_case2_path))
        optimizer = EnergyResourceOptimizer(config)

        output_path = optimizer.run()

        with open(output_path) as f:
            solution = json.load(f)
            assert "Resources" in solution
            assert len(solution["Resources"]) > 0

    def test_solution_file_creation(self, minimal_input_data, temp_output_dir):
        """Test that solution file is created correctly"""
        input_file = temp_output_dir / "test_input.json"
        output_file = temp_output_dir / "test_input_sln.json"

        with open(input_file, 'w') as f:
            json.dump(minimal_input_data, f)

        config = OptimizerConfig.from_input_file(str(input_file))
        optimizer = EnergyResourceOptimizer(config)
        optimizer.run()

        assert output_file.exists()

        with open(output_file) as f:
            solution = json.load(f)
            assert isinstance(solution, dict)

    def test_optimization_preserves_resource_count(self, multi_asset_input_data, temp_output_dir):
        """Test that all resources are in the solution"""
        input_file = temp_output_dir / "multi_asset.json"
        with open(input_file, 'w') as f:
            json.dump(multi_asset_input_data, f)

        config = OptimizerConfig.from_input_file(str(input_file))
        optimizer = EnergyResourceOptimizer(config)
        output_path = optimizer.run()

        with open(output_path) as f:
            solution = json.load(f)
            assert len(solution["Resources"]) == len(multi_asset_input_data["Resources"])

    def test_optimization_with_dcm(self, dcm_input_data, temp_output_dir):
        """Test optimization with DCM enabled"""
        input_file = temp_output_dir / "dcm_test.json"
        with open(input_file, 'w') as f:
            json.dump(dcm_input_data, f)

        config = OptimizerConfig.from_input_file(str(input_file))
        optimizer = EnergyResourceOptimizer(config)
        output_path = optimizer.run()

        with open(output_path) as f:
            solution = json.load(f)
            assert "Dcm" in solution
            assert "DcmHrs" in solution

    def test_optimization_respects_capacity_limits(self, minimal_input_data, temp_output_dir):
        """Test that solution respects the battery's energy budget"""
        # Budget of abs(-200)/100 = 2 hour-equivalents; 4 hours are available,
        # so the limit is binding. FR hours count at FrPercent (0.5).
        minimal_input_data["Resources"][0]["KwhLimit"] = -200.0

        input_file = temp_output_dir / "capacity_test.json"
        with open(input_file, 'w') as f:
            json.dump(minimal_input_data, f)

        config = OptimizerConfig.from_input_file(str(input_file))
        optimizer = EnergyResourceOptimizer(config)
        output_path = optimizer.run()

        with open(output_path) as f:
            solution = json.load(f)

        participation = solution["Resources"][0]["ProgramAnnualParticipation"]
        econ_hours = sum(m["TotalHours"] for m in participation["econ"]["MonthParticipation"])
        fr_hours = sum(m["TotalHours"] for m in participation["fr"]["MonthParticipation"])

        # The battery must actually participate, and weighted usage must
        # stay within the 2-hour-equivalent budget
        assert econ_hours + fr_hours > 0
        assert econ_hours + 0.5 * fr_hours <= 2.0

    def test_simple_math_strategy_optimization(self, minimal_input_data, temp_output_dir):
        """Test optimization with SIMPLE_MATH strategy"""
        input_file = temp_output_dir / "simple_math.json"
        with open(input_file, 'w') as f:
            json.dump(minimal_input_data, f)

        config = OptimizerConfig.from_input_file(str(input_file))
        config.strategy = OptimizationStrategy.SIMPLE_MATH
        optimizer = EnergyResourceOptimizer(config)
        output_path = optimizer.run()

        with open(output_path) as f:
            solution = json.load(f)
            assert "Resources" in solution

    def test_asset_level_strategy_optimization(self, minimal_input_data, temp_output_dir):
        """Test optimization with ASSET_LEVEL strategy"""
        input_file = temp_output_dir / "asset_level.json"
        with open(input_file, 'w') as f:
            json.dump(minimal_input_data, f)

        config = OptimizerConfig.from_input_file(str(input_file))
        config.strategy = OptimizationStrategy.ASSET_LEVEL
        optimizer = EnergyResourceOptimizer(config)
        output_path = optimizer.run()

        with open(output_path) as f:
            solution = json.load(f)
            assert "Resources" in solution

    def test_optimization_with_battery(self, minimal_input_data, temp_output_dir):
        """Test optimization with battery asset"""
        minimal_input_data["Resources"][0]["Type"] = "BT"

        input_file = temp_output_dir / "battery_test.json"
        with open(input_file, 'w') as f:
            json.dump(minimal_input_data, f)

        config = OptimizerConfig.from_input_file(str(input_file))
        optimizer = EnergyResourceOptimizer(config)
        output_path = optimizer.run()

        with open(output_path) as f:
            solution = json.load(f)
            assert solution["Resources"][0]["Type"] == "BT"

    def test_optimization_with_generator(self, minimal_input_data, temp_output_dir):
        """Test optimization with generator asset"""
        minimal_input_data["Resources"][0]["Type"] = "GN"
        minimal_input_data["Resources"][0]["FuelCost"] = 0.05

        input_file = temp_output_dir / "generator_test.json"
        with open(input_file, 'w') as f:
            json.dump(minimal_input_data, f)

        config = OptimizerConfig.from_input_file(str(input_file))
        optimizer = EnergyResourceOptimizer(config)
        output_path = optimizer.run()

        with open(output_path) as f:
            solution = json.load(f)
            assert solution["Resources"][0]["Type"] == "GN"

    def test_optimization_with_load(self, minimal_input_data, temp_output_dir):
        """Test optimization with load asset"""
        minimal_input_data["Resources"][0]["Type"] = "LD"

        input_file = temp_output_dir / "load_test.json"
        with open(input_file, 'w') as f:
            json.dump(minimal_input_data, f)

        config = OptimizerConfig.from_input_file(str(input_file))
        optimizer = EnergyResourceOptimizer(config)
        output_path = optimizer.run()

        with open(output_path) as f:
            solution = json.load(f)
            assert solution["Resources"][0]["Type"] == "LD"

    def test_custom_solver_timeout(self, minimal_input_data, temp_output_dir):
        """Test optimization with custom solver timeout"""
        input_file = temp_output_dir / "timeout_test.json"
        with open(input_file, 'w') as f:
            json.dump(minimal_input_data, f)

        config = OptimizerConfig.from_input_file(str(input_file))
        config.max_execution_time = 30
        optimizer = EnergyResourceOptimizer(config)
        output_path = optimizer.run()

        assert Path(output_path).exists()

    def test_custom_mip_gap(self, minimal_input_data, temp_output_dir):
        """Test optimization with custom MIP gap"""
        input_file = temp_output_dir / "mip_gap_test.json"
        with open(input_file, 'w') as f:
            json.dump(minimal_input_data, f)

        config = OptimizerConfig.from_input_file(str(input_file))
        config.mip_gap = 0.05
        optimizer = EnergyResourceOptimizer(config)
        output_path = optimizer.run()

        assert Path(output_path).exists()

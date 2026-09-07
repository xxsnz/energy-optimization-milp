import pytest

from energy_optimizer import OptimizerConfig, SolverName, detect_solver


class TestOptimizerConfig:
    """Tests for OptimizerConfig class"""

    def test_from_input_file_basic(self, temp_output_dir):
        """Test basic config creation from input file"""
        input_file = temp_output_dir / "test_input.json"
        input_file.write_text("{}")

        config = OptimizerConfig.from_input_file(str(input_file))

        assert config.input_path == input_file
        assert config.max_execution_time == 200
        assert config.mip_gap == 0.01

    def test_solver_discovery(self, temp_output_dir):
        """Test that an available solver is discovered"""
        input_file = temp_output_dir / "test.json"
        input_file.write_text("{}")

        config = OptimizerConfig.from_input_file(str(input_file))

        assert config.solver_name in (SolverName.HIGHS, SolverName.GLPK)
        if config.solver_name == SolverName.GLPK:
            assert config.solver_path is not None
            assert "glpsol" in config.solver_path

    def test_output_path_generation(self, temp_output_dir):
        """Test output file name generation"""
        input_file = temp_output_dir / "test_input.json"
        input_file.write_text("{}")

        config = OptimizerConfig.from_input_file(str(input_file))

        expected_output = temp_output_dir / "test_input_sln.json"
        assert config.output_path == expected_output

    def test_output_path_with_suffix(self, temp_output_dir):
        """Test output file with _sln suffix"""
        input_file = temp_output_dir / "test.json"
        input_file.write_text("{}")

        config = OptimizerConfig.from_input_file(str(input_file))

        assert str(config.output_path).endswith("_sln.json")

    def test_custom_parameters(self, temp_output_dir):
        """Test config with custom timeout and mip_gap"""
        input_file = temp_output_dir / "test.json"
        input_file.write_text("{}")

        config = OptimizerConfig(
            input_path=input_file,
            output_path=input_file.with_stem(f"{input_file.stem}_sln"),
            solver_name=SolverName.HIGHS,
            max_execution_time=300,
            mip_gap=0.05
        )

        assert config.max_execution_time == 300
        assert config.mip_gap == 0.05

    def test_missing_solver_raises_error(self, monkeypatch, temp_output_dir):
        """Test handling when no solver is available"""
        input_file = temp_output_dir / "test.json"
        input_file.write_text("{}")

        monkeypatch.setattr("importlib.util.find_spec", lambda name: None)
        monkeypatch.setattr("shutil.which", lambda name: None)

        with pytest.raises(RuntimeError, match="No MILP solver found"):
            OptimizerConfig.from_input_file(str(input_file))

    def test_invalid_time_limit_rejected(self, temp_output_dir):
        """Test that a non-positive time limit is rejected"""
        input_file = temp_output_dir / "test.json"
        input_file.write_text("{}")

        with pytest.raises(ValueError, match="max_execution_time must be positive"):
            OptimizerConfig.from_input_file(str(input_file), max_execution_time=-1)

    def test_invalid_mip_gap_rejected(self, temp_output_dir):
        """Test that a negative or non-finite MIP gap is rejected"""
        input_file = temp_output_dir / "test.json"
        input_file.write_text("{}")

        with pytest.raises(ValueError, match="mip_gap must be"):
            OptimizerConfig.from_input_file(str(input_file), mip_gap=-0.01)

        with pytest.raises(ValueError, match="mip_gap must be"):
            OptimizerConfig.from_input_file(str(input_file), mip_gap=float("nan"))

    def test_explicit_solver_preference(self, monkeypatch):
        """Test that an explicit but unavailable solver raises an error"""
        monkeypatch.setattr("shutil.which", lambda name: None)

        with pytest.raises(RuntimeError, match="GLPK solver requested"):
            detect_solver(SolverName.GLPK.value)

    def test_missing_input_file(self, temp_output_dir):
        """Test handling of missing input file"""
        # Don't create the file, just reference it
        input_file = temp_output_dir / "nonexistent.json"

        # Should still create config (file check happens at load time)
        config = OptimizerConfig.from_input_file(str(input_file))
        assert config.input_path == input_file

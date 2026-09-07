# Test Suite

Tests cover the full optimization pipeline, organized by concern:

| File | Focus |
|------|-------|
| `test_config.py` | `OptimizerConfig`: solver auto-detection, parameter validation, output path generation |
| `test_data_extraction.py` | `ResourceDataExtractor`: asset properties, benefit mapping, time periods, mutual exclusivity detection |
| `test_integration.py` | End-to-end runs: real example cases, all asset types, strategies, solver options |
| `test_edge_cases.py` | Missing files, invalid JSON, empty inputs, zero capacity/benefits, single-hour periods |
| `test_properties.py` | Property-based (Hypothesis): random inputs must always yield solutions respecting exclusivity, energy budgets, dominance, and benefit accounting |

## Running

```bash
pip install -e ".[dev]"

pytest                       # all tests
pytest tests/test_integration.py -v
pytest --cov=energy_optimizer --cov-report=html
pytest --lf                  # only tests that failed last run
```

No system solver is needed — tests run against HiGHS, which installs with the
package.

## Fixtures (`conftest.py`)

- `minimal_input_data` — single battery with ECON/FR programs
- `multi_asset_input_data` — battery + generator
- `dcm_input_data` — DCM optimization scenario
- `example_case1_path` / `example_case2_path` — real inputs from `examples/`
- `temp_output_dir` — per-test temporary directory

## Adding tests

Follow the existing arrange/act/assert pattern: write input JSON to
`temp_output_dir`, build a config with `OptimizerConfig.from_input_file`, run
`EnergyResourceOptimizer`, and assert on the solution file contents.

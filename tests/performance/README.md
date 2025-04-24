# Performance Tests for ia-sdk

This directory contains performance tests that measure and benchmark the ia-sdk's performance characteristics. These tests are designed to help identify performance bottlenecks, track performance changes over time, and establish baseline expectations for production use.

## Test Categories

The performance tests are organized into the following categories:

- **Throughput Tests**: Measure data processing speed and throughput under various conditions
- **Latency Tests**: Measure response time and latency, especially under load
- **Memory Tests**: Measure memory consumption patterns and efficiency
- **Scalability Tests**: Measure how performance scales with increasing data size or complexity

## Running Performance Tests

Performance tests are resource-intensive and generally take longer to run than other tests. They are not included in the standard test suite and must be run explicitly:

```bash
# Run all performance tests
cd tests/performance
pytest -xvs

# Run a specific category of tests
pytest -xvs test_throughput.py

# Run a specific test
pytest -xvs test_throughput.py::test_observation_throughput
```

## Configuration

You can configure performance tests using environment variables:

```bash
# Number of iterations for each test (higher = more accurate but slower)
export PERF_TEST_ITERATIONS=10

# Data size multiplier (adjust for your hardware capabilities)
export PERF_TEST_SIZE_MULTIPLIER=1.0

# Whether to save performance results to files
export PERF_TEST_SAVE_RESULTS=true

# Directory to save performance results
export PERF_TEST_RESULTS_DIR="./results"
```

## Interpreting Results

Performance tests produce the following metrics:

1. **Mean**: Average value across all test iterations
2. **Median**: Middle value in the sorted results (less affected by outliers)
3. **Standard Deviation**: Measure of result variability
4. **Min/Max**: Minimum and maximum values observed
5. **Percentiles**: 95th and 99th percentile values (useful for SLA planning)

Results are printed to the console and optionally saved to CSV files for tracking over time.

## Adding New Performance Tests

When adding new performance tests:

1. Use the appropriate test category file or create a new one if needed
2. Follow the pattern of existing tests: setup, measurement, cleanup
3. Use the provided performance fixtures for consistent measurement
4. Include baseline expectations where possible
5. Document any specific hardware/environment requirements

## Benchmark System

Performance results are relative to the system they're run on. Tests include system information in the results to help with interpretation.

To make results more meaningful:

1. Run on isolated systems when possible
2. Run multiple iterations to account for variability
3. Note any other processes that might be competing for resources
4. Include system specifications when sharing results

## Performance Regression Testing

The performance test suite can be used for regression testing by:

1. Establishing a performance baseline on your target system
2. Running the tests regularly (e.g., after significant changes)
3. Comparing results against the baseline
4. Investigating significant deviations

The `--compare-baseline` flag can be used to automatically compare current results with saved baseline results.


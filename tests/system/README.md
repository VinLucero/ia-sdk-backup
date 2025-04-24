# System Tests for ia-sdk

This directory contains system tests that verify the end-to-end functionality of the ia-sdk. Unlike unit and integration tests, system tests validate that the entire system works together as expected in real-world scenarios.

## Test Structure

- `workflows/`: Tests for complete operational workflows
  - `test_basic_workflow.py`: Basic end-to-end workflow tests
  - `test_advanced_workflow.py`: More complex workflow scenarios

## Prerequisites

Before running system tests, ensure that:

1. You have Python 3.8+ installed
2. All dependencies are installed: `pip install -r requirements.txt`
3. Docker is installed and running (for tests that use containerized agents)
4. You have appropriate API keys and access to required services
5. Environment variables are set properly (see Configuration section)

## Configuration

The system tests can be configured using environment variables:

```bash
# Required environment variables
export GAIUS_API_KEY="your-api-key"
export GAIUS_DOMAIN="your-domain"

# Optional configuration
export GAIUS_TEST_TIMEOUT=300  # Timeout in seconds (default: 300)
export GAIUS_TEST_CLEANUP=true  # Whether to clean up resources after tests (default: true)
export GAIUS_TEST_LEVEL=full    # Test level: minimal, standard, or full (default: standard)
```

You can also create a `.env` file in the `tests/system` directory with these variables.

## Running the Tests

To run all system tests:

```bash
cd tests/system
pytest -xvs
```

To run only basic workflow tests:

```bash
pytest -xvs workflows/test_basic_workflow.py
```

To run a specific test:

```bash
pytest -xvs workflows/test_basic_workflow.py::test_agent_initialization_and_connection
```

## Test Tags

Tests are tagged for selective execution:

- `@pytest.mark.basic`: Basic functionality tests
- `@pytest.mark.advanced`: Advanced functionality tests
- `@pytest.mark.slow`: Tests that may take longer to run
- `@pytest.mark.docker`: Tests that require Docker

For example, to run only basic tests:

```bash
pytest -xvs -m basic
```

## Troubleshooting

If you encounter issues with the system tests:

1. Check that all prerequisites are met
2. Verify that environment variables are set correctly
3. Look for detailed error messages in the test output
4. Inspect log files in the `logs/` directory
5. Try running with increased verbosity: `pytest -xvs --log-cli-level=DEBUG`

For persistent issues, please consult the documentation or file an issue in the repository.


# Integration Tests for ia-sdk

This directory contains integration tests for the ia-sdk package. These tests verify that the SDK works correctly with actual running instances of the Gaius agent, including Docker containers and other deployment configurations.

## Test Structure

- `docker/`: Tests specifically for Docker functionality
- Additional directories may be added for other deployment methods

## Running the Tests

### Prerequisites

- Python 3.8 or higher
- Required dependencies (install from the specific test's requirements.txt)
- Docker (for Docker integration tests)

### Docker Integration Tests

1. Install the required dependencies:

```bash
cd tests/integration/docker
pip install -r requirements.txt
```

2. Make sure Docker is running

3. Run the tests:

```bash
pytest -xvs
```

## Notes for Test Development

- Tests should be isolated and not depend on each other
- Tests should clean up after themselves (no leftover containers, etc.)
- Tests should be configurable via environment variables when appropriate
- Tests should use fixtures to reuse code and maintain isolation


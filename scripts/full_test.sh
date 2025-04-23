#!/bin/bash

# Full test of ia-sdk functionality
echo "Running complete ia-sdk test..."

# Create and activate new test environment
python -m venv fresh_test_env
source fresh_test_env/bin/activate

# Install from backup including pandas and all dependencies
pip install --no-index --find-links packages pandas ia-sdk

# Run functionality test
python -c "
from ia.gaius.agent_client import AgentQueryError
from ia.gaius.data_structures import DataFeed

# Test creating a basic data feed
feed = DataFeed(name=\"test_feed\", description=\"Test feed for verification\")
print(f\"Successfully created data feed: {feed.name} - {feed.description}\")"

# Cleanup
deactivate
rm -rf fresh_test_env

echo "Test complete!"

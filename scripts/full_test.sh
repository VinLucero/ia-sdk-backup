#!/bin/bash

# Full test of ia-sdk functionality
echo "Running complete ia-sdk test..."

# Create and activate new test environment
python -m venv fresh_test_env
source fresh_test_env/bin/activate

# Install from backup including all dependencies
pip install --no-index --find-links packages pandas networkx ia-sdk

# Run functionality test
python -c "
from ia.gaius.agent_client import AgentQueryError
from ia.gaius.manager import Agent

# Test creating a basic agent
agent = Agent(name=\"test_agent\", description=\"Test agent for verification\")
print(f\"Successfully created agent: {agent.name} - {agent.description}\")"

# Cleanup
deactivate
rm -rf fresh_test_env

echo "Test complete!"

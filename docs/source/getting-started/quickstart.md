---
title: Quickstart Guide
description: Get up and running with ia-sdk in minutes
author: Documentation Team
date: April 2025
---

# Quickstart Guide

This guide will help you get started with ia-sdk quickly. Follow these simple steps to install the package, create your first agent, and run a basic interaction.

## Prerequisites

Before beginning, make sure you have:

- Python 3.8 or higher installed
- pip package manager
- Access to a terminal or command prompt
- Internet connection for downloading packages

## Installation

Install ia-sdk using pip:

```bash
pip install ia-sdk
```

For development installations with extra tools:

```bash
pip install ia-sdk[dev]
```

Verify your installation:

```bash
python -c "import ia_sdk; print(ia_sdk.__version__)"
```

Expected output:
```
0.4.22
```

## Creating Your First Agent

Here's a simple example to create and interact with an agent:

```python
import ia_sdk
from ia_sdk.client import AgentClient

# Initialize the client
client = AgentClient()

# Create a new agent
agent = client.create_agent(
    name="my-first-agent",
    capabilities=["text-processing", "question-answering"]
)

# Send a query to the agent
response = agent.query("What is the capital of France?")

# Print the response
print(response.content)
```

Expected output:
```
The capital of France is Paris.
```

## Handling Connections and Errors

```python
import ia_sdk
from ia_sdk.client import AgentClient
from ia_sdk.exceptions import ConnectionError

try:
    # Initialize with a timeout for better error handling
    client = AgentClient(timeout=30)
    
    # Test connection
    status = client.check_connection()
    print(f"Connection status: {status}")
    
except ConnectionError as e:
    print(f"Connection failed: {e}")
    # Implement retry or fallback logic
```

## Next Steps

Now that you've created your first agent, you can:

1. Explore more advanced [configuration options](../user_guide/configuration)
2. Learn about [agent capabilities](../user_guide/advanced_usage)
3. Implement [error handling strategies](../troubleshooting/common_issues)
4. Explore the complete [API reference](../api_reference/client)

For a deeper understanding of how ia-sdk works, check out the [technical deep dive](../user_guide/technical-deep-dive) and [practical examples](../user_guide/practical-examples).

## Quick Reference

Common operations:

```python
# List all agents
agents = client.list_agents()

# Get agent by ID
agent = client.get_agent(agent_id="agent-123")

# Update agent configuration
agent.update_config(memory_size=2048, timeout=60)

# Delete an agent
client.delete_agent(agent_id="agent-123")
```

That's it! You're now ready to build applications with ia-sdk.

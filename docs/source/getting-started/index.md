# Getting Started with ia-sdk

## Learning Paths

### New Users

Start here if you're new to ia-sdk:

1. [Installation and Basic Usage](quickstart.md)
2. [Common Patterns](practical-examples.md#basic-operations-pattern)
3. [Error Handling](technical-deep-dive.md#error-handling)

### Intermediate Users

For users familiar with the basics:

1. [Technical Details](technical-deep-dive.md#component-structure)
2. [Advanced Patterns](practical-examples.md#resilient-pattern)
3. [Performance Tips](technical-deep-dive.md#performance-considerations)

### System Architects

For system-level integration:

1. [Architecture](technical-deep-dive.md#architecture-overview)
2. [Integration](practical-examples.md#integration-example)
3. [Performance](technical-deep-dive.md#performance-considerations)

## Quick Reference

### Basic Operations

```python
from ia.gaius.agent_client import AgentClient

# Initialize
agent_info = {
    'api_key': 'your-api-key',
    'name': 'your-agent',
    'domain': 'your-domain',
    'secure': True
}
client = AgentClient(agent_info)

# Connect
client.connect()

# Configure nodes
client.set_ingress_nodes(['P1'])
client.set_query_nodes(['P1'])

# Execute query
result = client._query(client.session.get, '/test', nodes=['P1'])
```

### Common Patterns

* [Connection Management](technical-deep-dive.md#connection-flow)
* [Node Operations](technical-deep-dive.md#node-operations)
* [Query System](technical-deep-dive.md#query-system)
* [Error Handling](technical-deep-dive.md#error-handling)

### Best Practices

1. Error Handling
   ```python
   try:
       client.connect()
   except AgentConnectionError as e:
       print(f"Connection failed: {e}")
   ```

2. State Management
   ```python
   if not client._connected:
       client.connect()
   ```

3. Resource Cleanup
   ```python
   try:
       result = client._query(method, path)
   finally:
       # Clean up resources
       pass
   ```

## Documentation Map

### Core Concepts
- [Basic Usage](quickstart.md)
- [Technical Details](technical-deep-dive.md)
- [Practical Examples](practical-examples.md)

### Common Tasks
- [Installation](quickstart.md#installation)
- [Configuration](technical-deep-dive.md#configuration)
- [Querying](practical-examples.md#query-operations)

### Advanced Topics
- [Performance](technical-deep-dive.md#performance-considerations)
- [Security](technical-deep-dive.md#security-considerations)
- [Testing](technical-deep-dive.md#testing-strategies)

## Support

If you need help:

1. Check the [Troubleshooting Guide](technical-deep-dive.md#troubleshooting-guide)
2. Review [Common Issues](technical-deep-dive.md#common-issues)
3. See [Error Handling Examples](practical-examples.md#error-handling)


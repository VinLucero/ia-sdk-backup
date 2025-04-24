# Quick Start Guide

## Installation {#installation}

### Standard Installation
```bash
pip install ia-sdk
```

### Offline Installation
```bash
pip install --no-index --find-links packages ia-sdk
```

## Basic Usage

### Initialize Client {#initialize-client}
```python
from ia.gaius.agent_client import AgentClient

agent_info = {
    'api_key': 'your-api-key',
    'name': 'your-agent',
    'domain': 'your-domain',
    'secure': True
}
client = AgentClient(agent_info)
```

### Connect to Agent {#connect-to-agent}
```python
try:
    client.connect()
except AgentConnectionError as e:
    print(f"Connection failed: {e}")
```

### Configure Nodes {#configure-nodes}
```python
# Set ingress nodes
client.set_ingress_nodes(['P1'])

# Set query nodes
client.set_query_nodes(['P1'])
```

### Basic Operations {#basic-operations}
```python
# Execute query
result = client._query(
    client.session.get,
    '/test',
    nodes=['P1']
)
```

## Error Handling {#error-handling}

### Connection Errors
```python
try:
    client.connect()
except AgentConnectionError as e:
    print(f"Connection error: {e}")
```

### Query Errors
```python
try:
    result = client._query(method, path, nodes=['P1'])
except AgentQueryError as e:
    print(f"Query error: {e}")
```

## Common Pitfalls {#common-pitfalls}

### Connection Issues
1. Invalid API key
2. Wrong domain
3. Network connectivity
4. SSL verification

### Node Configuration
1. Missing nodes
2. Invalid node names
3. Permissions issues
4. Configuration timing

### Query Problems
1. Invalid method
2. Wrong path
3. Missing nodes
4. Response format

## Best Practices {#best-practices}

### State Management
```python
def ensure_connected(client):
    if not client._connected:
        client.connect()
```

### Error Recovery
```python
def safe_query(client, method, path, nodes, max_retries=3):
    for attempt in range(max_retries):
        try:
            return client._query(method, path, nodes=nodes)
        except AgentQueryError:
            if attempt == max_retries - 1:
                raise
            client.connect()  # Try reconnecting
```

### Resource Cleanup
```python
def managed_query(client, method, path, nodes):
    try:
        return client._query(method, path, nodes=nodes)
    finally:
        # Cleanup resources
        pass
```

## Next Steps

For more detailed information:
1. [API Reference](technical-deep-dive.md#api-reference)
2. [Examples](practical-examples.md#examples)
3. [Troubleshooting](technical-deep-dive.md#troubleshooting)

# Quick Start Guide for ia-sdk

## Overview
The ia-sdk provides a Python interface for interacting with GAIuS agents. This guide will help you get started with the basic operations.

## Installation

### Standard Installation
```bash
pip install ia-sdk
```

### Offline Installation (from backup)
```bash
# Clone the backup repository
git clone https://github.com/VinLucero/ia-sdk-backup.git
cd ia-sdk-backup

# Install from local files
pip install --no-index --find-links packages ia-sdk
```

## Basic Usage

### 1. Initialize the Client
```python
from ia.gaius.agent_client import AgentClient

# Configure your agent
agent_info = {
    'api_key': 'your-api-key',
    'name': 'your-agent-name',
    'domain': 'your-domain',
    'secure': False  # Set to True for HTTPS
}

# Create the client
client = AgentClient(agent_info)
```

### 2. Connect to Agent
```python
try:
    client.connect()
except AgentConnectionError as e:
    print(f"Connection failed: {e}")
```

### 3. Configure Nodes
```python
# Set ingress nodes (where data will be sent)
client.set_ingress_nodes(['P1'])

# Set query nodes (where queries will be directed)
client.set_query_nodes(['P1'])
```

### 4. Basic Operations
```python
# Perform a query
try:
    result = client._query(client.session.get, '/test', nodes=['P1'])
    print(f"Query result: {result}")
except AgentQueryError as e:
    print(f"Query failed: {e}")
```

## Important Concepts

### Connection State
- The client must be connected before performing operations
- Connection state is maintained in `client._connected`
- Always check connection status before operations

### Node Configuration
- Nodes must be configured before use
- Use primitive nodes for basic operations
- Node IDs are mapped internally through the genome

### Error Handling
```python
from ia.gaius.agent_client import AgentQueryError, AgentConnectionError

try:
    client.connect()
    client.set_ingress_nodes(['P1'])
    result = client._query(client.session.get, '/test', nodes=['P1'])
except AgentConnectionError as e:
    print(f"Connection error: {e}")
except AgentQueryError as e:
    print(f"Query error: {e}")
```

## Common Pitfalls

1. **Connection Issues**
   - Ensure proper API key and domain
   - Check network connectivity
   - Verify SSL settings if using HTTPS

2. **Node Configuration**
   - Verify node names exist in genome
   - Configure both ingress and query nodes
   - Check node permissions

3. **Query Operations**
   - Always provide node list for queries
   - Use correct HTTP method (get, post, etc.)
   - Handle response format properly

## Best Practices

1. **Connection Management**
```python
def ensure_connection(client):
    if not client._connected:
        client.connect()
```

2. **Node Validation**
```python
def validate_nodes(client, nodes):
    for node in nodes:
        if node not in client.genome.primitive_map:
            raise ValueError(f"Invalid node: {node}")
```

3. **Error Recovery**
```python
def safe_query(client, method, path, nodes):
    try:
        return client._query(method, path, nodes=nodes)
    except AgentQueryError:
        client.connect()  # Reconnect and retry
        return client._query(method, path, nodes=nodes)
```

## Next Steps

1. Explore Advanced Features
   - Custom node types
   - Complex queries
   - Data transformations

2. Integration Patterns
   - Docker integration
   - Database connectivity
   - Error handling strategies

3. Performance Optimization
   - Connection pooling
   - Query optimization
   - State management

## Troubleshooting

### Common Issues and Solutions

1. Connection Failed
```python
# Check connection parameters
print(f"URL: {client._url}")
print(f"SSL Verify: {client._verify}")
```

2. Node Not Found
```python
# List available nodes
print("Available nodes:", client.genome.primitive_map.keys())
```

3. Query Failed
```python
# Verify node configuration
print("Ingress nodes:", client.ingress_nodes)
print("Query nodes:", client.query_nodes)
```

## Support

For more detailed information:
- Consult the [API Reference](../api-reference/index.md)
- Check the [Examples](../examples/index.md)
- Review the [Troubleshooting Guide](../guides/troubleshooting.md)

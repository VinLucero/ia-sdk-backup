# ia-sdk Technical Deep Dive

## Architecture Overview

### Component Structure
```
ia.gaius/
├── agent_client.py    # Main interface
├── genome_info.py     # Genome definitions
├── data_structures.py # Core data types
└── experimental/      # Advanced features
```

## Key Components Deep Dive

### 1. Agent Client Lifecycle

#### Connection Flow
```python
# Internal connection process
def connect(self):
    # 1. Initial connection
    response_data = self.session.get(f'{self._url}connect').json()
    
    # 2. Status verification
    if response_data['status'] != 'okay':
        raise AgentConnectionError
    
    # 3. Genome initialization
    self.genome = Genome(response_data['genome'])
    
    # 4. Agent configuration
    self.gaius_agent = response_data['genome']['agent']
```

#### State Management
```python
class AgentClient:
    def __init__(self):
        self._connected = False
        self.genome = None
        self.gaius_agent = None
        self.ingress_nodes = []
        self.query_nodes = []
```

### 2. Genome Structure

#### Topology Definition
```python
GENOME_STRUCTURE = {
    'agent': str,           # Agent identifier
    'description': str,     # Genome description
    'primitive_map': dict,  # Node mapping
    'nodes': {
        'id': {
            'name': str,
            'type': str,
            'description': str
        }
    },
    'elements': {
        'nodes': list,
        'edges': list
    }
}
```

#### Node Operations
```python
def set_ingress_nodes(self, nodes):
    """
    Critical Points:
    1. Nodes must exist in primitive_map
    2. Node IDs are mapped from names
    3. State is maintained in ingress_nodes
    """
    self.ingress_nodes = [
        {'id': self.genome.primitive_map[node],
         'name': node}
        for node in nodes
    ]
```

### 3. Query System

#### Query Flow
```python
def _query(self, query_method, path, data=None, nodes=None):
    """
    Critical Points:
    1. Connection state verification
    2. Node validation
    3. Response processing
    4. Error handling
    """
    # Connection check
    if not self._connected:
        raise AgentConnectionError
    
    # Node processing
    if isinstance(nodes[0], str):
        nodes = [{'name': name, 'id': self.genome.primitive_map[name]}
                 for name in nodes]
    
    # Query execution and response handling
    for node in nodes:
        try:
            response = self._execute_query(node, path, data)
            self._process_response(response)
        except Exception as e:
            raise AgentQueryError(str(e))
```

## Advanced Usage Patterns

### 1. Error Recovery
```python
class ResilientAgent:
    def __init__(self, agent_info):
        self.client = AgentClient(agent_info)
        self.retry_count = 3
    
    def safe_query(self, method, path, nodes):
        for attempt in range(self.retry_count):
            try:
                if not self.client._connected:
                    self.client.connect()
                return self.client._query(method, path, nodes=nodes)
            except AgentConnectionError:
                if attempt == self.retry_count - 1:
                    raise
                continue
```

### 2. State Management
```python
class ManagedAgent:
    def __init__(self, agent_info):
        self.client = AgentClient(agent_info)
        self.state = {
            'connected': False,
            'nodes_configured': False,
            'last_query_time': None
        }
    
    def ensure_ready(self):
        if not self.state['connected']:
            self.client.connect()
            self.state['connected'] = True
        
        if not self.state['nodes_configured']:
            self.client.set_ingress_nodes(['P1'])
            self.client.set_query_nodes(['P1'])
            self.state['nodes_configured'] = True
```

## Performance Considerations

### 1. Connection Management
- Maintain connection state
- Implement connection pooling
- Handle reconnection gracefully

### 2. Query Optimization
- Batch queries when possible
- Reuse node configurations
- Cache frequently used data

### 3. Resource Management
- Monitor memory usage
- Implement proper cleanup
- Handle large responses efficiently

## Security Considerations

### 1. Authentication
```python
def secure_client_setup(api_key, domain):
    return AgentClient({
        'api_key': api_key,
        'name': f'secure-agent-{uuid.uuid4().hex[:8]}',
        'domain': domain,
        'secure': True  # Enable HTTPS
    })
```

### 2. Data Handling
```python
def safe_query_execution(client, method, path, sensitive_data):
    """Handle sensitive data carefully"""
    try:
        # Sanitize input
        safe_data = sanitize_data(sensitive_data)
        
        # Execute query
        result = client._query(method, path, data=safe_data)
        
        # Clean response
        return clean_response(result)
    finally:
        # Cleanup sensitive data
        del sensitive_data
```

## Testing Strategies

### 1. Component Testing
```python
def test_agent_lifecycle():
    """Test complete agent lifecycle"""
    client = AgentClient(TEST_CONFIG)
    
    # Test connection
    client.connect()
    assert client._connected
    
    # Test node configuration
    client.set_ingress_nodes(['P1'])
    assert len(client.ingress_nodes) == 1
    
    # Test query
    result = client._query(client.session.get, '/test', nodes=['P1'])
    assert result['status'] == 'okay'
```

### 2. Integration Testing
```python
def test_complete_workflow():
    """Test full workflow integration"""
    agent = ResilientAgent(PROD_CONFIG)
    
    # Setup
    agent.ensure_ready()
    
    # Operations
    data = generate_test_data()
    result = agent.safe_query(method='GET', 
                            path='/process',
                            nodes=['P1'])
    
    # Verification
    verify_result(result)
```

## Troubleshooting Guide

### Common Issues

1. Connection Failures
```python
def diagnose_connection(client):
    """Diagnose connection issues"""
    try:
        client.connect()
    except AgentConnectionError as e:
        print(f"Connection configuration:")
        print(f"URL: {client._url}")
        print(f"Headers: {client._headers}")
        print(f"SSL Verify: {client._verify}")
        raise
```

2. Node Configuration Issues
```python
def verify_node_config(client):
    """Verify node configuration"""
    print("Available nodes:", client.genome.primitive_map.keys())
    print("Configured ingress:", client.ingress_nodes)
    print("Configured query:", client.query_nodes)
```

3. Query Issues
```python
def debug_query(client, method, path, nodes):
    """Debug query execution"""
    try:
        result = client._query(method, path, nodes=nodes)
        return result
    except AgentQueryError as e:
        print(f"Query parameters:")
        print(f"Method: {method}")
        print(f"Path: {path}")
        print(f"Nodes: {nodes}")
        print(f"Error: {e}")
        raise
```

## Best Practices Summary

1. Always implement proper error handling
2. Maintain connection state carefully
3. Validate node configurations
4. Use retry mechanisms for resilience
5. Implement proper resource cleanup
6. Monitor and log operations
7. Handle sensitive data securely
8. Test all critical paths
9. Document failure modes
10. Maintain state consistency


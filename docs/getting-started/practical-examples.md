# ia-sdk Practical Examples

## Common Usage Patterns

### Basic Operations Pattern
```python
from ia.gaius.agent_client import AgentClient, AgentConnectionError, AgentQueryError

class BasicAgent:
    """Basic agent usage pattern"""
    def __init__(self, api_key, domain):
        self.agent_info = {
            'api_key': api_key,
            'name': 'basic-agent',
            'domain': domain,
            'secure': True
        }
        self.client = None
        
    def initialize(self):
        try:
            self.client = AgentClient(self.agent_info)
            self.client.connect()
            self.client.set_ingress_nodes(['P1'])
            self.client.set_query_nodes(['P1'])
            return True
        except AgentConnectionError as e:
            print(f"Initialization failed: {e}")
            return False

    def execute_query(self, path):
        try:
            return self.client._query(self.client.session.get, path, nodes=['P1'])
        except AgentQueryError as e:
            print(f"Query failed: {e}")
            return None
```

### Resilient Pattern
```python
import time
from functools import wraps

def retry_on_failure(max_retries=3, delay=1):
    """Decorator for retry logic"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except (AgentConnectionError, AgentQueryError) as e:
                    if attempt == max_retries - 1:
                        raise
                    time.sleep(delay)
                    continue
        return wrapper
    return decorator

class ResilientAgent:
    """Agent with retry and recovery logic"""
    def __init__(self, api_key, domain):
        self.agent_info = {
            'api_key': api_key,
            'name': 'resilient-agent',
            'domain': domain,
            'secure': True
        }
        self.client = None
        self.initialize()
    
    @retry_on_failure(max_retries=3)
    def initialize(self):
        self.client = AgentClient(self.agent_info)
        self.client.connect()
        self.client.set_ingress_nodes(['P1'])
        self.client.set_query_nodes(['P1'])
    
    @retry_on_failure(max_retries=3)
    def execute_query(self, path, nodes=None):
        if not nodes:
            nodes = ['P1']
        return self.client._query(self.client.session.get, path, nodes=nodes)
```

### State Management Pattern
```python
from enum import Enum
from datetime import datetime, timedelta

class AgentState(Enum):
    INITIALIZED = "initialized"
    CONNECTED = "connected"
    ERROR = "error"
    DISCONNECTED = "disconnected"

class ManagedAgent:
    """Agent with state management"""
    def __init__(self, api_key, domain):
        self.agent_info = {
            'api_key': api_key,
            'name': 'managed-agent',
            'domain': domain,
            'secure': True
        }
        self.client = None
        self.state = AgentState.INITIALIZED
        self.last_connection = None
        self.reconnect_interval = timedelta(minutes=30)
        
    def ensure_connected(self):
        current_time = datetime.now()
        needs_reconnect = (
            self.state != AgentState.CONNECTED or
            (self.last_connection and 
             current_time - self.last_connection > self.reconnect_interval)
        )
        
        if needs_reconnect:
            try:
                self.client = AgentClient(self.agent_info)
                self.client.connect()
                self.client.set_ingress_nodes(['P1'])
                self.client.set_query_nodes(['P1'])
                self.state = AgentState.CONNECTED
                self.last_connection = current_time
            except Exception as e:
                self.state = AgentState.ERROR
                raise
    
    def execute_query(self, path, nodes=None):
        self.ensure_connected()
        return self.client._query(
            self.client.session.get,
            path,
            nodes=nodes or ['P1']
        )
```

### Batch Operations Pattern
```python
class BatchAgent:
    """Agent with batch operation support"""
    def __init__(self, api_key, domain):
        self.agent = ManagedAgent(api_key, domain)
        self.batch_size = 10
        self.results = []
        
    def batch_query(self, paths):
        """Execute multiple queries in batches"""
        results = []
        for i in range(0, len(paths), self.batch_size):
            batch = paths[i:i + self.batch_size]
            batch_results = []
            for path in batch:
                try:
                    result = self.agent.execute_query(path)
                    batch_results.append((path, result))
                except Exception as e:
                    batch_results.append((path, e))
            results.extend(batch_results)
        return results
```

## Real-World Examples

### Monitoring System
```python
class AgentMonitor:
    """Monitor agent health and operations"""
    def __init__(self, api_key, domain):
        self.agent = ResilientAgent(api_key, domain)
        self.health_checks = {
            'connection': self._check_connection,
            'nodes': self._check_nodes,
            'queries': self._check_queries
        }
        
    def _check_connection(self):
        try:
            self.agent.initialize()
            return True, "Connection healthy"
        except Exception as e:
            return False, f"Connection error: {e}"
    
    def _check_nodes(self):
        try:
            nodes = self.agent.client.genome.primitive_map.keys()
            return True, f"Found {len(nodes)} nodes"
        except Exception as e:
            return False, f"Node check error: {e}"
    
    def _check_queries(self):
        try:
            result = self.agent.execute_query('/health')
            return True, "Queries operational"
        except Exception as e:
            return False, f"Query check error: {e}"
    
    def run_health_check(self):
        results = {}
        for check_name, check_func in self.health_checks.items():
            success, message = check_func()
            results[check_name] = {
                'status': 'healthy' if success else 'error',
                'message': message
            }
        return results
```

### Data Processing Pipeline
```python
class DataPipeline:
    """Example data processing pipeline"""
    def __init__(self, api_key, domain):
        self.agent = ManagedAgent(api_key, domain)
        self.processing_steps = []
        
    def add_step(self, path, transformer=None):
        self.processing_steps.append({
            'path': path,
            'transformer': transformer or (lambda x: x)
        })
        
    def process(self, initial_data):
        current_data = initial_data
        results = []
        
        for step in self.processing_steps:
            try:
                # Execute query
                result = self.agent.execute_query(
                    step['path'],
                    data=current_data
                )
                
                # Transform result
                current_data = step['transformer'](result)
                
                results.append({
                    'step': step['path'],
                    'status': 'success',
                    'data': current_data
                })
            except Exception as e:
                results.append({
                    'step': step['path'],
                    'status': 'error',
                    'error': str(e)
                })
                break
                
        return results
```

### Integration Example
```python
def main():
    # Configuration
    API_KEY = "your-api-key"
    DOMAIN = "your-domain"
    
    # Initialize components
    monitor = AgentMonitor(API_KEY, DOMAIN)
    pipeline = DataPipeline(API_KEY, DOMAIN)
    
    # Setup pipeline
    pipeline.add_step('/preprocess')
    pipeline.add_step('/analyze', lambda x: x['processed_data'])
    pipeline.add_step('/summarize')
    
    # Health check
    health_status = monitor.run_health_check()
    if all(check['status'] == 'healthy' for check in health_status.values()):
        # Process data
        initial_data = {"raw_data": "example"}
        results = pipeline.process(initial_data)
        
        # Handle results
        for result in results:
            if result['status'] == 'success':
                print(f"Step {result['step']} completed")
            else:
                print(f"Step {result['step']} failed: {result['error']}")
    else:
        print("System unhealthy:", health_status)

if __name__ == "__main__":
    main()
```

## Best Practices Summary

1. Always use error handling and retry logic
2. Implement proper state management
3. Use batch operations where appropriate
4. Monitor system health
5. Handle data transformations carefully
6. Implement proper cleanup
7. Use appropriate logging
8. Handle failures gracefully
9. Validate all inputs and outputs
10. Maintain connection state


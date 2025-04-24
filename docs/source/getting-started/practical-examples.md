# Practical Examples

## Basic Operations Pattern {#basic-operations-pattern}

```python
from ia.gaius.agent_client import AgentClient, AgentQueryError

class BasicAgent:
    def __init__(self, api_key, domain):
        self.agent_info = {
            'api_key': api_key,
            'name': 'basic-agent',
            'domain': domain,
            'secure': True
        }
        self.client = AgentClient(self.agent_info)
        self.initialize()
    
    def initialize(self):
        self.client.connect()
        self.client.set_ingress_nodes(['P1'])
        self.client.set_query_nodes(['P1'])
    
    def execute_query(self, path):
        return self.client._query(
            self.client.session.get,
            path,
            nodes=['P1']
        )
```

## Resilient Pattern {#resilient-pattern}

```python
import time
from functools import wraps

def retry_on_failure(max_retries=3, delay=1):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise
                    time.sleep(delay)
            return None
        return wrapper
    return decorator

class ResilientAgent:
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
    def execute_query(self, path):
        return self.client._query(
            self.client.session.get,
            path,
            nodes=['P1']
        )
```

## State Management Pattern {#state-management-pattern}

```python
from enum import Enum
from datetime import datetime, timedelta

class AgentState(Enum):
    INITIALIZED = "initialized"
    CONNECTED = "connected"
    ERROR = "error"

class ManagedAgent:
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
        if (self.state != AgentState.CONNECTED or
            (self.last_connection and 
             datetime.now() - self.last_connection > self.reconnect_interval)):
            self.initialize()
    
    def initialize(self):
        try:
            self.client = AgentClient(self.agent_info)
            self.client.connect()
            self.client.set_ingress_nodes(['P1'])
            self.client.set_query_nodes(['P1'])
            self.state = AgentState.CONNECTED
            self.last_connection = datetime.now()
        except Exception as e:
            self.state = AgentState.ERROR
            raise
```

## Batch Operations Pattern {#batch-operations-pattern}

```python
from typing import List, Dict, Any

class BatchAgent:
    def __init__(self, api_key, domain):
        self.agent = ManagedAgent(api_key, domain)
        self.batch_size = 10
    
    def batch_query(self, paths: List[str]) -> List[Dict[str, Any]]:
        """Execute multiple queries in batches."""
        results = []
        for i in range(0, len(paths), self.batch_size):
            batch = paths[i:i + self.batch_size]
            batch_results = []
            for path in batch:
                try:
                    result = self.agent.execute_query(path)
                    batch_results.append({
                        'path': path,
                        'status': 'success',
                        'data': result
                    })
                except Exception as e:
                    batch_results.append({
                        'path': path,
                        'status': 'error',
                        'error': str(e)
                    })
            results.extend(batch_results)
        return results
```

## Integration Example {#integration-example}

```python
def main():
    # Configuration
    API_KEY = "your-api-key"
    DOMAIN = "your-domain"
    
    # Initialize components
    batch_agent = BatchAgent(API_KEY, DOMAIN)
    
    # Prepare queries
    paths = [
        '/data/preprocess',
        '/data/analyze',
        '/data/summarize'
    ]
    
    # Execute batch queries
    results = batch_agent.batch_query(paths)
    
    # Process results
    for result in results:
        if result['status'] == 'success':
            print(f"Path {result['path']}: Success")
            print(f"Data: {result['data']}")
        else:
            print(f"Path {result['path']}: Error")
            print(f"Error: {result['error']}")

if __name__ == "__main__":
    main()
```

## Error Handling {#error-handling}

```python
class ErrorHandler:
    def __init__(self):
        self.errors = []
    
    def handle_error(self, error, context=None):
        error_info = {
            'timestamp': datetime.now(),
            'error': str(error),
            'type': type(error).__name__,
            'context': context
        }
        self.errors.append(error_info)
        return error_info

class SafeAgent:
    def __init__(self, api_key, domain):
        self.agent = ResilientAgent(api_key, domain)
        self.error_handler = ErrorHandler()
    
    def safe_execute(self, path, context=None):
        try:
            return self.agent.execute_query(path)
        except Exception as e:
            error_info = self.error_handler.handle_error(e, context)
            return {
                'status': 'error',
                'error_info': error_info
            }
```

## Best Practices

### Error Recovery
```python
def safe_operation(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except AgentConnectionError:
            # Handle connection errors
            pass
        except AgentQueryError:
            # Handle query errors
            pass
    return wrapper
```

### Resource Management
```python
class ManagedResource:
    def __init__(self):
        self.resources = []
    
    def acquire(self, resource):
        self.resources.append(resource)
    
    def release(self):
        for resource in self.resources:
            try:
                resource.close()
            except:
                pass
        self.resources.clear()
```

### State Validation
```python
def validate_state(client):
    assert client._connected, "Client not connected"
    assert client.ingress_nodes, "No ingress nodes configured"
    assert client.query_nodes, "No query nodes configured"
```


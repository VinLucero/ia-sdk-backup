# ia-sdk Implementation Analysis

## 1. Core Components

### AgentClient Class Requirements
- Needs specific initialization parameters:
  - api_key
  - name
  - domain
  - secure (boolean)
- Uses requests.Session for HTTP operations
- Maintains connection state via _connected flag

### Decorators
```python
@_ensure_connected
```
- Ensures methods are only called after successful connection
- Raises AgentConnectionError if not connected

### Helper Functions
```python
def _remove_unique_id(response: dict) -> dict
```
- Processes responses
- Removes unique_id fields from nested dictionaries

## 2. Connection Flow
1. Initialize client
2. Create session
3. Connect to agent
4. Verify connection
5. Get genome information

## 3. Testing Strategy

### Basic Tests (Working)
- Initialization
- Error classes
- String representation

### Connection Tests (Need Fix)
- Mock session properly
- Handle genome response
- Verify connection state

### Query Tests (Need Fix)
- Ensure connected state
- Mock proper responses
- Handle nested data

## 4. Test Implementation Plan

1. Create proper fixtures:
```python
@pytest.fixture
def mock_session():
    """Create properly mocked session with all required responses."""
    session = MagicMock()
    session.request.side_effect = create_mock_responses()
    return session

@pytest.fixture
def connected_client(mock_session):
    """Create pre-connected client for testing."""
    client = create_client(mock_session)
    client.connect()
    return client
```

2. Mock responses correctly:
```python
def create_mock_responses():
    """Create response chain for different requests."""
    def mock_response(*args, **kwargs):
        method, url = args
        if 'genome' in url:
            return MockResponse(200, {
                'status': 'success',
                'primitive_map': {'node1': 'id1'},
                'manipulative_map': {'node1': 'id1'}
            })
        return MockResponse(200, {'status': 'success'})
    return mock_response
```

3. Test decorated methods properly:
```python
def test_decorated_method(connected_client):
    """Test method with @_ensure_connected decorator."""
    # Method should work with connected client
    connected_client.some_method()

    # Should fail with disconnected client
    disconnected_client = create_client()
    with pytest.raises(AgentConnectionError):
        disconnected_client.some_method()
```

## 5. Implementation Requirements

### Connection Requirements
- Valid API key
- Valid domain
- Successful genome retrieval
- Proper error handling

### Query Requirements
- Connected state
- Valid nodes configuration
- Proper response handling
- Error handling

## 6. Next Steps

1. Update test fixtures:
   - Create proper session mocking
   - Handle all response types
   - Mock genome correctly

2. Fix connection tests:
   - Handle the full connection flow
   - Verify state changes
   - Test error conditions

3. Update query tests:
   - Test with connected client
   - Verify response processing
   - Test error handling

4. Document verified behaviors:
   - Update README
   - Add usage examples
   - Document limitations

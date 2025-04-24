"""Unit tests for the comcom_client module."""
import pytest
import sys
import os
from unittest.mock import Mock, patch, MagicMock

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../src')))

from ia.gaius.experimental.comcom_client import COMCOMClient, COMCOMConnectionError, COMCOMQueryError

class MockCOMCOMResponse:
    """Mock HTTP response."""
    def __init__(self, status_code, json_data):
        self.status_code = status_code
        self._json_data = json_data

    def json(self):
        return self._json_data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f"HTTP Error: {self.status_code}")
        return None

class MockCOMCOMSession:
    """Mock session with proper response handling."""
    def __init__(self):
        self.responses = {
            'connect': {
                'status': 'okay',
                'connection': 'okay',
                'message': 'Successfully connected'
            },
            'default': {
                'status': 'okay',
                'message': 'Operation successful'
            },
            'error': {
                'status': 'failed',
                'message': 'Operation failed'
            }
        }

    def get(self, url, **kwargs):
        if 'connect' in url:
            return MockCOMCOMResponse(200, self.responses['connect'])
        elif 'error' in url:
            return MockCOMCOMResponse(400, self.responses['error'])
        return MockCOMCOMResponse(200, self.responses['default'])
    
    def post(self, url, **kwargs):
        if 'error' in url:
            return MockCOMCOMResponse(400, self.responses['error'])
        return MockCOMCOMResponse(200, self.responses['default'])
    
    def request(self, method, url, **kwargs):
        if method == 'GET':
            return self.get(url, **kwargs)
        elif method == 'POST':
            return self.post(url, **kwargs)
        return MockCOMCOMResponse(200, self.responses['default'])

@pytest.fixture
def mock_comcom_session():
    """Create mock session."""
    return MockCOMCOMSession()

@pytest.fixture
def mock_comcom_client(mock_comcom_session):
    """Create client with mocked session."""
    with patch('requests.Session', return_value=mock_comcom_session):
        client = COMCOMClient({
            'api_key': 'test-key',
            'name': 'test-comcom',
            'domain': 'test.com',
            'secure': False
        })
        return client

@pytest.fixture
def connected_comcom_client(mock_comcom_client):
    """Create pre-connected client."""
    mock_comcom_client.connect()
    return mock_comcom_client

def test_initialization():
    """Test client initialization."""
    info = {
        'api_key': 'test-key',
        'name': 'test-comcom',
        'domain': 'test.com',
        'secure': False
    }
    with patch('requests.Session'):
        client = COMCOMClient(info)
        assert client.name == 'test-comcom'
        assert client._domain == 'test.com'
        assert client._api_key == 'test-key'
        assert client._url == 'http://test-comcom.test.com/'

def test_secure_initialization():
    """Test secure client initialization."""
    info = {
        'api_key': 'test-key',
        'name': 'test-comcom',
        'domain': 'test.com',
        'secure': True
    }
    with patch('requests.Session'):
        client = COMCOMClient(info)
        assert client._secure is True
        assert client._url == 'https://test-comcom.test.com/'

def test_connection(mock_comcom_client):
    """Test connection process."""
    # Test connection
    result = mock_comcom_client.connect()
    assert mock_comcom_client._connected is True
    assert result['connection'] == 'okay'

def test_query_requires_connection(mock_comcom_client):
    """Test query fails without connection."""
    with pytest.raises(COMCOMConnectionError):
        mock_comcom_client._query(mock_comcom_client.session.get, 'test')

def test_query_with_connection(connected_comcom_client):
    """Test query succeeds with connection."""
    result = connected_comcom_client._query(connected_comcom_client.session.get, 'test')
    assert result == 'Operation successful'

def test_connection_error():
    """Test error handling during connection."""
    error_session = MagicMock()
    error_session.get.return_value = MockCOMCOMResponse(401, {'status': 'error'})
    
    with patch('requests.Session', return_value=error_session):
        client = COMCOMClient({
            'api_key': 'test-key',
            'name': 'test-comcom',
            'domain': 'test.com',
            'secure': False
        })
        with pytest.raises(COMCOMConnectionError):
            client.connect()

def test_query_error(connected_comcom_client):
    """Test error handling during query."""
    with pytest.raises(COMCOMQueryError):
        connected_comcom_client._query(connected_comcom_client.session.get, 'error')

def test_ensure_connected_decorator():
    """Test _ensure_connected decorator."""
    client = COMCOMClient({
        'api_key': 'test-key',
        'name': 'test-comcom',
        'domain': 'test.com',
        'secure': False
    })
    
    # Should raise error when not connected
    with pytest.raises(COMCOMConnectionError):
        client.connect_to_agent('key', 'domain', 'name', 'type')

def test_slot_operations(connected_comcom_client):
    """Test operations on input and output slots."""
    # Test connecting input slot
    result = connected_comcom_client.connect_input_slot(
        input_name="test_input",
        input_type="test_type"
    )
    assert result == 'Operation successful'
    
    # Test disconnecting input slot
    result = connected_comcom_client.disconnect_input_slot("test_input")
    assert result == 'Operation successful'
    
    # Test connecting output slot
    result = connected_comcom_client.connect_output_slot(
        output_name="test_output",
        output_type="test_type"
    )
    assert result == 'Operation successful'
    
    # Test disconnecting output slot
    result = connected_comcom_client.disconnect_output_slot("test_output")
    assert result == 'Operation successful'

def test_agent_operations(connected_comcom_client):
    """Test operations related to agents."""
    # Test connecting to agent
    result = connected_comcom_client.connect_to_agent(
        api_key="test-key",
        domain="test.com",
        agent_name="test-agent",
        agent_type="test-type"
    )
    assert result == 'Operation successful'
    
    # Test disconnecting from agent
    result = connected_comcom_client.disconnect_agent("test-agent")
    assert result == 'Operation successful'
    
    # Test calling agent command
    result = connected_comcom_client.call_agent_command(
        agent_name="test-agent",
        command="test-command",
        command_parameters={}
    )
    assert result == 'Operation successful'
    
    # Test clearing agents
    result = connected_comcom_client.clear_agents()
    assert result == 'Operation successful'

def test_pipeline_operations(connected_comcom_client):
    """Test operations related to pipelines."""
    # Test creating pipeline
    result = connected_comcom_client.create_pipeline(
        pipeline_name="test-pipeline",
        pipeline_function_parameters={},
        pipeline_source_fields={},
        pipeline_destination_fields={},
        pipeline_connections={},
        pipeline_starting_functions=[]
    )
    assert result == 'Operation successful'
    
    # Test modifying pipeline
    result = connected_comcom_client.modify_pipeline(
        pipeline_name="test-pipeline",
        modification_type="test-mod"
    )
    assert result == 'Operation successful'
    
    # Test getting pipeline data
    result = connected_comcom_client.get_pipeline_data("test-pipeline")
    assert result == 'Operation successful'
    
    # Test deleting pipeline
    result = connected_comcom_client.delete_pipeline("test-pipeline")
    assert result == 'Operation successful'

def test_listing_operations(connected_comcom_client):
    """Test listing operations."""
    # Test listing agents
    result = connected_comcom_client.list_agent_connections()
    assert result == 'Operation successful'
    
    # Test listing input slots
    result = connected_comcom_client.list_input_slots()
    assert result == 'Operation successful'
    
    # Test listing output slots
    result = connected_comcom_client.list_output_slots()
    assert result == 'Operation successful'
    
    # Test listing pipelines
    result = connected_comcom_client.list_pipelines()
    assert result == 'Operation successful'
    
    # Test listing COMCOM
    result = connected_comcom_client.list_comcom()
    assert result == 'Operation successful'


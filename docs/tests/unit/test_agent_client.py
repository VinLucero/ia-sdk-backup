"""Unit tests for the agent_client module."""
import pytest
from unittest.mock import Mock, patch, MagicMock
from ia.gaius.agent_client import AgentClient, AgentQueryError, AgentConnectionError

class MockGenome:
    """Mock Genome class for testing."""
    def __init__(self):
        self.primitive_map = {
            'node1': 'id1',
            'node2': 'id2',
            'node3': 'id3',
            'node4': 'id4'
        }
        self.manipulative_map = self.primitive_map.copy()

class MockResponse:
    """Mock Response class for testing."""
    def __init__(self, status_code, json_data):
        self.status_code = status_code
        self._json_data = json_data

    def json(self):
        return self._json_data

def create_mock_session():
    """Create a mock session with proper response handling."""
    session = MagicMock()
    def mock_request(method, url, **kwargs):
        if 'genome' in url:
            return MockResponse(200, {
                'status': 'success',
                'primitive_map': {'node1': 'id1'},
                'manipulative_map': {'node1': 'id1'}
            })
        return MockResponse(200, {'status': 'success', 'data': 'test_data'})
    
    session.request = Mock(side_effect=mock_request)
    return session

@pytest.fixture
def mock_agent_client():
    """Create a mock agent client for testing."""
    agent_info = {
        'api_key': 'test-key',
        'name': 'test-agent',
        'domain': 'test.com',
        'secure': False
    }
    
    with patch('requests.Session', return_value=create_mock_session()):
        client = AgentClient(agent_info)
        return client

def test_agent_client_initialization():
    """Test AgentClient initialization with valid config."""
    agent_info = {
        'api_key': 'test-key',
        'name': 'test-agent',
        'domain': 'test.com',
        'secure': False
    }
    with patch('requests.Session'):
        client = AgentClient(agent_info)
        assert client.name == 'test-agent'
        assert client._domain == 'test.com'
        assert client._api_key == 'test-key'

def test_agent_client_initialization_missing_fields():
    """Test AgentClient initialization with missing fields."""
    agent_info = {'name': 'test-agent'}
    with pytest.raises(KeyError):
        AgentClient(agent_info)

def test_agent_query_error():
    """Test AgentQueryError creation and message."""
    error = AgentQueryError("Test error message")
    assert str(error) == "Test error message"

def test_agent_connection_error():
    """Test AgentConnectionError creation and message."""
    error = AgentConnectionError("Test connection error")
    assert str(error) == "Test connection error"

def test_connect_success(mock_agent_client):
    """Test successful connection."""
    mock_agent_client.connect()
    assert mock_agent_client._connected is True

def test_connect_failure():
    """Test connection failure."""
    session = MagicMock()
    session.request.return_value = MockResponse(401, {'status': 'error'})
    
    with patch('requests.Session', return_value=session):
        agent_info = {
            'api_key': 'test-key',
            'name': 'test-agent',
            'domain': 'test.com',
            'secure': False
        }
        client = AgentClient(agent_info)
        with pytest.raises(AgentConnectionError):
            client.connect()

def test_basic_node_operations(mock_agent_client):
    """Test node operations after connection."""
    # First connect
    mock_agent_client.connect()
    
    # Set nodes
    mock_agent_client.set_ingress_nodes(['node1'])
    mock_agent_client.set_query_nodes(['node1'])
    
    # Check nodes are set
    assert len(mock_agent_client.ingress_nodes) == 1
    assert len(mock_agent_client.query_nodes) == 1

def test_query_after_connection(mock_agent_client):
    """Test query operation after successful connection."""
    # Connect first
    mock_agent_client.connect()
    
    # Set up query nodes
    mock_agent_client.set_query_nodes(['node1'])
    
    # Perform query
    result = mock_agent_client._query('GET', '/test')
    assert result['status'] == 'success'

def test_string_representation(mock_agent_client):
    """Test string representation of client."""
    str_rep = str(mock_agent_client)
    assert mock_agent_client.name in str_rep
    assert mock_agent_client._domain in str_rep


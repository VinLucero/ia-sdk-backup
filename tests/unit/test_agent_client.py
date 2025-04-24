"""Unit tests for the agent_client module."""
import pytest
import sys
import os
from unittest.mock import Mock, patch, MagicMock

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

from ia.gaius.agent_client import AgentClient, AgentQueryError, AgentConnectionError

MOCK_GENOME_DATA = {
    'agent': 'test_agent',
    'description': 'Test agent genome',
    'primitive_map': {
        'node1': 'id1',
        'P1': 'pid1'  # Add standard primitive node
    },
    'manipulative_map': {
        'node1': 'id1',
        'P1': 'pid1'
    },
    'nodes': {
        'id1': {
            'name': 'node1',
            'type': 'test',
            'description': 'Test node'
        },
        'pid1': {
            'name': 'P1',
            'type': 'primitive',
            'description': 'Primitive node'
        }
    },
    'elements': {
        'nodes': [
            {
                'data': {
                    'id': 'id1',
                    'name': 'node1',
                    'type': 'test',
                    'description': 'Test node'
                }
            },
            {
                'data': {
                    'id': 'pid1',
                    'name': 'P1',
                    'type': 'primitive',
                    'description': 'Primitive node'
                }
            }
        ],
        'edges': []
    },
    'style': [
        {
            'selector': 'node',
            'style': {
                'label': 'data(name)'
            }
        },
        {
            'selector': 'edge',
            'style': {
                'curve-style': 'bezier'
            }
        }
    ]
}

class MockGenome:
    """Mock Genome class for testing."""
    def __init__(self):
        self.primitive_map = MOCK_GENOME_DATA['primitive_map']
        self.manipulative_map = MOCK_GENOME_DATA['manipulative_map']
        self.primitives = {
            'id1': {'name': 'node1', 'id': 'id1'},
            'pid1': {'name': 'P1', 'id': 'pid1'}
        }

class MockResponse:
    """Mock HTTP response."""
    def __init__(self, status_code, json_data):
        self.status_code = status_code
        self._json_data = json_data

    def json(self):
        return self._json_data

class MockSession:
    """Mock session with proper response handling."""
    def __init__(self):
        self.responses = {
            'connect': {
                'status': 'okay',
                'connection': 'okay',
                'genie': 'test_genie',
                'agent_name': 'test_agent',
                'genome': MOCK_GENOME_DATA
            },
            'genome': {
                'status': 'okay',
                'connection': 'okay',
                'genie': 'test_genie',
                'genome': MOCK_GENOME_DATA
            },
            'default': {
                'status': 'okay',
                'connection': 'okay',
                'genie': 'test_genie',
                'data': 'test_data'
            }
        }

    def get(self, url, **kwargs):
        if 'connect' in url:
            return MockResponse(200, self.responses['connect'])
        elif 'genome' in url:
            return MockResponse(200, self.responses['genome'])
        return MockResponse(200, self.responses['default'])
    
    def request(self, method, url, **kwargs):
        if method == 'GET':
            return self.get(url, **kwargs)
        return MockResponse(200, self.responses['default'])

@pytest.fixture
def mock_session():
    """Create mock session."""
    return MockSession()

@pytest.fixture
def mock_agent_client(mock_session):
    """Create agent client with mocked session."""
    with patch('requests.Session', return_value=mock_session):
        client = AgentClient({
            'api_key': 'test-key',
            'name': 'test-agent',
            'domain': 'test.com',
            'secure': False
        })
        return client

@pytest.fixture
def connected_client(mock_agent_client):
    """Create pre-connected client."""
    with patch('ia.gaius.genome_info.Genome', return_value=MockGenome()):
        mock_agent_client.connect()
        return mock_agent_client

def test_initialization():
    """Test client initialization."""
    info = {
        'api_key': 'test-key',
        'name': 'test-agent',
        'domain': 'test.com',
        'secure': False
    }
    with patch('requests.Session'):
        client = AgentClient(info)
        assert client.name == 'test-agent'
        assert client._domain == 'test.com'
        assert client._api_key == 'test-key'

def test_connection(mock_agent_client):
    """Test connection process."""
    with patch('ia.gaius.genome_info.Genome', return_value=MockGenome()):
        # Test connection
        result = mock_agent_client.connect()
        assert mock_agent_client._connected is True
        assert mock_agent_client.genome is not None
        assert result['connection'] == 'okay'
        assert result['agent'] == 'test_genie'
    
def test_query_requires_connection(mock_agent_client):
    """Test query fails without connection."""
    with pytest.raises(AgentConnectionError):
        mock_agent_client._query('GET', '/test')

def test_query_with_connection(connected_client):
    """Test query succeeds with connection."""
    result = connected_client._query('GET', '/test', nodes=['P1'])
    assert result['status'] == 'okay'

def test_error_handling():
    """Test error handling during connection."""
    error_session = MagicMock()
    error_session.get.return_value = MockResponse(401, {'status': 'error'})
    
    with patch('requests.Session', return_value=error_session):
        client = AgentClient({
            'api_key': 'test-key',
            'name': 'test-agent',
            'domain': 'test.com',
            'secure': False
        })
        with pytest.raises(AgentConnectionError):
            client.connect()

def test_set_nodes(connected_client):
    """Test setting ingress and query nodes."""
    # Set nodes
    connected_client.set_ingress_nodes(['P1'])
    connected_client.set_query_nodes(['P1'])
    
    # Verify nodes were set
    assert len(connected_client.ingress_nodes) == 1
    assert len(connected_client.query_nodes) == 1
    assert connected_client.ingress_nodes[0]['name'] == 'P1'
    assert connected_client.query_nodes[0]['name'] == 'P1'

def test_node_operations(connected_client):
    """Test more complex node operations."""
    # Set multiple nodes
    nodes = ['P1']
    connected_client.set_ingress_nodes(nodes)
    connected_client.set_query_nodes(nodes)
    
    # Verify node settings
    assert len(connected_client.ingress_nodes) == len(nodes)
    assert len(connected_client.query_nodes) == len(nodes)
    
    # Verify node properties
    for node in connected_client.ingress_nodes:
        assert 'id' in node
        assert 'name' in node
        assert node['name'] == 'P1'
        assert node['id'] == 'pid1'

def test_query_execution_with_parameters(connected_client):
    """Test query execution with different parameters."""
    # Test query with data parameter
    data = {'strings': ['test'], 'vectors': [], 'emotives': {}}
    result = connected_client._query(connected_client.session.post, 'observe', data=data, nodes=['P1'])
    assert result['status'] == 'okay'
    
    # Test query with unique_id
    unique_id = 'test-id-123'
    result, returned_id = connected_client._query(connected_client.session.post, 'observe', 
                                                 data=data, nodes=['P1'], unique_id=unique_id)
    assert result['status'] == 'okay'
    assert returned_id == unique_id

    # Test query with multiple nodes
    connected_client.set_summarize_for_single_node(False)
    result = connected_client._query(connected_client.session.get, 'status', nodes=['P1', 'P1'])
    assert 'P1' in result
    assert result['P1']['status'] == 'okay'

def test_query_timeout_handling(mock_session):
    """Test query timeout handling."""
    # Create client with timeout
    with patch('requests.Session', return_value=mock_session):
        client = AgentClient({
            'api_key': 'test-key',
            'name': 'test-agent',
            'domain': 'test.com',
            'secure': False
        }, timeout=5.0)
        
        # Verify timeout was set
        assert client._timeout == 5.0
        
        # Test changing timeout
        client.set_timeout(10.0)
        
        # Since we're mocking, we can't really test the timeout behavior directly,
        # but we can verify the method works
        with patch('ia.gaius.genome_info.Genome', return_value=MockGenome()):
            client.connect()
            assert client._connected is True

def test_query_with_invalid_nodes(connected_client):
    """Test query with invalid node configurations."""
    # Test with empty node list
    with pytest.raises(Exception):  # Should raise some kind of exception
        connected_client._query(connected_client.session.get, 'status', nodes=[])
    
    # Test with non-existing node
    mock_response = MagicMock()
    mock_response.json.return_value = {'status': 'failed', 'message': 'Node not found'}
    
    with patch.object(connected_client.session, 'get', return_value=mock_response):
        with pytest.raises(AgentQueryError):
            connected_client._query(connected_client.session.get, 'status', nodes=['NonExistentNode'])

def test_query_response_processing(connected_client):
    """Test query response processing."""
    # Test response processing with send_unique_ids=True
    connected_client.send_unique_ids = True
    unique_id = 'test-unique-id'
    
    # Mock response with unique_id
    mock_response = MagicMock()
    mock_response.json.return_value = {
        'status': 'okay', 
        'message': {'data': 'test_data', 'unique_id': unique_id}
    }
    
    with patch.object(connected_client.session, 'get', return_value=mock_response):
        result, returned_id = connected_client._query(
            connected_client.session.get, 'test', nodes=['P1'], unique_id=unique_id
        )
        assert 'unique_id' in result
        assert result['unique_id'] == unique_id
        assert returned_id == unique_id
    
    # Test response processing with send_unique_ids=False
    connected_client.send_unique_ids = False
    
    with patch.object(connected_client.session, 'get', return_value=mock_response):
        result, returned_id = connected_client._query(
            connected_client.session.get, 'test', nodes=['P1'], unique_id=unique_id
        )
        # unique_id should be removed from the response
        assert 'unique_id' not in result
        assert returned_id == unique_id
    
    # Test summarize_for_single_node behavior
    connected_client.send_unique_ids = True
    connected_client.summarize_for_single_node = True
    
    with patch.object(connected_client.session, 'get', return_value=mock_response):
        result = connected_client._query(connected_client.session.get, 'test', nodes=['P1'])
        # Result should be directly from the message, not wrapped in a dict
        assert result == {'data': 'test_data', 'unique_id': unique_id}
    
    # Test multiple nodes (should not summarize)
    connected_client.summarize_for_single_node = True
    
    with patch.object(connected_client.session, 'get', return_value=mock_response):
        result = connected_client._query(connected_client.session.get, 'test', nodes=['P1', 'P1'])
        # Result should be a dict with node names as keys
        assert 'P1' in result
        assert result['P1'] == {'data': 'test_data', 'unique_id': unique_id}

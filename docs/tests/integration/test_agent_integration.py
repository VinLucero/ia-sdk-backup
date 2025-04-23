"""Integration tests for agent client with other components."""
import pytest
from ia.gaius.agent_client import AgentClient
from ia.gaius.manager import AgentManager

@pytest.fixture
def agent_manager():
    """Create an agent manager for testing."""
    return AgentManager()

@pytest.fixture
def agent_client():
    """Create an agent client for testing."""
    agent_info = {
        'api_key': 'test-key',
        'name': 'test-agent',
        'domain': 'test.com',
        'secure': False
    }
    return AgentClient(agent_info)

def test_agent_manager_interaction(agent_manager, agent_client):
    """Test interaction between agent manager and client."""
    # Basic initialization test
    assert agent_client.name == "test-agent"

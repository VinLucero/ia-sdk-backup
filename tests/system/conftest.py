"""Common fixtures for system tests."""
import os
import time
import pytest
import logging
import tempfile
import requests
import uuid
from typing import Dict, Any
from dotenv import load_dotenv

from ia.gaius.agent_client import AgentClient
from ia.gaius.manager import AgentManager

# Load environment variables from .env file if present
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('system_tests.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('ia_system_tests')

# Global constants
DEFAULT_TIMEOUT = int(os.getenv('GAIUS_TEST_TIMEOUT', 300))
DEFAULT_CLEANUP = os.getenv('GAIUS_TEST_CLEANUP', 'true').lower() == 'true'
DEFAULT_API_KEY = os.getenv('GAIUS_API_KEY')
DEFAULT_DOMAIN = os.getenv('GAIUS_DOMAIN')
TEST_LEVEL = os.getenv('GAIUS_TEST_LEVEL', 'standard')


@pytest.fixture(scope="session")
def agent_manager():
    """Provides a session-wide AgentManager for starting and managing agents."""
    manager = AgentManager(local=True)
    manager.start_hoster()
    yield manager
    
    if DEFAULT_CLEANUP:
        logger.info("Cleaning up all agents after tests")
        manager.kill_all_agents()


@pytest.fixture(scope="function")
def temp_agent(agent_manager):
    """Provides a temporary agent for a test function and ensures cleanup."""
    agent_id = f"test-agent-{uuid.uuid4().hex[:8]}"
    agent_name = agent_id
    
    logger.info(f"Starting temporary agent {agent_name}")
    agent_obj = agent_manager.start_agent(
        genome_name="simple.genome",
        agent_id=agent_id,
        agent_name=agent_name
    )
    
    # Get the agent client and connect
    agent = agent_obj.get_agent_client()
    agent.connect()
    agent.set_ingress_nodes(["P1"])
    agent.set_query_nodes(["P1"])
    
    # Log agent info
    logger.info(f"Temporary agent {agent_name} started successfully")
    
    yield agent
    
    if DEFAULT_CLEANUP:
        logger.info(f"Cleaning up temporary agent {agent_name}")
        agent_manager.delete_agent(agent_name)


@pytest.fixture(scope="function")
def remote_agent():
    """Provides a remote agent client for a test function."""
    if not DEFAULT_API_KEY or not DEFAULT_DOMAIN:
        pytest.skip("GAIUS_API_KEY and GAIUS_DOMAIN environment variables must be set for remote agent tests")
    
    agent_info = {
        'api_key': DEFAULT_API_KEY,
        'name': f"test-remote-{uuid.uuid4().hex[:8]}",
        'domain': DEFAULT_DOMAIN,
        'secure': True
    }
    
    logger.info(f"Creating remote agent client for {agent_info['name']}")
    agent = AgentClient(agent_info)
    
    try:
        # Test connection
        connection_result = agent.connect()
        if connection_result.get('connection') != 'okay':
            pytest.skip(f"Could not connect to remote agent: {connection_result}")
        
        agent.set_ingress_nodes(["P1"])
        agent.set_query_nodes(["P1"])
        
        yield agent
    except requests.exceptions.RequestException as e:
        pytest.skip(f"Network error connecting to remote agent: {str(e)}")


@pytest.fixture(scope="function")
def temp_directory():
    """Provides a temporary directory for a test function."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


@pytest.fixture(scope="function")
def sample_data():
    """Provides sample data for testing."""
    data = {
        "simple_strings": ["hello", "world", "test"],
        "nested_sequence": [
            {"strings": ["event1"], "vectors": [], "emotives": {}},
            {"strings": ["event2"], "vectors": [], "emotives": {}},
            {"strings": ["event3"], "vectors": [], "emotives": {}}
        ],
        "classification_data": [
            ({"strings": ["feature1", "feature2"], "vectors": [], "emotives": {}}, "class1"),
            ({"strings": ["feature2", "feature3"], "vectors": [], "emotives": {}}, "class2"),
            ({"strings": ["feature1", "feature3"], "vectors": [], "emotives": {}}, "class1")
        ]
    }
    return data


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "basic: mark a test as a basic functionality test")
    config.addinivalue_line("markers", "advanced: mark a test as an advanced functionality test")
    config.addinivalue_line("markers", "slow: mark a test as a potentially slow test")
    config.addinivalue_line("markers", "docker: mark a test as requiring Docker")
    

def pytest_collection_modifyitems(config, items):
    """Filter tests based on TEST_LEVEL environment variable."""
    if TEST_LEVEL == 'minimal':
        skip_non_basic = pytest.mark.skip(reason="Test skipped in minimal test level")
        for item in items:
            if 'basic' not in item.keywords:
                item.add_marker(skip_non_basic)
    elif TEST_LEVEL == 'standard':
        skip_slow = pytest.mark.skip(reason="Slow tests skipped in standard test level")
        for item in items:
            if 'slow' in item.keywords:
                item.add_marker(skip_slow)


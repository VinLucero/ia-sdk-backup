"""Integration tests for Docker functionality of the ia-sdk."""
import pytest
import requests
import time
import sys
import os
from pathlib import Path

# Add the src directory to the Python path
src_path = str(Path(__file__).parent.parent.parent.parent / "src")
sys.path.insert(0, src_path)

from ia.gaius.agent_client import AgentClient, AgentConnectionError

def test_docker_container_running(docker_container):
    """Test that the Docker container is running."""
    assert docker_container.status == "running"
    
    # Check container logs for error messages
    logs = docker_container.logs().decode('utf-8')
    assert "ERROR" not in logs, f"Found errors in container logs: {logs}"

def test_container_health_check(docker_container):
    """Test that the container is healthy and accepting HTTP requests."""
    # Simple HTTP request to check if the container is responding
    base_url = f"http://localhost:{docker_container.host_port}"
    max_retries = 5
    retry_delay = 2
    
    for attempt in range(max_retries):
        try:
            response = requests.get(f"{base_url}/health", timeout=5)
            if response.status_code == 200:
                break
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                continue
            pytest.fail(f"Failed to connect to container after {max_retries} attempts")
    
    assert response.status_code == 200, f"Health check failed with status code: {response.status_code}"
    health_data = response.json()
    assert health_data["status"] == "healthy", f"Container health status is not healthy: {health_data}"

def test_agent_client_connection(agent_config):
    """Test that the AgentClient can connect to the agent in the Docker container."""
    client = AgentClient(agent_config)
    
    # Try to connect
    connection_result = client.connect()
    
    # Verify connection was successful
    assert client._connected is True, "Agent client failed to connect"
    assert connection_result["connection"] == "okay", f"Connection result was not okay: {connection_result}"
    
    # Verify agent information
    assert client.genome is not None, "Agent genome is None after connection"
    assert client.gaius_agent is not None, "Agent info is None after connection"
    assert len(client.all_nodes) > 0, "No nodes found in agent"

def test_agent_client_query_operations(agent_config):
    """Test basic query operations with the agent in the Docker container."""
    client = AgentClient(agent_config)
    client.connect()
    
    # Set up nodes
    primitive_nodes = [node["name"] for node in client.all_nodes if "name" in node]
    if not primitive_nodes:
        pytest.skip("No primitive nodes found in agent")
    
    test_node = primitive_nodes[0]
    client.set_ingress_nodes([test_node])
    client.set_query_nodes([test_node])
    
    # Test status query
    status = client.show_status(nodes=[test_node])
    assert status is not None, "Failed to get status from agent"
    
    # Test simple observe operation
    test_data = {"strings": ["test_string"], "vectors": [], "emotives": {}}
    observe_result = client.observe(test_data, nodes=[test_node])
    assert observe_result is not None, "Failed to observe data in agent"
    
    # Test working memory after observe
    wm = client.get_wm(nodes=[test_node])
    assert wm is not None, "Failed to get working memory from agent"
    
    # Test clear working memory
    clear_result = client.clear_wm(nodes=[test_node])
    assert clear_result is not None, "Failed to clear working memory"

def test_agent_client_cleanup(agent_config):
    """Test that the AgentClient properly cleans up resources."""
    client = AgentClient(agent_config)
    client.connect()
    
    # Connect and disconnect multiple times to check for resource leaks
    for _ in range(3):
        # Create a new session by reconnecting
        client.connect()
        assert client._connected is True, "Agent client failed to reconnect"
        
        # Check if we can still make queries
        primitive_nodes = [node["name"] for node in client.all_nodes if "name" in node]
        if primitive_nodes:
            test_node = primitive_nodes[0]
            status = client.show_status(nodes=[test_node])
            assert status is not None, "Failed to get status after reconnection"


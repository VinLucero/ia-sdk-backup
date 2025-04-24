import os
import pytest
import docker
import time
import uuid
from typing import Dict, Generator

# Default Docker image settings
DEFAULT_DOCKER_IMAGE = "ia/gaius-agent:latest"
DEFAULT_DOCKER_PORT = 8080
DEFAULT_TIMEOUT = 30  # seconds

@pytest.fixture(scope="session")
def docker_client() -> docker.DockerClient:
    """Create a Docker client to interact with the Docker daemon."""
    client = docker.from_env()
    yield client
    client.close()

@pytest.fixture(scope="function")
def docker_container(docker_client: docker.DockerClient) -> Generator[docker.models.containers.Container, None, None]:
    """Create a Docker container for testing and ensure it's cleaned up after the test."""
    # Generate a unique container name to avoid conflicts
    container_name = f"test-gaius-agent-{uuid.uuid4().hex[:8]}"
    
    # Create the container
    container = docker_client.containers.run(
        DEFAULT_DOCKER_IMAGE,
        name=container_name,
        detach=True,
        ports={f"{DEFAULT_DOCKER_PORT}/tcp": None},  # Dynamically assign a host port
        environment={
            "GAIUS_API_KEY": "test-api-key",
            "GAIUS_AGENT_NAME": "test-agent",
            "LOG_LEVEL": "INFO"
        },
        remove=True,
        auto_remove=True,
    )
    
    # Wait for container to be ready
    start_time = time.time()
    while time.time() - start_time < DEFAULT_TIMEOUT:
        if container.status == "running":
            break
        time.sleep(1)
        container.reload()  # Refresh the container object
    
    if container.status != "running":
        raise Exception(f"Container {container_name} did not start in time")
    
    # Get the dynamically assigned host port
    container.reload()
    host_port = docker_client.api.inspect_container(container.id)['NetworkSettings']['Ports'][f"{DEFAULT_DOCKER_PORT}/tcp"][0]['HostPort']
    container.host_port = int(host_port)
    
    # Wait for agent to be ready
    # (In a real implementation, you might want to add additional checks)
    time.sleep(5)
    
    yield container
    
    # Cleanup - stop the container
    try:
        container.stop(timeout=5)
    except docker.errors.NotFound:
        # Container already removed
        pass

@pytest.fixture(scope="function")
def agent_config(docker_container) -> Dict:
    """Create an agent client configuration for connecting to the Docker container."""
    return {
        "api_key": "test-api-key",
        "name": "test-agent",
        "domain": f"localhost:{docker_container.host_port}",
        "secure": False
    }


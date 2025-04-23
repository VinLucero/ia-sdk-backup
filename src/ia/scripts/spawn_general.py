import logging
from typing import Set

import docker
import docker.errors as de
from docker.models.containers import Container

logging.basicConfig(format='%(asctime)s,%(msecs)03d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                    datefmt='%Y-%m-%d:%H:%M:%S')
logger = logging.getLogger(__name__)

def get_allocated_host_ports(dc: docker.DockerClient) -> Set[int]:
    """Get a list of the ports currently allocated by docker containers running on the provided DockerClient.

    Args:
        dc (docker.DockerClient): DockerClient to query

    Returns:
        Set[int]: set of port numbers
    """
    all_containers: list[Container] = dc.containers.list(all=True)
    all_ports = [c.ports for c in all_containers]

    all_host_ports = set()
    container_port_map: dict
    for container_port_map in all_ports:
        for _, list_of_binds in container_port_map.items():
            # print(f'{port=}, {list_of_binds=}')
            if not list_of_binds:
                continue
            all_host_ports.update(int(bind['HostPort']) for bind in list_of_binds)

    return all_host_ports

def spawn_container(container_name: str,
                    api_key: str,
                    ports: dict,
                    docker_image: str,
                    privileged: bool = False,
                    volumes: dict = None,
                    env: dict = None,
                    hostname: str = None):

    client = docker.from_env()

    if env is None:
        env = {}

    env['API_KEY'] = api_key

    if volumes is None:
        volumes = {}

    if hostname is None:
        hostname = container_name
    
    try:
        client.containers.run(image=docker_image,
                              init=True,
                              ports=ports,
                              privileged=privileged,
                              name=container_name,
                              volumes=volumes,
                              environment=env,
                              detach=True,
                              hostname=hostname)

    except de.ImageNotFound as e:
        logger.error(f'Image not found: {str(e)}')
        raise Exception(f'Failed to start Container: {str(e)}')

    except de.APIError as e:
        logger.error(f'Docker API Error: {str(e)}')
        raise Exception(f'Failed to start Container: {str(e)}')

    return True

def create_docker_network(network_name: str) -> None:
    
    try:
        # create docker network for comcom
        client = docker.from_env()
        client.networks.create(name=network_name)
    
    except de.APIError as docker_error:
        logger.exception('Exception while making docker network')
        raise

def kill_container(container_name: str) -> bool:

    client = docker.from_env()

    try:
        logger.debug(f"attempting to remove container {container_name}")
        tf: Container = client.containers.get(container_name)
        # tf.kill()
        tf.stop()
        tf.remove(force=True)
    except de.NotFound as e:
        logger.error(
            f'Container {container_name} not found: {str(e)}')
        return True
    except de.APIError as e:
        logger.error(f'Docker API Error: {str(e)}')
        raise Exception(f'Failed to kill container {str(e)}')
    return True



def connect_networks_container(networks: list, container_name: str):
    client = docker.from_env()

    try:
        container = client.containers.get(container_name)

        docker_networks = client.networks.list(names=networks)
        for net in docker_networks:
            logger.info(f'Connecting to {net.name}')
            try:
                net.connect(container)
            except de.APIError as e:
                logger.error(f'Docker API Error: {str(e)}')
                pass  # already connected on network
    except de.NotFound as e:
        logger.error(
            f'Container {container_name} not found: {str(e)}')
        return False
    except de.APIError as e:
        logger.error(f'Docker API Error: {str(e)}')
        raise Exception(f'Docker API Error: {str(e)}')

    return True


def get_docker_bridge_ip() -> str:
    client = docker.from_env()

    try:

        bridge = client.networks.get('bridge')
        bridge_ip: str = bridge.attrs['IPAM']['Config'][0]['Gateway']
        logger.debug(f'Docker bridge IP = {bridge_ip}')
        return bridge_ip

    except Exception as bridge_error:
        logger.exception(
            f'Exception while retrieving docker bridge IP address: {str(bridge_error)}')
        raise

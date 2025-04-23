#!/usr/bin/env python3
import json
import logging
import os
import shutil
import subprocess
import uuid
from contextlib import contextmanager
from copy import deepcopy
from pathlib import Path
from typing import Dict, List, Union

import docker
import docker.errors as de
import platformdirs as plat
import tempfile
from filelock import FileLock, Timeout

from ia.gaius.agent_client import AgentClient
from ia.gaius.experimental.comcom_client import COMCOMClient
from ia.scripts.spawn_agent import delete_docker_network, start_agent, stopit
from ia.scripts.spawn_general import (connect_networks_container,
                                      create_docker_network,
                                      get_docker_bridge_ip, kill_container,
                                      spawn_container)

logger = logging.getLogger(__name__)

agent_manager_lock_path = os.path.join(tempfile.gettempdir(), 'ia_agent_manger.lock')
agent_manager_lock = FileLock(lock_file=agent_manager_lock_path, timeout=-1)
class AgentInfo:
    def __init__(self,
                 user_id: str,
                 agent_id: str,
                 agent_name: str,
                 genome_name: str = None,
                 genome_file: str = None,
                 agent_config=None,
                 location: str = 'local',
                 LOG_LEVEL=logging.INFO,
                 api_key="ABCD-1234",
                 genome_dir=None,
                 agents_dir=None,
                 genome=None,
                 single_container: bool = False,
                 local_agent_config=None,
                 version='latest',
                 **kwargs):
        """Wrapper class for Agent information. Used to start/stop agents, and save config information to a central location

        Args:
            user_id (str): User id attached to docker contaienrs spawned using AgentInfo
            agent_id (str): Agent id attached to docker containers spawned using AgentInfo
            agent_name (str): Descriptive, user-friendly name to refer to agent by
            genome_name (str, optional): If genome already in centralized location, refer to it by its name
            genome_file (str, optional): To copy outside genome into genome store, provide filepath here
            agent_config (_type_, optional): Stores AgentConfig details once agent is spawned.
            location (str, optional): In future will support spawning at several locations (local, private cloud, DigitalOcean, etc). Defaults to 'local'.
            LOG_LEVEL (logging.LEVEL, optional): Used to control verbosity of messages in agent spawn script. Defaults to logging.INFO.
            api_key (str, optional): Used to set API KEY of spawned agent. Defaults to "ABCD-1234"
        """
        self.data_dir = plat.user_data_dir(
            appname="IA_SDK_AgentManager", appauthor="IntelligentArtifacts")
        self.genome_dir = f'{self.data_dir}/genomes'
        if genome_dir:
            self.genome_dir = genome_dir
        self.agents_dir = f'{self.data_dir}/agents'
        if agents_dir:
            self.agents_dir = agents_dir

        if genome_name:
            self.genome_name = genome_name
        else:
            self.genome_name = os.path.basename(genome_file)
            if os.path.exists(f'{self.genome_dir}/{self.genome_name}'):
                logger.debug(
                    f'copying genome to genome dir would overwrite current genome {os.path.basename(genome_file)}, using genome already present')
            else:
                shutil.copyfile(src=genome_file,
                                dst=f'{self.genome_dir}/{self.genome_name}')

        self.genome_file = f'{self.genome_dir}/{self.genome_name}'
        self.user_id = user_id
        self.agent_id = agent_id
        self.location = location
        self.agent_name = agent_name
        self.agent_config = agent_config
        self.local_agent_config = local_agent_config
        self.api_key = api_key
        self.single_container = single_container
        self.version = version

        self.genome = genome
        if self.genome is None:
            with open(self.genome_file) as f:
                self.genome = json.load(f)
                if self.single_container:
                    self.genome['communication_protocol'] = 'uds'

    def check_running(self):
        """Check if we can access the agent

        Returns:
            bool: True for success, False for failure
        """
        if self.location == 'local':
            agent = AgentClient(bottle_info=self.agent_config)
            try:
                agent.set_timeout(10)
                agent.connect()
            except Exception:
                return False

            return True

        else:
            raise Exception(f'unknown location {self.location}')

    def delete_config_file(self):
        """Kill agent and delete config information from agents directory
        """
        self.kill_agent()
        if os.path.exists(f'{self.agents_dir}/{self.agent_name}'):
            os.remove(f'{self.agents_dir}/{self.agent_name}')
        return f"deleted {self.agents_dir}/{self.agent_name}"

    def save_config_file(self):
        """Store config information for agent in agents directory, based on agent name
        """
        with open(f'{self.agents_dir}/{self.agent_name}', 'w') as f:
            json.dump(obj=self.toJSON(), fp=f)

        logger.info(f'saved to {self.agents_dir}/{self.agent_name}')
        return f'{self.agents_dir}/{self.agent_name}'

    def kill_agent(self):
        """Attempt to kill a running agent
        """
        stopit(self.genome, user_id=self.user_id, agent_id=self.agent_id)

    def spawn(self, connect_jia=True):
        """Start a new agent using information provided in constructor

        Args:
            api_key (str, optional): API Key for agent. Defaults to "ABCD-1234".
        """
        # with open(self.genome_file, 'r') as f:
        #     genome = json.load(f)

        json_obj = {'agent_id': self.agent_id,
                    'user_id': self.user_id,
                    'kill': False,
                    'network': None,
                    'api_key': self.api_key,
                    'genome': self.genome,
                    'version': self.version}

        self.save_config_file()
        try:
            self.agent_config, ports = start_agent(json_obj=json_obj)
            self.local_agent_config = {'name': '',
                                       'domain': f'localhost:{ports["80/tcp"]}',
                                       'api_key': self.api_key,
                                       'secure': False}
            logger.debug(
                f'updating config file with new agent config: {self.agent_config}')
            self.save_config_file()
        except de.DockerException as spawn_error:
            logger.exception(
                "Received exception while spawning agent. Cleaning up and re-raising")
            self.delete_config_file()
            raise spawn_error

        if connect_jia:
            self.connect_jia()

        return json.loads(json.dumps(self.agent_config))

    def get_docker_networks(self):
        """Get names of networks this agent is a part of (uses gaius-api-{user_id}-{agent_id})

        Raises:
            Exception: More that one container found with same name

        Returns:
            _type_: list of networks
        """
        docker_client = docker.from_env()
        gapi_container = docker_client.containers.list(
            filters={'name': f'gaius-api-{self.user_id}-{self.agent_id}'})
        gapi_container = [container for container in gapi_container if container.name ==
                          f'gaius-api-{self.user_id}-{self.agent_id}']
        if len(gapi_container) == 1:
            gapi_container = gapi_container[0]
            return list(gapi_container.attrs['NetworkSettings']['Networks'].keys())
        elif len(gapi_container) > 1:
            self.delete_config_file()
            raise Exception(
                'too many docker containers with same GAIuS API name')
        else:
            raise Exception('gaius-api container not found, start agent first')

    def connect_jia(self):
        """Connect agent to jia (add jia to the agent's network)
        """
        docker_client = docker.from_env()
        jias = docker_client.containers.list()
        jias = [container for container in jias if any(
            ['registry.digitalocean.com/intelligent-artifacts/jia' in tag for tag in container.image.tags])]
        nets = self.get_docker_networks()
        nets = docker_client.networks.list(names=nets)
        if len(jias) == 0:
            logger.info("No JIA notebooks found! Skipping...")
        elif len(jias) == 1:
            logger.info(f'connecting single jia')
            jia = docker_client.containers.get(
                jias[0].short_id)  # .attrs['Config']['Name']
            for net in nets:
                net.reload()
                if jia.id in [cont.id for cont in net.containers]:
                    logger.info(f'jia already connected to network {net.name}')
                    continue
                net.connect(jia)
                logger.info(f"Connecting JIA id: {jia.name} on {net.name}")
        elif len(jias) > 1:
            def connect_jia_func():
                logger.info(
                    "More than one JIA found. Please select which to connect:")
                for c, i in enumerate(jias):
                    x = int(input(f"    {i}: {c} {c.name} connect? Y/N - "))
                    if x.lowercase() == 'y':
                        for net in nets:
                            net.reload()
                            if c.id in [cont.id for cont in net.containers]:
                                logger.info(
                                    f'jia already connected to network {net.name}')
                                continue
                            net.connect(c)
                            logger.info(
                                f"Connecting JIA id: {c.name} on {net.name}")
                    else:
                        logger.info("Invalid entry. Try again...")

    def get_agent_client(self, local: bool = False):
        """Retreive AgentClient object from started agent

        Returns:
            ia.gaius.agent_client.AgentClient
        """
        if self.agent_config == None:
            raise Exception(
                'agent_config information empty, must start agent first')
        elif local:
            return AgentClient(bottle_info=self.local_agent_config)

        return AgentClient(bottle_info=self.agent_config)

    def toJSON(self):
        """Dump config information to a JSON object (dict)

        Returns:
            dict: config information
        """
        return {'genome_name': self.genome_name,
                'genome_file': self.genome_file,
                'agent_id': self.agent_id,
                'user_id': self.user_id,
                'agent_name': self.agent_name,
                'location': self.location,
                'agent_config': self.agent_config,
                'local_agent_config': self.local_agent_config,
                'api_key': self.api_key,
                'genome_dir': str(self.genome_dir),
                'agents_dir': str(self.agents_dir),
                'genome': json.dumps(self.genome),
                'single_container': self.single_container
                }

    @classmethod
    def fromFile(cls, filepath: Union[str, Path]):
        """Construct AgentInfo object from file

        Args:
            filepath (str): path to file to load

        Returns:
            AgentInfo: AgentInfo object created from the file
        """
        with open(filepath, 'r') as f:
            json_obj = json.load(f)

        return cls.fromJSON(json_obj=json_obj)

    @classmethod
    def fromJSON(cls, json_obj):
        """Construct AgentInfo from JSON object

        Args:
            json_obj (dict): Contains fields necessary for constructing AgentInfo

        Returns:
            AgentInfo: AgentInfo object created from JSON object
        """
        return cls(**json_obj)


class TFInfo:
    def __init__(self,
                 user_id: str,
                 tf_id: str,
                 tf_name: str,
                 location: str,
                 api_key: str,
                 thinkflux_dir: str,
                 docker_image: str,
                 port: int,
                 privileged: bool = False,
                 environment: dict = None,
                 volumes: dict = None,
                 **kwargs) -> None:

        if volumes is None:
            volumes = {}
        if environment is None:
            environment = {}

        self.user_id = user_id
        self.tf_id = tf_id
        self.tf_name = tf_name
        self.location = location
        self.api_key = api_key
        self.thinkflux_dir = thinkflux_dir
        self.docker_image = docker_image
        self.port = port
        self.privileged = privileged
        self.volumes = volumes
        self.environment = environment
        self.container_name = f'tf-{user_id}-{tf_id}'

    def spawn(self) -> bool:

        if spawn_container(container_name=self.container_name,
                           api_key=self.api_key,
                           ports={'8080/tcp': self.port},
                           docker_image=self.docker_image,
                           env=self.environment,
                           volumes=self.volumes):
            self.save_config_file()
            return True

        return False

    def kill(self):
        kill_container(self.container_name)
        return self.delete_config_file()

    def delete_config_file(self):
        """delete config information from agents directory
        """
        if os.path.exists(f'{self.thinkflux_dir}/{self.tf_name}'):
            os.remove(f'{self.thinkflux_dir}/{self.tf_name}')
        return f"deleted {self.thinkflux_dir}/{self.tf_name}"

    def save_config_file(self):
        """Store config information for agent in agents directory, based on agent name
        """
        with open(f'{self.thinkflux_dir}/{self.tf_name}', 'w') as f:
            json.dump(obj=self.toJSON(), fp=f)

        logger.debug(f'saved to {self.thinkflux_dir}/{self.tf_name}')
        return f'{self.thinkflux_dir}/{self.tf_name}'

    def connect_agents(self, agents: List[AgentInfo]):
        nets = set()
        for agent in agents:
            nets.update(agent.get_docker_networks())

        logger.debug(f'{nets=}')
        if not connect_networks_container(networks=list(nets), container_name=self.container_name):
            return False

        return True

    def toJSON(self):
        """Dump config information to a JSON Object

        Returns:
            dict: config information
        """
        return {'user_id': self.user_id,
                'tf_id': self.tf_id,
                'tf_name': self.tf_name,
                'location': self.location,
                'api_key': self.api_key,
                'port': self.port,
                'thinkflux_dir': str(self.thinkflux_dir),
                'docker_image': self.docker_image,
                'environment': self.environment,
                'privileged': self.privileged,
                'volumes': self.volumes
                }

    @classmethod
    def fromFile(cls, filepath: Union[str, Path]):
        """Construct AgentInfo object from file

        Args:
            filepath (str): path to file to load

        Returns:
            AgentInfo: AgentInfo object created from the file
        """
        with open(filepath, 'r') as f:
            json_obj = json.load(f)

        return cls.fromJSON(json_obj=json_obj)

    @classmethod
    def fromJSON(cls, json_obj):
        """Construct AgentInfo from JSON object

        Args:
            json_obj (dict): Contains fields necessary for constructing AgentInfo

        Returns:
            AgentInfo: AgentInfo object created from JSON object
        """
        return cls(**json_obj)


class ComcomInfo:
    def __init__(self,
                 comcom_id: str,
                 name: str,
                 location: str,
                 api_key: str,
                 save_dir: str,
                 docker_image: str,
                 port: int,
                 additional_ports: Dict[str, int] = {},
                 volumes: dict = None
                 ) -> None:
        """Construct a ComcomInfo object. Used to manage spawning and connecting
        Comcom docker containeres with agents and thinkflux instances

        Args:
            comcom_id (str): Unique identifier attached to Comcom docker container spawned using this object
            name (str): Human friendly name used to retrieve ComcomInfo from AgentManager
            location (str): Where to spawn this Comcom. Currently only supports "local"
            api_key (str): api key passed to docker container in environment variable
            save_dir (str): where ComcomInfo objects are to be saved (as file)
            docker_image (str): Specific docker image to utilize when spawning Comcom
            port (int): Port which Comcom will be connected to
        """

        self.comcom_id = comcom_id
        self.name = name
        self.location = location
        self.api_key = api_key
        self.port = port
        self.save_dir = save_dir
        self.docker_image = docker_image
        self.container_name = f'Comcom-{comcom_id}'
        self._mongo_container_name = f'{self.container_name}-kb'
        self._redis_container_name = f'{self.container_name}-redis-kb'
        self._network_name=f'g2network-{self.container_name}'
        self.additional_ports = additional_ports
        self.volumes = volumes

    def spawn(self) -> bool:

        ports = list(range(7510, 7600))
        port_range_dict = {f'{port}/udp': port for port in ports}

        # docker_bridge_ip = get_docker_bridge_ip()
        comcom_ports = {'8081/tcp': self.port,
                        }

        comcom_ports.update(port_range_dict)
        # add additional ports
        comcom_ports.update(self.additional_ports)
        
        
        try:
            spawn_container(container_name=self._mongo_container_name,
                        hostname='comcom-kb',
                        api_key='b1',
                        docker_image='mongo:latest',
                        ports={})

            spawn_container(container_name=self._redis_container_name,
                        hostname='comcom-redis-kb',
                        api_key='b1',
                        docker_image='redis:latest',
                        ports={})
            
            logger.debug("COMCOM database containers spawned, now spawning COMCOM proper.")

            spawn_container(container_name=self.container_name,
                        api_key=self.api_key,
                        ports=comcom_ports,
                        docker_image=self.docker_image,
                        volumes=self.volumes)
        
        
            create_docker_network(network_name=self._network_name)
            
            connect_networks_container(networks=[self._network_name], container_name=self.container_name)
            connect_networks_container(networks=[self._network_name], container_name=self._mongo_container_name)
            connect_networks_container(networks=[self._network_name], container_name=self._redis_container_name)
        except Exception as error:
            logger.exception("Failed to start Comcom")
            self.kill()
            raise

        self.save_config_file()

        return True

    def get_comcom_client(self, local: bool = False) -> COMCOMClient:
        """Create A COMCOMClient instance corresponding to the spawned Comcom 

        Args:
            local (bool, optional): Whether to use container_name or localhost to connect. Defaults to False.

        Returns:
            COMCOMClient
        """
        domain = f"{self.container_name}:{self.port}"
        if local:
            domain = f"localhost:{self.port}"
            
        comcom_details = {
            "name" : "",
            "domain" : domain,
            "api_key" : self.api_key,
            "secure" : True
        }
        return COMCOMClient(comcom_details, verify=False)
        
    def kill(self):
        """Kill Comcom and delete container
        """
        kill_container(self.container_name)
        kill_container(self._mongo_container_name)
        kill_container(self._redis_container_name)
        delete_docker_network(docker_client=docker.from_env(), network_name=self._network_name)
        return self.delete_config_file()

    def delete_config_file(self):
        """delete config file information
        """
        if os.path.exists(f'{self.save_dir}/{self.name}'):
            os.remove(f'{self.save_dir}/{self.name}')
        return f"deleted {self.save_dir}/{self.name}"

    def save_config_file(self):
        """Store config information, based on comcom name
        """
        with open(f'{self.save_dir}/{self.name}', 'w') as f:
            json.dump(obj=self.toJSON(), fp=f)

        logger.debug(f'saved to {self.save_dir}/{self.name}')
        return f'{self.save_dir}/{self.name}'

    def connect_agents(self, agents: List[AgentInfo]):
        """Connect agents to Comcom docker network

        Args:
            agents (List[AgentInfo]): list of AgentInfo objects to connect to network
        """
        nets = set()
        for agent in agents:
            nets.update(agent.get_docker_networks())

        logger.debug(f'{nets=}')
        if not connect_networks_container(networks=list(nets), container_name=self.container_name):
            return False

        return True

    def toJSON(self):
        """Dump config information to a JSON Object

        Returns:
            dict: config information
        """
        return {
            'comcom_id': self.comcom_id,
            'name': self.name,
            'location': self.location,
            'api_key': self.api_key,
            'port': self.port,
            'additional_ports': self.additional_ports,
            'save_dir': str(self.save_dir),
            'docker_image': self.docker_image,
        }

    @classmethod
    def fromFile(cls, filepath: Union[str, Path]):
        """Construct AgentInfo object from file

        Args:
            filepath (str): path to file to load

        Returns:
            AgentInfo: AgentInfo object created from the file
        """
        with open(filepath, 'r') as f:
            json_obj = json.load(f)

        return cls.fromJSON(json_obj=json_obj)

    @classmethod
    def fromJSON(cls, json_obj):
        """Construct AgentInfo from JSON object

        Args:
            json_obj (dict): Contains fields necessary for constructing AgentInfo

        Returns:
            AgentInfo: AgentInfo object created from JSON object
        """
        return cls(**json_obj)


class AgentManager:
    def __init__(self,
                 genome_dir: Path = None,
                 agents_dir: Path = None,
                 thinkflux_dir: Path = None,
                 comcom_dir: Path = None,
                 local: bool = False):
        """Initialize AgentManager object (setup dirs, etc.)

        This object can be used to spawn Agents using the start_agent() method.
        """
        self.data_dir = plat.user_data_dir(
            appname="IA_SDK_AgentManager", appauthor="IntelligentArtifacts")
        self.genome_dir = Path(f'{self.data_dir}/genomes')
        if genome_dir:
            self.genome_dir = Path(genome_dir)
        self.agents_dir = Path(f'{self.data_dir}/agents')
        if agents_dir:
            self.agents_dir = Path(agents_dir)

        self.thinkflux_dir = Path(f'{self.data_dir}/thinkflux')
        if thinkflux_dir:
            self.thinkflux_dir = Path(thinkflux_dir)

        self.comcom_dir = Path(f'{self.data_dir}/comcom')
        if comcom_dir:
            self.comcom_dir = Path(comcom_dir)

        self.config_file = f'{self.data_dir}/config.json'
        self.local = local
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir, exist_ok=True)
        logger.info(f'   agents dir: {self.agents_dir}')
        logger.info(f'   genome dir: {self.genome_dir}')
        logger.info(f'thinkflux dir: {self.thinkflux_dir}')
        logger.info(f'   comcom_dir: {self.comcom_dir}')

        self.current_agents: Dict[str, AgentInfo] = {}
        self.current_tfs: Dict[str, TFInfo] = {}
        self.current_comcoms: Dict[str, ComcomInfo] = {}

        with agent_manager_lock:
            if not os.path.exists(self.genome_dir):
                os.makedirs(self.genome_dir, exist_ok=True)

            if not os.path.exists(self.agents_dir):
                os.makedirs(self.agents_dir, exist_ok=True)

            if not os.path.exists(self.thinkflux_dir):
                os.makedirs(self.thinkflux_dir, exist_ok=True)

            if not os.path.exists(self.comcom_dir):
                os.makedirs(self.comcom_dir, exist_ok=True)


            self.update_current_agents()

    def start_hoster(self):
        """Start `dvdarias/docker-hoster <https://github.com/dvddarias/docker-hoster>`_ docker container to resolve
        container hostnames into IP addresses. More friendly for AgentManager usage"""
        START_COMMAND = """
        if [ ! "$(docker ps -a -q -f name=docker-hoster)" ]; then
            if [ "$(docker ps -aq -f status=exited -f name=docker-hoster)" ]; then
                # cleanup
                docker rm docker-hoster
            fi
            # run your container
            
            docker run -d --rm\
                    -v /var/run/docker.sock:/tmp/docker.sock \
                    -v /etc/hosts:/tmp/hosts \
                    --name docker-hoster \
                    dvdarias/docker-hoster
        fi
        """
        output = subprocess.run(START_COMMAND, capture_output=True, shell=True)
        if output.returncode != 0:
            raise Exception(
                f'Starting hoster failed with exitcode {output.returncode}')
        return

    def stop_hoster(self):
        """Stop `dvdarias/docker-hoster <https://github.com/dvddarias/docker-hoster>`_ docker container"""
        STOP_COMMAND = """
        if [ "$(docker ps -a -q -f name=docker-hoster)" ]; then
            docker rm --force docker-hoster;
        fi
        
        """
        output = subprocess.run(STOP_COMMAND,
                                capture_output=True,
                                shell=True)
        if output.returncode != 0:
            raise Exception(
                f'Stopping hoster failed with exitcode {output.returncode}')
        return

    def start_tf(self,
                 tf_name: str,
                 api_key: str,
                 docker_image: str,
                 port: int = 8090,
                 user_id: str = 'tf',
                 tf_id: str = '1',
                 environment: dict = None,
                 privileged: bool = None,
                 volumes: dict = None,
                 agents_to_connect: list = None) -> TFInfo:
        """Spawn a Thinkflux container using provided config. Store config in AgentManager

        Container name is defined as:
            "tf-{user_id}-{tf_id}"

        Args:
            tf_name (str): descriptive name "alias" for Thinkflux
            api_key (str): Passed as API_KEY env variable to container
            docker_image (str): Container image to spawn. E.g. "registry.digitalocean.com/intelligent-artifacts/thinkflux:develop"
            port (int, optional): _description_. Defaults to 8090.
            user_id (str, optional): user_id portion of container extension. Defaults to 'tf'.
            tf_id (str, optional): tf_id portion of container extension. Defaults to '1'.
            environment (dict, optional): additional environment variables to provide to container, as key-value pairs. Defaults to None.
            privileged (bool, optional): run container in privileged mode. Defaults to None.
            volumes (dict, optional): volumes to mount in container as key-value pairs. Defaults to None.
            agents_to_connect (list, optional): list of agents to connect to Thinkflux. Defaults to None.

        Raises:
            Exception: If invalid agents passed in agents_to_connect
            Exception: If tf_name already exists in AgentManager
            Exception: If a thinkflux with user_id and tf_id already exists in AgentManager

        Returns:
            TFInfo: Object corresponding to spawned Thinkflux
        """
        with agent_manager_lock:
            self.update_current_agents()

            agents = []

            if agents_to_connect is None:
                agents_to_connect = []

            for agent_name in agents_to_connect:
                if isinstance(agent_name, AgentInfo):
                    agents.append(agent_name)

                elif isinstance(agent_name, str):

                    if agent_name not in self.current_agents:
                        raise KeyError(
                            f'Agent {agent_name} not found in current agents')
                    agents.append(self.current_agents[agent_name])

                else:
                    raise Exception(
                        f"Invalid agent found in agents_to_connect: {agent_name}")

            if tf_name in self.current_tfs:
                raise Exception(f'Thinkflux({tf_name}) already exists')
                pass

            for name, tf in self.current_tfs.items():
                if tf.tf_id == tf_id and tf.user_id == user_id:
                    raise Exception(
                        f'Thinkflux({name}) with user_id {user_id} and tf_id {tf_id} already exists, please choose other ids')

            tf = TFInfo(user_id=user_id,
                        tf_id=tf_id,
                        tf_name=tf_name,
                        location='local',
                        api_key=api_key,
                        thinkflux_dir=self.thinkflux_dir,
                        docker_image=docker_image,
                        port=port,
                        environment=environment,
                        privileged=privileged,
                        volumes=volumes)
            
            tf.spawn()
            self.update_current_agents()  # update agents after spawn, before linking networks
            logger.debug(f'{agents=}')
            tf.connect_agents(agents=agents)

            return tf

    def delete_tf(self,
                  tf_name: str):
        """Kill a Thinkflux container using it's tf_name attribute

        Args:
            tf_name (str): attribute passed when spawning Thinkflux

        Raises:
            Exception: When config not found
        """
        with agent_manager_lock:
            if tf_name not in self.current_tfs:
                raise Exception(f'Thinkflux({tf_name}) not found in current_tfs')

            tf: TFInfo = self.current_tfs[tf_name]
            tf.kill()

            self.update_current_agents()

    def start_comcom(self,
                     name: str,
                     api_key: str,
                     docker_image: str,
                     port: int = 8081,
                     comcom_id: str = '1',
                     agents_to_connect: list = None,
                     additional_ports : Dict[str, int] = {},
                     volumes: dict = None) -> ComcomInfo:

        with agent_manager_lock:
            self.update_current_agents()

            agents = []

            if agents_to_connect is None:
                agents_to_connect = []

            for agent_name in agents_to_connect:
                if isinstance(agent_name, AgentInfo):
                    agents.append(agent_name)

                elif isinstance(agent_name, str):
                    if agent_name not in self.current_agents:
                        raise KeyError(
                            f'Agent {agent_name} not found in current agents')
                    agents.append(self.current_agents[agent_name])

            if name in self.current_comcoms:
                raise Exception(f'Comcom({name}) already exists')
                pass

            for name, comcom in self.current_comcoms.items():
                if comcom.comcom_id == comcom_id:
                    raise Exception(
                        f'Comcom({name}) with comcom_id {comcom_id} already exists, please choose other ids')

            comcom = ComcomInfo(comcom_id=comcom_id,
                                name=name,
                                location='local',
                                api_key=api_key,
                                save_dir=self.comcom_dir,
                                docker_image=docker_image,
                                port=port,
                                additional_ports=additional_ports,
                                volumes=volumes
                                )

            comcom.spawn()
            self.update_current_agents()  # update agents after spawn, before linking networks
            logger.debug(f'{agents=}')
            try:
                comcom.connect_agents(agents=agents)
            except Exception as connect_agents_error:
                logger.exception(f'Failed to connect agents to comcom')
                comcom.kill()
                raise

            return comcom

    def delete_comcom(self,
                      name: str):
        with agent_manager_lock:
            if name not in self.current_comcoms:
                raise Exception(
                    f'Comcom({name}) not found in current_comcoms')

            comcom: ComcomInfo = self.current_comcoms[name]
            comcom.kill()

            self.update_current_agents()

    def start_agent(self,
                    genome_file=None,
                    genome_name=None,
                    user_id: str = 'jia',
                    agent_id: str = '1',
                    agent_name=None,
                    connect_jia=True,
                    api_key='ABCD-1234',
                    single_container=False,
                    **kwargs) -> AgentInfo:
        """Spawn an agent and save its information in the localized agents dir

        .. note:: 

            If you wish to use a genome that has not been used by the AgentManager before,
            pass it in the genome_file field. This will retrieve the genome from the specified path,
            and save it in the localized genome dir for future use.


        Args:
            genome_file (str, optional): Path to outside genome file. Defaults to None.
            genome_name (str, optional): Name of genome in the localized genome dir. Defaults to None.
            user_id (str, optional): user id for naming docker containers. Defaults to 'jia'.
            agent_id (str, optional): agent id for naming docker containers. Defaults to '1'.
            agent_name (_type_, optional): descriptive name "alias" for agent. Defaults to None.
            connect_jia (bool, optional): Whether to attempt to connect agent to Jia docker container. Defaults to True.
            api_key (str, optional): Control the api key used to access agent. Defaults to 'ABCD-1234'.

        Raises:
            Exception: If there is a conflicting agent with user_id and agent_id already present/alive

        Returns:
            AgentInfo: AgentInfo object corresponding to started agent. can be used to retrieve
            AgentClient object using AgentInfo.get_agent_client()
        """
        if agent_name is None:
            agent_name = f'agent-{uuid.uuid4().hex[:8]}'

        with agent_manager_lock:
            self.update_current_agents()
            for name, agent in self.current_agents.items():
                if agent.agent_id == agent_id and agent.user_id == user_id:
                    raise Exception(
                        f'Agent({name}) with user_id {user_id} and agent_id {agent_id} already exists, please choose other ids')

            agent = AgentInfo(agent_id=agent_id,
                            user_id=user_id,
                            genome_file=genome_file,
                            genome_name=genome_name,
                            agent_name=agent_name,
                            api_key=api_key,
                            genome_dir=str(self.genome_dir),
                            agents_dir=str(self.agents_dir),
                            single_container=single_container,
                            **kwargs)
            try:
                agent.spawn(connect_jia=connect_jia)
            except Exception:
                logger.exception("Failed to spawn agent, cleaning up")
                agent.delete_config_file()
                raise
            self.update_current_agents()
            logger.info(f'started agent {agent.agent_name}')
            return agent

    def get_all_agent_status(self):
        """Get the status of all agents in current_agents dict

        Returns:
            dict: { agent_name : alive? }
        """
        with agent_manager_lock:
            agent_status = {}
            for agent_name, agent in self.current_agents.items():
                try:
                    agent_status[agent_name] = agent.check_running()
                except Exception as error:
                    logger.exception(
                        f'Error checking status of agent {agent_name}: {str(error)}')
                    agent_status[agent_name] = False
                    pass

            return agent_status

    def delete_agent(self, agent_name):
        """Stop/Delete agent & remove config file from agents_dir

        Args:
            agent_name (str): name of agent to stop

        Returns:
            str: string depicting deletion status
        """
        with agent_manager_lock:
            result = self.current_agents[agent_name].delete_config_file()
            del self.current_agents[agent_name]
            self.update_current_agents()
            return result

    def list_genomes(self):
        """List the genomes present in the localized genome store

        Returns:
            list: list of genome files 
        """
        return os.listdir(self.genome_dir)

    def delete_genome(self, genome_name):
        """Delete genome from centralized genome_dir

        Args:
            genome_name (str): genome name to delete
        """
        with agent_manager_lock:
            for name, agent in self.current_agents.items():
                if agent.genome_name == genome_name:
                    raise Exception(
                        f'Genome {genome_name} in use by Agent {name}. Please kill agent before removing genome')
            genome_path = os.path.join(self.genome_dir, genome_name)
            logger.debug(f'will remove genome {genome_path}')
            os.remove(genome_path)
            return

    def get_genome(self, genome_name):
        """Get genome by name, return as dict

        Args:
            genome_name (str): filename for genome in genome_dir

        Raises:
            Exception: When genome not found

        Returns:
            dict: contents of genome file
        """
        genome_path = os.path.join(self.genome_dir, genome_name)

        if genome_name not in self.list_genomes():
            raise Exception(
                f'{genome_name} not in genome dir: {self.list_genomes()}')
        with open(genome_path, 'r') as f:
            return json.load(f)

    def add_genome(self, genome_file: dict):
        """add genome from provided filepath

        Args:
            genome_file (str): genome file to add to AgentManager

        Raises:
            Exception: When genome not found

        Returns:
            dict: contents of genome file
        """
        self.genome_name = os.path.basename(genome_file)
        if os.path.exists(f'{self.genome_dir}/{self.genome_name}'):
            logger.warn(
                f'copying genome to genome dir would overwrite current genome {os.path.basename(genome_file)}, delete old genome before adding new genome')
        else:
            shutil.copyfile(src=genome_file,
                            dst=f'{self.genome_dir}/{self.genome_name}')

    def update_current_agents(self):
        """Update AgentManager's list of configured agents, thinkflux, comcom, genomes
        """

        # retrieve all agent files
        with agent_manager_lock:
            self.current_agents = os.listdir(self.agents_dir)
            self.current_tfs = os.listdir(self.thinkflux_dir)
            self.current_comcoms = os.listdir(self.comcom_dir)

        # get full paths of agent files
        self.current_agents = [self.agents_dir.joinpath(
            agent) for agent in self.current_agents]

        self.current_tfs = [self.thinkflux_dir.joinpath(
            tf) for tf in self.current_tfs]

        self.current_comcoms = [self.comcom_dir.joinpath(
            comcom) for comcom in self.current_comcoms]

        # instantiate AgentInfo classes
        self.current_agents = [AgentInfo.fromFile(
            agent) for agent in self.current_agents]

        self.current_tfs = [TFInfo.fromFile(
            tf) for tf in self.current_tfs]

        self.current_comcoms = [ComcomInfo.fromFile(
            comcom) for comcom in self.current_comcoms]

        # make current agents into a dict by agent_name
        self.current_agents = {
            agent.agent_name: agent for agent in self.current_agents}
        self.current_tfs = {tf.tf_name: tf for tf in self.current_tfs}
        self.current_comcoms = {
            comcom.name: comcom for comcom in self.current_comcoms}

    def remediate_dead_agents(self):
        """Remove all agents that cannot be pinged.
        """

        agent_status = self.get_all_agent_status()

        killed_agents = []
        for agent_name, alive in agent_status.items():
            if not alive:
                with agent_manager_lock:
                    logger.debug(f'{agent_name} is not alive, cleaning up')
                    self.delete_agent(agent_name)
                    killed_agents.append(agent_name)

        logger.debug(f'{killed_agents=}')

    def kill_all_agents(self, update=True):
        """Kill all agents known to AgentManager

        Args:
            update (bool, optional): Whether to update AgentManager information before killing containers. Defaults to True.
        """
        with agent_manager_lock:
            if update:
                self.update_current_agents()

            # We modify the dicts during iteration,
            # so we use this funky syntax
            for agent_name in list(self.current_agents.keys()):
                logger.info(f"Killing agent {agent_name}")
                self.delete_agent(agent_name=agent_name)

            for tf_name in list(self.current_tfs.keys()):
                self.delete_tf(tf_name=tf_name)

            for comcom_name in list(self.current_comcoms.keys()):
                self.delete_comcom(name=comcom_name)

    @contextmanager
    def agent_context(self,
                      genome_file: str = None,
                      genome_name: str = None,
                      user_id: str = 'jia',
                      agent_id: str = '1',
                      agent_name: str = None,
                      connect_jia=True,
                      api_key='ABCD-1234'):
        """Provide ability to use Agent as a context manager. Internally calls start_agent and stop_agent.

        Args:
            genome_file (_type_, optional): _description_. Defaults to None.
            genome_name (_type_, optional): _description_. Defaults to None.
            user_id (str, optional): _description_. Defaults to 'jia'.
            agent_id (str, optional): _description_. Defaults to '1'.
            agent_name (_type_, optional): _description_. Defaults to None.
            connect_jia (bool, optional): _description_. Defaults to True.
            api_key (str, optional): _description_. Defaults to 'ABCD-1234'.

        Yields:
            _type_: _description_
        """
        try:
            with agent_manager_lock:
                agent = self.start_agent(genome_file=genome_file,
                                        genome_name=genome_name,
                                        user_id=user_id,
                                        agent_id=agent_id,
                                        agent_name=agent_name,
                                        connect_jia=connect_jia,
                                        api_key=api_key)
            yield agent.get_agent_client(local=self.local)
        finally:
            with agent_manager_lock:
                self.delete_agent(agent.agent_name)

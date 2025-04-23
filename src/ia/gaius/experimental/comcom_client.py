'''Implements the COMCOM interface.'''
import functools
import json
from typing import Dict, List, Any, Tuple, Union
import requests
from ia.gaius.utils import plot_directed_networkx_graph
import networkx as nx
from collections import defaultdict


class COMCOMQueryError(BaseException):
    """Raised if any query to any node returns an error."""
    pass


class COMCOMConnectionError(BaseException):
    """Raised if connecting to any node returns an error."""
    pass


def _ensure_connected(f):
    @functools.wraps(f)
    def inner(self, *args, **kwargs):
        if not self._connected:
            raise COMCOMConnectionError(
                'Not connected to a COMCOM instance. You must call `connect()` on a COMCOMClient instance before making queries'
            )
        return f(self, *args, **kwargs)

    return inner


def _remove_unique_id(response: dict) -> dict:
    """Return *response* with the key 'unique_id' removed regardless of nesting."""
    if isinstance(response, dict):
        if 'unique_id' in response:
            del response['unique_id']
        for value in response.values():
            if isinstance(value, dict):
                _remove_unique_id(value)
    return response


class COMCOMClient:
    '''Interface for interacting with COMCOM. Creating/interacting with input_slots
       and connecting agents to COMCOM'''

    def __init__(self, comcom_info: dict, verify=True):
        self.session = requests.Session()
        self._comcom_info = comcom_info
        self.name = comcom_info['name']
        self._domain = comcom_info['domain']
        self._api_key = comcom_info['api_key']
        self._headers = {'X-API-KEY': self._api_key}
        self._connected = False
        self.send_unique_ids = True
        self._verify = verify

        if 'secure' not in self._comcom_info or self._comcom_info['secure']:
            self._secure = True
            if not self.name:
                self._url = 'https://{domain}/'.format(**self._comcom_info)
            else:
                self._url = 'https://{name}.{domain}/'.format(
                    **self._comcom_info)
        else:
            self._secure = False
            if not self.name:
                self._url = 'http://{domain}/'.format(**self._comcom_info)
            else:
                self._url = 'http://{name}.{domain}/'.format(
                    **self._comcom_info)

    def connect(self) -> Dict:
        """
        Establishes initial connection to COMCOM, then allows calling of other function to 
        """
        response_data = self.session.get(
            self._url + 'connect', verify=self._verify, headers=self._headers).json()

        if 'status' not in response_data or response_data['status'] != 'okay':
            self._connected = False
            raise COMCOMConnectionError("Connection failed!", response_data)

        if response_data['status'] == 'okay':
            self._connected = True
        else:
            self._connected = False

        return {'connection': response_data['status']}

    '''def disconnect(self) -> Dict:
        """Establishes initial connection to COMCOM, then allows calling of other function to 
        """
        response_data = self.session.get(self._url + 'connect', verify=self._verify, headers=self._headers).json()

        if 'status' not in response_data or response_data['status'] != 'okay':
            self._connected = False
            raise COMCOMConnectionError("Connection failed!", response_data)

        self._connected = False

        return {'connection': response_data['status']}'''

    @_ensure_connected
    def _query(
        self, query_method: Any, path: str, data: Union[dict, str] = None, unique_id: str = None
    ) -> Union[dict, Tuple[dict, str]]:
        """Internal helper function to make a REST API call with the given *query* and *data*."""
        if not self._connected:
            raise COMCOMConnectionError(
                'Not connected to a agent. You must call `connect()` on a AgentClient instance before making queries'
            )
        result = {}
        if unique_id is not None:
            if data:
                data['unique_id'] = unique_id
            else:
                data = {'unique_id': unique_id}

        data = json.loads(json.dumps(data))

        full_path = f'{self._url}{path}'
        try:
            if data is not None:
                response = query_method(full_path, verify=self._verify,
                                        headers=self._headers, json=data)
            else:
                response = query_method(
                    full_path, verify=self._verify, headers=self._headers)
            response.raise_for_status()
            response = response.json()
            if response['status'] != 'okay':
                raise COMCOMQueryError(response['message'])
            if not self.send_unique_ids:
                response = _remove_unique_id(response['message'])
            else:
                response = response['message']
        except Exception as exception:
            raise COMCOMQueryError(str(exception)) from None

        if unique_id is not None:
            return response, unique_id

        return response

    def connect_to_agent(self, api_key : str, 
                         domain : str,
                         agent_name : str,
                         agent_type : str,
                         **kwargs) -> Union[dict, Tuple[dict, str]]:
        """Function to attempt to connect to an existing/accessible agent on the network to COMCOM,
            which can then be later used for other purposes

        Args:
            api_key (str): API key for the agent
            domain (str): Domain of the agent
            agent_name (str): The agent_name; which will also be used as an alias in COMCOM to refer to the agent
            agent_type (str): The type of agent

        Returns:
            Union[dict, Tuple[dict, str]]: response from COMCOM
        """
        data = {key: val for key, val in kwargs.items()}
        data["api_key"] = api_key
        data["domain"] = domain
        data["agent_name"] = agent_name
        data["agent_type"] = agent_type
        
        return self._query(self.session.post, 'connect_to_agent', data=data)

    def disconnect_agent(self, agent_name : str) -> Union[dict, Tuple[dict, str]]:
        """Function call that disconnects from agent with specific agent_name, and removes it
            from all input_slots

        Args:
            agent_name (str): The alias of the agent in COMCOM

        Returns:
            Union[dict, Tuple[dict, str]]: response from COMCOM
        """
        data = {"agent_name" : agent_name}
        return self._query(self.session.post, 'disconnect_destination', data=data)

#     def modify_agent(self, data : Dict) -> Union[dict, Tuple[dict, str]]:
#         '''
#             Function call to set agent parameters such as ingress/outgress nodes, or modify genes
#         '''
#         return self._query(self.session.post, 'config_agent', data=data)

    def call_agent_command(self, agent_name : str,
                           command : str,
                           command_parameters : Dict) -> Union[dict, Tuple[dict, str]]:
        """Function call to pass data through comcom and call command on agent

        Args:
            agent_name (str): The alias of the agent in COMCOM
            command (str): The command to call on the agent
            command_parameters (Dict): Any parameters/values needed for command(varies for each command)

        Returns:
            Union[dict, Tuple[dict, str]]: response from COMCOM
        """
        data = {"agent_name" : agent_name,
                "command" : command,
                "command_parameters" : command_parameters}

        return self._query(self.session.post, 'call_agent_command', data=data)

    def clear_agents(self) -> Union[dict, Tuple[dict, str]]:
        """Function call that removes all connected agents in COMCOM, and in its output_slots.

        Returns:
            Union[dict, Tuple[dict, str]]: response from COMCOM
        """
        return self._query(self.session.post, 'clear_agents', data={})

    def connect_input_slot(self,
                           input_name : str,
                           input_type : str,
                           pipeline_slots : List[str] = [],
                           input_slot_data_mapping : Dict = {},
                           max_command_queue_size : int = 100,
                           queue_block_on_full : bool = True,
                           queue_block_timeout : float = 1,
                           **kwargs) -> Union[dict, Tuple[dict, str]]:
        """Function call which takes in data to create a new input slot in COMCOM.

        Args:
            input_name (str): The name that this input slot will be known by.
            input_type (str): The type of the input_slot.
            pipeline_slots (List[str], optional): The pipelines to be run when data is received. Defaults to [].
            input_slot_data_mapping (Dict, optional): Special mapping of data from one set of key:value pairs to another(useful for pipelines). Defaults to {}.
            max_command_queue_size (int, optional): Max number of commands that can be in command_queue before data is dropped. Defaults to 100.
            queue_block_on_full (bool, optional): Bool flag controlling if input_slot should wait for free slot in queue up to `queue_block_timeout`. Defaults to True.
            queue_block_timeout (float, optional): Timeout for waiting for free slot in command_queue.. Defaults to 1.

        Returns:
            Union[dict, Tuple[dict, str]]: response from COMCOM
        """
        data = {key: val for key, val in kwargs.items()}
        data["input_type"] = input_type
        data["input_name"] = input_name
        data["pipeline_slots"] = pipeline_slots
        data["input_slot_data_mapping"] = input_slot_data_mapping
        data["max_command_queue_size"] = max_command_queue_size
        data["queue_block_on_full"] = queue_block_on_full
        data["queue_block_timeout"] = queue_block_timeout
        return self._query(self.session.post, 'connect_input_slot', data=data)
    
    def disconnect_input_slot(self, input_name : str) -> Union[dict, Tuple[dict, str]]:
        """Function that takes in unique input_name, and deletes it from COMCOM.

        Args:
            input_name (str): Name of input_slot to delete.

        Returns:
            Union[dict, Tuple[dict, str]]: response from COMCOM
        """
        data = {"input_name": input_name}
        return self._query(self.session.post, 'disconnect_input_slot', data=data)

    def connect_output_slot(self,
                           output_name : str,
                           output_type : str,
                           output_slot_data_mapping : Dict = {},
                           max_command_queue_size : int = 100,
                           queue_block_on_full : bool = True,
                           queue_block_timeout : float = 1,
                           **kwargs) -> Union[dict, Tuple[dict, str]]:
        """Function call which takes in data and constructs a new output slot in COMCOM.

        Args:
            output_name (str): The name that this output slot will be known by.
            output_type (str): The type of the output_slot.
            output_slot_data_mapping (Dict, optional): Special mapping of data from one set of key:value pairs to another(useful to get translate data from pipelines into relevant mappings). Defaults to {}.
            max_command_queue_size (int, optional): Max number of commands that can be in command_queue before data is dropped. Defaults to 100.
            queue_block_on_full (bool, optional): Bool flag controlling if output_slot should wait for free slot in queue up to `queue_block_timeout`. Defaults to True.
            queue_block_timeout (float, optional): Timeout for waiting for free slot in command_queue. Defaults to 1.

        Returns:
            Union[dict, Tuple[dict, str]]: _description_
        """
        data = {key: val for key, val in kwargs.items()}
        data["output_name"] = output_name
        data["output_type"] = output_type
        data["output_slot_data_mapping"] = output_slot_data_mapping
        data["max_command_queue_size"] = max_command_queue_size
        data["queue_block_on_full"] = queue_block_on_full
        data["queue_block_timeout"] = queue_block_timeout
        return self._query(self.session.post, 'connect_output_slot', data=data)
    
    def disconnect_output_slot(self, output_name : str) -> Union[dict, Tuple[dict, str]]:
        """Function that takes in unique input_name, and deletes it from COMCOM.

        Args:
            output_name (str): Name of output_slot to delete.

        Returns:
            Union[dict, Tuple[dict, str]]: response from COMCOM
        """
        data = {"output_name": output_name}
        return self._query(self.session.post, 'disconnect_output_slot', data=data)

    def modify_input_slot(self, input_name : str,
                          modification_type : str,
                          **kwargs) -> Union[dict, Tuple[dict, str]]:
        """Complex function call which can modify the input_slot according to the modification type.

        Args:
            input_name (str): Name of input_slot to modify.
            modification_type (str): Name of modification to perform.

        Returns:
            Union[dict, Tuple[dict, str]]: response from COMCOM
        """
        data = {key: val for key, val in kwargs.items()}
        data["input_name"] = input_name
        data["modification_type"] = modification_type
        
        return self._query(self.session.post, 'modify_input_slot', data=data)

    def modify_output_slot(self, output_name : str,
                           modification_type : str,
                           **kwargs) -> Union[dict, Tuple[dict, str]]:
        """Complex function call which can modify the output_slot according to the modification_type.

        Args:
            output_name (str): Name of output_slot to modify.
            modification_type (str): Name of modification to perform.

        Returns:
            Union[dict, Tuple[dict, str]]: response from COMCOM
        """
        data = {key: val for key, val in kwargs.items()}
        data["output_name"] = output_name
        data["modification_type"] = modification_type

        return self._query(self.session.post, 'modify_output_slot', data=data)

    def toggle_input_slot(self, input_name : str) -> Union[dict, Tuple[dict, str]]:
        """Function which negates the active status of the input_slot with passed name.

        Args:
            input_name (str): Name of input_slot to toggle.

        Returns:
            Union[dict, Tuple[dict, str]]: response from COMCOM
        """
        data = {
            "input_name" : input_name
        }
        return self._query(self.session.post, 'toggle_input_slot', data=data)
    
    def toggle_output_slot(self, output_name: str) -> Union[dict, Tuple[dict, str]]:
        """Function which negates the active status of the output_slot with passed name.

        Args:
            output_name (str): Name of output_slot to toggle.

        Returns:
            Union[dict, Tuple[dict, str]]: response from COMCOM
        """
        data = {
            "output_name" : output_name
        }
        return self._query(self.session.post, 'toggle_output_slot', data=data)

    def query_input_slot(self, input_name : str) -> Union[dict, Tuple[dict, str]]:
        """Function to have an input_slot retrieve a singular piece of data.
        Currently only a COMCOMDarkAgent can perform this action.

        Args:
            input_name (str): Name of input_slot to query.

        Returns:
            Union[dict, Tuple[dict, str]]: response from COMCOM
        """
        data = {
            "input_name" : input_name
        }
        return self._query(self.session.post, 'query_input_slot', data=data)

    def clear_input_slots(self) -> Union[dict, Tuple[dict, str]]:
        """Function call that tells COMCOM to clear all input slots from its system.

        Returns:
            Union[dict, Tuple[dict, str]]: response from COMCOM
        """
        return self._query(self.session.post, 'clear_input_slots', data={})

    def load_comcom_config(self, data: Dict) -> Union[dict, Tuple[dict, str]]:
        """Function call that configures COMCOM according to the passed json. This includes construction
        of Agent connections, Input_Slots, Output_Slots, and Pipelines.

        Args:
            data (Dict): JSON data containing the fields [Agents, Input_Slots, Output_Slots, Pipelines]

        Returns:
            Union[dict, Tuple[dict, str]]: response from COMCOM
        """

        return self._query(self.session.post, 'load_comcom_config', data=data)

    def list_comcom(self) -> Union[dict, Tuple[dict, str]]:
        """Function which lists all data about constructed objects in COMCOM.

        Returns:
            Union[dict, Tuple[dict, str]]: response from COMCOM
        """

        return self._query(self.session.post, 'list_comcom', data={})

    def list_agent_connections(self) -> Union[dict, Tuple[dict, str]]:
        """Function call to list all unique agent connections in COMCOM.

        Returns:
            Union[dict, Tuple[dict, str]]: response from COMCOM
        """
        return self._query(self.session.post, 'list_agent_connections', data={})

    def list_input_slots(self) -> Union[dict, Tuple[dict, str]]:
        """Function call to list all input_slots in COMCOM.

        Returns:
            Union[dict, Tuple[dict, str]]: response from COMCOM
        """
        return self._query(self.session.post, 'list_input_slots', data={})
    
    def list_pipelines(self) -> Union[dict, Tuple[dict, str]]:
        """Function call to list all pipelines in COMCOM.

        Returns:
            Union[dict, Tuple[dict, str]]: response from COMCOM
        """
        return self._query(self.session.post, 'list_pipelines', data={})

    def list_output_slots(self) -> Union[dict, Tuple[dict, str]]:
        """Function call to list all output_slots in COMCOM.

        Returns:
            Union[dict, Tuple[dict, str]]: response from COMCOM
        """
        return self._query(self.session.post, 'list_output_slots', data={})

    def list_preprocessing_functions(self) -> Union[dict, Tuple[dict, str]]:
        """Function call to list all unique pipelines in COMCOM.

        Returns:
            Union[dict, Tuple[dict, str]]: response from COMCOM
        """
        return self._query(self.session.post, 'list_preprocessing_functions', data={})

    def get_agent_data(self, agent_name : str) -> Union[dict, Tuple[dict, str]]:
        """Function call to get detailed information about connection with passed agent_name.

        Args:
            agent_name (str): Name of agent to get info about.

        Returns:
            Union[dict, Tuple[dict, str]]: response from COMCOM
        """
        data = {
            "agent_name" : agent_name
        }
        return self._query(self.session.post, 'get_agent_data', data=data)

    def get_output_slot_data(self, output_name : str) -> Union[dict, Tuple[dict, str]]:
        """Function call to get detailed information about output_slot with passed output_name.

        Args:
            output_name (str): Name of output_slot to get info about.

        Returns:
            Union[dict, Tuple[dict, str]]: response from COMCOM
        """
        data = {
            "output_name" : output_name
        }
        return self._query(self.session.post, 'get_output_slot_data', data=data)

    def get_input_slot_data(self, input_name : str) -> Union[dict, Tuple[dict, str]]:
        """Function call to get detailed information about input_slot with passed input_name.

        Args:
            input_name (str): Name of input_slot to get info about.

        Returns:
            Union[dict, Tuple[dict, str]]: Name of agent to get info about.
        """
        data = {
            "input_name" : input_name
        }
        return self._query(self.session.post, 'get_input_slot_data', data=data)

    def query_db(self, db_name : str,
                 lookup_config : Dict,
                 **kwargs) -> Union[dict, Tuple[dict, str]]:
        """Function call to query COMCOM for information from its internal Database.

        Args:
            db_name (str): Name of database collection/table to query.
            lookup_config (Dict): Configuration data in format acceptable by MongoDB.

        Returns:
            Union[dict, Tuple[dict, str]]: response from COMCOM
        """
        data = {key: val for key, val in kwargs.items()}
        data = {
            "db_name" : db_name,
            "lookup_config" : lookup_config
        }
        return self._query(self.session.post, 'query_db', data=data)

    def clear_comcom(self) -> Union[dict, Tuple[dict, str]]:
        """Function to clear COMCOM of everyting. Literally scorched earth mode. (VERY DANGEROUS)

        Returns:
            Union[dict, Tuple[dict, str]]: response from COMCOM
        """
        return self._query(self.session.post, 'clear_comcom', data={})

    def clear_outputslot_command_queue(self, output_name : str) -> Union[dict, Tuple[dict, str]]:
        """Function to clear the pending data in an output_slot with passed output_name. 

        Args:
            output_name (str): Name of output_slot whose work queue should be cleared.

        Returns:
            Union[dict, Tuple[dict, str]]: response from COMCOM
        """
        data = {
            "output_name" : output_name
        }
        return self._query(self.session.post, 'clear_outputslot_command_queue', data=data)

    def synchronize_input_slots(self, inputs_to_sync_to : List[str],
                                timeout_duration : float) -> Union[dict, Tuple[dict, str]]:
        """Function call to synchronize two or more input_slots.

        Args:
            inputs_to_sync_to (List[str]): List of input_slots to synchronization together.
            timeout_duration (float): The max amount of time that a source will wait before discregarding data.

        Returns:
            Union[dict, Tuple[dict, str]]: response from COMCOM
        """
        data = {
            "inputs_to_sync_to" : inputs_to_sync_to,
            "timeout_duration" : timeout_duration
        }
        return self._query(self.session.post, 'synchronize_input_slots', data=data)

    def desynchronize_input_slots(self, inputs_to_desync : List[str]) -> Union[dict, Tuple[dict, str]]:
        """Function call to desynchronize two or more input_slots.

        Args:
            inputs_to_desync (List[str]): List of input_slots to remove from synchronization pools.

        Returns:
            Union[dict, Tuple[dict, str]]: response from COMCOM
        """
        data = {
            "inputs_to_desync" : inputs_to_desync
        }
        return self._query(self.session.post, 'desynchronize_input_slots', data=data)

    def get_dds_message_types(self) -> Union[dict, Tuple[dict, str]]:
        '''
            Function call to get all available DDS message types
        '''
        return self._query(self.session.post, 'get_dds_message_types')
    
    def create_pipeline(self, pipeline_name : str,
                        pipeline_function_parameters : Dict,
                        pipeline_source_fields : Dict[str, Dict[str, str]],
                        pipeline_destination_fields : Dict[str, Dict[str, str]],
                        pipeline_connections : Dict[str, List[str]],
                        pipeline_starting_functions : List[str],
                        **kwargs) -> Union[dict, Tuple[dict, str]]:
        """Function call to create a pipeline that can be used by an input_slot.

        Args:
            pipeline_name (str): Name that the pipeline will be known by in COMCOM.
            pipeline_function_parameters (Dict): Dictionary of static functions parameters for each function that is in pipeline. 
            pipeline_source_fields (Dict[str, Dict[str, str]]): Dictionary of data fields that are expected to be in the output if it is a dict. Ignored if output is anything else.
            pipeline_destination_fields (Dict[str, Dict[str, str]]): Dictionary of data fields where function output data will be mapped to in the general data dictionary.
            pipeline_connections (Dict[str, List[str]]): Dictionary of connections between pipeline functions which maps flow of data during pipeline execution.
            pipeline_starting_functions (List[str]): List of functions that the pipeline will start with.

        Returns:
            Union[dict, Tuple[dict, str]]: response from COMCOM
        """
        data = {key: val for key, val in kwargs.items()}
        data["pipeline_name"] = pipeline_name
        data["pipeline_function_parameters"] = pipeline_function_parameters
        data["pipeline_source_fields"] = pipeline_source_fields
        data["pipeline_destination_fields"] = pipeline_destination_fields
        data["pipeline_connections"] = pipeline_connections
        data["pipeline_starting_functions"] = pipeline_starting_functions
        return self._query(self.session.post, 'create_pipeline', data=data)
    
    def modify_pipeline(self, pipeline_name : str,
                        modification_type : str,
                        **kwargs) -> Union[dict, Tuple[dict, str]]:
        """Function call to modify a pipeline

        Args:
            pipeline_name (str): Name of pipeline to modify
            modification_type (str): Name of modification to perform.

        Returns:
            Union[dict, Tuple[dict, str]]: response from COMCOM
        """
        data = {key: val for key, val in kwargs.items()}
        data["pipeline_name"] = pipeline_name
        data["modification_type"] = modification_type
        return self._query(self.session.post, 'modify_pipeline', data=data)
    
    def get_pipeline_data(self, pipeline_name : str) -> Union[dict, Tuple[dict, str]]:
        """Function call to get detailed pipeline information

        Args:
            pipeline_name (str): Name of pipeline to get details about.

        Returns:
            Union[dict, Tuple[dict, str]]: response from COMCOM
        """
        data = {
            "pipeline_name" : pipeline_name
        }
        return self._query(self.session.post, 'get_pipeline_data', data=data)
    
    def delete_pipeline(self, pipeline_name : str) -> Union[dict, Tuple[dict, str]]:
        """Function call to delete a pipeline in COMCOM.

        Args:
            pipeline_name (str): Name of pipeline to delete.

        Returns:
            Union[dict, Tuple[dict, str]]: response from COMCOM
        """
        data = {
            "pipeline_name" : pipeline_name
        }
        return self._query(self.session.post, 'delete_pipeline', data=data)
    
    def get_debug_topic_data_stream(self, pipeline_name : str,
                                    function_name : str,
                                    input_slot_name : str) -> Union[dict, Tuple[dict, str]]:
        """Function call to get a stream of debug messages from function, in a pipeline, that was run by the input_slot

        Args:
            pipeline_name (str): Name of pipeline containing said function
            function_name (str): Name of function whose debug message you wish to get
            input_slot_name (str): Name of input slot which ran the pipeline

        Returns:
            Union[dict, Tuple[dict, str]]: response from COMCOM
        """
        data = {
            "pipeline_name" : pipeline_name,
            "function_name" : function_name,
            "input_slot_name" : input_slot_name,
        }
        return self._query(self.session.post, 'debug_topic_stream', data=data)
    
    def get_debug_topic_data_single(self, pipeline_name : str,
                                    function_name : str,
                                    input_slot_name : str,
                                    display_result = True) -> Any:
        """Function call to get a singulr debug message from function, in a pipeline, that was run by the input_slot

        Args:
            pipeline_name (str): Name of pipeline containing said function
            function_name (str): Name of function whose debug message you wish to get
            input_slot_name (str): Name of input slot which ran the pipeline
            display_result (bool, optional): whether to display result in a general way or just return the formatted result(if applicable). Defaults to True.

        Returns:
            Any: _description_
        """
        data = {
            "pipeline_name" : pipeline_name,
            "function_name" : function_name,
            "input_slot_name" : input_slot_name,
        }
        result = self._query(self.session.post, 'debug_topic_single', data=data)
        print("Got result from COMCOM", result)
        result = {key: json.loads(data) for key, data in result.items() if data is not None}

        def convert_to_better_rep(data : Any, return_type : str):
            """Function that will convert passed data into a more appropraite type.
            Very circumstantial based on needs of team, and no foolproof way to ensure correct
            format.

            Args:
                data (Any): _description_
                return_type (str): _description_

            Returns:
                _type_: _description_
            """
            if return_type == "dict":
                # if its a dict, not much else can be done
                return data
            elif return_type == "list":
                # if its a list, not much else can be done
                return data
            elif return_type == "image":
                # can convert to numpy array
                import numpy as np
                return np.array(data, dtype=np.float64)
            elif return_type == "audio":
                import numpy as np
                return np.frombuffer(data, dtype=np.int16)
            return data

        def display_result(data, return_type : str):
            from pprint import pp
            if return_type == "dict":
                # if its a dict, not much else can be done
                pp(data)
            elif return_type == "list":
                # if its a list, not much else can be done
                pp(data)
            elif return_type == "image":
                # can convert to numpy array
                import matplotlib.pyplot as plt
                import numpy as np
                plt.figure(figsize=(15, 15))
                plt.imshow(data)
                plt.show()
            elif return_type == "audio":
                import matplotlib.pyplot as plt
                import numpy as np
                plt.figure(figsize=(15, 5))
                times = np.linspace(0, len(data)/6000, num=len(data))
                plt.plot(times, data)
                plt.title('Left Channel')
                plt.ylabel('Signal Value')
                plt.xlabel('Time (s)')
                plt.xlim(0, len(data))
                plt.show()

        if len(result["return_types"]) > 1:
            # things get complicated
            if isinstance(result["result"], dict):
                for data_key in result["return_types"].keys():
                    result["result"][data_key] = convert_to_better_rep(result["result"][data_key], result["return_types"][data_key])
                    if display_result:
                        pass
            else:
                for i, data_key in enumerate(result["return_types"].keys()):
                    result["result"][i] = convert_to_better_rep(result["result"][i], result["return_types"][data_key])
                    if display_result:
                        pass
        else:
            # read in type and convert to a nicer representation
            result = convert_to_better_rep(result["result"], list(result["return_types"].values())[0])
            if display_result:
                pass
        
        return result
    
    def get_config_as_json(self) -> Union[dict, Tuple[dict, str]]:
        """Gets the json configuration to reload current comcom config at a later date

        Returns:
            json: Json object with relevant information to rebuild comcom
        """
        return self._query(self.session.post, 'dump_config_to_json')
    
    def visualize_pipeline(self, pipeline_name : str) -> None:
        """Function to visualize a pipeline with passed pipeline_name using plotly.

        Args:
            pipeline_name (str): The name of the pipeline to visualize.
        """
        data = {
            "pipeline_name" : pipeline_name
        }
        cytoscape_data = self._query(self.session.post, 'pipeline_to_cytoscape', data=data)

        pipeline_data = self._query(self.session.post, 'get_pipeline_data', data=data)

        cyto_graph = nx.cytoscape.cytoscape_graph(cytoscape_data)

        plot_directed_networkx_graph(cyto_graph, pipeline_data["starting_functions"], title=f"Graph of Pipeline {pipeline_name}")
        return 
    
    def pipeline_to_cytoscape(self, pipeline_name : str) -> Union[dict, Tuple[dict, str]]:
        """Gets the cytoscape representation of the pipeline with passed name pipeline_name.

        Args:
            pipeline_name (str): The name of the pipeline to get representation of.

        Returns:
            Union[dict, Tuple[dict, str]]: Cytoscape json data
        """
        data = {
            "pipeline_name" : pipeline_name
        }
        return self._query(self.session.post, 'pipeline_to_cytoscape', data=data)
    
    def input_slot_to_cytoscape(self, input_slot_name : str) -> Union[dict, Tuple[dict, str]]:
        """Gets the cytoscape representation of the input_slot with passed name input_slot_name.

        Args:
            input_slot_name (str): The name of the input_slot to get representation of.

        Returns:
            Union[dict, Tuple[dict, str]]: Cytoscape json data
        """
        data = {
            "input_slot_name" : input_slot_name
        }
        return self._query(self.session.post, 'input_slot_to_cytoscape', data=data)
    
    def visualize_input_slot(self, input_slot_name : str) -> None:
        """Function to visualize a pipeline with passed pipeline_name using plotly.

        Args:
            input_slot_name (str): The name of the input_slot to visualize.
        """
        data = {
            "input_slot_name" : input_slot_name
        }
        cytoscape_data = self._query(self.session.post, 'input_slot_to_cytoscape', data=data)

        cyto_graph = nx.cytoscape.cytoscape_graph(cytoscape_data)

        # starting nodes are the input_slots
        starting_nodes = [input_slot_name]

        plot_directed_networkx_graph(cyto_graph, starting_nodes, title=f"Graph of Input Slot {input_slot_name}")
        return
    
    def comcom_to_cytoscape(self) -> Union[dict, Tuple[dict, str]]:
        """Get cytoscape representation of all of comcom.

        Returns:
            Union[dict, Tuple[dict, str]]: Cytoscape json data
        """
        return self._query(self.session.post, 'comcom_to_cytoscape')
    
    def visualize_comcom(self) -> None:
        """Function to visualize all of comcom using plotly
        """
        cytoscape_data = self._query(self.session.post, 'comcom_to_cytoscape')

        cyto_graph = nx.cytoscape.cytoscape_graph(cytoscape_data)

        all_input_slots = self._query(self.session.post, 'list_input_slots')

        plot_directed_networkx_graph(cyto_graph, all_input_slots, title="COMCOM Graph")
        return
    
    def add_function_to_comcom(self, function_name : str, function_input_types : Dict[str, str], function_return_types : Dict[str, str], source : str, source_type : str = "block") -> Union[dict, Tuple[dict, str]]:
        """Function to add a new preprocessing function from a source code 'block' or 'file'.
        This function will be run in a restricted manner, to protect COMCOM from nefarious functions.

        Args:
            function_name (str): _description_
            function_input_types (Dict[str, str]): A key-value pair stating the expected input type of parameters
            function_return_types (Dict[str, str]): A key-value pair stating the expected return type of variables
            source (str): Either a block of code in text format, or path to a source code file
            source_type (str, optional): Type of source. Either 'file', or 'block'. Defaults to "block".

        Returns:
            Union[dict, Tuple[dict, str]]: response from COMCOM
        """
        data = {
            "function_name" : function_name,
            "function_input_types" : function_input_types,
            "function_return_types" : function_return_types,
            "source" : source,
            "source_type" : source_type,
        }
        return self._query(self.session.post, 'add_function', data=data)
    
    def delete_function_from_comcom(self, function_name : str = "Craig") -> Union[dict, Tuple[dict, str]]:
        """Deletes a function from COMCOM

        Args:
            function_name (str, optional): Name of function to delete. Defaults to "Craig".

        Returns:
            Union[dict, Tuple[dict, str]]: response from COMCOM
        """
        data = {
            "function_name" : function_name
        }
        return self._query(self.session.post, 'delete_function', data=data)
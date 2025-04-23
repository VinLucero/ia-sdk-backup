from typing import Dict, List, Any, Tuple, Union, Callable
import requests
from requests import Response
import logging

logger = logging.getLogger(__name__)


class TFQueryError(BaseException):
    """Raised if any query to TF returns an error."""
    pass


# example tf_info
# { "name": "MainTF",
#   "url": "https://tf.intelligent-artifacts.com:8090",
#   "api_key": "ABCD-1234"
# }

class TFClient:
    """Thinkflux Client Wrapper (interface to TF REST API)
    """

    def __init__(self, tf_info: dict, verify: bool = True) -> None:

        self._tf_info = tf_info

        self._url = tf_info['url']
        self._api_key = tf_info['api_key']
        self.name = tf_info['name']

        self.session = requests.Session()
        self.session.headers['X-API-KEY'] = self._api_key
        self.verify = verify
        self.session.verify = verify

    def set_verify(self, verify: bool):
        self.verify = verify
        self.session.verify = verify

    def _query(self,
               query_method: Callable,
               path: str,
               timeout: float = None,
               **kwargs) -> Response:
        """Internal function to call a specified route on Thinkflux. Useful for routes we haven't explicitly defined here (e.g. prototyping new routes)

        Args:
            query_method (Callable): funciton from requests library. e.g. requests.get, requests.post, requests.delete
            path (str): url used for the HTTP request, including schema (http vs https) and port
            timeout (float, optional): Timeout for the HTTP request. Defaults to None.
            **kwargs (optional): Additional arguments passed directly to the requests function
        Raises:
            TFQueryError: If we get a bad response from Thinkflux

        Returns:
            Response: requests library Response object
        """
        response: Response = query_method(path,
                                          verify=self.verify,
                                          timeout=timeout,
                                          **kwargs)
        if not response.ok:
            raise TFQueryError(
                f"Bad response {response} from TF: {response.content}")
        return response

    def ping(self) -> str:
        """Ensure connection can be established with Thinkflux. Sanity check.

        Raises:
            TFQueryError: _description_

        Returns:
            str: _description_
        """
        response = requests.get(self._url + '/ping', verify=self.verify)
        if response.status_code != 200:
            raise TFQueryError("Failed to ping Thinkflux")
        return response.text

    def show_status(self) -> dict:

        return self._query(requests.get, self._url + '/show_status').json()

    def clear_all_kbs(self) -> dict:

        return self._query(requests.get, self._url + '/clear_all_kbs').json()

    def clear_wm(self) -> dict:

        return self._query(requests.get, self._url + '/clear_wm').json()

    def clear_concepts_and_instances(self) -> dict:
        """Remove all Concepts and instances from Thinkflux

        Returns:
            dict: _description_
        """

        return self._query(requests.get, self._url + '/clear_concepts_and_instances').json()

    def add_schema_symbol_information(self) -> Response:

        return self._query(requests.get, self._url + '/add_schema_symbol_information')

    def observe(self, data: dict) -> dict:
        """Observe data on Thinkflux

        Args:
            data (dict): data percept to observe

        """

        return self._query(requests.post, self._url + '/observe', json=data).json()

    def add_interface_nodes(self, agent_config: dict) -> dict:
        """Add an interface node from GAIuS agent to Thinkflux

        Args:
            agent_config (dict): dictionary with configuration details for interface node

            agent_config dict needs the following fields:
            {
                "name": str,
                "domain: str,
                "secure": bool,
                "api_key": str,
                "interface_nodes": List[str]
            }

        """

        return self._query(requests.post, self._url + '/add_interface_nodes', json=agent_config).json()

    def list_interface_nodes(self) -> dict:

        return self._query(requests.get, self._url + '/list_interface_nodes').json()

    def delete_interface_nodes(self, data: dict) -> Response:

        return self._query(requests.post, self._url + '/delete_interface_nodes', json=data).json()

    def get_model_association_networks(self) -> Response:

        return self._query(requests.get, self._url + '/get_model_association_networks')

    def timer(self) -> Response:

        return self._query(requests.get, self._url + '/timer')

    def update_schema(self, data: dict) -> Response:

        return self._query(requests.post, self._url + '/update_schema', json=data)

    def bootstrap_concepts(self,
                           hierarchy: bool = False,
                           labelled: bool = False,
                           use_labels_for_concepts: bool = False,
                           use_labels_for_hierarchy: bool = False,
                           subsequence_clustering: bool = False,
                           **kwargs) -> Response:
        """_summary_

        Args:
            hierarchy (bool, optional): Whether to generate a hierarchy of concepts. Defaults to False.
            labelled (bool, optional): If the dataset contains labels. Defaults to False.
            use_labels_for_concepts (bool, optional): Whether labels should be used for concept names. Defaults to False.
            use_labels_for_hierarchy (bool, optional): Make a hierarchy using labels. Defaults to False.
            subsequence_clustering (bool, optional): Perform subsequence clustering when generating concepts. Defaults to False.
            **kwargs: Other arguments to pass

        Returns:
            Response: Response object from requests
        """
        json_obj = {'hierarchy': hierarchy,
                    'labelled': labelled,
                    'use_labels_for_concepts': use_labels_for_concepts,
                    'use_labels_for_hierarchy': use_labels_for_hierarchy,
                    'subsequence_clustering': subsequence_clustering}
        json_obj.update(kwargs)
        return self._query(requests.post, self._url + '/bootstrap_concepts', json=json_obj)

    def investigate(self, data: dict) -> Response:

        return self._query(requests.post, self._url + '/investigate_tf', json=data)

    def dreamer(self, data: dict) -> Response:

        return self._query(requests.post, self._url + '/dreamer', json=data)

    def load_schema_base(self, schema_base: dict) -> Response:
        """Load a SchemaBase on Thinkflux, from a dictionary object

        Args:
            schema_base (dict): the SchemaBase to load

        Returns:
            Response: requests Response object
        """

        return self._query(requests.post, self._url + '/load_sb', json=schema_base)

    def clear_all_emotives(self) -> dict:

        return self._query(requests.get, self._url + '/clear_all_emotives').json()

    def get_rules_kb(self) -> dict:

        return self._query(requests.get, self._url + '/get_rules_kb').json()

    def set_rules_kb(self, rules_kb: dict) -> dict:

        return self._query(requests.post, self._url + '/set_rules_kb', json=rules_kb).json()

    def set_symbolic_goal(self, symbolic_goal: dict) -> dict:

        return self._query(requests.post, self._url + '/set_symbolic_goal', json=symbolic_goal).json()

    def get_symbolic_goal(self) -> dict:

        return self._query(requests.get, self._url + '/get_symbolic_goal').json()

    def evaluate_world(self, data: dict) -> dict:

        return self._query(requests.post, self._url + '/evaluate_world', json=data).json()

    def get_plan(self) -> dict:

        return self._query(requests.get, self._url + '/get_plan').json()

    def get_concept(self, concept_name: str) -> dict:
        """Retrieve a single concept from Thinkflux by concept name

        Args:
            concept_name (str): Name of the ooncept to retrieve
        """

        return self._query(requests.get, self._url + f"/concept/{concept_name}").json()

    def get_concepts(self) -> dict:
        """Retrieve all concepts from Thinkflux
        """

        return self._query(requests.get, self._url + f"/get_concepts").json()

    def get_instances(self) -> dict:
        """Retrieve current instances from Thinkflux
        """

        return self._query(requests.get, self._url + f"/get_instances").json()

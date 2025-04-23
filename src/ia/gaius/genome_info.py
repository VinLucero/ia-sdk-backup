import json
import logging

logger = logging.getLogger(__file__)


class Genome:
    """Wrapper class for a Genome topology, loaded from a dict

    :ivar topology: the data representing a Genome
    :ivar agent: agent data parsed from topology
    :ivar description: Genome description field
    :ivar primitive_map: dict of "node name" to "node id" pairings
    """

    def __init__(self, topology: dict):
        """Initialize a genome from a GAIuS agent topology (dict)

        Args:
            topology (dict, required): GAIuS agent topology
        """
        self.topology = topology
        self.agent = self.topology['agent']
        self.description = self.topology['description']
        # Not everyone will have style information, so wrap this:
        try:
            self.style_obj = self.topology['style']
            self.style_obj[1]['style']['curve-style'] = 'bezier'
        except Exception:
            pass
        self.primitives = {}
        self.manipulatives = {}
        self.action_ids = []
        self.actions_manifests = {}
        for node in self.topology['elements']['nodes']:
            if node['data']['type'] == 'primitive':
                self.primitives[node['data']['id']] = node['data']
            elif node['data']['type'] == 'manipulative':
                self.manipulatives[node['data']['id']] = node['data']

        self.agent_genome = {'primitives': self.primitives,
                             'manipulatives': self.manipulatives}
        self.primitive_map = {x['name']: _id for _id,
                              x in self.primitives.items()}
        self.manipulative_map = {_id: x['name']
                                 for _id, x in self.manipulatives.items()}

        return

    def get_nodes(self):
        """Return a tuple of :samp:`primitive node names`, :samp:`manipulative node names` from the topology"""
        return self.agent_genome['primitives'], self.agent_genome['manipulatives']

    def get_primitive_map(self):
        """Get a map of node names to primitive ids in the GAIuS agent topology

        Example:
            .. code-block:: python

                >>> agent = AgentClient(agent_info)
                >>> agent.connect()
                >>> agent.genome.get_primitive_map()
                {'P1': 'p46b6b076c'}
        """
        return self.primitive_map

    def get_manipulative_map(self):
        """Get a map of the manipulatives connected to each primitive node in the GAIuS agent topology

        Returns:
            dict: dictionary of manipulatives mappings in the topology
        """
        return self.manipulative_map

    def change_genes(self, p_id, gene_data):
        """Change the genes of a primitive in the Genome's cache

        Args:
            p_id (str): primitive id of the node to edit
            gene_data (dict): dictionary of genes to update in the Genome's cache
        """
        for key, value in gene_data.items():
            self.agent_genome['primitives'][p_id][key] = value
        return

    def display(self):  # pragma: no cover
        """Display the Genome topology in Cytoscape
        """
        try:
            from ipycytoscape import CytoscapeWidget
            from IPython.display import display, clear_output
            from ipywidgets import Output
        except ImportError as e:
            logger.exception(
                "Failed to import dependencies for displaying Cytoscape graph")
            raise

        cyto = CytoscapeWidget()
        cyto.graph.add_graph_from_json(self.topology['elements'])
        cyto.set_style(self.style_obj)
        clear_output()

        out = Output(layout={'border': '1px solid black'})

        def display_node_data(node):
            """Show node data on click
            """
            with out:
                out.clear_output()
                print(
                    f'Node {node["data"]["id"]} details:\n{json.dumps(node, indent=2)}')
            pass

        def display_edge_data(edge):
            """Show edge data on click
            """
            with out:
                out.clear_output()
                print(
                    f'Edge {edge["data"]["id"]} details:\n{json.dumps(edge, indent=2)}')
            pass

        cyto.on('node', 'click', display_node_data)
        cyto.on('edge', 'click', display_edge_data)
        display(cyto)
        display(out)

        return

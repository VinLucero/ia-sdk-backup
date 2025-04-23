"""Utility functions for interacting with GAIuS"""
import warnings
import json
import os
from itertools import chain
from collections import Counter
from copy import deepcopy
import networkx as nx
import plotly.graph_objs as go
import numpy as np
from typing import Dict, List
from collections import defaultdict

class GDFFormatError(BaseException):
    """Error raised when GDF is of improper format"""
    pass

def create_gdf(strings=None,
               vectors=None,
               emotives=None,
               metadata=None) -> dict:
    """Create GDF using supplied list of strings, vectors, emotives, and/or
    metadata

    Args:
        strings (list, optional): Used to provide symbols as string data
            to GAIuS. Defaults to None.
        vectors (list, optional): Used to input vector data to GAIuS.
            Defaults to None.
        emotives (dict, optional): Used to provide emotional data to GAIuS.
            Defaults to None.
        metadata (dict, optional): Used to provide miscellaneous data to GAIuS.
            Defaults to None.

    Returns:
        dict: A dictionary representing the GDF

    Example:
        .. code-block:: python

            from ia.gaius.utils import create_gdf
            gdf = create_gdf(strings=["hello"], emotives={"happy": 10.0})


    .. warning::
        If fields provided are not of the type expected, a GDFFormatError will be
        raised
    
    .. testsetup:: creategdf
        
        # here are the expected gdfs
        gdf1 = {"strings": [],
                "vectors": [],
                "emotives": {},
                "metadata": {}
                }
        gdf2 = {"strings": ["hello"],
                "vectors": [],
                "emotives": {},
                "metadata": {}
                }
        gdf3 = {"strings": ["hello"],
                "vectors": [[1, 2, 3, 4]],
                "emotives": {},
                "metadata": {}
                }
        gdf4 = {"strings": ["hello"],
                "vectors": [[1, 2, 3, 4]],
                "emotives": {"utility": 50},
                "metadata": {}
                }
        gdf5 = {"strings": ["hello"],
                "vectors": [[1, 2, 3, 4]],
                "emotives": {"utility": 50},
                "metadata": {"hello": "world"}
                }
        from ia.gaius.utils import create_gdf
        
    .. doctest:: creategdf
        :hide:
        
        >>> create_gdf() == gdf1
        True
        >>> create_gdf(strings=["hello"]) == gdf2
        True
        >>> create_gdf(strings=["hello"], vectors=[[1, 2, 3, 4]]) == gdf3
        True
        >>> create_gdf(strings=["hello"], vectors=[[1, 2, 3, 4]], emotives={"utility": 50}) == gdf4
        True
        >>> create_gdf(strings=["hello"], vectors=[[1, 2, 3, 4]], emotives={"utility": 50}, metadata={"hello": "world"}) == gdf5
        True

    """
    gdf = {
        "vectors": [] if vectors is None else vectors,
        "strings": [] if strings is None else strings,
        "emotives": {} if emotives is None else emotives,
        "metadata": {} if metadata is None else metadata
    }

    if not isinstance(gdf['vectors'], list):
        raise GDFFormatError(f"vectors field is of type \
                                  {type(gdf['vectors'])}, expected list")
    for v in gdf['vectors']:
        if not isinstance(v, list):
            raise GDFFormatError(f'Vector at index {gdf["vectors"].index(v)} is not a list')
    if not isinstance(gdf['strings'], list):
        raise GDFFormatError(f"strings field is of type \
                                  {type(gdf['strings'])}, expected list")
    if not isinstance(gdf['emotives'], dict):
        raise GDFFormatError(f"emotives field is of type \
                                  {type(gdf['emotives'])}, expected dict")
    if not isinstance(gdf['metadata'], dict):
        raise GDFFormatError(f"metadata field is of type \
                                  {type(gdf['metadata'])}, expected dict")

    return gdf


def log_progress(sequence, every=None, size=None, name='Items'): # pragma: no cover
    """
    A nice little Jupyter progress bar widget from:
    https://github.com/alexanderkuk/log-progress
    """
    from ipywidgets import IntProgress, HTML, VBox
    from IPython.display import display

    is_iterator = False
    if size is None:
        try:
            size = len(sequence)
        except TypeError:
            is_iterator = True
    if size is not None:
        if every is None:
            if size <= 200:
                every = 1
            else:
                every = int(size / 200)     # every 0.5%
    else:
        assert every is not None, 'sequence is iterator, set every'

    if is_iterator:
        progress = IntProgress(min=0, max=1, value=1)
        progress.bar_style = 'info'
    else:
        progress = IntProgress(min=0, max=size, value=0)
    label = HTML()
    box = VBox(children=[label, progress])
    display(box)

    index = 0
    try:
        for index, record in enumerate(sequence, 1):
            if index == 1 or index % every == 0:
                if is_iterator:
                    label.value = '{name}: {index} / ?'.format(
                        name=name,
                        index=index
                    )
                else:
                    progress.value = index
                    label.value = u'{name}: {index} / {size}'.format(
                        name=name,
                        index=index,
                        size=size
                    )
            yield record
    except Exception as error:
        print(f'Error in log_progress function: {str(error)})')
        progress.bar_style = 'danger'
        raise
    else:
        progress.bar_style = 'success'
        progress.value = index
        label.value = "{name}: {index}".format(
            name=name,
            index=str(index or '?')
        )


def abstract_names(ensemble: list) -> list:
    """Get a set of model names from a prediction ensemble

    Args:
        ensemble (list): a prediction ensemble

    Returns:
        list: list of models from predictions in the prediction ensemble

    Example:

        .. code-block:: python

            from ia.gaius.agent_client import AgentClient
            from ia.gaius.utils import abstract_names
            ...
            agent = AgentClient(agent_info)
            agent.connect()
            ...
            ensemble = agent.get_predictions(nodes=['P1'])
            models = abstract_names(ensemble)

    .. testsetup:: abstract_names
    
        # example prediction sequences
        ensemble1 = []
        ensemble2 = [{"name": "MODEL|1"},
                     {"name": "MODEL|2"},
                     {"name": "MODEL|3"},
                     {"name": "MODEL|4"},
                     {"name": "MODEL|5"}]
        ensemble3 = [{"name": "MODEL|0"},
                     {"name": "MODEL|0"},
                     {"name": "MODEL|0"},
                     {"name": "MODEL|0"},
                     {"name": "MODEL|0"}]
        from ia.gaius.utils import abstract_names

    .. doctest:: abstract_names
        :hide:
        
        >>> abstract_names(ensemble1) == []
        True
        >>> sorted(abstract_names(ensemble2)) == sorted(["MODEL|1", "MODEL|2", "MODEL|3", "MODEL|4", "MODEL|5"])
        True
        >>> abstract_names(ensemble3) == ['MODEL|0']
        True

    """
    return list(set([pred['name'] for pred in ensemble]))


def write_gdf_to_file(directory_name: str,
                      filename: str,
                      sequence: list) -> str:
    """Write a GDF sequence to a file

    Args:
        directory_name (str, required): directory to save GDFs to
        filename (str, required): filename to save to
        sequence (list, required): list of individual GDF events
            making up a sequence

    Example:
        .. code-block:: python

            from ia.gaius.utils import write_gdf_to_file, create_gdf
            sequence = [create_gdf(strings=["hello"]),
                        create_gdf(strings=["world"])]
            filename = 'hello_world'
            directory_name = '/example/dir'
            write_gdf_to_file(directory_name, filename, sequence)

    .. warning::
        Will overwrite the file at ``<directory_name>/<filename>``.
        Please ensure it is acceptable to do so.
        No safety checks are performed in this function

    """
    gdf_file_path = os.path.join(directory_name, filename)
    with open(gdf_file_path, 'w') as f:
        for event_idx, event in enumerate(sequence):
            json.dump(event, f)
            if event_idx != len(sequence) - 1:
                f.write('\n')

    return 'success'


def load_sequence_from_file(directory_name: str,
                      filename: str) -> list:
    """Load a GDF sequence to a file

    Args:
        directory_name (str, required): directory to load GDFs from
        filename (str, required): filename to load from

    Example:
        .. code-block:: python

            from ia.gaius.utils import load_sequence_from_file, create_gdf
            sequence = [create_gdf(strings=["hello"]),
                        create_gdf(strings=["world"])]
            filename = 'hello_world'
            directory_name = '/example/dir'
            load_sequence_from_file(directory_name, filename)


    """
    gdf_file_path = os.path.join(directory_name, filename)
    with open(gdf_file_path, 'r') as f:
        sequence = [json.loads(line) for line in f.readlines()]

    return sequence


def retrieve_bottom_level_records(traceback: dict) -> list:
    """Retrieve all records from a traceback
    (:func:`ia.gaius.agent_client.AgentClient.investigate_record`)
    call that have bottomLevel=True

    Args:
        traceback (dict): the dictionary pertaining to the output
            of an investigate call

    Returns:
        list: list of records from the traceback

    Example:
        .. code-block:: python

            from ia.gaius.agent_client import AgentClient
            from ia.gaius.utils import retrieve_bottom_level_records
            ...
            agent = AgentClient(agent_info)
            ...
            traceback_output = agent.investigate_record(record=record,
                                                        node=['P1'])
            bottom_level = retrieve_bottom_level_records(traceback_output)

    """
    bottom_level_records = []
    if traceback['bottomLevel'] is not True:
        for item_list in traceback['subitems']:
            for item in item_list:
                if isinstance(item, dict):
                    bottom_level_records.extend(retrieve_bottom_level_records(deepcopy(item)))
    else:
        bottom_level_records.append(traceback)

    return bottom_level_records

def merge_gdfs(gdf1: dict, gdf2: dict) -> dict:
    """Merge two GDFs into a single gdf, accumulating the values in each field

    Args:
        gdf1 (dict): First GDF
        gdf2 (dict): Second GDF

    Raises:
        Exception: When vectors are of differing lengths

    Returns:
        dict: Merged GDF
    """

    merge_strings = list(chain(gdf1["strings"], gdf2["strings"]))

    merge_vecs = list(chain(gdf1["vectors"], gdf2["vectors"]))
    print(f"{merge_vecs=}")
    if len(merge_vecs) > 0:
        if not all([len(vec) == len(merge_vecs[0]) for vec in merge_vecs]):
            raise Exception(f"Vectors not all of same length!!!")

    merge_emotives = Counter()
    merge_emotives.update(gdf1["emotives"])
    merge_emotives.update(gdf2["emotives"])
    merge_emotives = dict(merge_emotives)

    # no way to get around conflicts here, just going to add keys from gdf1, then update with keys from gdf2
    merge_metadata = dict()
    merge_metadata.update(gdf1.get("metadata", {}))
    merge_metadata.update(gdf2.get("metadata", {}))

    return create_gdf(strings=merge_strings, vectors=merge_vecs, emotives=merge_emotives, metadata=merge_metadata)

def node_data_to_plotly_string(node_data : Dict, hover_line_length = 30):
    return_string = "{"
    past_chunk = ""

    # output source_fields
    past_chunk = ""
    past_chunk += "'source_fields' : ["
    for name in node_data["source_fields"]:
        past_chunk += name
        past_chunk += ", "

        if len(past_chunk) > hover_line_length:
#             print("past_chunk", past_chunk)
            return_string += (past_chunk + "<br>")
            past_chunk = ""
    
    return_string += past_chunk
    return_string += "],<br>"

    # output destination_fields
    past_chunk = ""
    past_chunk += "'destination_fields' : ["
    for name in node_data["destination_fields"]:
        past_chunk += name
        past_chunk += ", "

        if len(past_chunk) > hover_line_length:
#             print("past_chunk", past_chunk)
            return_string += (past_chunk + "<br>")
            past_chunk = ""
    
    return_string += past_chunk
    return_string += "],<br>"
    
    # output params
    past_chunk = ""
    past_chunk += "'params' : {"
    for param_name, param_data in node_data["params"].items():
        print(param_name, param_data)
        past_chunk += f"'{param_name}' : {param_data}"
        past_chunk += "',"

        if len(past_chunk) > hover_line_length:
#             print("past_chunk", past_chunk)
            return_string += (past_chunk + "<br>")
            past_chunk = ""
    
    return_string += past_chunk
    return_string += "  },<br>"
    return_string += "}"
#     print("return_string", return_string)
    return return_string

def plot_directed_networkx_graph(graph : nx.DiGraph, 
                                 starting_functions:list, 
                                 base_x_distance = 10, 
                                 base_y_distance = 10,
                                 arrow_marker_size = 15,
                                 node_marker_size = 15,
                                 hover_line_length = 30,
                                 title='Directed Graph'):
    dict_of_all_nodes = {node[0] : node[1] for node in list(graph.nodes(data=True))}
    # seperate nodes into layers
    layers = []

    # layer 0, aka the starting functions
    layers.append({node_name : dict_of_all_nodes[node_name] for node_name in starting_functions})

    # remove starting functions from dict_of_all_nodes
    for node_name in starting_functions:
        dict_of_all_nodes.pop(node_name)
    
    layer_num_to_look_for_connections_to = 0
    while layer_num_to_look_for_connections_to <= len(layers) and len(dict_of_all_nodes) != 0:
        next_layer_node_names = []
        # go through all nodes in previous layer, and coallate all directly connected functions in pipeline
        for node_name in layers[layer_num_to_look_for_connections_to].keys():
            # print("Directly connected to", node_name, [node for node in graph.neighbors(node_name)])
            # get all nodes for next layer
            next_layer_node_names.extend([node for node in graph.neighbors(node_name)])
        
        # remove duplicates
        next_layer_node_names = set(next_layer_node_names)
        
        # append empty dict
        layers.append({})

        # retrieve actual node dicts from dict_of_all_nodes, and add to next layer
        # also remove from dict_of_all_nodes
        for node_name in next_layer_node_names:
            if node_name not in dict_of_all_nodes:
                continue
            layers[layer_num_to_look_for_connections_to+1][node_name] = dict_of_all_nodes[node_name]
            dict_of_all_nodes.pop(node_name)
        
        layer_num_to_look_for_connections_to += 1
    
    # pp(layers)
    # pp(dict_of_all_nodes)

    # now we can process each layer and create some positions for the nodes on the graph
    current_layer_x = 0
    node_x = {}
    node_y = {}
    for layer in layers:
        x_vals = [current_layer_x for i in range(len(layer))]
        if(len(layer) != 1):
            y_vals = list(np.linspace(-len(layer) * base_y_distance, len(layer) * base_y_distance, len(layer)))
        else:
            y_vals = [0]
        for node_name in layer.keys():
            node_x[node_name] = x_vals.pop()
            node_y[node_name] = y_vals.pop()
        
        current_layer_x += base_x_distance

    # now that we have the node locations, we need their edges
    edge_x = []
    edge_y = []
    
    # create node scatter points
    node_round_robin_num = 0
    css_colors = ["aliceblue", "antiquewhite", "aqua", "aquamarine", "azure",
            "beige", "bisque", "black", "blanchedalmond", "blue",
            "blueviolet", "brown", "burlywood", "cadetblue",
            "chartreuse", "chocolate", "coral", "cornflowerblue",
            "cornsilk", "crimson", "cyan", "darkblue", "darkcyan",
            "darkgoldenrod", "darkgray", "darkgrey", "darkgreen",
            "darkkhaki", "darkmagenta", "darkolivegreen", "darkorange",
            "darkorchid", "darkred", "darksalmon", "darkseagreen",
            "darkslateblue", "darkslategray", "darkslategrey",
            "darkturquoise", "darkviolet", "deeppink", "deepskyblue",
            "dimgray", "dimgrey", "dodgerblue", "firebrick",
            "floralwhite", "forestgreen", "fuchsia", "gainsboro",
            "ghostwhite", "gold", "goldenrod", "gray", "grey", "green",
            "greenyellow", "honeydew", "hotpink", "indianred", "indigo",
            "ivory", "khaki", "lavender", "lavenderblush", "lawngreen",
            "lemonchiffon", "lightblue", "lightcoral", "lightcyan",
            "lightgoldenrodyellow", "lightgray", "lightgrey",
            "lightgreen", "lightpink", "lightsalmon", "lightseagreen",
            "lightskyblue", "lightslategray", "lightslategrey",
            "lightsteelblue", "lightyellow", "lime", "limegreen",
            "linen", "magenta", "maroon", "mediumaquamarine",
            "mediumblue", "mediumorchid", "mediumpurple",
            "mediumseagreen", "mediumslateblue", "mediumspringgreen",
            "mediumturquoise", "mediumvioletred", "midnightblue",
            "mintcream", 'mistyrose', 'moccasin', 'navajowhite', 'navy',
            'oldlace', 'olive', 'olivedrab', 'orange', 'orangered',
            'orchid', 'palegoldenrod', 'palegreen', 'paleturquoise',
            'palevioletred', 'papayawhip', 'peachpuff', 'peru', 'pink',
            'plum', 'powderblue', 'purple', 'red', 'rosybrown',
            'royalblue', 'rebeccapurple', 'saddlebrown', 'salmon',
            'sandybrown', 'seagreen', 'seashell', 'sienna', 'silver',
            'skyblue', 'slateblue', 'slategray', 'slategrey', 'snow',
            'springgreen', 'steelblue', 'tan', 'teal', 'thistle', 'tomato',
            'turquoise', 'violet', 'wheat', 'white', 'whitesmoke',
            'yellow', 'yellowgreen']

    node_colors = []
    marker_colors = []
    node_round_robin_num = 0
    for layer in layers:
        for node, node_dat in layer.items():
            node_colors.append(css_colors[node_round_robin_num])
            # print(node_dat)

            for neighbor in graph.neighbors(node):
                marker_colors.append(css_colors[node_round_robin_num])
                marker_colors.append(css_colors[node_round_robin_num])
                marker_colors.append("black")

                x0, y0 = node_x[node], node_y[node]
                x1, y1 = node_x[neighbor], node_y[neighbor]
                # print("edge[0]", x0, y0)
                # print("edge[1]", x1, y1)
                edge_x.append(x0)
                edge_x.append(x1)
                edge_x.append(None)
                edge_y.append(y0)
                edge_y.append(y1)
                edge_y.append(None)
            node_round_robin_num += 1
    
    # print(marker_colors)    

    # create hover text
    node_text = []
    for layer in layers:
        for node in layer.values():
            node_text.append(node_data_to_plotly_string(node))
    
    node_trace = go.Scatter(
                x=list(node_x.values()), y=list(node_y.values()),
                mode='markers',
                hoverinfo='text',
                hovertemplate="%{customdata}<extra></extra>",
                customdata=node_text,
                marker=dict(
                    showscale=False,
                    # colorscale options
                    #'Greys' | 'YlGnBu' | 'Greens' | 'YlOrRd' | 'Bluered' | 'RdBu' |
                    #'Reds' | 'Blues' | 'Picnic' | 'Rainbow' | 'Portland' | 'Jet' |
                    #'Hot' | 'Blackbody' | 'Earth' | 'Electric' | 'Viridis' |
                    colorscale='YlGnBu',
                    reversescale=True,
                    color=node_colors,
                    size=node_marker_size,
                    colorbar=dict(
                        thickness=15,
                        title='Node Connections',
                        xanchor='left',
                        titleside='right'
                    ),
                    line_width=2)
                    )
    
    # node_trace.text = list(node_x.keys())
    
    # create edges
    edge_trace = go.Scatter(
        x=edge_x, y=edge_y,
        line=dict(width=0.5, color="black"),
        hoverinfo='none',
        mode="lines+markers",
        marker=dict(size=arrow_marker_size,symbol= "arrow-bar-up", angleref="previous"),
        )
    
    edge_trace.marker.color = marker_colors

    fig = go.Figure(data=[edge_trace, node_trace],
                layout=go.Layout(
                    title='<br>Network graph made with Python',
                    titlefont_size=16,
                    showlegend=False,
                    hovermode='closest',
                    margin=dict(b=20,l=5,r=5,t=40),
                    annotations=[ dict(
                        text="Pipeline Graph",
                        showarrow=False,
                        xref="paper", yref="paper",
                        x=0.005, y=-0.002 ) ],
                    xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                    yaxis=dict(showgrid=False, zeroline=False, showticklabels=False))
                    )
    fig.update_layout(
                        template='seaborn'
    )
    fig.show()

def build_pipeline_layers(input_slot_data, pipelines_dict):
    layers = defaultdict(list)
    # print(f"Processing pipelines for {input_slot_name}")
    for pipeline_name in input_slot_data["pipelines"]:
        # create copy of pipeline since it might appear in multiple input_slots
        pipeline_copy = deepcopy(pipelines_dict[pipeline_name])

        # create graph for easy processing
        dict_of_all_nodes = {node[0] : node[1] for node in pipeline_copy["pipeline_preprocessing_functions"].items()}

        # layer 0, aka the starting functions
        layers[pipeline_name].append({node_name : dict_of_all_nodes[node_name] for node_name in pipeline_copy["starting_functions"]})

        # remove starting functions from dict_of_all_nodes
        for node_name in pipeline_copy["starting_functions"]:
            dict_of_all_nodes.pop(node_name)

        # now to construct all other layers(it gets a bit complex)
        layer_num_to_look_for_connections_to = 0
        while len(dict_of_all_nodes) != 0:
            next_layer_node_names = []
            layers[pipeline_name].append({})
            # go through all nodes in previous layer, and coallate all directly connected functions in pipeline
            for node_name in layers[pipeline_name][layer_num_to_look_for_connections_to].keys():
                # print("Directly connected to", node_name, [node for node in pipeline_copy["pipeline_connections"][node_name].keys()])
                # get all nodes for next layer
                next_layer_node_names.extend([node for node in pipeline_copy["pipeline_connections"][node_name].keys()])

            # remove duplicates
            next_layer_node_names = set(next_layer_node_names)

            # retrieve actual node dicts from dict_of_all_nodes, and add to next layer
            # also remove from dict_of_all_nodes
            for node_name in next_layer_node_names:
                if node_name not in dict_of_all_nodes:
                    continue
                layers[pipeline_name][layer_num_to_look_for_connections_to+1][node_name] = \
                                                                        dict_of_all_nodes[node_name]
                dict_of_all_nodes.pop(node_name)

            layer_num_to_look_for_connections_to += 1
    
    return layers

def find_output_slots_and_add_to_end(pipeline_layers, output_slots_dict):
    # if there are no output_slots available then return original data
    if len(output_slots_dict) == 0:
        return pipeline_layers
    
    #check if final layer has any params named "output_slot_names"
    for pipeline_name in pipeline_layers.keys():
        for function_name, function_data in pipeline_layers[pipeline_name][-1].items():
            if "output_slot_names"  in function_data["preprocessor_params"]:
                print(function_data)
                if type(function_data["preprocessor_params"]["output_slot_names"]) is list:
                    pipeline_layers[pipeline_name].append({})
                    for output_slot_name in function_data["preprocessor_params"]["output_slot_names"]:
                        pipeline_layers[pipeline_name][-1][output_slot_name] = output_slots_dict[output_slot_name]
                elif type(function_data["preprocessor_params"]["output_slot_names"]) is dict:
                    pipeline_layers[pipeline_name].append({})
                    for output_slot_name in function_data["preprocessor_params"]["output_slot_names"].keys():
                        pipeline_layers[pipeline_name][-1][output_slot_name] = output_slots_dict[output_slot_name]
                else:
                    # skip there's nothing that can be done
                    continue
    return pipeline_layers

def dict_to_plotly_string(node_data : Dict, hover_line_length = 30):
    return_string = "{"
    past_chunk = ""

    for key, data in node_data.items():
        past_chunk = ""
        past_chunk += f"'{key}' : {data},"

        if len(past_chunk) > hover_line_length:
#             print("past_chunk", past_chunk)
            return_string += (past_chunk + "<br>")
            past_chunk = ""
        
        return_string += past_chunk
    
    return_string += past_chunk
    return_string += ""
    return_string += "}"
#     print("return_string", return_string)
    return return_string

# just a list of css_colors by name which are supported by plotly
css_colors = ["aliceblue", "antiquewhite", "aqua", "aquamarine", "azure",
            "beige", "bisque", "black", "blanchedalmond", "blue",
            "blueviolet", "brown", "burlywood", "cadetblue",
            "chartreuse", "chocolate", "coral", "cornflowerblue",
            "cornsilk", "crimson", "cyan", "darkblue", "darkcyan",
            "darkgoldenrod", "darkgray", "darkgrey", "darkgreen",
            "darkkhaki", "darkmagenta", "darkolivegreen", "darkorange",
            "darkorchid", "darkred", "darksalmon", "darkseagreen",
            "darkslateblue", "darkslategray", "darkslategrey",
            "darkturquoise", "darkviolet", "deeppink", "deepskyblue",
            "dimgray", "dimgrey", "dodgerblue", "firebrick",
            "floralwhite", "forestgreen", "fuchsia", "gainsboro",
            "ghostwhite", "gold", "goldenrod", "gray", "grey", "green",
            "greenyellow", "honeydew", "hotpink", "indianred", "indigo",
            "ivory", "khaki", "lavender", "lavenderblush", "lawngreen",
            "lemonchiffon", "lightblue", "lightcoral", "lightcyan",
            "lightgoldenrodyellow", "lightgray", "lightgrey",
            "lightgreen", "lightpink", "lightsalmon", "lightseagreen",
            "lightskyblue", "lightslategray", "lightslategrey",
            "lightsteelblue", "lightyellow", "lime", "limegreen",
            "linen", "magenta", "maroon", "mediumaquamarine",
            "mediumblue", "mediumorchid", "mediumpurple",
            "mediumseagreen", "mediumslateblue", "mediumspringgreen",
            "mediumturquoise", "mediumvioletred", "midnightblue",
            "mintcream", 'mistyrose', 'moccasin', 'navajowhite', 'navy',
            'oldlace', 'olive', 'olivedrab', 'orange', 'orangered',
            'orchid', 'palegoldenrod', 'palegreen', 'paleturquoise',
            'palevioletred', 'papayawhip', 'peachpuff', 'peru', 'pink',
            'plum', 'powderblue', 'purple', 'red', 'rosybrown',
            'royalblue', 'rebeccapurple', 'saddlebrown', 'salmon',
            'sandybrown', 'seagreen', 'seashell', 'sienna', 'silver',
            'skyblue', 'slateblue', 'slategray', 'slategrey', 'snow',
            'springgreen', 'steelblue', 'tan', 'teal', 'thistle', 'tomato',
            'turquoise', 'violet', 'wheat', 'white', 'whitesmoke',
            'yellow', 'yellowgreen']

def plot_directed_networkx_graph(graph : nx.DiGraph, 
                                 starting_functions:list, 
                                 base_x_distance = 10, 
                                 base_y_distance = 10,
                                 arrow_marker_size = 15,
                                 node_marker_size = 15,
                                 hover_line_length = 30,
                                 title='Directed Graph'):
    global css_colors
    dict_of_all_nodes = {node[0] : node[1] for node in list(graph.nodes(data=True))}
    # seperate nodes into layers
    layers = []

    # layer 0, aka the starting functions
    layers.append({node_name : dict_of_all_nodes[node_name] for node_name in starting_functions})

    # remove starting functions from dict_of_all_nodes
    for node_name in starting_functions:
        dict_of_all_nodes.pop(node_name)
    
    layer_num_to_look_for_connections_to = 0
    while layer_num_to_look_for_connections_to <= len(layers) and len(dict_of_all_nodes) != 0:
        next_layer_node_names = []
        # go through all nodes in previous layer, and coallate all directly connected functions in pipeline
        for node_name in layers[layer_num_to_look_for_connections_to].keys():
            # print("Directly connected to", node_name, [node for node in graph.neighbors(node_name)])
            # get all nodes for next layer
            next_layer_node_names.extend([node for node in graph.neighbors(node_name)])
        
        # remove duplicates
        next_layer_node_names = set(next_layer_node_names)
        
        # append empty dict
        layers.append({})

        # retrieve actual node dicts from dict_of_all_nodes, and add to next layer
        # also remove from dict_of_all_nodes
        for node_name in next_layer_node_names:
            if node_name not in dict_of_all_nodes:
                continue
            layers[layer_num_to_look_for_connections_to+1][node_name] = dict_of_all_nodes[node_name]
            dict_of_all_nodes.pop(node_name)
        
        layer_num_to_look_for_connections_to += 1
    
    # pp(layers)
    # pp(dict_of_all_nodes)

    # now we can process each layer and create some positions for the nodes on the graph
    current_layer_x = 0
    node_x = {}
    node_y = {}
    for layer in layers:
        x_vals = [current_layer_x for i in range(len(layer))]
        if(len(layer) != 1):
            y_vals = list(np.linspace(-len(layer) * base_y_distance, len(layer) * base_y_distance, len(layer)))
        else:
            y_vals = [0]
        for node_name in layer.keys():
            node_x[node_name] = x_vals.pop()
            node_y[node_name] = y_vals.pop()
        
        current_layer_x += base_x_distance

    # now that we have the node locations, we need their edges
    edge_x = []
    edge_y = []
    
    # create node scatter points
    node_round_robin_num = 0

    node_colors = []
    marker_colors = []
    node_round_robin_num = 0
    for layer in layers:
        for node, node_dat in layer.items():
            node_colors.append(css_colors[node_round_robin_num])
            # print(node_dat)

            for neighbor in graph.neighbors(node):
                marker_colors.append(css_colors[node_round_robin_num])
                marker_colors.append(css_colors[node_round_robin_num])
                marker_colors.append("black")

                x0, y0 = node_x[node], node_y[node]
                x1, y1 = node_x[neighbor], node_y[neighbor]
                # print("edge[0]", x0, y0)
                # print("edge[1]", x1, y1)
                edge_x.append(x0)
                edge_x.append(x1)
                edge_x.append(None)
                edge_y.append(y0)
                edge_y.append(y1)
                edge_y.append(None)
            node_round_robin_num += 1
    
    # print(marker_colors)    

    # create hover text
    node_text = []
    for layer in layers:
        for node in layer.values():
            node_text.append(dict_to_plotly_string(node))
    
    node_trace = go.Scatter(
                x=list(node_x.values()), y=list(node_y.values()),
                mode='markers',
                hoverinfo='text',
                hovertemplate="%{customdata}<extra></extra>",
                customdata=node_text,
                marker=dict(
                    showscale=False,
                    # colorscale options
                    #'Greys' | 'YlGnBu' | 'Greens' | 'YlOrRd' | 'Bluered' | 'RdBu' |
                    #'Reds' | 'Blues' | 'Picnic' | 'Rainbow' | 'Portland' | 'Jet' |
                    #'Hot' | 'Blackbody' | 'Earth' | 'Electric' | 'Viridis' |
                    colorscale='YlGnBu',
                    reversescale=True,
                    color=node_colors,
                    size=node_marker_size,
                    colorbar=dict(
                        thickness=15,
                        title='Node Connections',
                        xanchor='left',
                        titleside='right'
                    ),
                    line_width=2)
                    )
    
    # node_trace.text = list(node_x.keys())
    
    # create edges
    edge_trace = go.Scatter(
        x=edge_x, y=edge_y,
        line=dict(width=0.5, color="black"),
        hoverinfo='none',
        mode="lines+markers",
        marker=dict(size=arrow_marker_size,symbol= "arrow-bar-up", angleref="previous"),
        )
    
    edge_trace.marker.color = marker_colors

    fig = go.Figure(data=[edge_trace, node_trace],
                layout=go.Layout(
                    title=title,
                    titlefont_size=16,
                    showlegend=False,
                    hovermode='closest',
                    margin=dict(b=20,l=5,r=5,t=40),
                    # annotations=[ dict(
                    #     text="Pipeline Graph",
                    #     showarrow=False,
                    #     xref="paper", yref="paper",
                    #     x=0.005, y=-0.002 ) ],
                    xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                    yaxis=dict(showgrid=False, zeroline=False, showticklabels=False))
                    )
    fig.update_layout(
                        template='seaborn'
    )
    fig.show()
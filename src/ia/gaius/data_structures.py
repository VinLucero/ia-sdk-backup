from copy import deepcopy
import pandas as pd
import networkx as nx
from itertools import chain
from hashlib import sha1
from collections import defaultdict, Counter
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)


def conditional_add_edge(u, v, graph: nx.Graph, attributes: dict) -> None:
    if graph.has_edge(u, v):
        # update edge
        cur_edge_data = graph.get_edge_data(u, v)
        for key, value in attributes.items():
            if key in ["time"]:
                pass
            else:
                cur_edge_data[key] += value
    else:
        graph.add_edge(u, v, **attributes)


def update_edge_details(dict1: dict, dict2: dict) -> dict:
    new_dict = {}
    for k, v in dict2.items():
        if k in ["pos", "time", "data"]:
            continue
        if k not in dict1:
            new_dict[k] = v
        else:
            new_dict[k] = dict1[k] + v
    return new_dict


def update_node_details(final_node_data: dict, prev_node_data: dict) -> dict:
    for k, v in prev_node_data.items():
        if k in ["pos", "time", "data"]:
            continue
        if k not in final_node_data:
            final_node_data[k] = v
        else:
            final_node_data[k] += v

    return final_node_data


def hash_event(e: list) -> str:
    return sha1(str(e).encode()).hexdigest()[:8]


class Prediction(dict):
    """Data Structure to wrap a Prediction dictionary with additional functionality

    Provides interfaces for generating NetworkX graphs from prediction information

    """

    def __init__(self, prediction: dict = None, metadata: list = None, **kwargs):
        """Constuct Prediction class object. Optionally provide
        metadata information for sequence

        Args:
            prediction (dict, optional): Prediction dictionary. Defaults to None.
            metadata (list, optional): Optional sequence of metadata
                pertaining to prediction object (from model). Defaults to None.
        """
        if prediction is None:
            prediction = kwargs

        self._prediction = deepcopy(prediction)
        self.confidence: float = self._prediction["confidence"]
        self.confluence: float = self._prediction["confluence"]
        self.emotives: dict = self._prediction["emotives"]
        self.entropy: float = self._prediction["entropy"]
        self.evidence: float = self._prediction["evidence"]
        self.extras: list = self._prediction["extras"]
        self.fragmentation: float = self._prediction["fragmentation"]
        self.frequency: int = self._prediction["frequency"]
        self.future: list = self._prediction["future"]
        self.grand_hamiltonian: float = self._prediction["grand_hamiltonian"]
        self.hamiltonian: float = self._prediction["hamiltonian"]
        self.itfdf_similarity: float = self._prediction["itfdf_similarity"]
        self.matches: list = self._prediction["matches"]
        self.missing: list = self._prediction["missing"]
        self.name: str = self._prediction["name"]
        self.past: list = self._prediction["past"]
        self.potential: float = self._prediction["potential"]
        self.present: list = self._prediction["present"]
        self.similarity: float = self._prediction["similarity"]
        self.snr: float = self._prediction["snr"]
        self.type: str = self._prediction["type"]

        self.events = list(chain(self.past, self.present, self.future))

        if metadata is None:
            metadata = [None for _ in self.events]
        self.metadata = metadata
        pass

    def __repr__(self) -> str:
        return f"Prediction(MODEL|{self.name}, potential={self.potential})"

    def toJSON(self) -> dict:
        """Convert Prediction Object back into dictionary format

        Returns:
            dict: prediction in dict format
        """
        return {
            "confidence": self.confidence,
            "confluence": self.confluence,
            "emotives": self.emotives,
            "entropy": self.entropy,
            "evidence": self.evidence,
            "extras": self.extras,
            "fragmentation": self.fragmentation,
            "frequency": self.frequency,
            "future": self.future,
            "grand_hamiltonian": self.grand_hamiltonian,
            "hamiltonian": self.hamiltonian,
            "itfdf_similarity": self.itfdf_similarity,
            "matches": self.matches,
            "missing": self.missing,
            "name": self.name,
            "past": self.past,
            "potential": self.potential,
            "present": self.present,
            "similarity": self.similarity,
            "snr": self.snr,
            "type": self.type,
        }
        
    def toNumericJSON(self) -> dict:
        """Convert Prediction Object back into dictionary format

        Returns:
            dict: prediction in dict format
        """
        return {
            "confidence": self.confidence,
            "confluence": self.confluence,
            "entropy": self.entropy,
            "evidence": self.evidence,
            "fragmentation": self.fragmentation,
            "frequency": self.frequency,
            "grand_hamiltonian": self.grand_hamiltonian,
            "hamiltonian": self.hamiltonian,
            "itfdf_similarity": self.itfdf_similarity,
            "name": self.name,
            "potential": self.potential,
            "similarity": self.similarity,
            "snr": self.snr,
        }

    def toPastStateGraph(self, starting_idx=0) -> nx.Graph:
        """Make graph from symbols in past of prediction

        Args:
            starting_idx (int, optional): _description_. Defaults to 0.

        Returns:
            nx.Graph: resultant graph
        """
        G = nx.Graph()

        idx = starting_idx
        event: list
        event_indexes = []
        for event in self.past:
            symbol: str
            for symbol in event:
                # node metadata for graph (might not mean much for past state)
                symbol_attributes = {"symbol_type": None}
                if symbol in self.missing:
                    symbol_attributes["symbol_type"] = "missing"
                elif symbol in self.matches:
                    symbol_attributes["symbol_type"] = "matches"
                elif symbol in self.extras:
                    symbol_attributes["symbol_type"] = "extras"
                G.add_node(idx, **symbol_attributes)
                event_indexes.append(idx)
                if idx != 0:
                    G.add_edge(idx - 1, idx)
                idx += 1

        return G

    def toPresentStateGraph(self, starting_idx=0) -> nx.Graph:
        G = nx.Graph()

        idx = starting_idx
        event: list
        event_indexes = []
        for event in self.present:
            symbol: str
            for symbol in event:
                # node metadata for graph
                symbol_attributes = {"symbol_type": None}
                if symbol in self.missing:
                    symbol_attributes["symbol_type"] = "missing"
                elif symbol in self.matches:
                    symbol_attributes["symbol_type"] = "matches"
                elif symbol in self.extras:
                    symbol_attributes["symbol_type"] = "extras"
                G.add_node(idx, **symbol_attributes)
                event_indexes.append(idx)
                if idx != 0:
                    G.add_edge(idx - 1, idx)
                idx += 1

            event_indexes = []
        return G

    def toEventGraph(self) -> nx.Graph:
        G = nx.Graph()

        idx = 0
        past_idxs = []
        present_idxs = []
        future_idxs = []
        for e in self.past:
            past_idxs.append(idx)
            idx += 1
        for e in self.present:
            present_idxs.append(idx)
            idx += 1
        for e in self.future:
            future_idxs.append(idx)
            idx += 1
        print(f"{past_idxs=}, {present_idxs=}, {future_idxs=}")

        G.add_nodes_from(
            zip(past_idxs, [{"data": e, "time": "past"} for e in self.past])
        )
        G.add_nodes_from(
            zip(present_idxs, [{"data": e, "time": "present"}
                for e in self.present])
        )
        G.add_nodes_from(
            zip(future_idxs, [{"data": e, "time": "future"}
                for e in self.future])
        )

        for i, idx in enumerate(past_idxs):
            if i >= len(past_idxs) - 1:
                break
            u, v = past_idxs[i], past_idxs[i + 1]
            attributes = {"time": "past", "weight": 1,
                          "frequency": self.frequency}
            conditional_add_edge(u=u, v=v, graph=G, attributes=attributes)
        for i, event in enumerate(present_idxs):
            if i == 0 and self.past:
                u, v = past_idxs[-1], present_idxs[i]
                attributes = {
                    "time": "past_to_present",
                    "weight": 1,
                    "frequency": self.frequency,
                }
                conditional_add_edge(u=u, v=v, graph=G, attributes=attributes)
            if i >= len(present_idxs) - 1:
                break
            else:
                u, v = present_idxs[i], present_idxs[i + 1]
                attributes = {
                    "time": "present",
                    "weight": 1,
                    "frequency": self.frequency,
                }
                conditional_add_edge(u=u, v=v, graph=G, attributes=attributes)

        for i, event in enumerate(future_idxs):
            if i == 0 and self.present:
                u, v = present_idxs[-1], future_idxs[i]
                attributes = {
                    "time": "present_to_future",
                    "weight": 1,
                    "frequency": self.frequency,
                }
                conditional_add_edge(u=u, v=v, graph=G, attributes=attributes)
            if i == len(self.future) - 1:
                break
            else:
                u, v = future_idxs[i], future_idxs[i + 1]
                attributes = {
                    "time": "future",
                    "weight": 1,
                    "frequency": self.frequency,
                }
                conditional_add_edge(u=u, v=v, graph=G, attributes=attributes)

        return G

    def toLoopingEventGraph(self) -> nx.DiGraph:
        """Produce directed graph from sequence of events.
        Add metadata to edges between events

        Returns:
            nx.DiGraph: resultant graph
        """

        G = nx.DiGraph()

        # add a node for each event, including symbol list, time information in node_data
        event_hashes = [hash_event(e) for e in self.events]
        for event, event_hash in zip(self.events, event_hashes):
            cur_event_details = {"data": event}
            if G.has_node(event_hash):
                continue
            G.add_node(event_hash, **cur_event_details)

        edge_attribute_dict = defaultdict(lambda: defaultdict(list))
        for i, event_hash in enumerate(event_hashes):
            if i == len(event_hashes) - 1:
                break
            u, v = event_hashes[i], event_hashes[i + 1]
            attributes = {
                "metadata": [self.metadata[i]],
            }

            for attr_key, attr_val in attributes.items():
                edge_attribute_dict[u, v][attr_key] += attr_val

        for (u, v), edge_dict in edge_attribute_dict.items():
            G.add_edge(u, v, **edge_dict)

        return G

    def toSymbolGraphs(self) -> Dict[str, nx.DiGraph]:
        symbol_graphs: Dict[str, nx.DiGraph] = {}

        symbol_keys = set()
        event: list
        for event in self.events:
            sym: str
            for sym in event:
                symbol_key = sym.rsplit('|', maxsplit=1)[0]
                symbol_keys.add(symbol_key)

        for symbol_key in symbol_keys:
            symbol_sequence = []
            for event in self.events:
                cur_symbol_values = [sym.rsplit('|', maxsplit=1)[
                    1] for sym in event if f'{symbol_key}|' in sym]
                if not cur_symbol_values:
                    cur_symbol_values = ['null']
                symbol_sequence.append(cur_symbol_values)
            # print(f'Symbol {symbol_key} sequence = {symbol_sequence}')
            symbol_value_counter = Counter(chain(*symbol_sequence))

            symbol_graphs[symbol_key] = nx.DiGraph()
            symbol_graphs[symbol_key].add_nodes_from(
                [(sym, {'count': sym_count}) for sym, sym_count in symbol_value_counter.items()])

            symbol_transition_counter = Counter()
            for i, _ in enumerate(symbol_sequence):
                if i == 0:
                    continue
                for sym in symbol_sequence[i-1]:
                    for new_sym in symbol_sequence[i]:
                        symbol_transition_counter.update([(sym, new_sym)])

            for i, _ in enumerate(symbol_sequence):
                if i == 0:
                    continue

                for sym in symbol_sequence[i-1]:
                    for new_sym in symbol_sequence[i]:
                        symbol_graphs[symbol_key].add_edge(
                            sym, new_sym, weight=symbol_transition_counter[(sym, new_sym)])

        return symbol_graphs


class PredictionEnsemble:
    def __init__(
        self, ensemble, metadata_dict: dict = None, node_name: str = None
    ) -> None:
        """Convert Prediction ensemble into class object

        Args:
            ensemble (_type_): the ensemble in list or dict form
            metadata_dict (dict, optional): dict of {model_name: metadata}. Defaults to None.
            node_name (str, optional): Node name for ensemble if provided as list. Defaults to None.
        """
        if node_name is None:
            node_name = "NODE"

        if isinstance(ensemble, list):
            ensemble = {node_name: ensemble}

        self._ensemble: Dict[str, dict] = deepcopy(ensemble)
        self.ensemble: Dict[str, List[Prediction]] = {}

        for k, preds in self._ensemble.items():
            if metadata_dict:
                self.ensemble[k] = [
                    Prediction(prediction=p, metadata=metadata_dict[p["name"]])
                    for p in preds
                ]
            else:
                self.ensemble[k] = [Prediction(prediction=p) for p in preds]

    def __repr__(self) -> str:
        return f"PredictionEnsemble(nodes={list(self.ensemble.keys())})"

    def toDataFrame(self) -> pd.DataFrame:
        """Construct pandas DataFrame using prediction as a row

        Returns:
            pd.DataFrame: showing all predictions from ensemble
        """
        predictions = []
        for k, preds in self.ensemble.items():
            pred: Prediction
            for pred in preds:
                predictions.append({**pred.toJSON(), **{"node": k}})

        return pd.DataFrame(predictions)


    def toNumericDataFrame(self) -> pd.DataFrame:
        """Construct pandas DataFrame using prediction as a row. Use numeric fields and name only

        Returns:
            pd.DataFrame: showing all predictions from ensemble
        """
        predictions = []
        for k, preds in self.ensemble.items():
            pred: Prediction
            for pred in preds:
                predictions.append({**pred.toNumericJSON(), **{"node": k}})

        return pd.DataFrame(predictions)

    def toEventGraph(self) -> nx.DiGraph:
        """Merge Event graphs from each prediction into a single, larger directed graph

        Returns:
            nx.DiGraph: merged directed graph
        """
        pred_graphs = []
        for preds in self.ensemble.values():
            pred: Prediction
            for i, pred in enumerate(preds):
                pred_graphs.append(pred.toLoopingEventGraph())
        graph: nx.DiGraph
        for i, graph in enumerate(pred_graphs):
            for j, (node, node_data) in enumerate(graph.nodes(data=True)):
                node_data["pos"] = (10 * j, i)

        final_graph = nx.DiGraph()

        edge_attribute_dict = defaultdict(lambda: defaultdict(list))
        graph: nx.DiGraph
        for graph in pred_graphs:
            for node, prev_node_data in graph.nodes(data=True):
                # prev_node_data['time'] = None
                if not final_graph.has_node(node):
                    final_graph.add_node(node, **prev_node_data)

            for u, v, prev_edge_data in graph.edges(data=True):
                for attr_key, attr_val in prev_edge_data.items():
                    edge_attribute_dict[u, v][attr_key] += attr_val

        for (u, v), edge_dict in edge_attribute_dict.items():
            final_graph.add_edge(u, v, **edge_dict)

        logger.debug(
            f'Merged Graph: nodes={final_graph.number_of_nodes()}, edges={final_graph.number_of_edges()}')
        return final_graph

    def toSymbolGraphs(self) -> Dict[str, nx.DiGraph]:
        """Merge Symbol graphs from multiple predictions

        Returns:
            Dict[str, nx.DiGraph]: _description_
        """
        pred_graphs = []
        symbol_key_set = set()

        # generate graphs from all predictions
        for preds in self.ensemble.values():
            pred: Prediction
            for i, pred in enumerate(preds):
                pred_graphs.append(pred.toSymbolGraphs())

        # get set of each symbol key available
        for pred_graph_dict in pred_graphs:
            symbol_key_set.update(list(pred_graph_dict.keys()))

        final_graph_dict: Dict[str, nx.DiGraph] = {}

        # iterate across symbol keys, collecting attributes for each node
        for symbol_key in symbol_key_set:
            final_graph_dict[symbol_key] = nx.DiGraph()
            unique_sym_values = set()
            symbol_edge_data = defaultdict(lambda: defaultdict(int))
            for pred_graph_dict in pred_graphs:
                if symbol_key not in pred_graph_dict:
                    continue
                for (u, v), data in (pred_graph_dict[symbol_key]).edges.items():
                    for key, value in data.items():
                        symbol_edge_data[(u, v)][key] += value
                    unique_sym_values.update(pred_graph_dict[symbol_key].nodes)
            logger.debug(f'{symbol_key=}, {unique_sym_values=}')
            final_graph_dict[symbol_key].add_nodes_from(unique_sym_values)

            for (u, v), d in symbol_edge_data.items():
                final_graph_dict[symbol_key].add_edge(u, v, **d)

        return final_graph_dict

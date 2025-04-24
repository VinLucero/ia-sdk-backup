Utilities
=========

.. meta::
   :description: API reference for utility functions in the ia-sdk
   :keywords: utilities, gdf, helpers, gaius

This page documents utility functions provided by the ia-sdk.

.. module:: ia.gaius.utils

GDF Utilities
-------------

.. autofunction:: create_gdf


Visualization Utilities
-----------------------

.. autofunction:: plot_directed_networkx_graph

Usage Examples
--------------

Creating GDF data:

.. code-block:: python

    from ia.gaius.utils import create_gdf
    
    # Create basic GDF
    data = create_gdf(
        strings=["hello", "world"],
        vectors=[[0.1, 0.2, 0.3]],
        emotives={"importance": 0.8}
    )

Visualizing network graph:

.. code-block:: python

    import networkx as nx
    from ia.gaius.utils import plot_directed_networkx_graph
    
    # Create a simple graph
    G = nx.DiGraph()
    G.add_edge("A", "B")
    G.add_edge("B", "C")
    G.add_edge("C", "A")
    
    # Visualize the graph
    plot_directed_networkx_graph(G, title="Example Graph")



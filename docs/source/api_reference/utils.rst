Utilities
========

.. meta::
   :description: API reference for utility functions in the ia-sdk
   :keywords: utilities, gdf, helpers, gaius

This page documents utility functions provided by the ia-sdk.

.. module:: ia.gaius.utils

GDF Utilities
-----------

.. autofunction:: create_gdf

.. autofunction:: add_vector_to_gdf

.. autofunction:: add_string_to_gdf

.. autofunction:: add_emotive_to_gdf

Visualization Utilities
---------------------

.. autofunction:: plot_directed_networkx_graph

.. autofunction:: visualize_kb

Serialization Utilities
---------------------

.. autofunction:: get_json_serializable

.. autofunction:: decode_gdf_keys

Usage Examples
-------------

Creating GDF data:

.. code-block:: python

    from ia.gaius.utils import create_gdf, add_vector_to_gdf

    # Create basic GDF
    data = create_gdf(strings=["hello", "world"])
    
    # Add a vector
    data = add_vector_to_gdf(data, [0.1, 0.2, 0.3])
    
    # Add emotives
    data["emotives"] = {"importance": 0.8}

Visualizing knowledge base:

.. code-block:: python

    from ia.gaius.utils import visualize_kb
    from ia.gaius.agent_client import AgentClient
    
    agent = AgentClient(...)
    agent.connect()
    
    # Get knowledge base
    kb = agent.get_kbs_as_json(obj=True)
    
    # Visualize
    visualize_kb(kb)


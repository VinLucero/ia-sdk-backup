Models and Data Structures
=========================

.. meta::
   :description: API reference for data structures and models used in the ia-sdk
   :keywords: models, data structures, prediction, ensemble, gaius

This page documents the data structures and models used by the ia-sdk.

.. module:: ia.gaius.data_structures

Prediction Models
----------------

.. autoclass:: Prediction
   :members:
   :inherited-members:

.. autoclass:: PredictionEnsemble
   :members:
   :inherited-members:

Data Validation Models
--------------------

.. module:: ia.gaius.data_ops

.. autofunction:: validate_data

.. autofunction:: validate_gdf

Genome Information
----------------

.. module:: ia.gaius.genome_info

.. autoclass:: Genome
   :members:
   :inherited-members:

Usage Examples
-------------

Working with prediction ensembles:

.. code-block:: python

    from ia.gaius.agent_client import AgentClient
    from ia.gaius.data_structures import PredictionEnsemble

    # Get predictions from an agent
    agent = AgentClient(...)
    agent.connect()
    
    # Observe some data
    agent.observe({"strings": ["test"], "vectors": [], "emotives": {}})
    
    # Get predictions as an ensemble
    raw_predictions = agent.get_predictions()
    ensemble = PredictionEnsemble(raw_predictions)
    
    # Access prediction data
    for prediction in ensemble.get_predictions():
        print(f"Prediction: {prediction.get_name()}")
        print(f"Matches: {prediction.get_matches()}")


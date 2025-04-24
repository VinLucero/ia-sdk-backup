Models and Data Structures
==========================

.. meta::
   :description: Data models and structures used in the ia-sdk
   :keywords: models, data structures, gdf, prediction, gaius, sdk

This module contains the data structures and models used by the SDK.

.. note::
   All models provide serialization and deserialization methods, allowing
   for easy conversion between JSON and Python objects.


Prediction Models
-----------------

.. module:: ia.gaius.data_structures

.. autoclass:: Prediction
   :members:
   :inherited-members:
   
   This class represents a single prediction from the agent, including
   confidence scores, matching criteria, and associated metadata.

.. autoclass:: PredictionEnsemble
   :members:
   :inherited-members:
   
   A collection of :class:`Prediction` objects, providing aggregation
   and filtering capabilities for prediction results.

Data Validation Models
----------------------

.. module:: ia.gaius.data_ops

.. autofunction:: validate_data

Genome Information
------------------

.. module:: ia.gaius.genome_info

.. autoclass:: Genome
   :members:
   :inherited-members:
   
   Represents the complete genetic configuration of an agent, including
   learning parameters, prediction thresholds, and operating modes.
   
   .. seealso:: :meth:`ia.gaius.agent_client.AgentClient.change_genes` for modifying agent genes.


GDF Data Format
----------------

The Generalized Data Format (GDF) is used for all data exchange with GAIuS agents. 
It uses a standard dictionary structure with the following keys:

* ``strings``: A list of text strings
* ``vectors``: A list of numerical vectors (lists of numbers)
* ``emotives``: A dictionary of emotional or importance values
* ``metadata``: Optional metadata about the data

Example GDF structure:

.. code-block:: python

   {
       "strings": ["example text", "another string"],
       "vectors": [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]],
       "emotives": {"importance": 0.8, "urgency": 0.5},
       "metadata": {"timestamp": "2023-01-01T12:00:00Z"}
   }


Usage Examples
--------------

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
        print(f"Confidence: {prediction.get_confidence()}")
        print(f"Matches: {prediction.get_matches()}")

Working with genomes:

.. code-block:: python

    from ia.gaius.agent_client import AgentClient
    from ia.gaius.genome_info import Genome

    # Connect to agent
    agent = AgentClient(...)
    agent.connect()
    
    # Get current genome
    genome = agent.get_genome()
    
    # Modify specific genes
    agent.change_genes({
        "recall_threshold": 0.2,
        "max_predictions": 50
    })
    
    # Use predefined genome settings
    agent.set_fast_recall_mode()  # Example of a predefined setting method
    
    # Or use a specific genome configuration
    agent.set_genome_configuration("high_precision")

Creating and validating GDF data:

.. code-block:: python

    from ia.gaius.utils import create_gdf
    from ia.gaius.data_ops import validate_data
    
    # Create GDF data
    data = create_gdf(
        strings=["example text"],
        vectors=[[0.1, 0.2, 0.3]],
        emotives={"importance": 0.8}
    )
    
    # Validate the data
    try:
        validate_data(data)
        print("Data is valid")
    except Exception as e:
        print(f"GDF validation error: {e}")

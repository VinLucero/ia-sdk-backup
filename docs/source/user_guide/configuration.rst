Configuration
============

.. meta::
   :description: How to configure the ia-sdk for optimal performance
   :keywords: configuration, settings, optimization, gaius, sdk

This page covers how to configure the ia-sdk for optimal performance.

Basic Configuration
-----------------

When initializing an AgentClient, you can provide various configuration options:

.. code-block:: python

    from ia.gaius.agent_client import AgentClient

    agent_info = {
        'api_key': 'YOUR_API_KEY',
        'name': 'agent-name',
        'domain': 'your-domain.com',
        'secure': True  # Use HTTPS (recommended for production)
    }

    # Optional timeout setting
    agent = AgentClient(agent_info, timeout=30.0)

Agent Configuration
-----------------

Once connected, you can configure which nodes to use for input and output:

.. code-block:: python

    # Set ingress nodes (where data is sent)
    agent.set_ingress_nodes(["P1"])

    # Set query nodes (where predictions come from)
    agent.set_query_nodes(["P1"])

Performance Tuning
----------------

You can adjust various parameters to optimize agent performance:

.. code-block:: python

    # Modify agent genes
    agent.change_genes({
        "recall_threshold": 0.1,  # Lower values return more matches
        "max_predictions": 20,    # Maximum number of predictions to return
        "near_vector_count": 5    # Number of nearest vectors to consider
    })

    # Control prediction behavior
    agent.start_predicting()  # Enable predictions
    agent.stop_predicting()   # Disable predictions (faster training)

    # Control learning
    agent.start_autolearning()  # Enable automatic learning
    agent.stop_autolearning()   # Disable automatic learning

Environment Variables
------------------

The SDK supports configuration through environment variables:

.. code-block:: bash

    # API credentials
    export GAIUS_API_KEY=your_api_key
    export GAIUS_DOMAIN=your_domain.com

    # Connection settings
    export GAIUS_TIMEOUT=30
    export GAIUS_VERIFY_SSL=true

Advanced Configuration
-------------------

For advanced use cases, additional configuration options are available:

.. code-block:: python

    # Response format control
    agent.set_summarize_for_single_node(True)  # Simplify responses for single nodes
    agent.receive_unique_ids(False)  # Remove unique IDs from responses

    # Targeted prediction
    agent.set_target_class("specific_class")  # Focus predictions on a specific class


Agent Client
===========

.. meta::
   :description: API reference for the Agent Client module
   :keywords: agent, client, api, gaius, sdk

The Agent Client provides the primary interface for interacting with GAIuS agents.

.. module:: ia.gaius.agent_client

AgentClient
-----------

.. autoclass:: AgentClient
   :members:
   :inherited-members:
   :exclude-members: __init__

   .. automethod:: __init__

Exception Classes
----------------

.. autoclass:: AgentQueryError
   :members:

.. autoclass:: AgentConnectionError
   :members:

.. autoclass:: AgentQueryWarning
   :members:

Usage Examples
-------------

Connecting to an agent:

.. code-block:: python

    from ia.gaius.agent_client import AgentClient

    agent_info = {
        'api_key': 'YOUR_API_KEY',
        'name': 'agent-name',
        'domain': 'your-domain.com',
        'secure': True
    }

    agent = AgentClient(agent_info)
    agent.connect()

Observing data and getting predictions:

.. code-block:: python

    from ia.gaius.utils import create_gdf

    # Create some data in GDF format
    data = create_gdf(strings=["hello", "world"])

    # Observe the data
    agent.observe(data)

    # Get predictions
    predictions = agent.get_predictions()


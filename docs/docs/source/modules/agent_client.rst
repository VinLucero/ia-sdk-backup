Agent Client Module
==================

.. module:: ia.gaius.agent_client

Overview
--------

The Agent Client module provides the primary interface for interacting with GAIuS agents. It handles:

* Agent connection and authentication
* Query operations
* Memory management
* Knowledge base operations
* Model management

Core Classes
-----------

AgentClient
~~~~~~~~~~

.. autoclass:: AgentClient
   :members:
   :special-members: __init__
   :undoc-members:
   :show-inheritance:

   The main class for interacting with GAIuS agents.

Exception Classes
---------------

.. autoclass:: AgentQueryError
   :members:
   :show-inheritance:

.. autoclass:: AgentConnectionError
   :members:
   :show-inheritance:

.. autoclass:: AgentQueryWarning
   :members:
   :show-inheritance:

Usage Examples
------------

Basic Usage
~~~~~~~~~~

.. code-block:: python

    from ia.gaius.agent_client import AgentClient

    # Initialize client
    agent_info = {
        'api_key': 'your-api-key',
        'name': 'your-agent-name',
        'domain': 'your-domain',
        'secure': False
    }
    client = AgentClient(agent_info)

    # Connect to agent
    client.connect()

    # Set up nodes
    client.set_ingress_nodes(['node1'])
    client.set_query_nodes(['node1'])

Error Handling
~~~~~~~~~~~~

.. code-block:: python

    try:
        client.connect()
    except AgentConnectionError as e:
        print(f"Connection failed: {e}")
    except AgentQueryError as e:
        print(f"Query failed: {e}")

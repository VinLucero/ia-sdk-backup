Configuration
=============

.. meta::
   :description: How to configure the ia-sdk for optimal performance
   :keywords: configuration, settings, optimization, gaius, sdk

This page provides a comprehensive guide to configuring the ia-sdk, including all available options, environment variables, and configuration methods.

.. contents:: Table of Contents
   :local:
   :depth: 2

Configuration Methods
---------------------

The ia-sdk can be configured using three primary methods:

1. **Programmatic Configuration**: Direct parameters when initializing the AgentClient
2. **Environment Variables**: System-wide settings using GAIUS_* environment variables
3. **Configuration Files**: YAML, JSON, or INI files for persistent configuration

The configuration precedence (from highest to lowest) is:

1. Programmatic parameters (directly passed to AgentClient)
2. Environment variables
3. Configuration files
4. Default values

Basic Initialization
~~~~~~~~~~~~~~~~~~~~

When initializing an AgentClient, you can provide various configuration options:

.. code-block:: python

    from ia.gaius.agent_client import AgentClient

    agent_info = {
        'api_key': 'YOUR_API_KEY',          # Required: Your API authentication key
        'name': 'agent-name',               # Required: The name of the agent to connect to
        'domain': 'your-domain.com',        # Required: Your GAIuS domain
        'secure': True,                     # Optional: Use HTTPS (recommended for production)
        'port': 443,                        # Optional: Custom port if not using standard HTTP/HTTPS ports
        'verify_ssl': True                  # Optional: Verify SSL certificates
    }

    # Additional client configuration
    agent = AgentClient(
        agent_info,
        timeout=30.0,                       # Connection timeout in seconds
        retry_count=3,                      # Number of connection retry attempts
        retry_delay=1.0,                    # Delay between retries in seconds
        max_concurrent_requests=5,          # Maximum number of concurrent requests
        log_level='INFO'                    # Logging level (DEBUG, INFO, WARNING, ERROR)
    )

Environment Variables Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You can configure the SDK using environment variables, which is useful for containerized deployments or when you don't want to hardcode values:

.. code-block:: bash

    # Required credentials
    export GAIUS_API_KEY=your_api_key
    export GAIUS_AGENT_NAME=agent-name
    export GAIUS_DOMAIN=your_domain.com
    
    # Optional connection settings
    export GAIUS_SECURE=true                # Use HTTPS
    export GAIUS_PORT=443                   # Custom port
    export GAIUS_TIMEOUT=30                 # Connection timeout in seconds
    export GAIUS_VERIFY_SSL=true            # Verify SSL certificates
    
    # Retry behavior
    export GAIUS_RETRY_COUNT=3              # Number of connection retry attempts
    export GAIUS_RETRY_DELAY=1.0            # Delay between retries in seconds
    
    # Performance settings
    export GAIUS_MAX_CONCURRENT=5           # Maximum number of concurrent requests
    
    # Logging
    export GAIUS_LOG_LEVEL=INFO             # Logging level

Then initialize the client without explicitly providing these values:

.. code-block:: python

    from ia.gaius.agent_client import AgentClient
    
    # Values will be loaded from environment variables
    agent = AgentClient()
    agent.connect()

Configuration Files
~~~~~~~~~~~~~~~~~~~

For persistent configuration, you can use configuration files in YAML, JSON, or INI format.

**YAML Configuration** (`.gaius.yaml` or `.gaius.yml`):

.. code-block:: yaml

    # Connection details
    connection:
      api_key: your_api_key
      agent_name: agent-name
      domain: your-domain.com
      secure: true
      port: 443
      verify_ssl: true
      timeout: 30
    
    # Retry behavior
    retry:
      count: 3
      delay: 1.0
    
    # Performance
    performance:
      max_concurrent_requests: 5
    
    # Logging
    logging:
      level: INFO
      file: gaius.log

**JSON Configuration** (`.gaius.json`):

.. code-block:: json

    {
      "connection": {
        "api_key": "your_api_key",
        "agent_name": "agent-name",
        "domain": "your-domain.com",
        "secure": true,
        "port": 443,
        "verify_ssl": true,
        "timeout": 30
      },
      "retry": {
        "count": 3,
        "delay": 1.0
      },
      "performance": {
        "max_concurrent_requests": 5
      },
      "logging": {
        "level": "INFO",
        "file": "gaius.log"
      }
    }

**INI Configuration** (`.gaius.ini`):

.. code-block:: ini

    [connection]
    api_key = your_api_key
    agent_name = agent-name
    domain = your-domain.com
    secure = true
    port = 443
    verify_ssl = true
    timeout = 30
    
    [retry]
    count = 3
    delay = 1.0
    
    [performance]
    max_concurrent_requests = 5
    
    [logging]
    level = INFO
    file = gaius.log

To load configuration from a file:

.. code-block:: python

    from ia.gaius.agent_client import AgentClient
    
    # Automatically searches for .gaius.* files in current directory
    agent = AgentClient()
    
    # Or specify a configuration file directly
    agent = AgentClient(config_file="/path/to/my_config.yaml")

Complete Configuration Reference
--------------------------------

This section documents all configuration options available in the ia-sdk, their default values, and effects.

Connection Configuration
~~~~~~~~~~~~~~~~~~~~~~~~

These options control how the client connects to the GAIuS agent:

.. list-table::
   :header-rows: 1
   :widths: 20 15 50 15

   * - Option
     - Default
     - Description
     - Env Variable
   * - api_key
     - None
     - API key for authentication (required)
     - GAIUS_API_KEY
   * - name
     - None
     - Name of the agent to connect to (required)
     - GAIUS_AGENT_NAME
   * - domain
     - None
     - Domain for the GAIuS service (required)
     - GAIUS_DOMAIN
   * - secure
     - True
     - Use HTTPS instead of HTTP
     - GAIUS_SECURE
   * - port
     - 443/80
     - Custom port (defaults to 443 for HTTPS, 80 for HTTP)
     - GAIUS_PORT
   * - verify_ssl
     - True
     - Verify SSL certificates when using HTTPS
     - GAIUS_VERIFY_SSL
   * - timeout
     - 30.0
     - Connection timeout in seconds
     - GAIUS_TIMEOUT
   * - retry_count
     - 3
     - Number of connection retry attempts
     - GAIUS_RETRY_COUNT
   * - retry_delay
     - 1.0
     - Delay between retries in seconds
     - GAIUS_RETRY_DELAY
   * - max_concurrent_requests
     - 5
     - Maximum number of concurrent requests
     - GAIUS_MAX_CONCURRENT
   * - log_level
     - "INFO"
     - Logging level (DEBUG, INFO, WARNING, ERROR)
     - GAIUS_LOG_LEVEL

Agent Topology Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Once connected, you can configure which nodes to use for input and output. These settings determine how data flows through the agent:

.. code-block:: python

    # Set ingress nodes (where data is sent)
    agent.set_ingress_nodes(["P1", "P2"])

    # Set query nodes (where predictions come from)
    agent.set_query_nodes(["P3", "P4"])

    # Set specific node for a particular operation
    agent.set_node_for_operation("classification", "P5")

The available node types include:

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Node Type
     - Description
   * - Perception (P*)
     - Process incoming data and learn patterns
   * - Concept (C*)
     - Store and organize learned knowledge
   * - Emotive (E*)
     - Handle emotional/importance information
   * - Action (A*)
     - Execute actions based on predictions

.. note::
   The node structure depends on your specific agent configuration. Consult your agent documentation for the available nodes and their purposes.

Node Configuration Options:

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Method
     - Description
   * - set_ingress_nodes(node_list)
     - Define which nodes receive incoming data
   * - set_query_nodes(node_list)
     - Define which nodes are queried for predictions
   * - set_node_for_operation(operation, node)
     - Configure a specific node for a particular operation type
   * - get_active_nodes()
     - Retrieve the list of currently active nodes
   * - get_node_stats(node_name)
     - Get performance statistics for a specific node

Performance Tuning
------------------

You can adjust various parameters to optimize agent performance for different use cases. The optimal settings depend on your specific needs for recall accuracy, response time, and resource usage.

Genetic Parameters
~~~~~~~~~~~~~~~~~~

Genetic parameters control the core behavior of the agent. Modify them using the `change_genes()` method:

.. code-block:: python

    # Modify agent genes
    agent.change_genes({
        # Prediction configuration
        "recall_threshold": 0.1,        # Lower values return more matches (0.0-1.0)
        "max_predictions": 20,          # Maximum number of predictions to return
        "near_vector_count": 5,         # Number of nearest vectors to consider
        
        # Learning parameters
        "learning_rate": 0.01,          # How quickly the agent adapts to new information
        "forgetting_rate": 0.001,       # How quickly the agent forgets old information
        "min_novelty_threshold": 0.2,   # Minimum novelty required to create a new concept
        
        # Resource utilization
        "max_memory_percentage": 80,    # Maximum memory usage allowed (percentage)
        "max_processing_threads": 4     # Maximum parallel processing threads
    })

All available genetic parameters and their functions:

.. list-table::
   :header-rows: 1
   :widths: 30 15 55

   * - Parameter
     - Default
     - Description
   * - recall_threshold
     - 0.2
     - Minimum confidence threshold for predictions (0.0-1.0)
   * - max_predictions
     - 10
     - Maximum number of predictions to return
   * - near_vector_count
     - 3
     - Number of nearest vectors to consider for matching
   * - learning_rate
     - 0.01
     - Rate at which the agent incorporates new information
   * - forgetting_rate
     - 0.001
     - Rate at which old information is forgotten
   * - min_novelty_threshold
     - 0.3
     - Minimum novelty required to create a new concept
   * - max_memory_percentage
     - 75
     - Maximum memory usage allowed (percentage)
   * - max_processing_threads
     - 2
     - Maximum parallel processing threads
   * - concept_pruning_threshold
     - 0.05
     - Threshold for removing unused concepts
   * - emotive_influence
     - 0.5
     - How much emotional context influences predictions
   * - temporal_decay
     - 0.1
     - How quickly relevance decays over time

Learning and Prediction Control
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Toggle learning and prediction capabilities to optimize for different phases of your application:

.. code-block:: python

    # Control prediction behavior
    agent.start_predicting()      # Enable predictions
    agent.stop_predicting()       # Disable predictions (faster training)
    
    # Control learning
    agent.start_autolearning()    # Enable automatic learning
    agent.stop_autolearning()     # Disable automatic learning
    
    # Check current status
    is_predicting = agent.is_predicting()
    is_learning = agent.is_learning()
    
    # Configure learning modes
    agent.set_supervised_learning(True)     # Enable supervised learning
    agent.set_unsupervised_learning(True)   # Enable unsupervised learning
    agent.set_reinforcement_learning(True)  # Enable reinforcement learning

Preset Configurations
~~~~~~~~~~~~~~~~~~~~~

The SDK provides preset configurations for common scenarios:

.. code-block:: python

    # Import preset configurations
    from ia.gaius.genome_info import GeneCollection
    
    # Apply a preset configuration
    

Environment Variables
---------------------

The SDK supports configuration through environment variables:

.. code-block:: bash

    # API credentials
    export GAIUS_API_KEY=your_api_key
    export GAIUS_DOMAIN=your_domain.com

    # Connection settings
    export GAIUS_TIMEOUT=30
    export GAIUS_VERIFY_SSL=true

Advanced Configuration
----------------------

For advanced use cases, additional configuration options are available:

.. code-block:: python

    # Response format control
    agent.set_summarize_for_single_node(True)  # Simplify responses for single nodes
    agent.receive_unique_ids(False)  # Remove unique IDs from responses

    # Targeted prediction
    agent.set_target_class("specific_class")  # Focus predictions on a specific class


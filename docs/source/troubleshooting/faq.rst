Frequently Asked Questions
==========================

.. meta::
   :description: Frequently asked questions about the ia-sdk package
   :keywords: faq, questions, answers, gaius, sdk, troubleshooting

This page answers frequently asked questions about using the ia-sdk.

General Questions
-----------------

**What is the ia-sdk?**

The ia-sdk is a Python package that provides a comprehensive interface for working with GAIuS (General Artificial Intelligence System) agents. It allows you to connect to agents, observe data, learn patterns, get predictions, and integrate these capabilities into your applications.

**What can I do with the ia-sdk?**

The ia-sdk enables a wide range of applications:

* Pattern recognition and prediction
* Sequence learning and analysis
* Anomaly detection
* Classification tasks
* Knowledge representation and reasoning
* Multi-agent cognitive systems

**Is the ia-sdk open source?**

The ia-sdk client library is open source and available on GitHub. GAIuS agents themselves are provided as a service, with various licensing options available from Intelligent Artifacts.

**Is the ia-sdk suitable for production use?**

Yes, the ia-sdk is designed for production use. It includes features for robust error handling, performance optimization, and scalability. See the :doc:`/user_guide/best_practices` section for production deployment recommendations.

Installation Questions
----------------------

**Which Python versions are supported?**

The ia-sdk supports Python 3.8 and higher. For detailed requirements, see :doc:`/installation/requirements`.

**Can I use the ia-sdk in a virtual environment?**

Yes, and it's recommended. Here's how to install in a virtual environment:

.. code-block:: bash

    # Create a virtual environment
    python -m venv ia-sdk-env
    
    # Activate it
    source ia-sdk-env/bin/activate  # Linux/macOS
    .\ia-sdk-env\Scripts\activate    # Windows
    
    # Install ia-sdk
    pip install ia-sdk

**How do I install the ia-sdk offline?**

For offline installation instructions, see the "Offline Installation" section in :doc:`/installation/index`.

**What are the minimal system requirements?**

See the :doc:`/installation/requirements` page for detailed information on minimal system requirements.

Usage Questions
---------------

**How do I connect to an agent?**

.. code-block:: python

    from ia.gaius.agent_client import AgentClient
    
    # Create an agent client
    agent = AgentClient({
        'api_key': 'YOUR_API_KEY',
        'name': 'agent-name',
        'domain': 'your-domain.com',
        'secure': True
    })
    
    # Connect to the agent
    agent.connect()
    
    # Set ingress and query nodes
    agent.set_ingress_nodes(["P1"])
    agent.set_query_nodes(["P1"])

**What is the GDF format?**

GDF (Generalized Data Format) is the standard format for data exchange with GAIuS agents. It's a dictionary that can contain:

* `strings`: List of string data
* `vectors`: List of numerical vectors
* `emotives`: Dictionary of context values

You can create GDF data using the `create_gdf` utility:

.. code-block:: python

    from ia.gaius.utils import create_gdf
    
    data = create_gdf(
        strings=["category|electronics", "action|purchase"],
        vectors=[[0.1, 0.2, 0.3]],
        emotives={"importance": 0.8}
    )

**What are nodes in the context of GAIuS agents?**

Nodes are cognitive processing elements within a GAIuS agent. The most common node type is a primitive node (often named "P1"), which processes direct observations. When working with a simple agent topology, you typically set both ingress and query nodes to ["P1"].

**How do I train an agent?**

Training an agent involves:

1. Observing data
2. Learning from observations

.. code-block:: python

    # Observe data
    agent.observe({"strings": ["input_data"], "vectors": [], "emotives": {}})
    
    # Learn from observations
    agent.learn()

For supervised learning:

.. code-block:: python

    # Observe input
    agent.observe({"strings": ["input_feature_1", "input_feature_2"], "vectors": [], "emotives": {}})
    
    # Observe classification
    agent.observe({"strings": ["class_label"], "vectors": [], "emotives": {}})
    
    # Learn the association
    agent.learn()

**How do I get predictions from an agent?**

.. code-block:: python

    # Make sure predictions are enabled
    agent.start_predicting()
    
    # Observe input data
    agent.observe({"strings": ["input_data"], "vectors": [], "emotives": {}})
    
    # Get predictions
    predictions = agent.get_predictions()

Performance Questions
---------------------

**What are the critical paths that need testing?**

The critical paths that should be thoroughly tested include:

1. **Observation pipeline**: How efficiently data is observed and processed
2. **Learning operations**: Performance of learning from sequences
3. **Prediction retrieval**: Speed and accuracy of prediction generation
4. **Knowledge base operations**: Export/import and persistence operations

For performance testing guidance, see :doc:`/user_guide/best_practices`.

**How can I improve agent performance?**

1. **Optimize gene settings**:

   .. code-block:: python
   
       # Adjust genes for performance
       agent.change_genes({
           "recall_threshold": 0.1,  # Adjust based on recall vs precision needs
           "max_predictions": 20,    # Limit predictions for better performance
       })

2. **Process data in batches**:

   .. code-block:: python
   
       # Process data in manageable batches
       for batch in data_batches:
           agent.clear_wm()  # Clear working memory between batches
           
           for item in batch:
               agent.observe(item)
           
           agent.learn()

3. **Disable prediction during training**:

   .. code-block:: python
   
       # Disable predictions during training
       agent.stop_predicting()
       
       # Training code...
       
       # Re-enable predictions when needed
       agent.start_predicting()

For more concrete examples, see our :doc:`/user_guide/practical-examples`.

**Which platforms should we prioritize for testing?**

Testing priority generally follows this order:

1. Linux server environments (Ubuntu, RHEL/CentOS) for production deployments
2. macOS and Windows for development environments
3. Container platforms (Docker) for portable deployments

See :doc:`/installation/platform_specific` for platform-specific considerations.

Error Handling Questions
------------------------

**How do I handle connection errors?**

.. code-block:: python

    from ia.gaius.agent_client import AgentClient, AgentConnectionError
    
    try:
        agent = AgentClient({...})
        agent.connect()
    except AgentConnectionError as e:
        print(f"Connection error: {e}")
        # Implement retry logic or fallback behavior

**How should I handle version updates?**

When updating the ia-sdk:

1. Check the changelog for breaking changes
2. Test in a development environment before production deployment
3. Export knowledge bases before upgrading for backup
4. Consider using semantic versioning in your requirements:

   .. code-block:: text
   
       # In requirements.txt
       ia-sdk>=1.0.0,<2.0.0  # Compatible with 1.x versions

**What are the common error scenarios?**

1. **Connection failures**: Network issues or incorrect credentials
2. **Invalid data format**: GDF validation failures
3. **Resource exhaustion**: Out of memory errors during large operations
4. **Agent state issues**: Attempting predictions while agent is sleeping

See :doc:`/troubleshooting/common_issues` for solutions to these common problems.

Best Practices Questions
------------------------

**What are the most common use cases to document?**

The most common use cases for the ia-sdk include:

1. **Classification**: Training an agent to recognize and categorize inputs
2. **Sequence prediction**: Learning and predicting sequences of events
3. **Anomaly detection**: Identifying unusual patterns or outliers
4. **Knowledge representation**: Building and querying semantic networks
5. **Multi-agent systems**: Creating agent networks for complex reasoning

Examples for these use cases can be found in the :doc:`/user_guide/practical-examples` section.

**What are the security considerations for the agent connections?**

Key security considerations include:

1. **API key protection**: Secure your API keys and avoid hardcoding them
   
   .. code-block:: python
   
       import os
       
       # Use environment variables
       api_key = os.environ.get('GAIUS_API_KEY')
       
       agent = AgentClient({
           'api_key': api_key,
           'name': 'agent-name',
           'domain': 'your-domain.com',
           'secure': True  # Use HTTPS
       })

2. **HTTPS connections**: Always use `secure=True` in production environments
3. **Data validation**: Validate data before sending it to agents
4. **Access controls**: Use appropriate access controls for knowledge bases
5. **Error handling**: Implement proper error handling to prevent information leakage

See the :doc:`/user_guide/best_practices` section for more security recommendations.

**How do I handle concurrent access to agents?**

For concurrent agent access:

1. Consider using thread-safe connection pooling
2. Implement proper synchronization for shared agent access
3. Use thread-local storage for agent connections when appropriate

See the "Multi-Agent Systems" section in :doc:`/user_guide/advanced_usage` for examples.

**How do I back up and restore agent knowledge?**

.. code-block:: python

    # Export a knowledge base
    kb = agent.get_kbs_as_json(obj=False, path="agent_backup.json")
    
    # Later, restore the knowledge base
    agent.load_kbs_from_json(path="agent_backup.json")

See the "Knowledge Base Operations" section in :doc:`/user_guide/advanced_usage` for more details.

**How should large datasets be handled?**

For large datasets:

1. Process data in manageable batches
2. Use efficient data formats (vectors for numerical data)
3. Implement proper memory management
4. Consider using the `experimental.sklearn` integration for large datasets

See the "Performance Considerations" section in :doc:`/user_guide/advanced_usage` for detailed guidance.


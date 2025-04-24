Simple Plan: The 80/20 Approach to IA SDK
=====================================

.. meta::
   :description: A simplified approach to using the IA SDK, focusing on the 20% of features that deliver 80% of value
   :keywords: simplicity, getting started, wrapper, defaults, Pareto principle

Overview
--------

This document outlines a simplified approach to using the IA SDK that follows the Pareto principle - achieving approximately 80% of functionality with only 20% of the complexity. We introduce a wrapper layer designed for developers who want to quickly implement IA capabilities without managing the full architectural complexity.

The SimpleAgent Wrapper
-----------------------

The SimpleAgent wrapper provides a high-level interface to the IA SDK that abstracts away most of the architectural complexity while preserving core functionality.

Core Design Principles
^^^^^^^^^^^^^^^^^^^^^

1. **Sensible Defaults**: Pre-configured settings that work well for most use cases
2. **Minimal Configuration**: Only requires essential parameters to get started
3. **Progressive Disclosure**: Access to advanced features when needed
4. **Automated Resource Management**: Self-tuning based on workload patterns
5. **Simplified Terminology**: Focuses on business outcomes rather than technical implementation details

Implementation
-------------

The SimpleAgent wrapper is implemented as a lightweight layer on top of the full IA SDK architecture:

.. code-block:: python

   from ia.gaius.simple import SimpleAgent
   
   # Initialize with minimal configuration
   agent = SimpleAgent(
       api_key="your-api-key",  
       name="my-first-agent",    # Optional: defaults to API key-derived name
       template="standard"       # Optional: defaults to "standard"
   )
   
   # Process text and get predictions
   result = agent.process("Customer unable to reset password via mobile app")
   
   # Work with simplified results
   print(f"Category: {result.category}")
   print(f"Confidence: {result.confidence}")
   print(f"Suggested actions: {result.actions}")

Under the hood, the wrapper:

1. Sets up an appropriate node configuration based on the template
2. Manages observation creation and submission
3. Handles prediction retrieval and formatting
4. Automatically tunes performance based on usage patterns

Available Templates
^^^^^^^^^^^^^^^^^^

The wrapper includes several pre-configured templates to address common use cases:

1. **standard**: Balanced performance for general use (default)
2. **high-throughput**: Optimized for processing large volumes of data
3. **low-latency**: Prioritizes quick response times over throughput
4. **memory-efficient**: Minimizes memory usage for resource-constrained environments

Each template pre-configures the underlying node architecture, processing pipeline, and resource allocation to suit the specified use case.

Simplified Architecture
----------------------

The SimpleAgent wrapper reduces the visible complexity of the IA architecture in several key ways:

Abstracted Node Types
^^^^^^^^^^^^^^^^^^^^

Instead of working with specialized node types (I-Nodes, P-Nodes, Q-Nodes, M-Nodes), the SimpleAgent presents a unified interface that handles:

* **Data Input**: Simplified observation creation and submission
* **Processing**: Automatic distribution to appropriate processing resources
* **Results**: Streamlined prediction retrieval and formatting
* **Management**: Self-monitoring and adjustment

.. figure:: /_static/simple_agent_architecture.png
   :alt: Simplified Agent Architecture
   :width: 100%
   
   Simplified view of the agent architecture with complexity hidden through abstraction

Condensed Processing Pipeline
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The detailed six-stage processing pipeline is abstracted into three core phases:

1. **Input**: Handling and preparation of observation data
2. **Processing**: Pattern matching and analysis
3. **Output**: Prediction generation and formatting

Example Use Cases
----------------

The SimpleAgent wrapper is particularly well-suited for these common scenarios:

Text Classification
^^^^^^^^^^^^^^^^^

.. code-block:: python

   from ia.gaius.simple import SimpleAgent
   
   agent = SimpleAgent(api_key="your-api-key", template="standard")
   
   # Train with a few examples
   agent.learn([
       ("Our website is down", "technical-issue"),
       ("I can't reset my password", "account-access"),
       ("Charges on my account I didn't authorize", "billing-fraud")
   ])
   
   # Classify new text
   result = agent.process("The website gives a 404 error")
   print(f"Category: {result.category}, Confidence: {result.confidence}")
   # Output: Category: technical-issue, Confidence: 0.92

Sentiment Analysis
^^^^^^^^^^^^^^^^^

.. code-block:: python

   from ia.gaius.simple import SimpleAgent
   
   agent = SimpleAgent(api_key="your-api-key", template="standard")
   
   # Process text for sentiment
   result = agent.process_sentiment("I'm extremely disappointed with the customer service")
   
   print(f"Sentiment: {result.sentiment}")  # Negative
   print(f"Score: {result.score}")          # -0.75
   print(f"Emotions: {result.emotions}")    # {'disappointment': 0.8, 'frustration': 0.6}

Pattern Recognition
^^^^^^^^^^^^^^^^^

.. code-block:: python

   from ia.gaius.simple import SimpleAgent
   
   agent = SimpleAgent(api_key="your-api-key", template="standard")
   
   # Define patterns to look for
   agent.add_patterns([
       "server down",
       "connection error",
       "unable to login",
       "payment declined"
   ])
   
   # Process text and find matching patterns
   result = agent.process("Users report the server down in the east region")
   
   for match in result.pattern_matches:
       print(f"Pattern: {match.pattern}, Confidence: {match.confidence}")
   # Output: Pattern: server down, Confidence: 1.0

Progressive Complexity
---------------------

While the SimpleAgent wrapper provides simplicity for common use cases, it also allows for progressive access to more advanced features as needed:

Accessing Advanced Features
^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   from ia.gaius.simple import SimpleAgent
   
   # Start with the simple wrapper
   agent = SimpleAgent(api_key="your-api-key")
   
   # Basic usage
   result = agent.process("Customer unable to reset password")
   
   # Access the underlying full-featured client for advanced operations
   full_client = agent.get_advanced_client()
   
   # Now use advanced features with the full client
   full_client.set_processing_nodes(['P1', 'P2', 'P3'])
   full_client.set_node_preferences({
       'text_processing': ['P1', 'P2'],
       'pattern_matching': ['P3']
   })

Custom Templates
^^^^^^^^^^^^^^

Users can create custom templates that capture specific configurations:

.. code-block:: python

   from ia.gaius.simple import SimpleAgent, Template
   
   # Define a custom template
   my_template = Template(
       name="my-custom-template",
       processing_nodes=2,
       query_nodes=1,
       memory_allocation="high",
       processing_strategy="precision",
       default_confidence_threshold=0.7
   )
   
   # Register the template
   SimpleAgent.register_template(my_template)
   
   # Use the custom template
   agent = SimpleAgent(api_key="your-api-key", template="my-custom-template")

Implementation Details
---------------------

The SimpleAgent wrapper is implemented with these key components:

1. **Configuration Manager**: Handles template-based setup and defaults
2. **Resource Allocator**: Automatically manages nodes and processing resources
3. **Observation Factory**: Simplifies the creation of well-formed observations
4. **Result Formatter**: Transforms raw predictions into user-friendly formats
5. **Performance Monitor**: Tracks usage patterns to optimize performance

The wrapper maintains backward compatibility with the full IA SDK, ensuring that users can access advanced features when needed while benefiting from the simplified interface for common tasks.

Integration Example
------------------

This example demonstrates how to integrate the SimpleAgent wrapper into a real-world application:

.. code-block:: python

   from ia.gaius.simple import SimpleAgent
   from flask import Flask, request, jsonify
   
   app = Flask(__name__)
   
   # Initialize the agent once at startup
   agent = SimpleAgent(
       api_key="your-api-key",
       template="low-latency"  # Optimized for API response times
   )
   
   @app.route('/classify', methods=['POST'])
   def classify_text():
       text = request.json.get('text', '')
       if not text:
           return jsonify({'error': 'No text provided'}), 400
           
       # Process the text through the agent
       result = agent.process(text)
       
       # Return structured results
       return jsonify({
           'category': result.category,
           'confidence': result.confidence,
           'actions': result.actions,
           'processing_time_ms': result.processing_time_ms
       })
   
   if __name__ == '__main__':
       app.run(host='0.0.0.0', port=5000)

Migration Path
-------------

For users who start with the SimpleAgent wrapper and later need the full power of the IA SDK, a clear migration path is provided:

1. **Start Simple**: Begin with the SimpleAgent wrapper for rapid implementation
2. **Incremental Access**: Use `agent.get_advanced_client()` to access specific advanced features
3. **Full Migration**: When needed, transition to the full client using `agent.export_configuration()`
4. **Hybrid Approach**: Continue using SimpleAgent for common tasks while using the full client for advanced operations

This approach allows teams to start quickly while preserving a path to the full feature set when required.

Benefits of the SimpleAgent Approach
-----------------------------------

Adopting the SimpleAgent wrapper provides several key advantages:

1. **Faster Time-to-Value**: Implement IA capabilities with minimal setup time
2. **Reduced Learning Curve**: Focus on business outcomes rather than technical details
3. **Lower Maintenance Overhead**: Simplified architecture requires less management
4. **Scalable Complexity**: Access additional capabilities only when needed
5. **Consistent Performance**: Pre-optimized templates ensure good performance out of the box

Conclusion
---------

The SimpleAgent wrapper provides an 80/20 approach to the IA SDK, delivering the majority of functionality with a fraction of the complexity. This approach is ideal for teams who want to:

- Quickly implement IA capabilities
- Minimize technical overhead
- Focus on business outcomes
- Maintain a path to advanced features when needed

For users with specific requirements that go beyond the wrapper's capabilities, the full IA SDK architecture remains available, providing a smooth transition path as needs evolve.

Further Reading
--------------

* :doc:`/user_guide/simple_agent_api` - Complete API reference for the SimpleAgent wrapper
* :doc:`/examples/simple_agent_examples` - Additional code examples using the SimpleAgent wrapper
* :doc:`/user_guide/migrating_to_full_api` - Guide for transitioning from SimpleAgent to the full API
* :doc:`/user_guide/architecture-and-data-flow` - Detailed architecture documentation for advanced users 
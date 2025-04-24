Data Lifecycle: From Observation to Prediction
==============================================

.. meta::
   :description: Documentation covering the full lifecycle of observational data as it transforms into predictions
   :keywords: observation, prediction, data flow, gdf, gaius, sdk

Introduction
-----------

This document provides a comprehensive overview of how observational data flows through the IA system, from initial submission to final prediction. Understanding this lifecycle is essential for effective integration and usage of the SDK.

**Purpose and Scope**

This documentation:

* Describes the format and structure of observation data
* Explains how observations are processed and transformed
* Details the structure and properties of resulting prediction objects
* Provides integration guidelines and best practices

**Target Audience**

This guide is intended for:

* Developers integrating the IA SDK into applications
* Data scientists working with prediction results
* System architects designing observation-prediction workflows

**Prerequisites**

Readers should have:

* Basic understanding of the IA SDK
* Familiarity with Python programming
* Knowledge of JSON and data structures

Initial Observation Data Format (GDF)
------------------------------------

All data exchanged with GAIuS agents, including observations, uses the standardized Generalized Data Format (GDF).

GDF Schema Definition
^^^^^^^^^^^^^^^^^^^^

A valid GDF observation structure must contain the following required fields:

* ``strings``: A list of text strings containing the textual content to be processed
* ``vectors``: A list of numerical vectors (lists of numbers) representing feature vectors
* ``emotives``: A dictionary of numerical values representing emotional or importance weightings
* ``metadata`` (optional): A dictionary containing additional contextual information

.. note::
   The ``strings`` field is the primary carrier of information in most observation scenarios, while ``vectors`` and ``emotives`` provide additional context when available.

Validation Rules
^^^^^^^^^^^^^^^

GDF observations must adhere to specific validation rules:

* **Field presence**: ``strings``, ``vectors``, and ``emotives`` are required fields
* **Type validation**: 
  - ``strings`` must be a list of strings
  - ``vectors`` must be a list of numerical lists
  - ``emotives`` must be a dictionary with numerical values
  - ``metadata`` must be a dictionary if present

* **Content validation**:
  - Empty observations (empty ``strings`` and ``vectors``) may be rejected
  - Vector dimensions should be consistent across all vectors within the same observation
  - Emotive values typically range from 0.0 to 1.0

Example Observation
^^^^^^^^^^^^^^^^^^

A complete valid GDF observation:

.. code-block:: python

   {
       "strings": ["Customer reported issues with login authentication", 
                  "Error message displayed: 'Invalid credentials'"],
       "vectors": [[0.1, 0.2, 0.3, 0.5, 0.8], 
                  [0.4, 0.5, 0.6, 0.2, 0.1]],
       "emotives": {
           "importance": 0.8,
           "urgency": 0.7,
           "customer_impact": 0.9
       },
       "metadata": {
           "timestamp": "2024-04-23T08:15:22Z",
           "source": "customer_portal",
           "ticket_id": "CS-1234"
       }
   }

Invalid observation examples:

.. code-block:: python

   # Missing required field (vectors)
   {
       "strings": ["Customer reported login issue"],
       "emotives": {"importance": 0.8}
   }

   # Incorrect type (emotives should be a dictionary)
   {
       "strings": ["Customer reported login issue"],
       "vectors": [[0.1, 0.2, 0.3]],
       "emotives": [0.8, 0.7, 0.9]
   }
   
   # Empty observation content
   {
       "strings": [],
       "vectors": [],
       "emotives": {}
   }

.. seealso:: 
   See :meth:`ia.gaius.data_ops.validate_data` for programmatic validation of GDF data structures.


Transformation Process
---------------------

This section details how observations are processed by the agent and transformed into predictions.

Agent Processing Pipeline
^^^^^^^^^^^^^^^^^^^^^^^^

When an observation is submitted, it passes through several processing stages:

1. **Validation**: The observation's GDF structure is validated against schema requirements
2. **Preprocessing**: Text normalization, tokenization, and feature extraction
3. **Encoding**: Conversion of processed data into internal vector representations
4. **Comparison**: Matching against existing patterns in the agent's memory
5. **Ranking**: Ordering potential matches by confidence and relevance
6. **Prediction Formation**: Creation of prediction objects based on matches

.. figure:: /_static/observation_pipeline.png
   :alt: Observation to Prediction Pipeline
   :width: 100%
   
   Diagram illustrating the flow of observation data through the agent processing pipeline

The transformation occurs within the agent's processing nodes, with the client SDK handling the communication and data formatting aspects.

Role of the Agent's Genome
^^^^^^^^^^^^^^^^^^^^^^^^^

The agent's genome significantly influences how observations are processed. The genome contains parameters that control:

* **Recall Threshold**: Minimum confidence required for pattern matching
* **Feature Extraction**: How text and vector data are processed
* **Match Criteria**: Rules for determining when observations match existing patterns
* **Prediction Limits**: Maximum number of predictions to generate

These genome parameters can be tuned to optimize for:

* **Precision**: Higher confidence in predictions, but potentially fewer matches
* **Recall**: More comprehensive matching, potentially at the cost of precision
* **Speed**: Faster processing with simplified matching criteria

Example genome configuration affecting observation processing:

.. code-block:: python

   from ia.gaius.agent_client import AgentClient
   
   # Connect to agent
   agent = AgentClient(...)
   agent.connect()
   
   # Configure genome for high-precision observation processing
   agent.change_genes({
       "recall_threshold": 0.75,      # Higher threshold for more precise matches
       "max_predictions": 5,          # Limit to top 5 predictions
       "feature_extraction_depth": 3  # More detailed feature extraction
   })

   # Alternative: Use predefined genome configuration
   agent.set_genome_configuration("high_precision")

.. note::
   Changes to the genome will affect all subsequent observations processed by the agent. For critical applications, consider creating separate agents with different genome configurations rather than frequently modifying a single agent's genome.

Linking Observations to Predictions
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

When an observation is processed, it generates an internal representation that can match against patterns in the agent's memory. These matches form the basis for predictions.

**Intermediate Data Structures**

The following intermediate structures are created during transformation:

1. **Normalized Observation**: Preprocessed observation data
2. **Feature Vectors**: Extracted features from observation content
3. **Match References**: Links between input features and matching patterns
4. **Confidence Scores**: Numerical evaluation of match quality
5. **Raw Prediction Data**: Unformatted prediction data before final structure

These intermediate structures are typically not exposed directly through the API but are encapsulated in the final prediction objects.

**Complete Transformation Example**

The following example demonstrates the complete code flow from observation to prediction:

.. code-block:: python

   from ia.gaius.agent_client import AgentClient
   from ia.gaius.utils import create_gdf
   from ia.gaius.data_structures import PredictionEnsemble
   
   # 1. Initialize and connect to agent
   agent = AgentClient({
       'api_key': 'your-api-key',
       'name': 'your-agent-name',
       'domain': 'your-domain',
       'secure': True
   })
   agent.connect()
   
   # 2. Create observation in GDF format
   observation = create_gdf(
       strings=["Customer reported network connectivity issues"],
       vectors=[[0.1, 0.2, 0.3, 0.4, 0.5]],
       emotives={"urgency": 0.8, "impact": 0.7},
       metadata={"ticket_id": "NET-2045", "source": "helpdesk"}
   )
   
   # 3. Submit observation to agent
   agent.observe(observation)
   
   # 4. Retrieve and process predictions
   raw_predictions = agent.get_predictions()
   
   # 5. Create a prediction ensemble for easier handling
   predictions = PredictionEnsemble(raw_predictions)
   
   # 6. Access prediction data
   for prediction in predictions.get_predictions():
       print(f"Prediction: {prediction.get_name()}")
       print(f"Confidence: {prediction.get_confidence()}")
       print(f"Matches: {prediction.get_matches()}")

This code example demonstrates the complete transformation from GDF observation to accessible prediction objects that can be processed by application logic.


Prediction Object Structure
-------------------------

After observations are processed, they result in prediction objects that encapsulate the agent's reasoning and conclusions.

Single Prediction Format
^^^^^^^^^^^^^^^^^^^^^^

A single prediction represents one potential interpretation or match for an observation. Each prediction contains:

* **Label/Name**: Identifier for the prediction
* **Confidence Score**: Numerical value indicating match certainty (typically 0.0-1.0)
* **Matching Criteria**: Specific elements from the observation that matched
* **Metadata**: Additional information about the prediction
* **Source References**: Information about the patterns that generated the prediction

The basic structure of a prediction object as returned by the API:

.. code-block:: python

   {
       "name": "network_outage",
       "confidence": 0.87,
       "matches": {
           "keywords": ["network", "connectivity", "issues"],
           "patterns": ["connectivity problem"]
       },
       "metadata": {
           "category": "infrastructure",
           "severity": "high",
           "resolution_time": "1-4 hours"
       },
       "source_id": "pattern_lib_123"
   }

Prediction objects are immutable once created and provide methods for accessing their properties rather than direct dictionary access.

PredictionEnsemble Usage
^^^^^^^^^^^^^^^^^^^^^^

When multiple potential matches are found for an observation, they are returned as a collection. The :class:`PredictionEnsemble` class provides mechanisms for working with these collections.

**Key features of PredictionEnsemble:**

* **Aggregation**: Multiple predictions grouped by relevance
* **Ordering**: Predictions sorted by confidence score
* **Filtering**: Methods to select predictions based on criteria
* **Statistics**: Aggregate information about the prediction set

The PredictionEnsemble structure encapsulates a list of individual predictions and provides methods for accessing and manipulating them:

.. code-block:: python

   # Structure of a PredictionEnsemble object
   {
       "predictions": [
           {prediction_object_1},
           {prediction_object_2},
           ...
       ],
       "metadata": {
           "prediction_count": 3,
           "highest_confidence": 0.87,
           "average_confidence": 0.72,
           "source_observation_id": "obs_12345"
       }
   }

API Methods for Prediction Access
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The following methods are available for accessing prediction data:

**Individual Prediction Methods:**

.. code-block:: python

   # Accessing a single prediction
   prediction = predictions.get_predictions()[0]
   
   # Available methods
   name = prediction.get_name()           # Get prediction identifier
   confidence = prediction.get_confidence()   # Get confidence score (0.0-1.0)
   matches = prediction.get_matches()     # Get matching criteria dictionary
   metadata = prediction.get_metadata()   # Get prediction metadata
   category = prediction.get_category()   # Get prediction category (if available)
   
   # Check if prediction meets criteria
   if prediction.confidence_above(0.7) and prediction.has_metadata("severity"):
       # Process high-confidence predictions with severity information
       pass

**Ensemble Methods:**

.. code-block:: python

   # Working with prediction ensembles
   ensemble = PredictionEnsemble(raw_predictions)
   
   # Retrieval methods
   all_predictions = ensemble.get_predictions()  # Get all predictions
   top_prediction = ensemble.get_top_prediction()  # Get highest confidence prediction
   high_confidence = ensemble.filter_by_confidence(0.8)  # Get predictions above threshold
   
   # Filtering methods
   network_predictions = ensemble.filter_by_category("network")
   urgent_predictions = ensemble.filter_by_metadata("urgency", 0.7, operator=">=")
   
   # Statistical methods
   avg_confidence = ensemble.get_average_confidence()
   prediction_count = ensemble.get_prediction_count()
   has_high_confidence = ensemble.has_predictions_above_confidence(0.9)

For complete documentation of available methods, see :class:`ia.gaius.data_structures.Prediction` and :class:`ia.gaius.data_structures.PredictionEnsemble`.

Metadata Propagation
^^^^^^^^^^^^^^^^^^

Metadata from the original observation can propagate to the resulting predictions. This allows tracing the lineage of predictions back to their source observations.

**Metadata handling:**

1. **Observation Metadata**: Present in the original GDF observation
2. **Processing Metadata**: Added during transformation (timestamps, processing nodes)
3. **Prediction Metadata**: Specific to the prediction (confidence, match criteria)

The relationship between observation and prediction metadata:

.. code-block:: python

   # Original observation with metadata
   observation = create_gdf(
       strings=["Network connectivity issue reported"],
       vectors=[],
       emotives={},
       metadata={
           "ticket_id": "NET-2045",
           "source_system": "helpdesk",
           "timestamp": "2024-04-23T08:15:22Z"
       }
   )
   
   # Submit observation
   agent.observe(observation)
   
   # Retrieve predictions
   predictions = PredictionEnsemble(agent.get_predictions())
   top_prediction = predictions.get_top_prediction()
   
   # Access propagated metadata
   prediction_metadata = top_prediction.get_metadata()
   original_ticket_id = prediction_metadata.get("source_ticket_id")  # NET-2045
   observation_timestamp = prediction_metadata.get("observation_timestamp")  # 2024-04-23T08:15:22Z
   
   # New prediction-specific metadata
   prediction_timestamp = prediction_metadata.get("prediction_timestamp")
   processing_time_ms = prediction_metadata.get("processing_time_ms")

.. note::
   Not all observation metadata is automatically propagated to predictions. The specific metadata fields that propagate depend on the agent configuration and processing pipeline. Critical identifying information is typically preserved for traceability.


Integration Points
----------------

This section covers practical aspects of integrating the observation-prediction lifecycle into applications.

Observing Data with AgentClient
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The primary method for submitting observations to an agent is through the ``observe()`` method of the :class:`AgentClient` class. This method accepts GDF-formatted data and handles the communication with the agent.

**Connection Setup**

Before observations can be submitted, a connection to the agent must be established:

.. code-block:: python

   from ia.gaius.agent_client import AgentClient
   
   # Create agent connection configuration
   agent_info = {
       'api_key': 'your-api-key',     # Authentication key
       'name': 'your-agent-name',     # Agent identifier 
       'domain': 'your-domain',       # Domain for agent communication
       'secure': True,                # Use HTTPS (recommended for production)
       'timeout': 30,                 # Connection timeout in seconds
       'retry_attempts': 3            # Number of retry attempts on failure
   }
   
   # Create and connect the client
   try:
       agent = AgentClient(agent_info)
       agent.connect()
       print("Connected to agent successfully")
   except Exception as e:
       print(f"Connection error: {e}")
       # Handle connection failure

**Submitting Observations**

Once connected, observations can be submitted in several ways:

.. code-block:: python

   from ia.gaius.utils import create_gdf
   
   # Method 1: Using the create_gdf utility (recommended)
   observation = create_gdf(
       strings=["Customer reports payment failure with error code E-4123"],
       vectors=[],  # Optional feature vectors
       emotives={"importance": 0.9},  # Optional emotive values
       metadata={"source": "support_ticket", "id": "TICKET-5678"}  # Optional metadata
   )
   
   # Method 2: Direct dictionary creation (requires careful formatting)
   manual_observation = {
       "strings": ["Customer reports payment failure with error code E-4123"],
       "vectors": [],
       "emotives": {"importance": 0.9},
       "metadata": {"source": "support_ticket", "id": "TICKET-5678"}
   }
   
   # Submit the observation
   try:
       # With default options
       agent.observe(observation)
       
       # With specific options
       agent.observe(
           manual_observation,
           wait_for_processing=True,  # Block until observation is processed
           timeout=10,                # Custom timeout for this observation
           nodes=["P1", "P2"]         # Specific processing nodes to target
       )
   except Exception as e:
       print(f"Observation error: {e}")
       # Handle observation failure

**Batch Observation Processing**

For performance optimization with multiple observations:

.. code-block:: python

   # Create multiple observations
   observations = [
       create_gdf(strings=["Observation 1"], vectors=[], emotives={}),
       create_gdf(strings=["Observation 2"], vectors=[], emotives={}),
       create_gdf(strings=["Observation 3"], vectors=[], emotives={})
   ]
   
   # Batch process observations
   for obs in observations:
       agent.observe(obs, wait_for_processing=False)  # Non-blocking observations
   
   # Optionally wait for all processing to complete
   agent.wait_for_processing()

Retrieving and Handling Predictions
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

After observations are submitted and processed, predictions can be retrieved and handled using various methods.

**Synchronous Retrieval**

The most direct approach is synchronous retrieval immediately after observation:

.. code-block:: python

   from ia.gaius.data_structures import PredictionEnsemble
   
   # Submit observation and wait for processing
   agent.observe(observation, wait_for_processing=True)
   
   # Retrieve predictions
   raw_predictions = agent.get_predictions()
   
   # Convert to ensemble for easier handling
   predictions = PredictionEnsemble(raw_predictions)
   
   # Process predictions
   if predictions.has_predictions():
       top_prediction = predictions.get_top_prediction()
       print(f"Best match: {top_prediction.get_name()} with confidence {top_prediction.get_confidence()}")
   else:
       print("No predictions found for the observation")

**Asynchronous Processing**

For high-throughput applications, asynchronous processing may be more efficient:

.. code-block:: python

   import asyncio
   
   async def process_observation(agent, observation):
       # Submit observation (non-blocking)
       agent.observe(observation, wait_for_processing=False)
       
       # Poll for predictions (could implement with callbacks in production)
       max_attempts = 10
       attempt = 0
       
       while attempt < max_attempts:
           predictions = agent.get_predictions()
           if predictions:
               return PredictionEnsemble(predictions)
           
           attempt += 1
           await asyncio.sleep(0.5)  # Wait before polling again
       
       return None  # No predictions after max attempts
   
   # Usage in async context
   async def main():
       agent = AgentClient(agent_info)
       agent.connect()
       
       # Process multiple observations concurrently
       tasks = [
           process_observation(agent, create_gdf(strings=["Observation 1"], vectors=[], emotives={})),
           process_observation(agent, create_gdf(strings=["Observation 2"], vectors=[], emotives={})),
           process_observation(agent, create_gdf(strings=["Observation 3"], vectors=[], emotives={}))
       ]
       
       results = await asyncio.gather(*tasks)
       for idx, predictions in enumerate(results):
           if predictions:
               print(f"Observation {idx+1} produced {predictions.get_prediction_count()} predictions")

**Error Handling Patterns**

Robust error handling is essential for production applications:

.. code-block:: python

   def observe_with_retry(agent, observation, max_retries=3):
       """Submit an observation with retry logic"""
       attempt = 0
       while attempt < max_retries:
           try:
               agent.observe(observation, wait_for_processing=True, timeout=15)
               return True
           except ConnectionError as e:
               # Network error - can retry
               logging.warning(f"Connection error on attempt {attempt+1}: {e}")
               attempt += 1
               time.sleep(2 ** attempt)  # Exponential backoff
           except ValueError as e:
               # Data formatting error - fix before retry
               logging.error(f"Data format error: {e}")
               return False  # Don't retry invalid data
           except Exception as e:
               # Other errors - log and retry
               logging.error(f"Unknown error: {e}")
               attempt += 1
               time.sleep(1)
       
       logging.error(f"Failed to submit observation after {max_retries} attempts")
       return False

Validation and Logging
^^^^^^^^^^^^^^^^^^^

Proper validation and logging are critical for troubleshooting and maintaining the observation-prediction pipeline.

**Input Validation**

Validate observations before submission to prevent errors:

.. code-block:: python

   from ia.gaius.data_ops import validate_data
   
   def submit_validated_observation(agent, observation_data):
       """Validate and submit an observation"""
       # Ensure proper GDF format
       if not isinstance(observation_data, dict):
           observation_data = create_gdf(
               strings=[observation_data] if isinstance(observation_data, str) else [],
               vectors=[],
               emotives={}
           )
       
       # Validate the observation
       try:
           validate_data(observation_data)
       except Exception as e:
           logging.error(f"Invalid observation data: {e}")
           return False
       
       # Submit valid observation
       try:
           agent.observe(observation_data)
           return True
       except Exception as e:
           logging.error(f"Failed to submit observation: {e}")
           return False

**Logging Best Practices**

Implement comprehensive logging throughout the lifecycle:

.. code-block:: python

   import logging
   import uuid
   
   # Configure logging
   logging.basicConfig(level=logging.INFO)
   logger = logging.getLogger("observation-lifecycle")
   
   def process_observation_with_logging(agent, observation_data):
       # Generate unique ID for tracking this observation
       observation_id = str(uuid.uuid4())
       
       # Add tracking ID to metadata
       if "metadata" not in observation_data:
           observation_data["metadata"] = {}
       observation_data["metadata"]["tracking_id"] = observation_id
       
       # Log observation submission
       logger.info(f"Submitting observation {observation_id}")
       logger.debug(f"Observation data: {observation_data}")
       
       # Submit observation
       try:
           start_time = time.time()
           agent.observe(observation_data, wait_for_processing=True)
           processing_time = time.time() - start_time
           logger.info(f"Observation {observation_id} processed in {processing_time:.2f}s")
       except Exception as e:
           logger.error(f"Observation {observation_id} processing failed: {e}")
           return None
       
       # Retrieve predictions
       try:
           predictions = PredictionEnsemble(agent.get_predictions())
           prediction_count = predictions.get_prediction_count()
           
           logger.info(f"Observation {observation_id} generated {prediction_count} predictions")
           if prediction_count > 0:
               top_confidence = predictions.get_top_prediction().get_confidence()
               logger.info(f"Top prediction confidence: {top_confidence:.4f}")
           
           return predictions
       except Exception as e:
           logger.error(f"Failed to retrieve predictions for observation {observation_id}: {e}")
           return None

**Monitoring and Health Checks**

Implement monitoring to ensure the observation-prediction pipeline is functioning correctly:

.. code-block:: python

   def verify_observation_pipeline(agent):
       """Perform health check on the observation-prediction pipeline"""
       # Create a test observation
       test_observation = create_gdf(
           strings=["HEALTH_CHECK_TEST_OBSERVATION"],
           vectors=[],
           emotives={},
           metadata={"health_check": True, "timestamp": datetime.now().isoformat()}
       )
       
       # Track timing
       start_time = time.time()
       
       # Submit observation
       try:
           agent.observe(test_observation, wait_for_processing=True, timeout=10)
       except Exception as e:
           return {
               "status": "failed",
               "stage": "observation",
               "error": str(e),
               "elapsed_time": time.time() - start_time
           }
       
       # Retrieve predictions
       try:
           predictions = agent.get_predictions()
           elapsed_time = time.time() - start_time
           
           # Check for predictions
           if predictions:
               return {
                   "status": "healthy",
                   "prediction_count": len(predictions),
                   "elapsed_time": elapsed_time
               }
           else:
               return {
                   "status": "degraded",
                   "stage": "prediction",
                   "error": "No predictions returned",
                   "elapsed_time": elapsed_time
               }
       except Exception as e:
           return {
               "status": "failed",
               "stage": "prediction_retrieval",
               "error": str(e),
               "elapsed_time": time.time() - start_time
           }

.. seealso:: For more information on error handling and logging best practices, refer to the :doc:`/troubleshooting/common_issues` guide.


Conclusion
----------

This document has covered the full lifecycle of observation data as it transforms into prediction objects. Understanding this process is critical for effective integration and utilization of the IA SDK in applications.

**Summary of Key Concepts**

* Observations must follow the GDF format with required fields: ``strings``, ``vectors``, and ``emotives``
* The agent transforms observations through a multi-stage pipeline influenced by genome configuration
* Predictions are returned as objects with confidence scores, match criteria, and metadata
* The PredictionEnsemble provides methods for working with collections of predictions
* Proper error handling, validation, and logging are essential for robust integration

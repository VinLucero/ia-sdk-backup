"""Advanced end-to-end workflow tests for the ia-sdk package."""
import os
import time
import json
import pytest
import logging
import numpy as np
from typing import Dict, List, Any

from ia.gaius.utils import create_gdf
from ia.gaius.data_ops import validate_data
from ia.gaius.data_structures import PredictionEnsemble

logger = logging.getLogger('ia_system_tests')


@pytest.mark.advanced
def test_complex_data_processing(temp_agent, sample_data):
    """Test complex data processing with different data types."""
    # Clear working memory
    temp_agent.clear_all_memory()
    
    # Create a sequence with mixed data types
    mixed_data_sequence = [
        # Simple strings
        create_gdf(strings=sample_data["simple_strings"]),
        
        # Event with both strings and vectors
        create_gdf(
            strings=["vector_event"],
            vectors=[[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
        ),
        
        # Event with emotives
        create_gdf(
            strings=["emotive_event"],
            vectors=[],
            emotives={"importance": 0.8, "urgency": 0.7}
        ),
        
        # Classification event
        create_gdf(strings=["complex_class"])
    ]
    
    # Observe all events and learn
    for event in mixed_data_sequence:
        temp_agent.observe(event)
    
    # Learn from the sequence
    learn_result = temp_agent.learn()
    assert learn_result is not None
    
    # Retrieve working memory to verify all data types were processed
    wm = temp_agent.get_wm()
    assert wm is not None
    
    # Check working memory contents
    if isinstance(wm, dict) and 'P1' in wm:
        wm_content = wm['P1']
    else:
        wm_content = wm
    
    # Verify the various data types are present
    content_str = str(wm_content)
    assert any(s in content_str for s in sample_data["simple_strings"])
    assert "vector_event" in content_str
    assert "emotive_event" in content_str
    assert "complex_class" in content_str
    
    # Verify vectors were processed
    model_name = learn_result['P1'] if isinstance(learn_result, dict) and 'P1' in learn_result else learn_result
    model = temp_agent.get_model(model_name)
    
    if isinstance(model, dict) and 'sequence' in model:
        # Look for vector data in the model sequence
        sequence_str = str(model['sequence'])
        assert "vector" in sequence_str
        assert "emotive" in sequence_str


@pytest.mark.advanced
@pytest.mark.slow
def test_multi_agent_interaction(agent_manager):
    """Test interactions between multiple agents."""
    # Create two agents: a source and a target
    source_agent_name = f"test-source-{os.urandom(4).hex()}"
    target_agent_name = f"test-target-{os.urandom(4).hex()}"
    
    source_agent_obj = agent_manager.start_agent(
        genome_name="simple.genome",
        agent_id=source_agent_name,
        agent_name=source_agent_name
    )
    
    target_agent_obj = agent_manager.start_agent(
        genome_name="simple.genome",
        agent_id=target_agent_name,
        agent_name=target_agent_name
    )
    
    # Get client objects and connect
    source_agent = source_agent_obj.get_agent_client()
    target_agent = target_agent_obj.get_agent_client()
    
    source_agent.connect()
    target_agent.connect()
    
    try:
        # Set up node configurations
        source_agent.set_ingress_nodes(["P1"])
        source_agent.set_query_nodes(["P1"])
        
        target_agent.set_ingress_nodes(["P1"])
        target_agent.set_query_nodes(["P1"])
        
        # 1. Train the source agent
        source_agent.clear_all_memory()
        
        # Create training data
        training_data = [
            create_gdf(strings=["sourceEvent1"]),
            create_gdf(strings=["sourceEvent2"]),
            create_gdf(strings=["sourceResult"])
        ]
        
        # Train source agent
        for event in training_data:
            source_agent.observe(event)
        
        learn_result = source_agent.learn()
        assert learn_result is not None
        
        # 2. Transfer knowledge from source to target
        # Export knowledge base from source
        kb_data = source_agent.get_kbs_as_json(obj=True)
        assert kb_data is not None
        
        # Import knowledge base to target
        target_agent.load_kbs_from_json(obj=kb_data)
        
        # 3. Test target agent with the knowledge from source
        target_agent.clear_wm()  # Clear working memory but keep KB
        
        # Add the beginning of a sequence and see if it predicts correctly
        for event in training_data[:-1]:  # Send all but the last event
            target_agent.observe(event)
        
        # Get predictions
        predictions = target_agent.get_predictions()
        assert predictions is not None
        
        # Verify prediction contains expected result
        if isinstance(predictions, dict) and 'P1' in predictions:
            prediction_str = str(predictions['P1'])
            assert "sourceResult" in prediction_str
    
    finally:
        # Cleanup
        agent_manager.delete_agent(source_agent_name)
        agent_manager.delete_agent(target_agent_name)


@pytest.mark.advanced
def test_state_persistence_and_recovery(temp_agent, temp_directory):
    """Test agent state persistence and recovery."""
    # 1. Create and train the agent
    temp_agent.clear_all_memory()
    
    # Create some training data
    training_data = [
        create_gdf(strings=["persistence1"]),
        create_gdf(strings=["persistence2"]),
        create_gdf(strings=["persistenceResult"])
    ]
    
    # Train the agent
    for event in training_data:
        temp_agent.observe(event)
    
    learn_result = temp_agent.learn()
    assert learn_result is not None
    
    # 2. Save the KB to a file
    kb_file = os.path.join(temp_directory, "agent_kb.json")
    kb_data = temp_agent.get_kbs_as_json(obj=True)
    
    with open(kb_file, 'w') as f:
        json.dump(kb_data, f)
    
    # Verify file was created
    assert os.path.exists(kb_file)
    
    # 3. Clear the agent's memory
    temp_agent.clear_all_memory()
    
    # Verify KB is empty
    kb_after_clear = temp_agent.get_kbs_as_json(obj=True)
    
    if isinstance(kb_after_clear, dict) and 'P1' in kb_after_clear:
        symbols_after_clear = kb_after_clear['P1']['symbols_kb']
        assert "persistence1" not in str(symbols_after_clear)
    
    # 4. Load the saved KB back
    temp_agent.load_kbs_from_json(path=kb_file)
    
    # 5. Verify the agent now has the restored knowledge
    kb_after_load = temp_agent.get_kbs_as_json(obj=True)
    
    if isinstance(kb_after_load, dict) and 'P1' in kb_after_load:
        symbols_after_load = kb_after_load['P1']['symbols_kb']
        assert "persistence" in str(symbols_after_load)
    
    # 6. Test that the restored knowledge works
    temp_agent.clear_wm()  # Clear working memory but keep KB
    
    # Add the beginning of a sequence and see if it predicts correctly
    for event in training_data[:-1]:  # Send all but the last event
        temp_agent.observe(event)
    
    # Get predictions
    predictions = temp_agent.get_predictions()
    assert predictions is not None
    
    # Verify prediction contains expected result
    if isinstance(predictions, dict) and 'P1' in predictions:
        prediction_str = str(predictions['P1'])
        assert "persistenceResult" in prediction_str


@pytest.mark.advanced
@pytest.mark.slow
def test_performance_monitoring(temp_agent):
    """Test performance monitoring capabilities."""
    # Clear any existing memory
    temp_agent.clear_all_memory()
    
    # Create a large dataset to test performance
    large_sequence = []
    for i in range(20):  # Create 20 events
        large_sequence.append(create_gdf(strings=[f"perf_event_{i}"]))
    
    # 1. Measure response time for observations
    observation_times = []
    for event in large_sequence:
        start_time = time.time()
        temp_agent.observe(event)
        end_time = time.time()
        observation_times.append(end_time - start_time)
    
    # Calculate average observation time
    avg_observation_time = sum(observation_times) / len(observation_times)
    logger.info(f"Average observation time: {avg_observation_time:.6f} seconds")
    
    # 2. Test memory usage before and after learning
    # Get KB size before learning
    kb_before = temp_agent.get_kbs_as_json(obj=True)
    kb_size_before = len(str(kb_before))
    
    # Learn from the sequence
    learn_result = temp_agent.learn()
    assert learn_result is not None
    
    # Get KB size after learning
    kb_after = temp_agent.get_kbs_as_json(obj=True)
    kb_size_after = len(str(kb_after))
    
    # Memory usage should increase after learning
    assert kb_size_after > kb_size_before
    logger.info(f"KB size before learning: {kb_size_before} bytes")
    logger.info(f"KB size after learning: {kb_size_after} bytes")
    logger.info(f"KB size increase: {kb_size_after - kb_size_before} bytes")
    
    # 3. Measure prediction performance
    temp_agent.start_predicting()
    
    # Create test sequences
    test_sequences = [
        create_gdf(strings=["perf_event_0"]),  # First event in training
        create_gdf(strings=["perf_event_10"]),  # Middle event in training
        create_gdf(strings=["perf_event_19"]),  # Last event in training
        create_gdf(strings=["unknown_event"])   # Not in training
    ]
    
    # Measure prediction time for each sequence
    prediction_times = []
    prediction_counts = []
    
    for test_sequence in test_sequences:
        temp_agent.clear_wm()
        
        # Measure time to observe and predict
        start_time = time.time()
        temp_agent.observe(test_sequence)
        predictions = temp_agent.get_predictions()
        end_time = time.time()
        
        prediction_time = end_time - start_time
        prediction_times.append(prediction_time)
        
        # Count predictions
        if isinstance(predictions, dict) and 'P1' in predictions:
            prediction_count = len(predictions['P1'])
        else:
            prediction_count = 0
        
        prediction_counts.append(prediction_count)
        
        logger.info(f"Prediction time for {test_sequence}: {prediction_time:.6f} seconds")
        logger.info(f"Number of predictions: {prediction_count}")
    
    # 4. Resource utilization - agent status before and after tests
    status_before = temp_agent.show_status()
    temp_agent.clear_wm()  # Keep KB but clear WM
    status_after = temp_agent.show_status()
    
    # Log status information
    logger.info(f"Agent status before: {status_before}")
    logger.info(f"Agent status after: {status_after}")
    
    # 5. Cleanup
    temp_agent.clear_all_memory()


@pytest.mark.advanced
def test_resource_management(temp_agent):
    """Test resource management capabilities."""
    # 1. Test memory cleanup operations
    # First, populate memory with data
    for i in range(10):
        event = create_gdf(strings=[f"resource_event_{i}"])
        temp_agent.observe(event)
    
    # Get status before cleanup
    status_before = temp_agent.show_status()
    wm_size_before = 0
    
    if isinstance(status_before, dict) and 'P1' in status_before:
        wm_size_before = status_before['P1'].get('size_WM', 0)
    else:
        wm_size_before = status_before.get('size_WM', 0)
    
    assert wm_size_before > 0
    
    # Clear working memory
    temp_agent.clear_wm()
    
    # Get status after cleanup
    status_after = temp_agent.show_status()
    wm_size_after = 0
    
    if isinstance(status_after, dict) and 'P1' in status_after:
        wm_size_after = status_after['P1'].get('size_WM', 0)
    else:
        wm_size_after = status_after.get('size_WM', 0)
    
    # Working memory should be smaller or empty after clearing
    assert wm_size_after < wm_size_before
    
    # 2. Test resource allocation with gene modification
    # Modify genes to allocate more resources
    temp_agent.change_genes({
        "max_predictions": 100,  # Increase max predictions
        "recall_threshold": 0.01  # Lower recall threshold for more matches
    })
    
    # Create and observe training data
    for i in range(5):
        event = create_gdf(strings=[f"allocation_event_{i}"])
        temp_agent.observe(event)
    
    # Learn to create models
    temp_agent.learn()
    
    # Now test with high resource utilization
    temp_agent.clear_wm()
    temp_agent.start_predicting()
    
    # Observe a test event
    test_event = create_gdf(strings=["allocation_event_0"])
    temp_agent.observe(test_event)
    
    # Get predictions - should have more with lower recall threshold
    predictions = temp_agent.get_predictions()
    
    if isinstance(predictions, dict) and 'P1' in predictions:
        prediction_count = len(predictions['P1'])
        logger.info(f"Number of predictions with low recall threshold: {prediction_count}")
        # Should have at least some predictions
        assert prediction_count > 0
    
    # 3. Reset to normal resource allocation
    temp_agent.change_genes({
        "max_predictions": 10,  # Standard value
        "recall_threshold": 0.1  # Standard value
    })
    
    # 4. Test full cleanup
    temp_agent.clear_all_memory()
    kb_after_clear = temp_agent.get_kbs_as_json(obj=True)
    
    # KB should be empty or have minimal entries after clearing
    if isinstance(kb_after_clear, dict) and 'P1' in kb_after_clear:
        symbols_count = len(kb_after_clear['P1'].get('symbols_kb', {}))
        models_count = len(kb_after_clear['P1'].get('models_kb', {}))
        
        logger.info(f"Symbols after clear: {symbols_count}")
        logger.info(f"Models after clear: {models_count}")
        
        # Should have few or no models/symbols
        assert symbols_count == 0
        assert models_count == 0


@pytest.mark.advanced
def test_error_recovery(temp_agent):
    """Test error recovery capabilities."""
    # 1. Test recovery from invalid data
    # First establish a valid baseline
    temp_agent.clear_all_memory()
    valid_event = create_gdf(strings=["valid_event"])
    temp_agent.observe(valid_event)
    
    # Try to observe invalid data, then verify we can continue operating
    try:
        invalid_data = {"invalid_field": "test"}  # Missing required fields
        temp_agent.observe(invalid_data)
    except Exception as e:
        logger.info(f"Expected error with invalid data: {str(e)}")
        # System should continue functioning after error
    
    # Verify agent is still responsive after error
    valid_event2 = create_gdf(strings=["valid_event2"])
    response = temp_agent.observe(valid_event2)
    assert response is not None, "Agent should recover and process valid data after error"
    
    # 2. Test recovery from malformed model operations
    # Try to get a non-existent model
    try:
        temp_agent.get_model("NON_EXISTENT_MODEL_12345")
    except Exception as e:
        logger.info(f"Expected error with non-existent model: {str(e)}")
    
    # Verify agent is still responsive
    status = temp_agent.show_status()
    assert status is not None, "Agent should respond to status request after model error"
    
    # 3. Test recovery from extreme memory usage
    # Fill working memory with many events
    for i in range(100):  # Large number of events
        event = create_gdf(strings=[f"memory_intensive_event_{i}"])
        temp_agent.observe(event)
    
    # Check status
    status_after_load = temp_agent.show_status()
    assert status_after_load is not None, "Agent should remain responsive under memory load"
    
    # Clear working memory and verify recovery
    temp_agent.clear_wm()
    status_after_clear = temp_agent.show_status()
    
    # Working memory should be cleared
    if isinstance(status_after_clear, dict) and 'P1' in status_after_clear:
        wm_size = status_after_clear['P1'].get('size_WM', -1)
    else:
        wm_size = status_after_clear.get('size_WM', -1)
    
    assert wm_size == 0, "Working memory should be cleared during recovery"
    
    # 4. Test data corruption recovery
    # Train a model
    temp_agent.clear_wm()
    temp_agent.observe(create_gdf(strings=["recovery_event1"]))
    temp_agent.observe(create_gdf(strings=["recovery_event2"]))
    model_result = temp_agent.learn()
    
    # Get model name
    if isinstance(model_result, dict) and 'P1' in model_result:
        model_name = model_result['P1']
    else:
        model_name = model_result
    
    # Delete the model to simulate corruption
    temp_agent.delete_model(model_name)
    
    # Verify recovery by recreating the model
    temp_agent.clear_wm()
    temp_agent.observe(create_gdf(strings=["recovery_event1"]))
    temp_agent.observe(create_gdf(strings=["recovery_event2"]))
    new_model_result = temp_agent.learn()
    
    # Should be able to create a new model
    assert new_model_result is not None, "Agent should recover from model corruption"
    
    # 5. Final cleanup
    temp_agent.clear_all_memory()

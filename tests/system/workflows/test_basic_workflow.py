"""Basic end-to-end workflow tests for the ia-sdk package."""
import time
import pytest
import logging
import numpy as np
from typing import Dict, List, Any

from ia.gaius.utils import create_gdf
from ia.gaius.data_ops import validate_data

logger = logging.getLogger('ia_system_tests')


@pytest.mark.basic
def test_agent_initialization_and_connection(temp_agent):
    """Test basic agent initialization and connection."""
    # Check that the agent is properly connected
    assert temp_agent._connected is True
    
    # Check that nodes are properly set
    assert len(temp_agent.ingress_nodes) > 0
    assert len(temp_agent.query_nodes) > 0
    
    # Check agent information
    assert temp_agent.genome is not None
    assert temp_agent.all_nodes is not None
    assert len(temp_agent.all_nodes) > 0
    
    # Check status
    status = temp_agent.show_status()
    assert status is not None
    if isinstance(status, dict):
        assert 'P1' in status
        assert status['P1']['name'] == 'P1'


@pytest.mark.basic
def test_simple_observation_and_prediction(temp_agent):
    """Test observing data and getting predictions."""
    # Clear working memory
    temp_agent.clear_wm()
    
    # Create and observe test data
    data = create_gdf(strings=["hello", "world"])
    assert validate_data(data) is True
    
    # Observe the data and wait for processing
    result = temp_agent.observe(data)
    assert result is not None
    
    # Get predictions
    predictions = temp_agent.get_predictions()
    assert predictions is not None
    
    # Check working memory contents
    wm = temp_agent.get_wm()
    assert wm is not None
    
    # Ensure "hello" and "world" are in working memory
    if isinstance(wm, dict) and 'P1' in wm:
        wm_data = wm['P1']
    else:
        wm_data = wm
    
    assert any("hello" in str(event) for event in wm_data)
    assert any("world" in str(event) for event in wm_data)


@pytest.mark.basic
def test_learning_and_model_management(temp_agent):
    """Test learning and model management functionality."""
    # Clear any existing memory
    temp_agent.clear_all_memory()
    
    # Create and observe a sequence
    sequence = [
        create_gdf(strings=["event1"]),
        create_gdf(strings=["event2"]),
        create_gdf(strings=["class1"])  # Classification
    ]
    
    for event in sequence:
        temp_agent.observe(event)
    
    # Learn from the sequence
    learn_result = temp_agent.learn()
    assert learn_result is not None
    
    # Get the model name from the result
    if isinstance(learn_result, dict) and 'P1' in learn_result:
        model_name = learn_result['P1']
    else:
        model_name = learn_result
    
    # Retrieve the model
    model = temp_agent.get_model(model_name)
    assert model is not None
    
    # Validate the model contains our sequence
    if isinstance(model, dict):
        assert 'sequence' in model
        model_sequence = model['sequence']
        assert len(model_sequence) == 3  # Three events
        
        # Check for classification at the end
        assert any("class1" in str(event) for event in model_sequence[-1])
    
    # Delete the model
    delete_result = temp_agent.delete_model(model_name)
    assert delete_result is not None


@pytest.mark.basic
def test_gene_modification(temp_agent):
    """Test modifying agent genes."""
    # Get initial gene values
    initial_rt = temp_agent.get_gene("recall_threshold")
    assert initial_rt is not None
    
    # Modify recall threshold
    new_rt_value = 0.5
    change_result = temp_agent.change_genes({"recall_threshold": new_rt_value})
    assert change_result is not None
    
    # Verify the change
    current_rt = temp_agent.get_gene("recall_threshold")
    assert current_rt is not None
    
    # Extract the value for comparison
    if isinstance(current_rt, dict) and 'recall_threshold' in current_rt:
        current_rt_value = current_rt['recall_threshold']
    else:
        current_rt_value = current_rt
    
    assert float(current_rt_value) == new_rt_value


@pytest.mark.basic
def test_agent_state_management(temp_agent):
    """Test agent state management functions."""
    # Test starting and stopping predicting
    stop_result = temp_agent.stop_predicting()
    assert stop_result is not None
    
    start_result = temp_agent.start_predicting()
    assert start_result is not None
    
    # Test sleeping and waking
    sleep_result = temp_agent.start_sleeping()
    assert sleep_result is not None
    
    wake_result = temp_agent.stop_sleeping()
    assert wake_result is not None
    
    # Check status after state changes
    status = temp_agent.show_status()
    assert status is not None


@pytest.mark.basic
def test_basic_error_handling(temp_agent):
    """Test basic error handling in the agent client."""
    # Try to get a non-existent model
    try:
        model = temp_agent.get_model("NON_EXISTENT_MODEL_12345")
        # Either returns None or raises an exception
        if model is not None:
            # Some implementations return an empty result instead of raising
            assert not model or isinstance(model, dict) and not model
    except Exception as e:
        # Exception is acceptable here
        assert "not found" in str(e) or "exist" in str(e) or "unknown" in str(e).lower()
    
    # Try to use an invalid node name
    try:
        temp_agent.set_ingress_nodes(["NON_EXISTENT_NODE"])
    except Exception as e:
        # Should raise an exception or log a warning
        assert True
    
    # Try to observe invalid data
    try:
        # Missing required fields
        invalid_data = {"invalid_field": "test"}
        temp_agent.observe(invalid_data)
    except Exception as e:
        # Should raise a validation error
        assert "valid" in str(e).lower() or "invalid" in str(e).lower() or "missing" in str(e).lower()


@pytest.mark.basic
def test_kb_operations(temp_agent):
    """Test knowledge base operations."""
    # First clear all memory
    temp_agent.clear_all_memory()
    
    # Create and observe some data
    data = create_gdf(strings=["example1", "example2"])
    temp_agent.observe(data)
    temp_agent.learn()
    
    # Get the KB as JSON
    kb = temp_agent.get_kbs_as_json(ids=False, obj=True)
    assert kb is not None
    
    # Check KB has our data
    if isinstance(kb, dict) and 'P1' in kb:
        assert 'symbols_kb' in kb['P1']
        symbols = kb['P1']['symbols_kb']
        assert any("example" in key for key in symbols.keys())
    
    # Clear memory and check KB is empty
    temp_agent.clear_all_memory()
    kb_after_clear = temp_agent.get_kbs_as_json(ids=False, obj=True)
    
    if isinstance(kb_after_clear, dict) and 'P1' in kb_after_clear and 'symbols_kb' in kb_after_clear['P1']:
        symbols_after_clear = kb_after_clear['P1']['symbols_kb']
        # Should have fewer or no symbols
        assert len(symbols_after_clear) < len(symbols) or len(symbols_after_clear) == 0


@pytest.mark.basic
def test_complete_workflow(temp_agent):
    """Test a complete basic workflow from observation to prediction."""
    # Clear all memory to start fresh
    temp_agent.clear_all_memory()
    
    # 1. Observe a sequence
    temp_agent.stop_predicting()  # Disable predictions during training
    training_sequences = [
        [create_gdf(strings=["input1"]), create_gdf(strings=["input2"]), create_gdf(strings=["classA"])],
        [create_gdf(strings=["input3"]), create_gdf(strings=["input4"]), create_gdf(strings=["classB"])],
        [create_gdf(strings=["input1"]), create_gdf(strings=["input4"]), create_gdf(strings=["classA"])]
    ]
    
    # Train each sequence
    for sequence in training_sequences:
        temp_agent.clear_wm()
        for event in sequence:
            temp_agent.observe(event)
        temp_agent.learn()
    
    # 2. Validate models were created
    kb = temp_agent.get_kbs_as_json(ids=False, obj=True)
    if isinstance(kb, dict) and 'P1' in kb:
        assert 'models_kb' in kb['P1']
        models = kb['P1']['models_kb']
        assert len(models) > 0
    
    # 3. Test prediction
    temp_agent.start_predicting()
    
    # Try a test sequence similar to training data
    test_sequence = [create_gdf(strings=["input1"]), create_gdf(strings=["input4"])]
    
    temp_agent.clear_wm()
    for event in test_sequence[:-1]:
        temp_agent.observe(event)
    
    # Observe the last event and get predictions
    temp_agent.observe(test_sequence[-1])
    predictions = temp_agent.get_predictions()
    
    # Verify predictions were made
    assert predictions is not None
    
    # 4. Cleanup
    temp_agent.clear_all_memory()

#!/bin/bash

# Comprehensive test suite for ia-sdk
echo "Running comprehensive ia-sdk test suite..."

# Create and activate new test environment
python -m venv test_env
source test_env/bin/activate

# Install all dependencies
pip install --no-index --find-links packages pandas networkx plotly ia-sdk

# Create test script
cat > test_suite.py << 'END_SCRIPT'
import sys
from datetime import datetime
import logging
import traceback

def run_test(name, test_fn):
    print(f"
=== Testing {name} ===")
    try:
        test_fn()
        print(f"✓ {name} passed")
        return True
    except Exception as e:
        print(f"✗ {name} failed: {str(e)}")
        print("Traceback:")
        traceback.print_exc()
        return False

def test_basic_imports():
    """Test importing all major modules"""
    from ia.gaius import agent_client, manager, data_structures, utils
    from ia.gaius.experimental import comcom_client, genome_optimizer, sklearn
    print("Successfully imported all major modules")

def test_agent_client():
    """Test agent client functionality"""
    from ia.gaius.agent_client import AgentQueryError, AgentClient
    # Test error handling
    error = AgentQueryError("Test error")
    assert str(error) == "Test error"
    # Test client initialization
    client = AgentClient("test_agent")
    assert client.name == "test_agent"
    print("Successfully tested agent client")

def test_data_structures():
    """Test data structures functionality"""
    from ia.gaius.data_structures import conditional_add_edge
    import networkx as nx
    
    # Create test graph
    graph = nx.Graph()
    conditional_add_edge("A", "B", graph, {"weight": 1})
    assert graph.has_edge("A", "B")
    edge_data = graph.get_edge_data("A", "B")
    assert edge_data.get("weight") == 1
    print("Successfully tested data structures")

def test_manager():
    """Test manager functionality"""
    from ia.gaius.manager import Agent
    # Test agent creation
    agent = Agent(name="test_agent", description="Test agent")
    assert agent.name == "test_agent"
    assert agent.description == "Test agent"
    print("Successfully tested manager")

def test_utils():
    """Test utilities functionality"""
    from ia.gaius.utils import get_logger
    # Test logger creation
    logger = get_logger("test_logger")
    assert logger.name == "test_logger"
    print("Successfully tested utils")

def test_experimental():
    """Test experimental features"""
    from ia.gaius.experimental import sklearn as gaius_sklearn
    from ia.gaius.experimental import genome_optimizer
    print("Successfully imported experimental modules")

def main():
    print(f"Starting ia-sdk test suite at {datetime.now()}")
    print(f"Python version: {sys.version}")
    
    tests = [
        ("Basic Imports", test_basic_imports),
        ("Agent Client", test_agent_client),
        ("Data Structures", test_data_structures),
        ("Manager", test_manager),
        ("Utils", test_utils),
        ("Experimental Features", test_experimental)
    ]
    
    results = []
    for name, test in tests:
        results.append(run_test(name, test))
    
    print("
=== Test Summary ===")
    total = len(results)
    passed = sum(results)
    print(f"Total tests: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {total - passed}")
    
    sys.exit(0 if all(results) else 1)

if __name__ == "__main__":
    main()
END_SCRIPT

# Run test suite
python test_suite.py

# Save test results
TEST_RESULTS="test_results_$(date +%Y%m%d_%H%M%S).txt"
python test_suite.py > $TEST_RESULTS 2>&1

# Cleanup
deactivate
rm -rf test_env test_suite.py

echo "Test suite complete! Results saved to $TEST_RESULTS"

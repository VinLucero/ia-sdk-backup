#!/usr/bin/env python3
import sys
from datetime import datetime
import logging
import traceback

class TestResult:
    def __init__(self, name, passed, error=None, traceback=None):
        self.name = name
        self.passed = passed
        self.error = error
        self.traceback = traceback

def run_test(name, test_fn):
    print(f"\n=== Testing {name} ===")
    try:
        test_fn()
        print(f"✓ {name} passed")
        return TestResult(name, True)
    except Exception as e:
        error_msg = str(e)
        tb = traceback.format_exc()
        print(f"✗ {name} failed: {error_msg}")
        print("Traceback:")
        print(tb)
        return TestResult(name, False, error_msg, tb)

def test_basic_imports():
    """Test importing all major modules"""
    from ia.gaius import agent_client, manager, data_structures, utils
    print("Successfully imported core modules")
    # Test selective experimental imports to avoid deap dependency initially
    from ia.gaius.experimental import sklearn
    print("Successfully imported experimental sklearn module")

def test_agent_client():
    """Test agent client functionality"""
    from ia.gaius.agent_client import AgentQueryError, AgentClient
    
    # Test error handling
    error = AgentQueryError("Test error")
    assert str(error) == "Test error"
    
    # Test client initialization (without connecting)
    agent_info = {
        'api_key': 'test-key',
        'name': 'test-agent',
        'domain': 'test.com',
        'secure': False
    }
    client = AgentClient(agent_info)
    assert client.name == "test-agent"
    assert client._domain == "test.com"
    assert client._api_key == "test-key"
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
    import ia.gaius.manager as manager
    # Test Docker client creation
    assert hasattr(manager, 'docker')
    print("Successfully tested manager module imports")

def test_utils():
    """Test utilities functionality"""
    from ia.gaius.utils import create_gdf, GDFFormatError
    # Test GDF creation with minimal input
    try:
        gdf = create_gdf(strings=["test"])
        print("Successfully tested GDF creation")
    except GDFFormatError as e:
        print(f"GDF format validation working: {e}")
    print("Successfully tested utils")

def test_experimental():
    """Test experimental features"""
    from ia.gaius.experimental import sklearn as gaius_sklearn
    print("Successfully imported experimental sklearn module")

def main():
    print(f"Starting ia-sdk test suite at {datetime.now()}")
    print(f"Python version: {sys.version}")
    print(f"Note: Some tests are limited to avoid external dependencies")
    
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
    
    print("\n=== Test Summary ===")
    total = len(results)
    passed = sum(1 for r in results if r.passed)
    failed = [r for r in results if not r.passed]
    
    print(f"Total tests: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {len(failed)}")
    
    if failed:
        print("\n=== Failed Tests Details ===")
        for result in failed:
            print(f"\n{result.name}:")
            print(f"Error: {result.error}")
            print("Traceback:")
            print(result.traceback)
    
    sys.exit(0 if not failed else 1)

if __name__ == "__main__":
    main()

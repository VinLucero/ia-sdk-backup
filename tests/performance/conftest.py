"""Fixtures for performance testing."""
import os
import time
import json
import psutil
import pytest
import logging
import tempfile
import platform
import statistics
import numpy as np
import contextlib
import csv
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Callable

from ia.gaius.agent_client import AgentClient
from ia.gaius.manager import AgentManager
from ia.gaius.utils import create_gdf

# Configuration from environment variables
ITERATIONS = int(os.getenv('PERF_TEST_ITERATIONS', '5'))
SIZE_MULTIPLIER = float(os.getenv('PERF_TEST_SIZE_MULTIPLIER', '1.0'))
SAVE_RESULTS = os.getenv('PERF_TEST_SAVE_RESULTS', 'true').lower() == 'true'
RESULTS_DIR = os.getenv('PERF_TEST_RESULTS_DIR', './results')

# Ensure results directory exists if saving is enabled
if SAVE_RESULTS:
    Path(RESULTS_DIR).mkdir(parents=True, exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(RESULTS_DIR, 'performance_tests.log') if SAVE_RESULTS else 'performance_tests.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('ia_performance_tests')


@pytest.fixture(scope="session")
def perf_agent_manager():
    """Provides a session-wide AgentManager for performance testing."""
    manager = AgentManager(local=True)
    manager.start_hoster()
    yield manager
    
    # Clean up all agents
    logger.info("Cleaning up all agents after performance tests")
    manager.kill_all_agents()


@pytest.fixture(scope="function")
def perf_agent(perf_agent_manager):
    """Provides a clean agent for performance testing."""
    agent_id = f"perf-agent-{os.urandom(4).hex()}"
    agent_name = agent_id
    
    logger.info(f"Starting performance test agent {agent_name}")
    agent_obj = perf_agent_manager.start_agent(
        genome_name="simple.genome",
        agent_id=agent_id,
        agent_name=agent_name
    )
    
    # Get the agent client and connect
    agent = agent_obj.get_agent_client()
    agent.connect()
    agent.set_ingress_nodes(["P1"])
    agent.set_query_nodes(["P1"])
    
    # Set optimal settings for performance testing
    agent.change_genes({
        "max_predictions": 20,  # Balanced value for testing
        "recall_threshold": 0.1  # Standard value
    })
    
    yield agent
    
    # Clean up
    logger.info(f"Cleaning up performance test agent {agent_name}")
    perf_agent_manager.delete_agent(agent_name)


@pytest.fixture(scope="session")
def system_info():
    """Provides system information for contextualizing performance results."""
    info = {
        "platform": platform.platform(),
        "processor": platform.processor(),
        "python_version": platform.python_version(),
        "cpu_count": os.cpu_count(),
        "memory_total": psutil.virtual_memory().total,
        "timestamp": datetime.now().isoformat()
    }
    return info


@contextlib.contextmanager
def measure_time():
    """Context manager to measure execution time."""
    start_time = time.time()
    yield
    end_time = time.time()
    elapsed = end_time - start_time
    return elapsed


@pytest.fixture
def time_execution():
    """Fixture to time execution of code blocks."""
    def _time_execution(func, *args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        return result, end_time - start_time
    
    return _time_execution


@pytest.fixture
def benchmark_operation():
    """Fixture to benchmark an operation over multiple iterations."""
    def _benchmark(operation_func, iterations=ITERATIONS, setup_func=None, cleanup_func=None, **kwargs):
        """
        Benchmark an operation over multiple iterations.
        
        Args:
            operation_func: Function to benchmark
            iterations: Number of iterations
            setup_func: Function to run before each iteration
            cleanup_func: Function to run after each iteration
            **kwargs: Arguments to pass to operation_func
            
        Returns:
            Dict containing timing statistics
        """
        times = []
        results = []
        
        for i in range(iterations):
            if setup_func:
                setup_func(iteration=i)
                
            start_time = time.time()
            result = operation_func(**kwargs)
            end_time = time.time()
            
            elapsed = end_time - start_time
            times.append(elapsed)
            results.append(result)
            
            if cleanup_func:
                cleanup_func(iteration=i)
        
        # Calculate statistics
        stats = {
            "mean": statistics.mean(times),
            "median": statistics.median(times),
            "stdev": statistics.stdev(times) if len(times) > 1 else 0,
            "min": min(times),
            "max": max(times),
            "p95": np.percentile(times, 95),
            "p99": np.percentile(times, 99),
            "iterations": iterations,
            "total_time": sum(times)
        }
        
        logger.info(f"Benchmark results: {stats}")
        return stats, results
    
    return _benchmark


@pytest.fixture
def save_benchmark_results(system_info):
    """Fixture to save benchmark results to CSV."""
    def _save_results(test_name, results, additional_params=None):
        """
        Save benchmark results to CSV.
        
        Args:
            test_name: Name of the test
            results: Dictionary containing benchmark statistics
            additional_params: Additional parameters to include in the results
        """
        if not SAVE_RESULTS:
            return
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(RESULTS_DIR, f"{test_name}_{timestamp}.csv")
        
        # Combine results with system info
        full_results = {
            "test_name": test_name,
            "timestamp": timestamp,
            **results,
            **system_info
        }
        
        if additional_params:
            full_results.update(additional_params)
        
        # Save to CSV
        with open(filename, 'w', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=full_results.keys())
            writer.writeheader()
            writer.writerow(full_results)
        
        logger.info(f"Saved benchmark results to {filename}")
        return filename
    
    return _save_results


@pytest.fixture
def generate_test_data():
    """Fixture to generate test data of varying sizes."""
    def _generate_data(data_type="strings", size=10, complexity=1):
        """
        Generate test data of the specified type and size.
        
        Args:
            data_type: Type of data to generate ("strings", "vectors", "mixed")
            size: Number of items to generate
            complexity: Complexity multiplier
            
        Returns:
            List of GDF formatted data
        """
        # Apply size multiplier
        size = int(size * SIZE_MULTIPLIER * complexity)
        
        if data_type == "strings":
            # Generate string-only GDFs
            return [create_gdf(strings=[f"item_{i}_{j}" for j in range(int(complexity))]) 
                    for i in range(size)]
        
        elif data_type == "vectors":
            # Generate vector-only GDFs
            return [create_gdf(vectors=[[float(j)/10 for j in range(int(10*complexity))]]) 
                    for i in range(size)]
        
        elif data_type == "mixed":
            # Generate mixed GDFs with strings, vectors, and emotives
            return [create_gdf(
                strings=[f"item_{i}_{j}" for j in range(int(complexity))],
                vectors=[[float(j)/10 for j in range(int(5*complexity))]],
                emotives={"importance": i/size, "urgency": (size-i)/size}
            ) for i in range(size)]
        
        else:
            raise ValueError(f"Unknown data type: {data_type}")
    
    return _generate_data


@pytest.fixture
def measure_memory():
    """Fixture to measure memory usage."""
    def _measure_memory(func, *args, **kwargs):
        """
        Measure memory usage of a function.
        
        Args:
            func: Function to measure
            *args, **kwargs: Arguments to pass to func
            
        Returns:
            Tuple of (func_result, memory_stats)
        """
        # Get baseline memory usage
        process = psutil.Process(os.getpid())
        mem_before = process.memory_info().rss
        
        # Run the function
        result = func(*args, **kwargs)
        
        # Get memory usage after
        mem_after = process.memory_info().rss
        mem_diff = mem_after - mem_before
        
        stats = {
            "memory_before": mem_before,
            "memory_after": mem_after, 
            "memory_diff": mem_diff
        }
        
        logger.info(f"Memory usage: {mem_diff / (1024*1024):.2f} MB")
        return result, stats
    
    return _measure_memory


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    """Add performance test summary at the end of the test run."""
    if not any(item.module.__name__.startswith('test_') for item in terminalreporter.stats.get('passed', [])):
        return
    
    perf_passed = [item for item in terminalreporter.stats.get('passed', []) 
                  if item.module.__name__.startswith('test_')]
    
    if not perf_passed:
        return
    
    terminalreporter.write_sep("=", "Performance Test Summary")
    terminalreporter.write_line(f"Ran {len(perf_passed)} performance tests")
    
    if SAVE_RESULTS:
        terminalreporter.write_line(f"Results saved to: {RESULTS_DIR}")


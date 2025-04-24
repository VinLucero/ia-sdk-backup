"""Latency performance tests for the ia-sdk package."""
import pytest
import logging
import time
import random
import statistics
import numpy as np
from typing import Dict, List, Any
from threading import Thread

logger = logging.getLogger('ia_performance_tests')


@pytest.mark.performance
def test_operation_response_time(perf_agent, time_execution, save_benchmark_results):
    """Test response time of key operations."""
    # Operations to measure
    operations = {
        "observe": lambda: perf_agent.observe({"strings": ["latency_test"], "vectors": [], "emotives": {}}),
        "learn": lambda: perf_agent.learn(),
        "get_predictions": lambda: perf_agent.get_predictions(),
        "get_wm": lambda: perf_agent.get_wm(),
        "clear_wm": lambda: perf_agent.clear_wm(),
        "show_status": lambda: perf_agent.show_status(),
        "get_kbs_as_json": lambda: perf_agent.get_kbs_as_json(obj=True)
    }
    
    results = {}
    iterations = 10  # Number of measurements per operation
    
    # First clear all memory to start fresh
    perf_agent.clear_all_memory()
    
    # Measure each operation
    for op_name, op_func in operations.items():
        logger.info(f"Measuring response time for operation: {op_name}")
        
        # Run multiple iterations
        times = []
        for i in range(iterations):
            # Prepare operation context if needed
            if op_name == "learn" or op_name == "get_predictions":
                perf_agent.clear_wm()
                perf_agent.observe({"strings": [f"latency_item_{i}"], "vectors": [], "emotives": {}})
            
            # Measure execution time
            _, execution_time = time_execution(op_func)
            times.append(execution_time)
            
            # Small delay between operations
            time.sleep(0.1)
        
        # Calculate statistics
        mean_time = statistics.mean(times)
        median_time = statistics.median(times)
        stdev_time = statistics.stdev(times) if len(times) > 1 else 0
        min_time = min(times)
        max_time = max(times)
        p95_time = np.percentile(times, 95)
        
        logger.info(f"{op_name} response time: mean={mean_time:.6f}s, median={median_time:.6f}s, p95={p95_time:.6f}s")
        
        # Store results
        results[op_name] = {
            "operation": op_name,
            "mean_time": mean_time,
            "median_time": median_time,
            "stdev_time": stdev_time,
            "min_time": min_time,
            "max_time": max_time,
            "p95_time": p95_time
        }
        
        # Save results to file
        save_benchmark_results(
            test_name=f"operation_latency_{op_name}",
            results=results[op_name]
        )
    
    return results


@pytest.mark.performance
def test_latency_under_load(perf_agent, time_execution, generate_test_data, save_benchmark_results):
    """Test operation latency under different loads."""
    # Load parameters to test
    load_sizes = [10, 50, 100, 200]
    
    results = {}
    
    # First clear all memory
    perf_agent.clear_all_memory()
    
    for load_size in load_sizes:
        # Generate data for the specified load
        data = generate_test_data(data_type="mixed", size=load_size)
        
        # First populate the KB with the load
        logger.info(f"Preparing agent with load of {load_size} items")
        for i, event in enumerate(data):
            perf_agent.observe(event)
            if i % 10 == 0:  # Learn periodically
                perf_agent.learn()
        
        # Final learn
        perf_agent.learn()
        
        # Test operations under load
        operations = {
            "observe": lambda: perf_agent.observe({"strings": ["load_test"], "vectors": [], "emotives": {}}),
            "get_predictions": lambda: perf_agent.get_predictions(),
            "clear_wm": lambda: perf_agent.clear_wm(),
            "show_status": lambda: perf_agent.show_status()
        }
        
        load_results = {}
        for op_name, op_func in operations.items():
            # Prepare for operation
            perf_agent.clear_wm()
            if op_name == "get_predictions":
                perf_agent.observe({"strings": ["trigger"], "vectors": [], "emotives": {}})
            
            # Measure the operation with 5 iterations
            times = []
            for i in range(5):
                _, execution_time = time_execution(op_func)
                times.append(execution_time)
                time.sleep(0.1)  # Small delay
            
            # Calculate statistics
            mean_time = statistics.mean(times)
            median_time = statistics.median(times)
            p95_time = np.percentile(times, 95) if len(times) >= 3 else max(times)
            
            logger.info(f"[Load {load_size}] {op_name} latency: mean={mean_time:.6f}s, median={median_time:.6f}s")
            
            # Store operation results
            load_results[op_name] = {
                "operation": op_name,
                "load_size": load_size,
                "mean_time": mean_time,
                "median_time": median_time,
                "p95_time": p95_time
            }
            
            # Save individual operation results
            save_benchmark_results(
                test_name=f"load_latency_{load_size}_{op_name}",
                results=load_results[op_name]
            )
        
        # Store all results for this load
        results[load_size] = load_results
        
        # Clear all memory before next load test
        perf_agent.clear_all_memory()
    
    return results


@pytest.mark.performance
def test_concurrent_operation_latency(perf_agent, time_execution, save_benchmark_results):
    """Test latency when performing concurrent operations."""
    # First clear all memory
    perf_agent.clear_all_memory()
    
    # Create some baseline data
    for i in range(20):
        perf_agent.observe({"strings": [f"concurrent_base_{i}"], "vectors": [], "emotives": {}})
    
    perf_agent.learn()
    
    # Prepare concurrent operation scenarios
    concurrent_scenarios = [
        {"name": "observe_while_learning", 
         "background": lambda: time.sleep(0.5) or perf_agent.learn(),
         "foreground": lambda: perf_agent.observe({"strings": ["concurrent_test"], "vectors": [], "emotives": {}})},
         
        {"name": "predict_while_learning",
         "background": lambda: time.sleep(0.5) or perf_agent.learn(),
         "foreground": lambda: perf_agent.get_predictions()},
        
        {"name": "status_while_observing",
         "background": lambda: [perf_agent.observe({"strings": [f"bg_{i}"], "vectors": [], "emotives": {}}) for i in range(10)],
         "foreground": lambda: perf_agent.show_status()},
         
        {"name": "kb_export_while_learning",
         "background": lambda: perf_agent.learn(),
         "foreground": lambda: perf_agent.get_kbs_as_json(obj=True)}
    ]
    
    results = {}
    
    for scenario in concurrent_scenarios:
        scenario_name = scenario["name"]
        logger.info(f"Testing concurrent scenario: {scenario_name}")
        
        # Reset state before test
        perf_agent.clear_wm()
        
        # Run the background operation in a thread
        background_thread = Thread(target=scenario["background"])
        background_thread.daemon = True
        
        # Measure foreground operation with background running
        times = []
        iterations = 3
        
        for i in range(iterations):
            # Start background operation
            background_thread = Thread(target=scenario["background"])
            background_thread.daemon = True
            background_thread.start()
            
            # Allow background to start
            time.sleep(0.1)
            
            # Measure foreground operation
            _, execution_time = time_execution(scenario["foreground"])
            times.append(execution_time)
            
            # Wait for background to finish
            background_thread.join(timeout=5.0)
            
            # Small delay between iterations
            time.sleep(0.5)
        
        # Calculate statistics
        mean_time = statistics.mean(times)
        median_time = statistics.median(times)
        max_time = max(times)
        
        logger.info(f"Concurrent {scenario_name} latency: mean={mean_time:.6f}s, median={median_time:.6f}s, max={max_time:.6f}s")
        
        # Also measure baseline (without concurrent operation)
        baseline_times = []
        for i in range(iterations):
            _, execution_time = time_execution(scenario["foreground"])
            baseline_times.append(execution_time)
        
        baseline_mean = statistics.mean(baseline_times)
        logger.info(f"Baseline (without concurrent operation): mean={baseline_mean:.6f}s")
        
        # Calculate impact
        latency_impact = (mean_time / baseline_mean) - 1.0  # Percentage increase
        
        # Store results
        results[scenario_name] = {
            "scenario": scenario_name,
            "concurrent_mean_time": mean_time,
            "concurrent_median_time": median_time,
            "concurrent_max_time": max_time,
            "baseline_mean_time": baseline_mean,
            "latency_impact_pct": latency_impact * 100  # Convert to percentage
        }
        
        # Save results
        save_benchmark_results(
            test_name=f"concurrent_latency_{scenario_name}",
            results=results[scenario_name]
        )
    
    return results

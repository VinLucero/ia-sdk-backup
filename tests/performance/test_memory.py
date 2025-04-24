"""Memory usage performance tests for the ia-sdk package."""
import pytest
import logging
import time
import gc
import psutil
import os
from typing import Dict, List, Any

logger = logging.getLogger('ia_performance_tests')


@pytest.mark.performance
def test_memory_usage_patterns(perf_agent, measure_memory, generate_test_data, save_benchmark_results):
    """Test memory usage patterns for different operations."""
    # Operations to measure
    operations = {
        "observe_single": lambda agent: agent.observe({"strings": ["memory_test"], "vectors": [], "emotives": {}}),
        "observe_batch": lambda agent: [agent.observe(event) for event in generate_test_data(data_type="strings", size=50)],
        "learn": lambda agent: agent.learn(),
        "get_kb": lambda agent: agent.get_kbs_as_json(obj=True),
        "clear_wm": lambda agent: agent.clear_wm(),
        "clear_all": lambda agent: agent.clear_all_memory()
    }
    
    results = {}
    
    # Force garbage collection before test
    gc.collect()
    
    # Get process to monitor memory
    process = psutil.Process(os.getpid())
    base_memory = process.memory_info().rss
    logger.info(f"Base memory usage: {base_memory / (1024*1024):.2f} MB")
    
    for op_name, op_func in operations.items():
        logger.info(f"Measuring memory usage for operation: {op_name}")
        
        # Reset state before test
        perf_agent.clear_all_memory()
        time.sleep(1)  # Allow memory to stabilize
        gc.collect()
        
        # Measure memory usage
        _, memory_stats = measure_memory(lambda: op_func(perf_agent))
        
        # Calculate relative change
        memory_diff_mb = memory_stats["memory_diff"] / (1024 * 1024)
        memory_pct = (memory_stats["memory_diff"] / memory_stats["memory_before"]) * 100
        
        logger.info(f"{op_name} memory impact: {memory_diff_mb:.2f} MB ({memory_pct:.2f}%)")
        
        # Store results
        results[op_name] = {
            "operation": op_name,
            "memory_before_mb": memory_stats["memory_before"] / (1024 * 1024),
            "memory_after_mb": memory_stats["memory_after"] / (1024 * 1024),
            "memory_diff_mb": memory_diff_mb,
            "memory_change_pct": memory_pct
        }
        
        # Save results
        save_benchmark_results(
            test_name=f"memory_usage_{op_name}",
            results=results[op_name]
        )
    
    return results


@pytest.mark.performance
def test_memory_leak_detection(perf_agent, measure_memory, generate_test_data, save_benchmark_results):
    """Test for potential memory leaks during repeated operations."""
    # Number of iterations for each test
    iterations = 20
    
    # Operations to test repeatedly
    operations = {
        "observe_clear_cycle": lambda agent: (
            agent.observe({"strings": ["leak_test"], "vectors": [], "emotives": {}}),
            agent.clear_wm()
        ),
        "observe_learn_cycle": lambda agent: (
            agent.observe({"strings": ["leak_test"], "vectors": [], "emotives": {}}),
            agent.learn()
        ),
        "predict_cycle": lambda agent: (
            agent.observe({"strings": ["predict_test"], "vectors": [], "emotives": {}}),
            agent.get_predictions()
        )
    }
    
    results = {}
    
    for op_name, op_func in operations.items():
        logger.info(f"Testing for memory leaks in operation: {op_name}")
        
        # Reset state before test
        perf_agent.clear_all_memory()
        time.sleep(1)  # Allow memory to stabilize
        gc.collect()
        
        # Get process to monitor memory
        process = psutil.Process(os.getpid())
        memory_measurements = []
        
        # Perform operation repeatedly
        for i in range(iterations):
            # Record memory before
            memory_before = process.memory_info().rss
            
            # Perform operation
            op_func(perf_agent)
            
            # Force garbage collection
            gc.collect()
            
            # Record memory after
            memory_after = process.memory_info().rss
            memory_delta = memory_after - memory_before
            memory_measurements.append((i, memory_before, memory_after, memory_delta))
            
            # Brief pause to stabilize
            time.sleep(0.1)
        
        # Analyze memory growth pattern
        iteration_numbers = [m[0] for m in memory_measurements]
        memory_deltas = [m[3] for m in memory_measurements]
        
        # Calculate metrics
        total_memory_change = memory_measurements[-1][2] - memory_measurements[0][1]
        avg_memory_change = total_memory_change / iterations
        memory_growth_rate = total_memory_change / iterations if iterations > 0 else 0
        
        # Calculate slope of memory usage (for leak detection)
        if len(memory_measurements) > 2:
            # Use simple linear regression to estimate slope
            mean_x = sum(iteration_numbers) / len(iteration_numbers)
            mean_y = sum(memory_deltas) / len(memory_deltas)
            numerator = sum((x - mean_x) * (y - mean_y) for x, y in zip(iteration_numbers, memory_deltas))
            denominator = sum((x - mean_x) ** 2 for x in iteration_numbers)
            slope = numerator / denominator if denominator != 0 else 0
        else:
            slope = 0
        
        # Log results
        logger.info(f"{op_name} memory growth: {total_memory_change / (1024*1024):.2f} MB over {iterations} iterations")
        logger.info(f"{op_name} memory growth rate: {memory_growth_rate / (1024*1024):.4f} MB/iteration")
        logger.info(f"{op_name} memory growth slope: {slope / (1024*1024):.6f} MB/iteration (stable should be near zero)")
        
        # Potential leak detection
        leak_threshold = 1024 * 50  # 50 KB per iteration is suspicious for a leak
        leak_suspected = slope > leak_threshold
        
        if leak_suspected:
            logger.warning(f"Potential memory leak detected in {op_name}: growth rate {slope / (1024*1024):.2f} MB/iteration")
        else:
            logger.info(f"No significant memory leak detected in {op_name}")
        
        # Store results
        results[op_name] = {
            "operation": op_name,
            "iterations": iterations,
            "total_memory_change_mb": total_memory_change / (1024*1024),
            "memory_growth_rate_mb": memory_growth_rate / (1024*1024),
            "memory_growth_slope_mb": slope / (1024*1024),
            "leak_suspected": leak_suspected
        }
        
        # Save results
        save_benchmark_results(
            test_name=f"memory_leak_{op_name}",
            results=results[op_name]
        )
        
        # Reset agent state
        perf_agent.clear_all_memory()
        gc.collect()
    
    return results


@pytest.mark.performance
def test_resource_cleanup_efficiency(perf_agent, measure_memory, generate_test_data, save_benchmark_results):
    """Test efficiency of resource cleanup operations."""
    # Operations to test cleanup efficiency
    operations = {
        "clear_wm": lambda agent: agent.clear_wm(),
        "clear_all_memory": lambda agent: agent.clear_all_memory()
    }
    
    # Data load sizes to test
    load_sizes = [10, 50, 100, 200]
    
    results = {}
    
    for load_size in load_sizes:
        load_key = f"load_{load_size}"
        load_results = {}
        
        for op_name, op_func in operations.items():
            # Prepare test data
            test_data = generate_test_data(data_type="mixed", size=load_size)
            
            # Reset agent state
            perf_agent.clear_all_memory()
            gc.collect()
            
            # Monitor memory before loading data
            process = psutil.Process(os.getpid())
            memory_before_load = process.memory_info().rss
            
            # Load data into agent
            logger.info(f"Loading {load_size} items for {op_name} cleanup test")
            for event in test_data:
                perf_agent.observe(event)
            
            # Learn to create more resources to clean
            perf_agent.learn()
            
            # Monitor memory after loading
            memory_after_load = process.memory_info().rss
            load_delta = memory_after_load - memory_before_load
            
            # Measure the cleanup operation
            _, memory_stats = measure_memory(lambda: op_func(perf_agent))
            
            # Calculate cleanup efficiency
            memory_freed = memory_stats["memory_diff"]  # Negative value means memory was freed
            cleanup_efficiency = abs(memory_freed) / load_delta if load_delta > 0 else 0
            
            logger.info(f"{op_name} cleanup with {load_size} items:")
            logger.info(f"  Loaded: {load_delta / (1024*1024):.2f} MB")
            logger.info(f"  Freed: {abs(memory_freed) / (1024*1024):.2f} MB")
            logger.info(f"  Efficiency: {cleanup_efficiency:.2%}")
            
            # Store results
            load_results[op_name] = {
                "operation": op_name,
                "load_size": load_size,
                "memory_loaded_mb": load_delta / (1024*1024),
                "memory_freed_mb": abs(memory_freed) / (1024*1024),
                "cleanup_efficiency": cleanup_efficiency
            }
            
            # Save results
            save_benchmark_results(
                test_name=f"cleanup_efficiency_{op_name}_{load_size}",
                results=load_results[op_name]
            )
            
            # Reset agent state before next test
            perf_agent.clear_all_memory()
            gc.collect()
        
        results[load_key] = load_results
    
    return results

"""Scalability performance tests for the ia-sdk package."""
import pytest
import logging
import time
import statistics
import numpy as np
import concurrent.futures
from typing import Dict, List, Any
from threading import Thread

logger = logging.getLogger('ia_performance_tests')


@pytest.mark.performance
def test_data_volume_scaling(perf_agent, benchmark_operation, generate_test_data, save_benchmark_results):
    """Test how performance scales with increasing data volume."""
    # Volume parameters to test (events per batch)
    volumes = [10, 50, 100, 250, 500]
    
    results = {}
    
    for volume in volumes:
        logger.info(f"Testing data volume scaling with {volume} events")
        
        # Generate test data
        test_data = generate_test_data(data_type="strings", size=volume)
        
        # Reset agent state
        perf_agent.clear_all_memory()
        
        # Define operation to benchmark - observing all events
        def observe_operation(agent=None, data=None):
            start_time = time.time()
            for event in data:
                agent.observe(event)
            end_time = time.time()
            return end_time - start_time
        
        # Run the benchmark
        stats, operation_times = benchmark_operation(
            operation_func=observe_operation,
            agent=perf_agent,
            data=test_data,
            iterations=3  # Fewer iterations for large data volumes
        )
        
        # Calculate throughput
        events_per_second = volume / stats["mean"]
        
        logger.info(f"Data volume {volume}: {events_per_second:.2f} events/second")
        logger.info(f"Mean processing time: {stats['mean']:.4f}s")
        
        # Now test learning performance
        def learn_operation(agent=None):
            start_time = time.time()
            agent.learn()
            end_time = time.time()
            return end_time - start_time
        
        # Run the learn benchmark
        learn_stats, learn_times = benchmark_operation(
            operation_func=learn_operation,
            agent=perf_agent,
            iterations=3
        )
        
        logger.info(f"Learning after {volume} events: {learn_stats['mean']:.4f}s")
        
        # Store results
        results[volume] = {
            "volume": volume,
            "events_per_second": events_per_second,
            "observe_mean_time": stats["mean"],
            "observe_max_time": stats["max"],
            "learn_mean_time": learn_stats["mean"],
            "learn_max_time": learn_stats["max"],
            "processing_efficiency": events_per_second / volume  # Lower is better
        }
        
        # Save results
        save_benchmark_results(
            test_name=f"data_volume_scaling_{volume}",
            results=results[volume]
        )
    
    # Calculate scaling factor
    smallest_volume = min(volumes)
    largest_volume = max(volumes)
    
    scaling_factor = (results[largest_volume]["observe_mean_time"] / results[smallest_volume]["observe_mean_time"]) / (largest_volume / smallest_volume)
    logger.info(f"Scaling factor: {scaling_factor:.4f} (1.0 is linear scaling, <1.0 is better than linear)")
    
    return results


@pytest.mark.performance
def test_operation_complexity_scaling(perf_agent, benchmark_operation, generate_test_data, save_benchmark_results):
    """Test how performance scales with increasing operation complexity."""
    # Complexity parameters (higher = more complex data)
    complexities = [1, 2, 5, 10]
    
    # Fixed data size
    data_size = 50
    
    results = {}
    
    for complexity in complexities:
        logger.info(f"Testing operation complexity scaling with complexity={complexity}")
        
        # Generate complex test data with strings, vectors, and emotives
        test_data = generate_test_data(data_type="mixed", size=data_size, complexity=complexity)
        
        # Reset agent state
        perf_agent.clear_all_memory()
        
        # Define operation to benchmark - observing all events
        def observe_operation(agent=None, data=None):
            for event in data:
                agent.observe(event)
            return len(data)
        
        # Run the benchmark
        stats, _ = benchmark_operation(
            operation_func=observe_operation,
            agent=perf_agent,
            data=test_data
        )
        
        # Define learn operation to benchmark
        def learn_operation(agent=None):
            return agent.learn()
        
        # Run the learn benchmark
        learn_stats, _ = benchmark_operation(
            operation_func=learn_operation,
            agent=perf_agent
        )
        
        # Define prediction operation
        def predict_operation(agent=None, data=None):
            agent.clear_wm()
            agent.observe(data[0])  # Use first event as trigger
            return agent.get_predictions()
        
        # Run the prediction benchmark
        predict_stats, _ = benchmark_operation(
            operation_func=predict_operation,
            agent=perf_agent,
            data=test_data
        )
        
        logger.info(f"Complexity {complexity}:")
        logger.info(f"  Observe time: {stats['mean']:.4f}s")
        logger.info(f"  Learn time: {learn_stats['mean']:.4f}s")
        logger.info(f"  Predict time: {predict_stats['mean']:.4f}s")
        
        # Store results
        results[complexity] = {
            "complexity": complexity,
            "observe_mean_time": stats["mean"],
            "learn_mean_time": learn_stats["mean"],
            "predict_mean_time": predict_stats["mean"],
            "observe_max_time": stats["max"],
            "learn_max_time": learn_stats["max"],
            "predict_max_time": predict_stats["max"]
        }
        
        # Save results
        save_benchmark_results(
            test_name=f"complexity_scaling_{complexity}",
            results=results[complexity]
        )
    
    # Calculate complexity scaling factors
    base_complexity = min(complexities)
    max_complexity = max(complexities)
    
    observe_scaling = (results[max_complexity]["observe_mean_time"] / results[base_complexity]["observe_mean_time"]) / (max_complexity / base_complexity)
    learn_scaling = (results[max_complexity]["learn_mean_time"] / results[base_complexity]["learn_mean_time"]) / (max_complexity / base_complexity)
    
    logger.info(f"Observe complexity scaling factor: {observe_scaling:.4f}")
    logger.info(f"Learn complexity scaling factor: {learn_scaling:.4f}")
    
    return results


@pytest.mark.performance
def test_resource_utilization_under_scale(perf_agent, measure_memory, generate_test_data, save_benchmark_results):
    """Test resource utilization as data scale increases."""
    # Scale parameters
    scales = [10, 50, 100, 200]
    
    results = {}
    
    for scale in scales:
        logger.info(f"Testing resource utilization with scale={scale}")
        
        # Reset agent state
        perf_agent.clear_all_memory()
        
        # Generate test data
        test_data = generate_test_data(data_type="mixed", size=scale)
        
        # Measure memory usage during data loading
        def load_data(agent=None, data=None):
            for event in data:
                agent.observe(event)
            agent.learn()  # Create models as well
            return len(data)
        
        # Measure memory and CPU during load
        process = psutil.Process(os.getpid())
        
        # Baseline measurements
        memory_before = process.memory_info().rss
        cpu_percent_before = process.cpu_percent()
        
        # Reset CPU monitoring
        process.cpu_percent()  # First call just resets monitoring
        time.sleep(0.1)  # Wait a bit for CPU monitoring to initialize
        
        # Run load operation and measure
        start_time = time.time()
        load_data(perf_agent, test_data)
        end_time = time.time()
        
        # After measurements
        memory_after = process.memory_info().rss
        cpu_percent_after = process.cpu_percent()
        
        # Calculate metrics
        memory_usage_mb = (memory_after - memory_before) / (1024 * 1024)
        memory_per_event_kb = (memory_after - memory_before) / scale / 1024
        processing_time = end_time - start_time
        events_per_second = scale / processing_time
        
        logger.info(f"Scale {scale}:")
        logger.info(f"  Memory usage: {memory_usage_mb:.2f} MB")
        logger.info(f"  Memory per event: {memory_per_event_kb:.2f} KB")
        logger.info(f"  Processing time: {processing_time:.4f}s")
        logger.info(f"  CPU percentage: {cpu_percent_after:.1f}%")
        
        # Now measure query performance at this scale
        def query_operation(agent=None):
            agent.clear_wm()
            agent.observe(test_data[0])  # Use first event as trigger
            return agent.get_predictions()
        
        # Run a few queries and measure
        query_times = []
        cpu_percentages = []
        
        for i in range(5):
            # Reset CPU monitoring
            process.cpu_percent()
            
            # Run query
            start_time = time.time()
            query_operation(perf_agent)
            end_time = time.time()
            
            query_times.append(end_time - start_time)
            cpu_percentages.append(process.cpu_percent())
        
        # Calculate query metrics
        avg_query_time = sum(query_times) / len(query_times)
        avg_cpu_percent = sum(cpu_percentages) / len(cpu_percentages)
        
        logger.info(f"  Average query time: {avg_query_time:.4f}s")
        logger.info(f"  Average query CPU: {avg_cpu_percent:.1f}%")
        
        # Store results
        results[scale] = {
            "scale": scale,
            "memory_usage_mb": memory_usage_mb,
            "memory_per_event_kb": memory_per_event_kb,
            "loading_time": processing_time,
            "events_per_second": events_per_second,
            "cpu_percent": cpu_percent_after,
            "avg_query_time": avg_query_time,
            "avg_query_cpu": avg_cpu_percent
        }
        
        # Save results
        save_benchmark_results(
            test_name=f"resource_utilization_{scale}",
            results=results[scale]
        )
    
    # Calculate scaling factors
    smallest_scale = min(scales)
    largest_scale = max(scales)
    
    memory_scaling = (results[largest_scale]["memory_usage_mb"] / results[smallest_scale]["memory_usage_mb"]) / (largest_scale / smallest_scale)
    time_scaling = (results[largest_scale]["loading_time"] / results[smallest_scale]["loading_time"]) / (largest_scale / smallest_scale)
    query_scaling = (results[largest_scale]["avg_query_time"] / results[smallest_scale]["avg_query_time"]) / (largest_scale / smallest_scale)
    
    logger.info(f"Memory usage scaling factor: {memory_scaling:.4f}")
    logger.info(f"Processing time scaling factor: {time_scaling:.4f}")
    logger.info(f"Query time scaling factor: {query_scaling:.4f}")
    
    return results


@pytest.mark.performance
def test_concurrent_operation_scaling(perf_agent_manager, time_execution, generate_test_data, save_benchmark_results):
    """Test how performance scales with concurrent operations."""
    # Concurrency levels to test
    concurrency_levels = [1, 2, 4, 8]
    
    # Operations to test concurrently
    operations = {
        "observe": lambda agent, data: agent.observe(data),
        "learn": lambda agent, data: agent.learn(),
        "predict": lambda agent, data: agent.get_predictions()
    }
    
    results = {}
    
    # Create a set of agents for concurrency testing
    agents = []
    test_data = generate_test_data(data_type="strings", size=10)
    
    # Pre-populate all agents with same baseline data
    baseline_data = generate_test_data(data_type="strings", size=20)
    
    for op_name, op_func in operations.items():
        logger.info(f"Testing concurrent scaling for operation: {op_name}")
        
        operation_results = {}
        
        for concurrency in concurrency_levels:
            logger.info(f"Testing with concurrency level: {concurrency}")
            
            # Create or ensure we have enough agents
            while len(agents) < concurrency:
                agent_id = f"perf-concurrent-{len(agents)}"
                agent_obj = perf_agent_manager.start_agent(
                    genome_name="simple.genome",
                    agent_id=agent_id,
                    agent_name=agent_id
                )
                agent = agent_obj.get_agent_client()
                agent.connect()
                agent.set_ingress_nodes(["P1"])
                agent.set_query_nodes(["P1"])
                
                # Pre-populate with common data
                for event in baseline_data:
                    agent.observe(event)
                agent.learn()
                
                agents.append(agent)
            
            # Prepare the concurrent execution
            active_agents = agents[:concurrency]
            execution_times = []
            
            # Run concurrent operations using ThreadPoolExecutor
            with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
                # Start operation timing
                start_time = time.time()
                
                # Submit all operations to executor
                futures = []
                for agent in active_agents:
                    if op_name == "observe":
                        futures.append(executor.submit(op_func, agent, test_data[0]))
                    elif op_name == "predict":
                        # Ensure working memory is set up for prediction
                        agent.clear_wm()
                        agent.observe(test_data[0])
                        futures.append(executor.submit(op_func, agent, None))
                    else:
                        futures.append(executor.submit(op_func, agent, None))
                
                # Wait for all operations to complete
                for future in concurrent.futures.as_completed(futures):
                    try:
                        future.result()
                    except Exception as exc:
                        logger.error(f"Operation generated an exception: {exc}")
                
                # End operation timing
                end_time = time.time()
                total_time = end_time - start_time
                execution_times.append(total_time)
            
            # Run multiple iterations to get better statistics
            for i in range(2):  # 2 more iterations
                with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
                    # Start operation timing
                    start_time = time.time()
                    
                    # Submit all operations to executor
                    futures = []
                    for agent in active_agents:
                        if op_name == "observe":
                            futures.append(executor.submit(op_func, agent, test_data[0]))
                        elif op_name == "predict":
                            # Ensure working memory is set up for prediction
                            agent.clear_wm()
                            agent.observe(test_data[0])
                            futures.append(executor.submit(op_func, agent, None))
                        else:
                            futures.append(executor.submit(op_func, agent, None))
                    
                    # Wait for all operations to complete
                    for future in concurrent.futures.as_completed(futures):
                        try:
                            future.result()
                        except Exception as exc:
                            logger.error(f"Operation generated an exception: {exc}")
                    
                    # End operation timing
                    end_time = time.time()
                    total_time = end_time - start_time
                    execution_times.append(total_time)
            
            # Calculate statistics
            avg_execution_time = sum(execution_times) / len(execution_times)
            max_execution_time = max(execution_times)
            throughput = concurrency / avg_execution_time  # Operations per second
            
            logger.info(f"Concurrency {concurrency} for {op_name}:")
            logger.info(f"  Average execution time: {avg_execution_time:.4f}s")
            logger.info(f"  Throughput: {throughput:.2f} ops/sec")
            
            # Calculate efficiency (ideal vs. actual)
            if concurrency == 1:
                # Baseline for single operation
                baseline_time = avg_execution_time
                efficiency = 1.0
            else:
                # Ideal: linear scaling (N operations should take the same time as 1 operation)
                # Actual: Measured time for N concurrent operations
                # Efficiency = ideal / actual = baseline / (avg_time * concurrency/1)
                efficiency = baseline_time / (avg_execution_time * concurrency)
            
            logger.info(f"  Parallelization efficiency: {efficiency:.2%}")
            
            # Store results
            operation_results[concurrency] = {
                "operation": op_name,
                "concurrency": concurrency,
                "avg_execution_time": avg_execution_time,
                "max_execution_time": max_execution_time,
                "throughput": throughput,
                "efficiency": efficiency
            }
            
            # Save results
            save_benchmark_results(
                test_name=f"concurrent_scaling_{op_name}_{concurrency}",
                results=operation_results[concurrency]
            )
            
            # Reset agents for next test
            for agent in active_agents:
                agent.clear_wm()
        
        results[op_name] = operation_results
    
    # Clean up agents
    for i, agent in enumerate(agents):
        perf_agent_manager.delete_agent(f"perf-concurrent-{i}")
    
    return results


import psutil
import os

"""Throughput performance tests for the ia-sdk package."""
import pytest
import logging
import time
from typing import Dict, List, Any

logger = logging.getLogger('ia_performance_tests')


@pytest.mark.performance
def test_observation_throughput(perf_agent, benchmark_operation, generate_test_data, save_benchmark_results):
    """Test data observation throughput."""
    # Test parameters
    batch_sizes = [10, 50, 100, 500]
    
    results = {}
    
    for batch_size in batch_sizes:
        # Generate test data
        test_data = generate_test_data(data_type="strings", size=batch_size)
        
        # Define the operation to benchmark
        def observation_operation(agent=None, data=None):
            agent.clear_wm()
            for event in data:
                agent.observe(event)
            return batch_size
        
        # Run the benchmark
        stats, _ = benchmark_operation(
            operation_func=observation_operation,
            agent=perf_agent,
            data=test_data
        )
        
        # Calculate events per second
        events_per_second = batch_size / stats["mean"]
        logger.info(f"Observation throughput for batch size {batch_size}: {events_per_second:.2f} events/second")
        
        # Save results
        results[batch_size] = {
            "batch_size": batch_size,
            "events_per_second": events_per_second,
            **stats
        }
        
        # Save to file
        save_benchmark_results(
            test_name=f"observation_throughput_{batch_size}",
            results=results[batch_size]
        )
    
    # Return combined results
    return results


@pytest.mark.performance
def test_learning_throughput(perf_agent, benchmark_operation, generate_test_data, save_benchmark_results):
    """Test learning throughput performance."""
    # Test parameters
    sequence_counts = [5, 10, 20, 50]
    sequence_length = 3  # Each sequence has 3 events (2 inputs + 1 classification)
    
    results = {}
    
    for sequence_count in sequence_counts:
        # Create sequences of the pattern: event1, event2, classification
        sequences = []
        for i in range(sequence_count):
            sequence = [
                generate_test_data(data_type="strings", size=1, complexity=1)[0],
                generate_test_data(data_type="strings", size=1, complexity=1)[0],
                generate_test_data(data_type="strings", size=1, complexity=0.5)[0]  # Classification event (simpler)
            ]
            sequences.append(sequence)
        
        # Define setup function - populate working memory with sequences
        def setup_learning(iteration=0):
            perf_agent.clear_all_memory()
            perf_agent.stop_predicting()
        
        # Define the operation to benchmark
        def learning_operation(agent=None, data=None):
            # Observe all sequences and learn from each
            model_count = 0
            for sequence in data:
                agent.clear_wm()
                for event in sequence:
                    agent.observe(event)
                agent.learn()
                model_count += 1
            return model_count
        
        # Run the benchmark
        stats, _ = benchmark_operation(
            operation_func=learning_operation,
            setup_func=setup_learning,
            agent=perf_agent,
            data=sequences
        )
        
        # Calculate models per second
        models_per_second = sequence_count / stats["mean"]
        logger.info(f"Learning throughput for {sequence_count} sequences: {models_per_second:.2f} models/second")
        
        # Save results
        results[sequence_count] = {
            "sequence_count": sequence_count,
            "models_per_second": models_per_second,
            **stats
        }
        
        # Save to file
        save_benchmark_results(
            test_name=f"learning_throughput_{sequence_count}",
            results=results[sequence_count]
        )
    
    return results


@pytest.mark.performance
def test_prediction_throughput(perf_agent, benchmark_operation, generate_test_data, save_benchmark_results):
    """Test prediction throughput performance."""
    # Test parameters
    test_sizes = [10, 20, 50, 100]
    
    results = {}
    
    # Set up the agent with some learned patterns first
    perf_agent.clear_all_memory()
    
    # Create and observe some training sequences
    for i in range(10):  # Train 10 different patterns
        perf_agent.clear_wm()
        perf_agent.observe(generate_test_data(data_type="strings", size=1, complexity=1)[0])
        perf_agent.observe(generate_test_data(data_type="strings", size=1, complexity=1)[0])
        perf_agent.observe(generate_test_data(data_type="strings", size=1, complexity=0.5)[0])
        perf_agent.learn()
    
    for test_size in test_sizes:
        # Generate test events
        test_events = generate_test_data(data_type="strings", size=test_size)
        
        # Define setup function
        def setup_prediction(iteration=0):
            perf_agent.clear_wm()
            perf_agent.start_predicting()
        
        # Define the operation to benchmark
        def prediction_operation(agent=None, data=None):
            predictions_count = 0
            for event in data:
                agent.observe(event)
                predictions = agent.get_predictions()
                if isinstance(predictions, dict) and 'P1' in predictions:
                    predictions_count += len(predictions['P1'])
                agent.clear_wm()  # Clear WM between predictions
            return predictions_count
        
        # Run the benchmark
        stats, results_list = benchmark_operation(
            operation_func=prediction_operation,
            setup_func=setup_prediction,
            agent=perf_agent,
            data=test_events
        )
        
        # Calculate predictions per second
        total_predictions = sum(results_list)
        predictions_per_second = total_predictions / stats["total_time"]
        events_per_second = test_size / stats["mean"]
        
        logger.info(f"Prediction throughput for {test_size} events: {events_per_second:.2f} events/second")
        logger.info(f"Prediction throughput: {predictions_per_second:.2f} predictions/second")
        
        # Save results
        results[test_size] = {
            "test_size": test_size,
            "events_per_second": events_per_second,
            "predictions_per_second": predictions_per_second,
            "total_predictions": total_predictions,
            **stats
        }
        
        # Save to file
        save_benchmark_results(
            test_name=f"prediction_throughput_{test_size}",
            results=results[test_size]
        )
    
    return results


@pytest.mark.performance
def test_batch_processing_performance(perf_agent, benchmark_operation, generate_test_data, save_benchmark_results):
    """Test batch processing performance under different loads."""
    # Test parameters - combinations of batch size and complexity
    test_configs = [
        {"batch_size": 10, "complexity": 1},
        {"batch_size": 10, "complexity": 5},
        {"batch_size": 50, "complexity": 1},
        {"batch_size": 50, "complexity": 5},
        {"batch_size": 100, "complexity": 1}
    ]
    
    results = {}
    
    for config in test_configs:
        batch_size = config["batch_size"]
        complexity = config["complexity"]
        
        # Generate complex mixed data
        test_data = generate_test_data(
            data_type="mixed", 
            size=batch_size,
            complexity=complexity
        )
        
        # Define setup function
        def setup_batch(iteration=0):
            perf_agent.clear_all_memory()
        
        # Define the operation to benchmark - full cycle of observe -> learn -> predict
        def batch_operation(agent=None, data=None):
            # First observe all events
            for event in data:
                agent.observe(event)
            
            # Learn from the batch
            agent.learn()
            
            # Get predictions
            agent.clear_wm()  # Clear working memory but keep KB
            agent.start_predicting()
            
            # Observe one test event and get predictions
            test_event = data[0]  # Use first event as test
            agent.observe(test_event)
            predictions = agent.get_predictions()
            
            # Return batch size as result
            return batch_size
        
        # Run the benchmark
        stats, _ = benchmark_operation(
            operation_func=batch_operation,
            setup_func=setup_batch,
            agent=perf_agent,
            data=test_data
        )
        
        # Calculate processing rate
        events_per_second = batch_size / stats["mean"]
        config_key = f"batch_{batch_size}_complexity_{complexity}"
        
        logger.info(f"Batch processing rate for {batch_size} events (complexity {complexity}): {events_per_second:.2f} events/second")
        
        # Save results
        results[config_key] = {
            "batch_size": batch_size,
            "complexity": complexity,
            "events_per_second": events_per_second,
            **stats
        }
        
        # Save to file
        save_benchmark_results(
            test_name=f"batch_processing_{config_key}",
            results=results[config_key]
        )
    
    return results

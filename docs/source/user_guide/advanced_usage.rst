Advanced Usage
=============

.. meta::
   :description: Advanced techniques and patterns for using the ia-sdk
   :keywords: advanced, techniques, patterns, gaius, sdk, multi-agent, knowledge-base

This page covers advanced usage patterns and techniques for the ia-sdk.

Multi-Agent Systems
-----------------

**Creating Agent Networks**

You can connect multiple agents together to form more complex cognitive systems:

.. code-block:: python

    from ia.gaius.agent_client import AgentClient
    from ia.gaius.manager import AgentManager

    # Create a manager for handling multiple agents
    manager = AgentManager()
    
    # Start multiple agents
    agent1 = manager.start_agent(
        genome_name="simple.genome",
        agent_name="perception"
    ).get_agent_client()
    
    agent2 = manager.start_agent(
        genome_name="simple.genome",
        agent_name="reasoning"
    ).get_agent_client()
    
    # Connect to both agents
    agent1.connect()
    agent2.connect()
    
    # Configure nodes
    agent1.set_ingress_nodes(["P1"])
    agent1.set_query_nodes(["P1"])
    agent2.set_ingress_nodes(["P1"])
    agent2.set_query_nodes(["P1"])

**Knowledge Transfer Between Agents**

Share knowledge between agents by exporting and importing knowledge bases:

.. code-block:: python

    # Export knowledge from source agent
    kb_data = agent1.get_kbs_as_json(obj=True)
    
    # Import to target agent
    agent2.load_kbs_from_json(obj=kb_data)

Knowledge Base Operations
----------------------

**Advanced KB Management**

The ia-sdk provides sophisticated KB manipulation capabilities:

.. code-block:: python

    # Find specific models
    models = agent.get_models_with_symbols(["category|electronics"])
    
    # Investigate a specific model
    model_details = agent.investigate("MODEL|a1b2c3d4")
    
    # Remove symbols from the system
    agent.remove_symbols_from_system(["obsolete_data"])
    
    # Remove patterns using regex
    agent.remove_patterns_from_system(["OLD_FORMAT\|.*"])

**Knowledge Base Analysis**

Analyze and visualize knowledge bases:

.. code-block:: python

    from ia.gaius.utils import visualize_kb
    from ia.gaius.kb_ops import list_symbols, get_models_containing_symbol
    
    # Get and visualize a knowledge base
    kb = agent.get_kbs_as_json(obj=True)
    visualize_kb(kb)
    
    # Analyze symbols and models
    symbols = list_symbols(agent)
    models_with_symbol = get_models_containing_symbol(agent, "important_concept")

Custom Integration Patterns
------------------------

**Asynchronous Processing**

Integrate with asynchronous applications:

.. code-block:: python

    import asyncio
    from concurrent.futures import ThreadPoolExecutor
    
    async def process_data_async(agent, data_batches):
        # Create thread pool for agent operations
        with ThreadPoolExecutor() as executor:
            # Process batches in parallel
            loop = asyncio.get_event_loop()
            futures = [
                loop.run_in_executor(
                    executor,
                    lambda d: agent.observe(d),
                    batch
                )
                for batch in data_batches
            ]
            
            # Wait for all observations to complete
            await asyncio.gather(*futures)
            
            # Learn from the observations
            return await loop.run_in_executor(
                executor,
                agent.learn
            )

**Custom Callbacks and Middleware**

Implement custom processing pipelines:

.. code-block:: python

    def preprocess_data(data):
        # Normalize strings
        if "strings" in data:
            data["strings"] = [s.lower() for s in data["strings"]]
        return data
        
    def postprocess_predictions(predictions):
        # Filter and enhance predictions
        if not predictions or 'P1' not in predictions:
            return []
            
        # Extract and sort by confidence
        sorted_preds = sorted(
            predictions['P1'], 
            key=lambda p: len(p._prediction.get('matches', [])),
            reverse=True
        )
        return sorted_preds[:5]  # Return top 5
        
    # Use in pipeline
    processed_data = preprocess_data(raw_data)
    agent.observe(processed_data)
    raw_predictions = agent.get_predictions()
    results = postprocess_predictions(raw_predictions)

Experimental Features
-------------------

**scikit-learn Integration**

Use GAIuS as a scikit-learn compatible classifier:

.. code-block:: python

    from ia.gaius.experimental.sklearn import GAIuSClassifier, GDFTransformer
    from sklearn.pipeline import Pipeline
    from sklearn.model_selection import train_test_split
    
    # Create a scikit-learn compatible pipeline
    pipeline = Pipeline([
        ('gdf_transformer', GDFTransformer()),
        ('gaius_classifier', GAIuSClassifier(recall_threshold=0.1))
    ])
    
    # Split data
    X_train, X_test, y_train, y_test = train_test_split(features, labels)
    
    # Train and evaluate
    pipeline.fit(X_train, y_train)
    accuracy = pipeline.score(X_test, y_test)

**Genome Optimization**

Use genetic algorithms to optimize agent parameters:

.. code-block:: python

    from ia.gaius.experimental.genome_optimizer import GenomeOptimizer
    
    # Define optimization parameters
    optimizer = GenomeOptimizer(
        path_to_original_genome="simple.genome",
        nodes_to_optimize=["P1"],
        pvt_config=pvt_config,
        gene_config={
            'recall_threshold': {'start': 0.001, 'stop': 0.5, 'step': 0},
            'max_predictions': {'start': 1, 'stop': 50, 'step': 1}
        },
        evolutionary_params={
            'npop': 10,
            'ngen': 5,
            'cxpb': 0.5,
            'mutpb': 0.2
        }
    )
    
    # Run optimization
    results = optimizer.multiprocessed_evolve(n_proc=4)

Performance Considerations
-----------------------

**Memory Management**

For large-scale applications, manage memory explicitly:

.. code-block:: python

    import gc
    
    # Process data in manageable batches
    batch_size = 1000
    for i in range(0, len(all_data), batch_size):
        batch = all_data[i:i+batch_size]
        
        # Process batch
        agent.clear_all_memory()  # Start fresh
        for item in batch:
            agent.observe(item)
        agent.learn()
        
        # Export incremental results
        kb = agent.get_kbs_as_json(obj=True)
        save_results(f"batch_{i}", kb)
        
        # Force garbage collection
        gc.collect()

**Custom Resource Management**

Implement resource pooling for high-throughput scenarios:

.. code-block:: python

    from concurrent.futures import ThreadPoolExecutor
    
    class AgentPool:
        def __init__(self, pool_size=5):
            self.pool_size = pool_size
            self.manager = AgentManager()
            self.agents = []
            self.initialize_pool()
            
        def initialize_pool(self):
            for i in range(self.pool_size):
                agent = self.manager.start_agent(
                    genome_name="simple.genome",
                    agent_name=f"agent-{i}"
                ).get_agent_client()
                agent.connect()
                agent.set_ingress_nodes(["P1"])
                agent.set_query_nodes(["P1"])
                self.agents.append(agent)
                
        def process_batch(self, data_items):
            with ThreadPoolExecutor(max_workers=self.pool_size) as executor:
                return list(executor.map(self._process_item, 
                                        zip(data_items, self.agents)))
                
        def _process_item(self, item_agent_pair):
            item, agent = item_agent_pair
            agent.clear_wm()
            agent.observe(item)
            return agent.get_predictions()


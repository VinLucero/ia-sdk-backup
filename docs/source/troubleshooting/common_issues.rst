Common Issues
===========

.. meta::
   :description: Solutions for common issues with the ia-sdk package
   :keywords: common issues, errors, solutions, fixes, gaius, sdk, troubleshooting

This page addresses common issues you might encounter when using the ia-sdk and provides solutions.

Connection Issues
--------------

**Issue: Unable to Connect to Agent**

.. code-block:: python

    from ia.gaius.agent_client import AgentClient, AgentConnectionError
    
    agent = AgentClient({...})
    try:
        agent.connect()
    except AgentConnectionError as e:
        print(f"Connection failed: {e}")

**Solutions:**

1. **Check API Credentials**:
   
   Ensure your API key, agent name, and domain are correct:
   
   .. code-block:: python
   
       agent_info = {
           'api_key': 'YOUR_CORRECT_API_KEY',  # Check this
           'name': 'your-agent-name',          # Check this
           'domain': 'your-domain.com',        # Check this
           'secure': True
       }

2. **Verify Network Connectivity**:
   
   Ensure you can reach the domain:
   
   .. code-block:: bash
   
       ping your-domain.com
       curl -v https://your-agent-name.your-domain.com/

3. **Check SSL/TLS Settings**:
   
   If you're behind a corporate firewall, you might need to disable SSL verification (not recommended for production):
   
   .. code-block:: python
   
       agent = AgentClient(agent_info, verify=False)

4. **Proxy Configuration**:
   
   Configure proxy settings if needed:
   
   .. code-block:: python
   
       import os
       os.environ['HTTP_PROXY'] = 'http://proxy.example.com:8080'
       os.environ['HTTPS_PROXY'] = 'http://proxy.example.com:8080'

Data Processing Issues
-------------------

**Issue: Observations Not Being Processed**

**Solutions:**

1. **Check Data Format**:
   
   Ensure your data is in the correct GDF format:
   
   .. code-block:: python
   
       from ia.gaius.utils import create_gdf
       from ia.gaius.data_ops import validate_data
       
       # Create properly formatted data
       data = create_gdf(strings=["test"])
       
       # Validate it
       is_valid = validate_data(data)
       if not is_valid:
           print("Data is invalid!")

2. **Verify Ingress Nodes**:
   
   Make sure you've set the correct ingress nodes:
   
   .. code-block:: python
   
       # Set the correct ingress nodes
       agent.set_ingress_nodes(["P1"])
       
       # Verify them
       print(f"Ingress nodes: {agent.ingress_nodes}")

3. **Check Agent State**:
   
   Ensure the agent is not in a sleeping state:
   
   .. code-block:: python
   
       # Check status
       status = agent.show_status()
       
       # If sleeping, wake it up
       if status.get('SLEEPING', False):
           agent.stop_sleeping()

**Issue: Unexpected or No Predictions**

**Solutions:**

1. **Check Working Memory**:
   
   View what's currently in working memory:
   
   .. code-block:: python
   
       wm = agent.get_wm()
       print(f"Working memory: {wm}")

2. **Verify Query Nodes**:
   
   Ensure query nodes are set correctly:
   
   .. code-block:: python
   
       agent.set_query_nodes(["P1"])

3. **Check Prediction Settings**:
   
   Ensure predictions are enabled and recall threshold is appropriate:
   
   .. code-block:: python
   
       # Enable predictions
       agent.start_predicting()
       
       # Adjust recall threshold (lower = more matches)
       agent.change_genes({"recall_threshold": 0.1})

Memory Management Issues
---------------------

**Issue: Out of Memory Errors**

**Solutions:**

1. **Clear Working Memory**:
   
   Regularly clear working memory:
   
   .. code-block:: python
   
       agent.clear_wm()

2. **Process in Batches**:
   
   Process large datasets in manageable batches:
   
   .. code-block:: python
   
       batch_size = 100
       for i in range(0, len(all_data), batch_size):
           batch = all_data[i:i+batch_size]
           
           # Process batch
           agent.clear_wm()
           for item in batch:
               agent.observe(item)
           
           # Learn or get predictions
           agent.learn()

3. **Manage Knowledge Base Size**:
   
   Periodically clean up unneeded models or symbols:
   
   .. code-block:: python
   
       # Remove symbols that match a pattern
       agent.remove_patterns_from_system(["OLD_DATA\|.*"])
       
       # Remove specific models
       agent.delete_model("MODEL|abcdef1234")

Installation Issues
----------------

**Issue: Package Installation Fails**

**Solutions:**

1. **Update pip**:
   
   .. code-block:: bash
   
       pip install --upgrade pip

2. **Install Build Dependencies**:
   
   .. code-block:: bash
   
       # Ubuntu/Debian
       sudo apt-get install python3-dev build-essential
       
       # CentOS/RHEL
       sudo yum install python3-devel gcc
       
       #


Troubleshooting
=============

.. meta::
   :description: Troubleshooting guide for common issues with the ia-sdk package
   :keywords: troubleshooting, help, issues, errors, solutions, gaius, sdk

Welcome to the ia-sdk troubleshooting guide. This section will help you diagnose and resolve common issues that you might encounter when using the ia-sdk.

Getting Help
-----------

If you encounter problems using the ia-sdk, there are several resources available:

1. **Documentation**: Check this troubleshooting guide and API reference first
2. **GitHub Issues**: Search existing issues or create a new one in the `ia-sdk repository <https://github.com/intelligent-artifacts/ia-sdk/issues>`_
3. **Community Forum**: Join the `ia-sdk community forum <https://community.intelligent-artifacts.com>`_ to discuss issues with other users
4. **Support Email**: Contact support at support@intelligent-artifacts.com

Before Seeking Help
-----------------

When reporting an issue, it's helpful to include:

1. ia-sdk version (`import ia.gaius; print(ia.gaius.__version__)`)
2. Python version (`python --version`)
3. Operating system and version
4. A minimal, reproducible example of the issue
5. Relevant error messages and logs
6. Steps you've already taken to try to resolve the issue

Troubleshooting Sections
----------------------

.. toctree::
   :maxdepth: 1
   
   common_issues
   faq

Diagnostic Tools
--------------

The ia-sdk includes built-in diagnostic tools to help identify issues:

**Connectivity Check**

.. code-block:: python

    from ia.gaius.agent_client import AgentClient
    
    # Create an agent client
    agent = AgentClient({
        'api_key': 'YOUR_API_KEY',
        'name': 'agent-name',
        'domain': 'your-domain.com',
        'secure': True
    })
    
    # Test connectivity
    try:
        result = agent.ping()
        print(f"Connection successful: {result}")
    except Exception as e:
        print(f"Connection failed: {e}")

**Agent Status Check**

.. code-block:: python

    # Check agent status
    try:
        status = agent.show_status()
        print(f"Agent status: {status}")
    except Exception as e:
        print(f"Failed to get status: {e}")

Enabling Debug Logging
-------------------

For more detailed diagnostics, enable debug logging:

.. code-block:: python

    import logging
    
    # Configure logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Use the SDK as normal
    from ia.gaius.agent_client import AgentClient
    
    # Operations will now produce detailed logs
    agent = AgentClient(...)


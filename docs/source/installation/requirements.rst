System Requirements
===================

.. meta::
   :description: System requirements and dependencies for the ia-sdk package
   :keywords: requirements, dependencies, python, version, system, gaius, sdk

This page outlines the system requirements and dependencies for using the ia-sdk.

Python Version
--------------

The ia-sdk requires:

* Python 3.8 or higher

Operating Systems
-----------------

The ia-sdk is compatible with:

* **Linux**: Ubuntu 18.04+, CentOS 7+, etc.
* **macOS**: 10.14 (Mojave) or higher
* **Windows**: Windows 10 or higher

Hardware Requirements
---------------------

Minimum specifications:

* **CPU**: 2+ cores
* **RAM**: 4GB minimum (8GB+ recommended)
* **Disk Space**: 500MB for installation (more needed for storing knowledge bases)

For production use or large datasets:

* **CPU**: 4+ cores
* **RAM**: 16GB+
* **Disk Space**: 10GB+ for knowledge base storage

Dependencies
------------

The following Python packages are required and automatically installed with the ia-sdk:

Core Dependencies:
~~~~~~~~~~~~~~~~~~

* **requests**: HTTP library for API communication
* **numpy**: Numerical computing
* **pandas**: Data manipulation and analysis
* **networkx**: Graph operations
* **tqdm**: Progress bars
* **jsonschema**: JSON schema validation
* **pyyaml**: YAML parsing
* **click**: Command-line interfaces

Optional Dependencies:
~~~~~~~~~~~~~~~~~~~~~~

* **matplotlib**: Visualization capabilities
* **plotly**: Interactive visualizations
* **scikit-learn**: Machine learning integration
* **ipython**: Improved interactive experience
* **jupyter**: Notebook support
* **docker**: For container-based agent management

Development Dependencies:
~~~~~~~~~~~~~~~~~~~~~~~~~

These are only needed if you are contributing to the ia-sdk development:

* **pytest**: Testing framework
* **flake8**: Code linting
* **black**: Code formatting
* **sphinx**: Documentation generation
* **sphinx_rtd_theme**: Documentation theme
* **mypy**: Type checking

Installing Dependencies
-----------------------

All required dependencies are automatically installed when you install the ia-sdk with pip:

.. code-block:: bash

    pip install ia-sdk

To install optional dependencies, use:

.. code-block:: bash

    pip install ia-sdk[all]


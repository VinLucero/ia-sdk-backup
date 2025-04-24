Installation Guide
==================

.. meta::
   :description: Installation instructions for the ia-sdk package
   :keywords: installation, setup, requirements, python, pip, gaius, sdk

This guide provides instructions for installing the ia-sdk package and getting started with GAIuS development.

Quick Install
-------------

For most users, the simplest way to install the ia-sdk is via pip:

.. code-block:: bash

    pip install ia-sdk

This will install the latest stable version of the package and its dependencies.

Installation Options
--------------------

.. toctree::
   :maxdepth: 1
   
   requirements
   platform_specific

Development Installation
------------------------

If you want to contribute to the ia-sdk or use the latest development version, you can install from source:

.. code-block:: bash

    git clone https://github.com/intelligent-artifacts/ia-sdk.git
    cd ia-sdk
    pip install -e .

This creates an editable installation that reflects changes you make to the code.

Verifying Installation
----------------------

You can verify that the package is installed correctly by running:

.. code-block:: python

    import ia.gaius
    print(ia.gaius.__version__)

Docker Installation
-------------------

The ia-sdk is also available as a Docker image, which includes all dependencies and tools:

.. code-block:: bash

    # Pull the Docker image
    docker pull intelligentartifacts/ia-sdk:latest
    
    # Run a container
    docker run -it intelligentartifacts/ia-sdk:latest

Offline Installation
--------------------

For environments without internet access, the ia-sdk can be installed offline:

1. Download the package and its dependencies on a machine with internet access:

   .. code-block:: bash

       pip download ia-sdk -d ./ia-sdk-packages

2. Transfer the `ia-sdk-packages` directory to the offline machine

3. Install from the local packages:

   .. code-block:: bash

       pip install --no-index --find-links=./ia-sdk-packages ia-sdk

Next Steps
----------

Once installed, you can:

* Follow the :doc:`/getting-started/quickstart` guide to create your first agent
* Read about :doc:`/user_guide/configuration` to customize your setup
* Check the :doc:`/api_reference/index` for detailed API documentation

If you encounter any issues during installation, please refer to the :doc:`/troubleshooting/common_issues` section.


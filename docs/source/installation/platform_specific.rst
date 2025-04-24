Platform-Specific Installation
===========================

.. meta::
   :description: Platform-specific installation instructions for the ia-sdk package
   :keywords: installation, linux, macos, windows, platform, gaius, sdk

This guide provides platform-specific installation instructions and considerations for the ia-sdk.

Linux Installation
----------------

Ubuntu/Debian
~~~~~~~~~~~~

1. Ensure you have Python 3.8+ and pip installed:

   .. code-block:: bash

       sudo apt update
       sudo apt install python3 python3-pip python3-venv

2. It's recommended to create a virtual environment:

   .. code-block:: bash

       python3 -m venv ia-sdk-env
       source ia-sdk-env/bin/activate

3. Install the ia-sdk:

   .. code-block:: bash

       pip install ia-sdk

CentOS/RHEL
~~~~~~~~~~

1. Ensure you have Python 3.8+ and pip installed:

   .. code-block:: bash

       sudo yum install python3 python3-pip

2. Create a virtual environment:

   .. code-block:: bash

       python3 -m venv ia-sdk-env
       source ia-sdk-env/bin/activate

3. Install the ia-sdk:

   .. code-block:: bash

       pip install ia-sdk

Linux Considerations
~~~~~~~~~~~~~~~~~

* **System Dependencies**: Some dependencies might require system libraries. If you encounter errors, install development packages:

  .. code-block:: bash

      # Ubuntu/Debian
      sudo apt install python3-dev build-essential libssl-dev

      # CentOS/RHEL
      sudo yum groupinstall "Development Tools"
      sudo yum install python3-devel openssl-devel

* **Docker Support**: If using Docker integration, ensure Docker is installed and the user has permission to use it:

  .. code-block:: bash

      # Install Docker
      curl -fsSL https://get.docker.com -o get-docker.sh
      sudo sh get-docker.sh
      
      # Add user to docker group
      sudo usermod -aG docker $USER
      newgrp docker

macOS Installation
---------------

Using pip
~~~~~~~~

1. Ensure you have Python 3.8+ installed. If not, install it using Homebrew:

   .. code-block:: bash

       # Install Homebrew if not already installed
       /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
       
       # Install Python
       brew install python

2. Create a virtual environment:

   .. code-block:: bash

       python3 -m venv ia-sdk-env
       source ia-sdk-env/bin/activate

3. Install the ia-sdk:

   .. code-block:: bash

       pip install ia-sdk

Using Homebrew
~~~~~~~~~~~~

You can also install the ia-sdk directly with Homebrew:

.. code-block:: bash

    brew tap intelligent-artifacts/ia
    brew install ia-sdk

macOS Considerations
~~~~~~~~~~~~~~~~

* **Xcode Command Line Tools**: Some dependencies might require compilation. Make sure you have the Xcode Command Line Tools installed:

  .. code-block:: bash

      xcode-select --install

* **M1/M2 Macs**: For Apple Silicon Macs (M1/M2), ensure you're using Python built for arm64 architecture. Homebrew installs the correct version by default.

* **OpenSSL**: If you encounter SSL-related issues, you might need to install OpenSSL through Homebrew:

  .. code-block:: bash

      brew install openssl

Windows Installation
-----------------

Using pip
~~~~~~~~

1. Install Python 3.8+ from the `official website <https://www.python.org/downloads/windows/>`_ or from the Microsoft Store.

2. Open Command Prompt or PowerShell as administrator and create a virtual environment:

   .. code-block:: powershell

       python -m venv ia-sdk-env
       .\ia-sdk-env\Scripts\activate

3. Install the ia-sdk:

   .. code-block:: powershell

       pip install ia-sdk

Using Anaconda
~~~~~~~~~~~~

If you're using Anaconda:

1. Create a new environment:

   .. code-block:: powershell

       conda create -n ia-sdk python=3.8
       conda activate ia-sdk

2. Install the ia-sdk:

   .. code-block:: powershell

       pip install ia-sdk

Windows Considerations
~~~~~~~~~~~~~~~~~~

* **Microsoft C++ Build Tools**: Some dependencies might require compilation. If you encounter errors, install the Microsoft C++ Build Tools:

  1. Download from the `official website <https://visualstudio.microsoft.com/visual-cpp-build-tools/>`_
  2. During installation, select "Desktop development with C++"

* **Path Length Limitations**: Windows has path length limitations. If you encounter issues:

  1. Enable long paths in Windows 10/11:
     
     Run in PowerShell as administrator:

     .. code-block:: powershell

         Set-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem" -Name "LongPathsEnabled" -Value 1

  2. Or install in a shorter path like `C:\ia-sdk-env`

* **Docker Desktop**: For Docker integration, install Docker Desktop for Windows:
  
  1. Download from the `Docker website <https://www.docker.com/products/docker-desktop/>`_
  2. Ensure WSL 2 is enabled for best performance

Virtual Environments Best Practices
--------------------------------

Regardless of platform, using virtual environments is highly recommended:

1. Create a dedicated environment for your ia-sdk projects:

   .. code-block:: bash

       # Linux/macOS
       python3 -m venv ia-sdk-env
       source ia-sdk-env/bin/activate
       
       # Windows
       python -m venv ia-sdk-env
       .\ia-sdk-env\Scripts\activate

2. Install the package and dependencies:

   .. code-block:: bash

       pip install ia-sdk

3. Create a requirements.txt file for your project:

   .. code-block:: bash

       pip freeze > requirements.txt

4. When sharing your project, others can recreate the environment:

   .. code-block:: bash

       pip install -r requirements.txt

Container-Based Installation
-------------------------

For consistent environments across platforms, consider using containers:

**Docker Installation**

.. code-block:: bash

    # Pull the official image
    docker pull intelligentartifacts/ia-sdk:latest
    
    # Run a container with current directory mounted
    docker run -it -v $(pwd):/app intelligentartifacts/ia-sdk:latest

**Using Docker Compose**

Create a `docker-compose.yml` file:

.. code-block:: yaml

    version: '3'
    services:
      ia-sdk:
        image: intelligentartifacts/ia-sdk:latest
        volumes:
          - .:/app
        working_dir: /app

Then run:

.. code-block:: bash

    docker-compose run ia-sdk


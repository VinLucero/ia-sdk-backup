Platform-Specific Installation
==============================

.. meta::
   :description: Platform-specific installation instructions for the ia-sdk package
   :keywords: installation, linux, macos, windows, platform, gaius, sdk

This guide provides platform-specific installation instructions and considerations for the ia-sdk.

Linux Installation
------------------

Ubuntu/Debian
~~~~~~~~~~~~~

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
~~~~~~~~~~~

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
~~~~~~~~~~~~~~~~~~~~

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
------------------

Using pip
~~~~~~~~~

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
~~~~~~~~~~~~~~

You can also install the ia-sdk directly with Homebrew:

.. code-block:: bash

    brew tap intelligent-artifacts/ia
    brew install ia-sdk

macOS Considerations
~~~~~~~~~~~~~~~~~~~~

* **Xcode Command Line Tools**: Some dependencies might require compilation. Make sure you have the Xcode Command Line Tools installed:

  .. code-block:: bash

      xcode-select --install

* **OpenSSL**: If you encounter SSL-related issues, you might need to install OpenSSL through Homebrew:

  .. code-block:: bash

      brew install openssl

Apple Silicon (M1/M2) Specific Instructions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For Apple Silicon Macs (M1/M2), there are some specific considerations to ensure optimal compatibility:

1. **Use Native arm64 Python**: Ensure you're using Python built for arm64 architecture:

   .. code-block:: bash

       # Check your Python architecture
       python3 -c "import platform; print(platform.machine())"
       # Should output: 'arm64'

2. **Homebrew Installation**: For arm64 native Homebrew:

   .. code-block:: bash

       # Install Homebrew for Apple Silicon
       /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
       
       # Make sure it's in your path
       echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
       eval "$(/opt/homebrew/bin/brew shellenv)"

3. **Architecture-specific Package Issues**: Some packages might have compatibility issues. You can create an environment with x86_64 architecture if needed:

   .. code-block:: bash

       # Install Rosetta 2 if not already installed
       softwareupdate --install-rosetta
       
       # Create an x86_64 specific virtual environment if needed
       arch -x86_64 python3 -m venv ia-sdk-x86-env
       source ia-sdk-x86-env/bin/activate

4. **Common Issues and Solutions**:

   * **C Extension Compilation Errors**: If you encounter C extension compilation errors:

     .. code-block:: bash

         # Install dependencies with Homebrew
         brew install cmake ninja
         
         # Set architecture-specific compiler flags
         export ARCHFLAGS="-arch arm64"
         pip install ia-sdk

   * **NumPy/SciPy Issues**: For numerical computation libraries:

     .. code-block:: bash

         # Install optimized versions
         brew install openblas
         pip install numpy scipy --no-binary :all:

Windows Installation
--------------------

Using pip
Using pip
~~~~~~~~~

1. Install Python 3.10+ from the `Python downloads page <https://www.python.org/downloads/windows/>`_ or from the Microsoft Store.
2. Open Command Prompt or PowerShell as administrator and create a virtual environment:

   .. code-block:: powershell

       python -m venv ia-sdk-env
       .\ia-sdk-env\Scripts\activate

3. Install the ia-sdk:

   .. code-block:: powershell

       pip install ia-sdk

Using Anaconda
~~~~~~~~~~~~~~

If you're using Anaconda:

1. Create a new environment:

   .. code-block:: powershell

       conda create -n ia-sdk python=3.10
       conda activate ia-sdk

2. Install the ia-sdk:

   .. code-block:: powershell

       pip install ia-sdk

Windows Considerations
~~~~~~~~~~~~~~~~~~~~~~

* **Microsoft C++ Build Tools**: Some dependencies might require compilation. If you encounter errors, install the Microsoft C++ Build Tools:

  1. Download from the `Visual C++ Build Tools page <https://visualstudio.microsoft.com/visual-cpp-build-tools/>`_
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
-----------------------------------

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
----------------------------

For consistent environments across platforms, consider using containers which provide a consistent runtime environment regardless of the host operating system.

Docker Installation
~~~~~~~~~~~~~~~~~~~

1. **Install Docker**:

   * **Linux**: Follow the instructions on the `Docker website (Linux installation) <https://docs.docker.com/engine/install/>`_
   * **macOS**: Install Docker Desktop from the `Docker website (macOS installation) <https://docs.docker.com/desktop/install/mac-install/>`_
   * **Windows**: Install Docker Desktop from the `Docker website (Windows installation) <https://docs.docker.com/desktop/install/windows-install/>`_

2. **Pull the official image**:

   .. code-block:: bash

       docker pull intelligentartifacts/ia-sdk:latest

3. **Run the container**:

   .. code-block:: bash

       # Run a container with current directory mounted
       docker run -it -v $(pwd):/app intelligentartifacts/ia-sdk:latest

Using Docker Compose
~~~~~~~~~~~~~~~~~~~~

For more complex setups, Docker Compose provides a convenient way to define and run multi-container applications.

1. **Install Docker Compose**:
   
   * It comes with Docker Desktop for macOS and Windows
   * For Linux, follow the instructions on the `Docker Compose website <https://docs.docker.com/compose/install/>`_

2. **Create a `docker-compose.yml` file**:

   .. code-block:: yaml

       version: '3'
       services:
         ia-sdk:
           image: intelligentartifacts/ia-sdk:latest
           volumes:
             - .:/app
           working_dir: /app
           environment:
             - GAIUS_API_KEY=${GAIUS_API_KEY}
             - GAIUS_DOMAIN=${GAIUS_DOMAIN}

3. **Run with Docker Compose**:

   .. code-block:: bash

       docker-compose run ia-sdk

Building Custom Docker Images
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You can also create custom Docker images tailored to your specific needs:

1. **Create a Dockerfile**:

   .. code-block:: dockerfile

       FROM python:3.10-slim
       
       WORKDIR /app
       
       # Install dependencies
       RUN pip install --no-cache-dir ia-sdk
       
       # Install your application dependencies
       COPY requirements.txt .
       RUN pip install --no-cache-dir -r requirements.txt
       
       # Copy your application code
       COPY . .
       
       # Run your application
       CMD ["python", "your_script.py"]

2. **Build the image**:

   .. code-block:: bash

       docker build -t your-ia-app .

3. **Run your custom container**:

   .. code-block:: bash

       docker run -it your-ia-app

Kubernetes Deployment
~~~~~~~~~~~~~~~~~~~~~

For production environments, you might want to deploy your application on Kubernetes:

1. **Create a deployment manifest**:

   .. code-block:: yaml

       apiVersion: apps/v1
       kind: Deployment
       metadata:
         name: ia-sdk-app
       spec:
         replicas: 3
         selector:
           matchLabels:
             app: ia-sdk-app
         template:
           metadata:
             labels:
               app: ia-sdk-app
           spec:
             containers:
             - name: ia-sdk-app
               image: your-ia-app:latest
               env:
               - name: GAIUS_API_KEY
                 valueFrom:
                   secretKeyRef:
                     name: ia-sdk-secrets
                     key: api-key
               - name: GAIUS_DOMAIN
                 valueFrom:
                   configMapKeyRef:
                     name: ia-sdk-config
                     key: domain

2. **Apply the manifest**:

   .. code-block:: bash

       kubectl apply -f deployment.yaml

Troubleshooting Container Issues
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* **Permission Issues**: If you encounter permission issues when mounting volumes:

  .. code-block:: bash

      # Linux/macOS
      docker run -it -v $(pwd):/app --user $(id -u):$(id -g) intelligentartifacts/ia-sdk:latest
      
      # Windows (PowerShell)
      docker run -it -v ${PWD}:/app intelligentartifacts/ia-sdk:latest

* **Network Issues**: If your container needs to access external services:

  .. code-block:: bash

      docker run -it --network host intelligentartifacts/ia-sdk:latest

* **Resource Constraints**: For memory-intensive operations:

   .. code-block:: bash

      docker run -it --memory=4g --cpus=2 intelligentartifacts/ia-sdk:latest

Troubleshooting Common Installation Issues
------------------------------------------

This section covers common installation issues and their solutions.

Python Version Conflicts
~~~~~~~~~~~~~~~~~~~~~~~~

* **Issue**: Conflicting Python versions on your system.
* **Solution**: Use virtual environments to isolate your ia-sdk installation:

  .. code-block:: bash

      # Create a virtual environment with the specific Python version
      python3.10 -m venv ia-sdk-env
      source ia-sdk-env/bin/activate  # Linux/macOS
      .\ia-sdk-env\Scripts\activate  # Windows

Dependency Conflicts
~~~~~~~~~~~~~~~~~~~~

* **Issue**: Dependency version conflicts with other packages.
* **Solution**: Create a dedicated virtual environment or use `pip-tools`:

  .. code-block:: bash

      pip install pip-tools
      pip-compile requirements.in
      pip-sync requirements.txt

Installation Fails with Build Errors
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* **Issue**: C extension compilation errors during installation.
* **Solution**: Install required build tools and development libraries:

  .. code-block:: bash

      # Ubuntu/Debian
      sudo apt install python3-dev build-essential
      
      # CentOS/RHEL
      sudo yum install python3-devel gcc
      
      # macOS
      xcode-select --install
      
      # Windows
      # Install Visual C++ Build Tools from Microsoft

SSL Certificate Verification Failed
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* **Issue**: SSL certificate errors when connecting to repositories.
* **Solution**: Update certificates or use a trusted connection:

  .. code-block:: bash

      # Update certificates
      pip install --upgrade certifi
      
      # Temporarily disable verification (not recommended for production)
      pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org ia-sdk

Installation Behind Corporate Proxies
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* **Issue**: Cannot connect to package repositories behind corporate firewalls.
* **Solution**: Configure pip to use your corporate proxy:

  .. code-block:: bash

      # Set environment variables
      export HTTP_PROXY="http://proxy.example.com:8080"
      export HTTPS_PROXY="http://proxy.example.com:8080"
      
      # Or configure in pip.conf
      pip config set global.proxy http://proxy.example.com:8080

Package Verification
~~~~~~~~~~~~~~~~~~~~

* **Issue**: Need to verify package authenticity and integrity.
* **Solution**: Verify package signatures:

  .. code-block:: bash

      # Install tools for verification
      pip install pyopenssl
      
      # Check that package hash matches published hash
      pip download ia-sdk --no-deps
      pip hash ia-sdk-x.y.z.tar.gz

#!/bin/bash

# Exit on error
set -e

echo "Setting up documentation build environment..."

# Create Python virtual environment if it doesn't exist
if [ ! -d "docs_env" ]; then
    python -m venv docs_env
fi

# Activate virtual environment
source docs_env/bin/activate

# Install dependencies
pip install sphinx sphinx-rtd-theme myst-parser

# Create docs structure if not exists
mkdir -p docs/source/{_static,_templates,getting-started}

# Configure Sphinx if not already configured
if [ ! -f "docs/source/conf.py" ]; then
    # Create conf.py directly
    cat > docs/source/conf.py << 'EOF'
import os
import sys
sys.path.insert(0, os.path.abspath('../..'))

project = 'ia-sdk'
copyright = '2025, Documentation Team'
author = 'Documentation Team'
version = '0.4.22'
release = '0.4.22'

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.viewcode',
    'sphinx.ext.napoleon',
    'sphinx.ext.intersphinx',
    'myst_parser'
]

templates_path = ['_templates']
exclude_patterns = []

html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']

# MyST Markdown settings
myst_enable_extensions = [
    "colon_fence",
    "deflist"
]

# Intersphinx mapping
intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
    'requests': ('https://requests.readthedocs.io/en/latest/', None),
}
EOF
fi

# Create Makefile if it doesn't exist
if [ ! -f "docs/Makefile" ]; then
    cat > docs/Makefile << 'EOF'
# Minimal makefile for Sphinx documentation

# You can set these variables from the command line, and also
# from the environment for the first two.
SPHINXOPTS    ?=
SPHINXBUILD   ?= sphinx-build
SOURCEDIR     = source
BUILDDIR      = build

# Put it first so that "make" without argument is like "make help".
help:
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

.PHONY: help Makefile

# Catch-all target: route all unknown targets to Sphinx using the new
# "make mode" option.  $(O) is meant as a shortcut for $(SPHINXOPTS).
%: Makefile
	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)
EOF
fi

# Create index.rst if it doesn't exist
if [ ! -f "docs/source/index.rst" ]; then
    cat > docs/source/index.rst << 'EOF'
ia-sdk Documentation
===================

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   getting-started/index
   getting-started/quickstart
   getting-started/technical-deep-dive
   getting-started/practical-examples

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
EOF
fi

# Copy documentation files
cp docs/getting-started/*.md docs/source/getting-started/

# Build documentation
echo "Building documentation..."
cd docs
make html
cd ..

echo "Documentation built successfully!"
echo "Open docs/build/html/index.html in your browser to view"

# Deactivate virtual environment
deactivate


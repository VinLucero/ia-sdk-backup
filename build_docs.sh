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

# Configure Sphinx if not already configured
if [ ! -f "docs/conf.py" ]; then
    cd docs
    sphinx-quickstart -q \
        -p "ia-sdk" \
        -a "Documentation Team" \
        -v "0.4.22" \
        -r "0.4.22" \
        -l en \
        --ext-autodoc \
        --ext-viewcode \
        --ext-napoleon \
        --sep
    cd ..
fi

# Copy documentation files
mkdir -p docs/source/getting-started
cp docs/getting-started/*.md docs/source/getting-started/

# Update conf.py with required extensions
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

# Create index file
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

# Build documentation
echo "Building documentation..."
cd docs
make html
cd ..

echo "Documentation built successfully!"
echo "Open docs/build/html/index.html in your browser to view"

# Deactivate virtual environment
deactivate


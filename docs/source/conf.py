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

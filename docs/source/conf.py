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
    'sphinx.ext.doctest',
    'myst_parser'
]

# Doctest configuration
doctest_global_setup = '''
import ia.gaius
from ia.gaius.data_ops import validate_data
from ia.gaius.utils import create_gdf, add_vector_to_gdf, add_string_to_gdf, add_emotive_to_gdf

# Test data for doctest
gdf1 = {"strings": [], "vectors": [], "emotives": {}, "metadata": {}}
gdf2 = {"strings": [], "vectors": [], "emotives": {}, "metadata": {}, "invalid": True}
gdf3 = {"strings": ["hello"], "vectors": [], "emotives": {}, "metadata": {}}
gdf4 = {"strings": ["hello"], "vectors": [[1, 2, 3, 4]], "emotives": {}, "metadata": {}}
gdf5 = {"strings": "hello", "vectors": [], "emotives": {}, "metadata": {}}
gdf6 = {"strings": ["hello"], "vectors": [1, 2, 3, 4], "emotives": {}, "metadata": {}}
gdf7 = {"strings": ["hello"], "vectors": [[1, 2, 3, 4]], "emotives": {"utility": "high"}, "metadata": {}}
gdf8 = {"strings": ["hello"], "vectors": [[1, 2, 3, 4]], "emotives": {"utility": 23.7}, "metadata": {}}
'''

doctest_test_doctest_blocks = 'default'

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

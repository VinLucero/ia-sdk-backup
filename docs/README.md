# ia-sdk Documentation

This directory contains the documentation for the ia-sdk package. The documentation is built using [Sphinx](https://www.sphinx-doc.org/), a powerful documentation generator that converts reStructuredText files into HTML, PDF, and other formats.

## Quick Start

To generate the documentation:

1. Install Sphinx and required theme:
   ```bash
   pip install sphinx sphinx_rtd_theme
   ```

2. Build the HTML documentation:
   ```bash
   # From the docs directory
   make html
   
   # Or on Windows
   .\make.bat html
   ```

3. View the documentation:
   - Open `build/html/index.html` in your web browser
   - Generated documentation will be in the `build/html` directory

## Documentation Structure

```
docs/
├── source/           # Source files for documentation
│   ├── _static/     # Static files (images, custom CSS, etc.)
│   ├── _templates/  # Custom HTML templates
│   ├── conf.py      # Sphinx configuration
│   ├── index.rst    # Main documentation entry point
│   └── ...          # Other .rst documentation files
├── Makefile         # Make file for building docs
├── make.bat         # Windows build script
└── README.md        # This file
```

## Writing Documentation

### Adding New Pages

1. Create a new .rst file in the appropriate directory under `source/`
2. Add the file to the toctree in `index.rst` or another parent document
3. Include proper metadata and section headers

Example .rst file:
```rst
Page Title
=========

.. meta::
   :description: Page description for SEO
   :keywords: key, words, for, search

Section Header
-------------

Content goes here.
```

### API Documentation

The API documentation is automatically generated from docstrings in the code. To document a new module or class:

1. Add proper docstrings to your Python code:
   ```python
   def my_function(arg1: str, arg2: int) -> bool:
       """
       Brief description of function.

       Args:
           arg1 (str): Description of arg1
           arg2 (int): Description of arg2

       Returns:
           bool: Description of return value

       Example:
           >>> my_function("test", 42)
           True
       """
       return True
   ```

2. Add the module to the appropriate .rst file using autodoc:
   ```rst
   .. automodule:: my_module
      :members:
      :undoc-members:
      :show-inheritance:
   ```

## Building Documentation

### HTML Output

```bash
make html
```

### PDF Output (requires LaTeX)

```bash
make latexpdf
```

### Checking for Errors

```bash
make linkcheck    # Check all external links
make doctest     # Run code examples in documentation
make coverage    # Check documentation coverage
```

## Development Guidelines

1. **File Organization**:
   - Keep related documentation files together
   - Use clear, descriptive file names
   - Follow the established directory structure

2. **Style Guidelines**:
   - Use consistent formatting
   - Include examples for complex features
   - Cross-reference related documentation
   - Include proper metadata for SEO

3. **Code Examples**:
   - Make examples clear and concise
   - Test all code examples
   - Include expected output
   - Show common use cases

## Useful Resources

- [Sphinx Documentation](https://www.sphinx-doc.org/)
- [reStructuredText Primer](https://www.sphinx-doc.org/en/master/usage/restructuredtext/basics.html)
- [Read the Docs Theme](https://sphinx-rtd-theme.readthedocs.io/)
- [Sphinx Extensions](https://www.sphinx-doc.org/en/master/usage/extensions/index.html)

## Getting Help

If you encounter issues with the documentation:

1. Check the Sphinx build output for errors
2. Review the Sphinx documentation
3. Check existing documentation for examples
4. Create an issue in the repository if needed

## Contributing

When contributing to the documentation:

1. Follow the existing structure and style
2. Test your changes by building the docs
3. Update the table of contents if needed
4. Add yourself to the contributors list
5. Create a pull request with your changes

## License

This documentation is licensed under the same terms as the ia-sdk package. See the main repository's LICENSE file for details.

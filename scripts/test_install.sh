#!/bin/bash

# Test script to verify ia-sdk installation from backup
echo "Testing ia-sdk installation from backup..."

# Create test virtual environment
TEST_VENV="test_venv"
python -m venv $TEST_VENV

# Activate test environment
source $TEST_VENV/bin/activate

# Show what packages are available
echo "Available packages in backup:"
ls -l packages/

# Install from backup with verbose output
echo "Installing packages..."
pip install -v --no-index --find-links packages ia-sdk

# Show installed packages
echo "Installed packages:"
pip list

# Test import
echo "Testing import..."
python -c "import ia.gaius; print(f\"Successfully installed ia-sdk {ia.gaius.__version__}\")"

# Cleanup
deactivate
rm -rf $TEST_VENV

echo "Test complete!"

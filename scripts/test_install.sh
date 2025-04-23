#!/bin/bash

# Test script to verify ia-sdk installation from backup
echo "Testing ia-sdk installation from backup..."

# Create test virtual environment
TEST_VENV="test_venv"
python -m venv $TEST_VENV

# Activate test environment
source $TEST_VENV/bin/activate

# Install from backup
pip install --no-index --find-links packages -r requirements.txt

# Test import
python -c "import ia.gaius; print(f\"Successfully installed ia-sdk {ia.gaius.__version__}\")"

# Cleanup
deactivate
rm -rf $TEST_VENV

echo "Test complete!"

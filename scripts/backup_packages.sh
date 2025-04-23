#!/bin/bash

# Script to download and verify ia-sdk and dependencies
VENV_DIR="venv"
BACKUP_DIR="packages"

# Create virtual environment
python -m venv $VENV_DIR

# Activate virtual environment
source $VENV_DIR/bin/activate

# Create backup directory
mkdir -p $BACKUP_DIR

# Download specific versions
pip download -d $BACKUP_DIR \
    ia-sdk==0.4.22 \
    docker \
    filelock \
    numpy \
    platformdirs \
    pymongo \
    requests \
    retry \
    sty

# Create hash verification file
cd $BACKUP_DIR
sha256sum * > checksums.txt
cd ..

# Create requirements with exact versions
pip freeze > requirements.txt

echo "Backup complete. Verify checksums with: cd $BACKUP_DIR && sha256sum -c checksums.txt"

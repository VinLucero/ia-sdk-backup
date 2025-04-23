# ia-sdk Backup and Rebuild Guide

## Overview
This repository contains tools and instructions for backing up and rebuilding ia-sdk v0.4.22 and its dependencies from publicly available pip packages.

## Contents
- `packages/`: Downloaded wheel files and source distributions
- `scripts/`: Utility scripts for backup and verification
- `requirements.txt`: Exact package versions
- `docs/`: Additional documentation

## Backup Process
1. Run the backup script:
   ```bash
   ./scripts/backup_packages.sh
   ```

## Rebuild Process
1. Create a new virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate
   ```

2. Install from backed up packages:
   ```bash
   pip install --no-index --find-links packages -r requirements.txt
   ```

## Verification
- All packages include SHA256 checksums in `packages/checksums.txt`
- Verify with: `cd packages && sha256sum -c checksums.txt`

## Package Versions
- ia-sdk==0.4.22
- All dependencies are pinned to specific versions in requirements.txt

## Legal Notice
This backup contains only publicly available packages from PyPI and is intended for legal use in accordance with all relevant licenses and terms of use.

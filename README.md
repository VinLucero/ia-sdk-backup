# ia-sdk Backup (v0.4.22)

This repository contains a complete backup of ia-sdk version 0.4.22 and all its dependencies, created on April 23, 2025. This backup allows for offline installation of the package and its dependencies.

## Repository Structure

- `packages/`: Contains all wheel files (.whl) and checksums
- `scripts/`: Utility scripts for backup and verification
- `src/`: Extracted package contents for reference
- `requirements.txt`: Exact package versions

## Package Contents

Main package:
- ia-sdk v0.4.22

Dependencies:
- docker
- filelock
- numpy
- platformdirs
- pymongo
- requests
- retry
- sty

## Installation Instructions

### Method 1: Using the Installation Script

1. Clone this repository:
   ```bash
   git clone https://github.com/VinLucero/ia-sdk-backup.git
   cd ia-sdk-backup
   ```

2. Run the test installation script:
   ```bash
   ./scripts/test_install.sh
   ```

### Method 2: Manual Installation

1. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scriptsctivate
   ```

2. Install from the backup:
   ```bash
   pip install --no-index --find-links packages ia-sdk
   ```

### Verification

To verify the package installation:
```python
from ia.gaius.agent_client import AgentQueryError
print("ia-sdk installed successfully")
```

## Platform Compatibility

This backup was created on macOS with the following specifications:
- Architecture: arm64
- Python version: 3.12
- Some wheels are platform-specific (e.g., numpy, pymongo)

For other platforms, you may need to download platform-specific wheels from PyPI or rebuild from source.

## How This Backup Was Created

1. Initial Setup:
   - Created backup directory and scripts
   - Initialized git repository

2. Package Download:
   ```bash
   mkdir packages
   pip download -d packages ia-sdk==0.4.22 [dependencies]
   ```

3. Verification:
   - Created SHA256 checksums
   - Implemented test installation script
   - Verified package imports

4. Documentation:
   - Added README with installation instructions
   - Created backup and test scripts
   - Documented package contents and structure

## Package Details

Wheel files included:
```
- packages/certifi-2025.1.31-py3-none-any.whl
- packages/charset_normalizer-3.4.1-cp312-cp312-macosx_10_13_universal2.whl
- packages/decorator-5.2.1-py3-none-any.whl
- packages/dnspython-2.7.0-py3-none-any.whl
- packages/docker-7.1.0-py3-none-any.whl
- packages/filelock-3.18.0-py3-none-any.whl
- packages/ia_sdk-0.4.22-py3-none-any.whl
- packages/idna-3.10-py3-none-any.whl
- packages/numpy-2.2.5-cp312-cp312-macosx_14_0_arm64.whl
- packages/platformdirs-4.3.7-py3-none-any.whl
- packages/py-1.11.0-py2.py3-none-any.whl
- packages/pymongo-4.12.0-cp312-cp312-macosx_11_0_arm64.whl
- packages/requests-2.32.3-py3-none-any.whl
- packages/retry-0.9.2-py2.py3-none-any.whl
- packages/sty-1.0.6-py3-none-any.whl
- packages/urllib3-2.4.0-py3-none-any.whl
```

## Usage Notes

1. The backup includes both the installable wheel files and reference source code
2. Checksums are provided for file verification
3. Test script ensures proper installation
4. Platform-specific dependencies may need to be replaced for different systems

## Legal Notice

This backup contains only publicly available packages from PyPI and is intended for legal use in accordance with all relevant licenses and terms of use. The source code is included for reference purposes only.

## Maintenance

To update this backup:
1. Update version numbers in scripts/backup_packages.sh
2. Run the backup script to download new versions
3. Test the installation
4. Update documentation as needed

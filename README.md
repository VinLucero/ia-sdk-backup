# ia-sdk Backup (v0.4.22)

This repository contains a complete backup of ia-sdk version 0.4.22 and all its dependencies, created on April 23, 2025. This backup allows for offline installation of the package and its dependencies.

## Repository Structure

- `packages/`: Contains all wheel files (.whl) and checksums
- `scripts/`: Utility scripts for backup and verification
- `src/`: Extracted package contents for reference
- `requirements.txt`: Exact package versions

## Package Contents

Main package:
- ia-sdk v0.4.22 (platform-independent)

Direct Dependencies:
- docker
- filelock
- numpy
- platformdirs
- pymongo
- requests
- retry
- sty
- pandas
- networkx
- plotly

Additional Dependencies:
- python-dateutil
- pytz
- tzdata
- six
- urllib3
- charset-normalizer
- idna
- certifi
- dnspython
- decorator
- py
- narwhals
- packaging

## Installation Instructions

### Method 1: Using the Installation Script

1. Clone this repository:
   ```bash
   git clone https://github.com/VinLucero/ia-sdk-backup.git
   cd ia-sdk-backup
   ```

2. Run the test installation script:
   ```bash
   ./scripts/full_test.sh
   ```

### Method 2: Manual Installation

1. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scriptsctivate
   ```

2. Install from the backup:
   ```bash
   pip install --no-index --find-links packages pandas networkx plotly ia-sdk
   ```

### Verification

To verify the package installation:
```python
from ia.gaius.agent_client import AgentQueryError
print("Successfully imported ia-sdk")
```

## Platform Compatibility

This backup was created on macOS with the following specifications:
- Architecture: arm64
- Python version: 3.12
- Some wheels are platform-specific (e.g., numpy, pymongo)

Platform-specific packages:
- numpy (2.2.5, macOS arm64)
- pymongo (4.12.0, macOS arm64)
- charset-normalizer (3.4.1, macOS universal2)

For other platforms, you'll need to:
1. Keep the platform-independent wheels
2. Download platform-specific wheels for your system from PyPI
3. Update checksums.txt accordingly

## Verification Status

Last verified on: April 23, 2025
Test results:
- ✓ Package installation
- ✓ Basic imports
- ✓ Object creation
- ✓ All dependencies resolved

## Legal Notice

This backup contains only publicly available packages from PyPI and is intended for legal use in accordance with all relevant licenses and terms of use. The source code is included for reference purposes only.

## Maintenance

To update this backup:
1. Update version numbers in scripts/backup_packages.sh
2. Run the backup script to download new versions
3. Test the installation
4. Update documentation as needed

## Troubleshooting

If you encounter platform compatibility issues:
1. Keep all platform-independent wheels
2. Download platform-specific wheels for your system
3. Update checksums.txt accordingly
4. Run the test installation script to verify

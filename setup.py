from setuptools import setup, find_packages

setup(
    name="ia-sdk",
    version="0.4.22",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "requests>=2.28.0",
        "numpy>=1.19.0",
        "pandas>=1.0.0",
        "networkx>=2.5",
        "tqdm>=4.64.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "sphinx>=4.5.0",
            "sphinx-rtd-theme>=1.0.0",
        ],
    },
)

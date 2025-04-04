from setuptools import setup, find_packages

# Read dependencies from requirements.txt
def parse_requirements(filename):
    with open(filename, "r") as f:
        return [line.strip() for line in f if line.strip() and not line.startswith("#")]

setup(
    name="tfbootstrap",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=parse_requirements("requirements.txt"),  # Dynamically load dependencies
    entry_points={
        "console_scripts": [
            "tfbootstrap=cli:main",  # CLI entry point
        ],
    },
)
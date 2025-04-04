# evmc-supply-curves
Data and a supporting lightweight Python package that describes possible costs for enabling EV managed charging from now to 2050 for three dispatch mechanisms (TOU, RTP, and DLC) and four flexibility scenarios.

# Installation for Development
After cloning the repository, create a virtual environment in the repository root:
```bash
python -m venv .venv
```
activate it:
```bash
source .venv/bin/activate
```
and install the project in editable mode with its development dependencies:
```bash
pip install -e .
```
. This automatically installs all project `dependencies` documented in `pyproject.toml`.
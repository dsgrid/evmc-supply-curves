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

# Useage
example.py contains examples to create cost tables and use 1% resolution particiption data to determine (1) per EV costs of given a targeted percent participation and (2) estimated percent participation of various programs and scenarios given a per EV cost.

```bash
sc=SupplyCurves()           
sc.load_existing_table()    # creates an instance of a supply curve table that can be queried

sc.cost_per_EV(PERCENT, EV_Type='LDV') # returns a per EV cost (1)
sc.participation_given_cost(COST, PRECISION) # returns percent participation

```
See example.py for more.
# evmc-supply-curves
Data and a supporting lightweight Python package that describes possible costs for enabling EV managed charging from 2025 to 2050 for three dispatch mechanisms (TOU, RTP, and DLC) and four flexibility scenarios.

Data and scripts include:
- `cost_inputs\scenario_vars.csv` contains costs and other supply curve parameters (upper limits of participation, enrollment response to a given incentive, and ratio of customers expected to require a new charger). 

- `supplycurve_helpers.py` generates all 288 supply curves, as well as functions to 1. generate a table of beta values (a variable that determines customer participation as a response to incentives), 2. return a per EV cost given a targeted percent of customer enrollment, and 3. return an expected percent of customer participation given a per customer budget or cost.

- `outputs\costs_table_1_pct.csv` is a table of per EV costs for all years, vehicle types, and programs at 1% increments of customer participation.

- `outputs\betas_table.csv` is a table of beta values, or values that determine the customer participation rate as a function of incentives. This function is a decaying exponential response or the form r*(1-e^(-beta*x)) where x is the incentive value in USD and r is a maximum participation rate.

The first two files are essential to generating EVMC supply curves, while the last two tables are provided for users who would like the supply curve data without needing to install or run code. 

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
`examples/basic_example.py` contains examples to create cost tables and use 1% resolution particiption data to determine (1) per EV costs of given a targeted percent participation and (2) estimated percent participation of various programs and scenarios given a per EV cost.

```bash
sc=SupplyCurves()           
sc.load_existing_table()    # creates an instance of a supply curve table that can be queried

sc.cost_per_EV(PERCENT, EV_Type='LDV') # returns a per EV cost (1)
sc.participation_given_cost(COST, PRECISION) # returns percent participation

```

NREL Software Record SWR-25-69 "Electric Vehicle Managed Charging (EVMC) Supply Curves"

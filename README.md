# evmc-supply-curves
Data and a supporting lightweight Python package that describes possible costs for enabling EV managed charging from 2025 to 2050 for three dispatch mechanisms: Time-of-Use (TOU), Real Time Pricing (RTP), and direct load control (DLC) and four flexibility scenarios (Flat and Low, Mid, and High Flex).

[Data Access](https://github.com/dsgrid/evmc-supply-curves/blob/main/outputs/costs_table_1_pct.csv) | [Install](#Installation)

Data files include:
- `cost_inputs/scenario_vars.csv` contains costs and other supply curve parameters (upper limits of participation, enrollment response to a given incentive, and ratio of customers expected to require a new charger). 

- `outputs/costs_table_1_pct.csv` is a table of per EV costs for all years ($ per vehicle in 2025 dollars), vehicle types, and programs at 1% increments of customer participation.

- `outputs/betas_table.csv` is a table of beta values, or values that determine the customer participation rate as a function of incentives. This function is a decaying exponential response of the form r*(1-e^(-beta*x)) where x is the annual incentive value in USD/vehicle-year and r is a maximum participation rate.

The first two files are essential to generating EVMC supply curves, while the last two tables are provided for users who would like the supply curve data without needing to install or run code. 

Key functions to generate data tables can be found in  `supplycurve_helpers.py`. These include: 

- `supplycurve_helpers.py/create_betas_table` generates a table of beta values (a variable that determines customer participation as a response to incentives or marketing costs). A .csv is also saved to the 'outputs' directory.

- `supplycurve_helpers.py/create_cost_table` generates all 288 supply curves as a dataframe of per vehicle costs for a given enrollment resolution. A .csv of this table of supply curves for this resolution, saved to the 'table_path'.

- `supplycurve_helpers.py/load_existing_table` loads a table of supply curves that has already been generated, such as the table provided at a resolution of 1% enrollment increments, or a user-generated table. This can then be used to find a per EV cost ($ per vehicle in 2025 dollars) given a targeted percent of customer enrollment using cost_per_EV.

- `supplycurve_helpers.py/cost_per_EV` returns per vehicle cost in USD for specified parameters. If more than one possible cost exists, this will return a DataFrame for all costs.


## Installation
After cloning the repository, create a virtual environment in the repository root:
```bash
python -m venv .venv
```
activate it (Windows):
```bash
.venv\Scripts\activate
```
or (for macOS/Unix):

```bash
source .venv/bin/activate
```
and install the project in editable mode with its development dependencies:
```bash
pip install -e .
```
This automatically installs all project `dependencies` documented in `pyproject.toml`.

# Usage
`examples/basic_example.py` contains examples to create cost tables and use 1% resolution particiption data to determine (1) per EV costs of given a targeted percent participation and (2) estimated percent participation of various programs and scenarios given a per EV cost.

```python
from evmc_supply_curves.supplycurve_helpers import SupplyCurves

sc=SupplyCurves()           
sc.load_existing_table()    # creates an instance of a supply curve table that can be queried

sc.cost_per_EV(PERCENT, EV_Type='LDV') # returns a per EV cost (1)
```

NREL Software Record SWR-25-69 "Electric Vehicle Managed Charging (EVMC) Supply Curves"

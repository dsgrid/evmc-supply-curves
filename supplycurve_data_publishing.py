import pandas as pd
import os
from supplycurve_helpers import ScenarioParameters

def create_cost_table(ENROLLMENT_RESOLUTION):
    cwd = os.getcwd()
    enrollment = [ENROLLMENT_RESOLUTION*i/100 for i in range(int(100/ENROLLMENT_RESOLUTION))]
    
    costs=pd.DataFrame()
    for EV_TYPE in ['LDV','MHDV']:
        df = pd.read_csv(os.path.join(cwd, 'cost_inputs','scenario_vars.csv'))
        df = df.loc[(df.ev_type==EV_TYPE)]
        for CUSTOMER_TYPE in ['new','recurring']:
            for i in range(len(df)):
                #get values and cost caluculations for each program, year, and scenario
                PARAMS=ScenarioParameters(df.iloc[i].to_frame().T, CUSTOMER_TYPE)
                PARAMS.calc_beta()

                """mix of new chargers and no new chargers"""
                customer_df = PARAMS.df_by_required_install('new_install', num_customers=5000) 
                customer_df['install']=['new_install']*len(customer_df)
                
                no_install_df=PARAMS.df_by_required_install('no_install', num_customers=5000)
                no_install_df['install']=['no_install']*len(no_install_df)

                customer_df = customer_df._append(no_install_df)

                #Don't double count marketing for LDV TOU
                if ( (PARAMS.ev_type=='LDV')and(PARAMS.program=='TOU') ):
                    customer_df['total_cost'] = customer_df[['op_and_admin', 'incentives']].sum(axis=1)
                else:
                    customer_df['total_cost'] = customer_df[['op_and_admin', 'marketing', 'incentives']].sum(axis=1)

                customer_df.sort_values('total_cost', inplace=True)

                customer_df.enrollment=customer_df.enrollment*100 #convert to percent

                customer_df.sort_values('total_cost', inplace=True)
                max_en=customer_df['enrollment'].max()
                customer_df['cumenrollment']=customer_df['enrollment'].expanding().count()*max_en/len(customer_df)
                """"""
                #pick out minimum difference from % enrollment specified
                customer_df['rounded']=customer_df['cumenrollment'].apply(lambda x: int(ENROLLMENT_RESOLUTION*round(x/ENROLLMENT_RESOLUTION)))
                customer_df['delta']=(customer_df['cumenrollment']-customer_df['rounded']).abs()

                new_row={'EV_Type': EV_TYPE,
                        'Program':PARAMS.program,
                        'Scenario': df.iloc[i].scenario,
                        'Year': df.iloc[i].year,
                        'Customer_Type': CUSTOMER_TYPE}
                for en in enrollment:
                    # find closest value
                    en_df=customer_df.loc[customer_df.rounded==int(en*100)]
                    en_df.loc[en_df.delta==en_df.delta.min()]['total_cost']

                    # costs for 0% enrollment are created but not meaningful
                    if en==0:
                        pass
                    elif en>=PARAMS.upper_limit:
                        new_row['{:.0f}%'.format((en*100))]='--'
                    else:
                        new_row['{:.0f}%'.format((en*100))]=en_df.loc[en_df.delta==en_df.delta.min()]['total_cost'].values[0]
                    
                costs=pd.concat([costs, pd.DataFrame(new_row, index=[i])])
    
    costs=costs.applymap(lambda x: f'{x:.2f}' if isinstance(x, float) else x)
    costs.to_csv(os.path.join(cwd,'outputs',f"costs_table_{ENROLLMENT_RESOLUTION}_pct.csv"),index=False)
    return costs

def cost_per_EV(PERCENT, costs=None, **kwargs):
    """returns per vehicle cost in USD for specified parameters. 
    If more than one possible cost exists, this will return a DataFrame for all costs."""
    assert isinstance(PERCENT, int), "PERCENT must be an int"
    assert PERCENT<=100, "PERCENT cannot but greater than 100"
    assert PERCENT>0, "PERCENT must be greater than zero"
    parameters=['EV_Type','Program','Scenario', 'Year', 'Customer_Type']
    args={'EV_Type': ['LDV', 'MHDV'],
          'Program':['DLC','RTP','TOU'],
          'Scenario':['high', 'mid', 'low', 'flat'],
          'Year': [2025, 2030, 2035, 2040, 2045, 2050],
          'Customer_Type': ['new', 'recurring']}
    for key, parameter in kwargs.items():
        assert key in parameters, f"{key} is not a defined parameter, expected parameters are 'EV_Type','Program','Scenario', 'Year', 'Customer_Type'"
        assert parameter in args[key], f"{parameter} is not an option for {key}, see values in cost table for examples "
    
    if costs is None:
        cwd = os.getcwd()
        costs=pd.read_csv(os.path.join(cwd, 'outputs','costs_table.csv'))
    else:
        #check if percent is in columns already
        cols=list(costs.columns)
        cols=[int(col.split('%')[0]) for col in cols if col not in parameters] 
        if PERCENT not in cols:
            print("cost table passed is not high resolution enough. Reading new table with 1% resolution.")
            cwd = os.getcwd()
            costs=pd.read_csv(os.path.join(cwd, 'outputs','costs_table.csv'))
                
    percent_col='{:.0f}%'.format(PERCENT)
    percent_df=costs.copy()
    for key, parameter in kwargs.items():
        percent_df=percent_df.loc[(percent_df[key]==parameter)]
    return percent_df[parameters+[percent_col]]

def participation_given_cost(COST, PRECISION=1, costs=None):
    """returns percent participation acheived given costs per vehicle. If no precision is defined,
    results to the nearest dollar are returned."""
    assert isinstance(PRECISION, int), "PRECISION must be an int"
    assert PRECISION>=1, "PRECISION cannot be less than $1"

    if ((costs is None) or (len(list(costs.columns))<104)):
        cwd = os.getcwd()
        costs=pd.read_csv(os.path.join(cwd, 'outputs','costs_table.csv'))
    parameters=['EV_Type','Program','Scenario', 'Year', 'Customer_Type']
    cols=set(costs.columns)
    cols=list(cols.difference(set(parameters)))
    costs[cols]=costs[cols].applymap(lambda x: float(x) if (x != '--') else x)
    rounded=costs.applymap(lambda x: (PRECISION * round(x/PRECISION)) if isinstance(x, float) else x)
    rounded_cost=PRECISION * round(COST/PRECISION)

    results=pd.concat([costs[parameters],costs[rounded[cols]==rounded_cost][cols]], axis=1)

    results=results.melt(id_vars=parameters,value_vars=cols)
    results=results.loc[~(results.value.isna())]
    results.rename(columns={'variable':'Percent_EVs_Participating',
                            'value': 'Cost_per_EV'},inplace=True)
    return results

if __name__ == "__main__":
    #User specified variables
    ENROLLMENT_RESOLUTION = 1 #percent
    
    #create tables
    costs=create_cost_table(ENROLLMENT_RESOLUTION)

    """get cost per vehicles"""
    
    PERCENT=20

    # If costs table with 1% enrollment resolution passed, use that. Otherwise, make table
    # User can specify any of 'EV_Type','Program','Scenario', 'Year', 'Customer_Type'
    example_1=cost_per_EV(PERCENT, EV_Type='LDV')
    example_2=cost_per_EV(PERCENT, costs, EV_Type='LDV', Program='DLC',Scenario='high', Year=2025, Customer_Type='new')
 

    """get percent enrollment given per vehicle budget"""
    COST=200
    # User can specify +/- how many dollars per vehicle
    PRECISION=1
    participation_given_cost(COST)

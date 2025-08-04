import os
import math
import matplotlib.pyplot as plt

import numpy as np
import pandas as pd
import evmc_supply_curves

CUSTOMER_RESOLUTION=1000 # determines precision of the table outputs

parameters={'EV_Type': ['LDV', 'MHDV'],
            'Program':['DLC','RTP','TOU'],
            'Scenario':['high', 'mid', 'low', 'flat'],
            'Year': [2025, 2030, 2035, 2040, 2045, 2050],
            'Customer_Type': ['new', 'recurring']}
    
class ScenarioParameters():
    """Loads variables and calculates supply curve features resulting from inputs"""    
    def __init__(self, vars_row, customer_type):
        self.new_install = vars_row['new_install'].values[0]
        self.customer_type = customer_type
        self.no_install = 1-self.new_install
        self.upper_limit = vars_row['upper_limit'].values[0]
        self.lower_limit = 0
        self.incentive_annual = vars_row['incentive_annual'].values[0]
        self.enrollment_anch = vars_row['enrollment_anch'].values[0]
        self.incentive_new_install = vars_row['incentive_new_install'].values[0]
        self.program_op = vars_row['program_op'].values[0]
        self.init_admin = vars_row['init_admin'].values[0]
        self.marketing = vars_row['marketing'].values[0]
        self.program = vars_row['program'].values[0]
        self.ev_type = vars_row['ev_type'].values[0]

    def calc_beta(self):
        """given an incentive and enrollment, find beta to use for customer response to incentives.
        Final equation using beta: enrollment_upperlimit * (1-np.exp(-beta*incentives))"""
        temp=(self.enrollment_anch-self.upper_limit)/(self.lower_limit-self.upper_limit)
        #customer enrollment increasing in response to marketing for LDVs in TOU programs 
        if ( (self.program == 'TOU') and (self.ev_type=='LDV') ): 
            with np.errstate(divide='ignore'):
                self.no_install_beta=np.divide(math.log(temp),(-self.marketing))
                self.install_beta = np.divide(math.log(temp),(-self.marketing))
        #customer enrollment responds to incentives in all other cases
        else:
            # find unique beta for customers requiring a new install
            with np.errstate(divide='ignore'):
                self.no_install_beta = np.divide(math.log(temp),(-self.incentive_annual))
                self.install_beta = np.divide(math.log(temp),(-self.incentive_new_install))
                
    def df_by_required_install(self, install_type, num_customers=CUSTOMER_RESOLUTION):
        """return df: each row is a customer with columns of associated costs
        and resulting enrollment probability"""

        assert install_type in ['new_install','no_install']

        customer_df=pd.DataFrame(columns=['incentive','op_and_admin','marketing'])

        """set install ratio to proportion of customers requiring a new charger or not"""
        if install_type=='new_install':
            cust_frac = 0 if self.customer_type=='recurring' else self.new_install  
            incentive = self.incentive_new_install  
        else:  
            cust_frac = self.no_install  
            incentive = self.incentive_annual  

        num_customers = int(num_customers * cust_frac)  
        
        if num_customers == 0:  
            return pd.DataFrame()  

        if self.customer_type=='new':
            op_and_admin=self.program_op+self.init_admin
        elif self.customer_type=='recurring':
            op_and_admin=self.program_op

        install_type_df=pd.DataFrame(
            {'incentive': incentive,
             'op_and_admin': op_and_admin,
             'marketing':self.marketing}, index=[0])
        new_cols=pd.concat([install_type_df]*int(num_customers), ignore_index=True)
        customer_df=pd.concat( [customer_df, new_cols] )
      
        """add incentive and resulting enrollment columns (enrollemnt will be x-axis)"""
        enrollment = [i*(self.upper_limit/int(num_customers))\
                    for i in list(range(int(num_customers)))]
        
        incentives = self._calc_incentives(enrollment, install_type)

        customer_df['incentives'], customer_df['enrollment'] = incentives, enrollment

        return customer_df
    
    def _calc_incentives(self, enrollment, install_type):
        """ use decaying exponential fn, defined by curve parameters,
            to calculate a list of incentives given a list of enrollments values"""
        if install_type=='new_install':
            beta=self.install_beta
        else:
            beta=self.no_install_beta
        if beta == None:
            incentives = [0]* len(enrollment)
        else:
            ll, ul =self.lower_limit, self.upper_limit
            incentives = [np.log( 1 - (en-ll)/(ul-ll) )/-beta if ((en-ll)/(ul-ll))<1 else 0 for en in enrollment]
        return incentives

class SupplyCurves():
    """ Table of EVMC Supply Curves for all scenarios, programs, vehicle types, and years. 
        Users can create new tables at a specified resolution of percent enrollment, or use the 
        1% enrollment table provided. Additional functions can query for costs given a 
        targeted enrollment level."""
    
    def __init__(self,enrollment_resolution=1, table_path=os.path.join(evmc_supply_curves.ROOT_DIR,'outputs')):
        self.table=pd.DataFrame()
        self.enrollment_resolution=enrollment_resolution
        # user can provide a different path
        self.table_path=os.path.join(table_path,f'costs_table_{enrollment_resolution}_pct.csv')

    def load_existing_table(self):
        """This function will read in a dataframe of already existing values for a given enrollment resolution to
        SupplyCurves.table. If the table has not already been generated, create_cost_table() should be used instead."""
        #check that the table for the specified resolution exists
        if not os.path.exists(self.table_path):
            raise NameError( f"No cost table found. Check that a table with {self.enrollment_resolution}%\
                             \nresolution exists and the path to the table is correct: {self.table_path}\
                             \nIf the path is correct and no table exists, use create_cost_table() instead\
                             \n of load_existing_table().")
        self.table = pd.read_csv(os.path.join(evmc_supply_curves.ROOT_DIR, 'outputs',f'costs_table_{self.enrollment_resolution}_pct.csv'))
 
    def create_cost_table(self, overwrite=False):
        """SupplyCurves.table will be a dataframe of per vehicle costs for a given enrollment resolution. This will create a new 
        table of supply curves for this resolution, saved to the 'table_path'."""
        if (os.path.exists(self.table_path) and not overwrite):
            raise NameError(f"A table for a resolution of {self.enrollment_resolution}% already exists in the specified path:\
                            \n\t{self.table_path}\
                            \nTo overwrite this table, use create_cost_table(overwrite=True). Alternatively, specify a new\
                            \ndirectory, or use SupplyCurves.load_existing_table().")

        # create list of enrollment levels to calculation as a ratio (vs percent)
        enrollment = [self.enrollment_resolution*i/100 for i in range(int(100/self.enrollment_resolution))]        
        costs=pd.DataFrame()
        df = pd.read_csv(os.path.join(evmc_supply_curves.ROOT_DIR,'cost_inputs','scenario_vars.csv'))
        
        for ev_type in parameters['EV_Type']:
            df_ev = df.loc[(df.ev_type==ev_type)]
            for CUSTOMER_TYPE in ['new','recurring']:
                for i in range(len(df_ev)):
                    #get values and cost caluculations for each program, year, and scenario
                    PARAMS=ScenarioParameters(df_ev.iloc[i].to_frame().T, CUSTOMER_TYPE)
                    PARAMS.calc_beta()

                    """mix of new chargers and no new chargers"""
                    customer_df = PARAMS.df_by_required_install('new_install', num_customers=CUSTOMER_RESOLUTION) 
                    customer_df['install']=['new_install']*len(customer_df)
                    
                    no_install_df=PARAMS.df_by_required_install('no_install', num_customers=CUSTOMER_RESOLUTION)
                    no_install_df['install']=['no_install']*len(no_install_df)

                    customer_df = customer_df._append(no_install_df)

                    #Don't double count marketing for LDV TOU
                    if ( (PARAMS.ev_type=='LDV') and (PARAMS.program=='TOU') ):
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
                    customer_df['rounded']=customer_df['cumenrollment'].apply(lambda x: int(self.enrollment_resolution*round(x/self.enrollment_resolution)))
                    customer_df['delta']=(customer_df['cumenrollment']-customer_df['rounded']).abs()

                    new_row={'EV_Type': ev_type,
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
        
        costs=costs.map(lambda x: f'{x:.2f}' if isinstance(x, float) else x)
        costs.to_csv(os.path.join(evmc_supply_curves.ROOT_DIR,'outputs',f"costs_table_{self.enrollment_resolution}_pct.csv"),index=False)
        self.table=costs    

    def cost_per_EV(self, percent, **kwargs):
        """returns per vehicle cost in USD for specified parameters. 
        If more than one possible cost exists, this will return a DataFrame for all costs."""
        if not isinstance(percent, int):
            raise ValueError("percent must be an int")
        if percent>100:
            raise ValueError("percent cannot be greater than 100")
        if percent<=0:
            raise ValueError("percent must be greater than zero")
        if self.table.empty:
            raise NameError("No cost table specified for query. Please use SupplyCurves.load_existing_table()")
        
        for key, parameter in kwargs.items():
            if key not in parameters:
                raise ValueError(f"{key} is not a defined parameter, expected parameters are  {list(parameters.keys())}'")
            if parameter not in parameters[key]:
                raise ValueError(f"{parameter} is not an option for {key}, see values in cost table for examples ")
        
        costs=self.table

        #check if percent is in columns already
        cols=list(costs.columns)
        cols=[int(col.split('%')[0]) for col in cols if col not in parameters] 
        if percent not in cols:
            # For best results, users should use a table of sufficient resolution (e.g. a query for 12% enrollment 
            # using a table with 10% precision will return a value closer to costs for 10% enrollment)
            print("cost table passed is not high resolution enough. Reading new table with 1% resolution.")
            self.enrollment_resolution=1
            self.load_existing_table()
            costs=self.table
                
        percent_col='{:.0f}%'.format(percent)
        percent_df=costs.copy()
        for key, parameter in kwargs.items():
            percent_df=percent_df.loc[(percent_df[key]==parameter)]
        return percent_df[list(parameters.keys())+[percent_col]]
    
    
    def create_betas_table(self):
        """Returns a table of beta parameters calculated from given incentives or marketing costs and
        customer enrollment responses. A .csv is also saved to the 'outputs' directory."""
        betas = pd.DataFrame()
        for ev_type in parameters['EV_Type']:
            df = pd.read_csv(os.path.join(evmc_supply_curves.ROOT_DIR, 'cost_inputs','scenario_vars.csv'))
            df = df.loc[(df.ev_type==ev_type)]
            for CUSTOMER_TYPE in ['new','recurring']:
                for i in range(len(df)):
                    #get values and cost caluculations for each program, year, and scenario
                    PARAMS=ScenarioParameters(df.iloc[i].to_frame().T, CUSTOMER_TYPE)
                    PARAMS.calc_beta()
                    
                    new_row={'EV_Type': ev_type,
                            'Program':PARAMS.program,
                            'Scenario': df.iloc[i].scenario,
                            'Year': df.iloc[i].year,
                            'Customer_Type': CUSTOMER_TYPE,
                            'beta_no_install': PARAMS.no_install_beta,
                            'beta_install_required': PARAMS.install_beta if CUSTOMER_TYPE=='new' else np.nan}
                        
                    betas=pd.concat([betas, pd.DataFrame(new_row, index=[i])])
        self.betas=betas   
        betas.to_csv(os.path.join(evmc_supply_curves.ROOT_DIR,'outputs',f"betas_table.csv"),index=False)
        return betas

# Plotting functions
def plot_incentives_v_enrollment(curve_params_dict, ax, incentives=list(range(0,1000))):
    """add a plot line of x = incentives and y = % enrollements given curve parameters
    decaying exponential response of enrollements"""
    enrollments=[curve_params_dict['lower_limit']+(curve_params_dict['upper_limit']-curve_params_dict['lower_limit'])\
                   *(1-math.exp(-curve_params_dict['beta']*i)) for i in incentives]
    ax.plot(incentives, [100*p for p in enrollments], \
         label='Assume {:.0f}% enrollment with ${} incentive\n    (Upper limit of {:.0f}%)'\
            .format( (curve_params_dict['enrollment_anch']*100),(curve_params_dict['incentive']),(curve_params_dict['upper_limit']*100) ))

def plot_cost_v_kW(customer_df,INPUTS):
    fig, ax = plt.subplots(figsize=(8, 6))  
    ax.plot( customer_df['MW']*1000, customer_df['value']/1000, lw=3, label='All Costs', )
    plt.ylim(0,None)
    plt.ylabel('Cost ($/kW)')
    plt.xlabel('kW')
    plt.title('{} Scenario: {} {} , {} {} Customers'
            .format(INPUTS.DATA['user_inputs']['scenario'].capitalize(), \
                    INPUTS.program,
                    INPUTS.DATA['user_inputs']['year'], \
                    INPUTS.DATA['user_inputs']['customer_type'].capitalize(),\
                    INPUTS.DATA['user_inputs']['ev_type']))
    return fig

def plot_cost_v_ev(customer_df,INPUTS):
    fig, ax = plt.subplots(figsize=(8, 6))  
    ax.plot( customer_df['evs_enrolled'], customer_df['total_cost'], lw=3, label='All Costs',color= 'darkorchid' )
    plt.ylabel('Cost ($/Vehicle)')
    plt.xlabel('Percent of EVs Participating')
    plt.title('{}-Flexibility Scenario: {} {}, {} {} Customers'
            .format(INPUTS.DATA['user_inputs']['scenario'].capitalize(), \
                    INPUTS.program,
                    INPUTS.DATA['user_inputs']['year'], \
                    INPUTS.DATA['user_inputs']['customer_type'].capitalize(),\
                    INPUTS.DATA['user_inputs']['ev_type']))
    colors={    'op_and_admin': 'dodgerblue',
                'marketing':'crimson',
            }
    names={     'op_and_admin': 'Administrative and operating',
                'marketing':'Marketing',
            }
    fixed_costs={}
    upper_x=int(np.ceil(customer_df['enrollment'].max()))
    if ((INPUTS.program=='TOU') and (INPUTS.DATA['user_inputs']['ev_type']=='LDV')):
        costs_list=['op_and_admin']
        ax.plot( customer_df['evs_enrolled'], customer_df['total_cost'], lw=1.5, color='crimson',linestyle='--', label='Marketing', )
    else: 
        costs_list=['op_and_admin', 'marketing']

    for cost in costs_list:
        fixed_costs[cost]=customer_df[cost].values[0]
    
    start_y=0
    for cost in fixed_costs.keys():
        if fixed_costs[cost]>0:
            ax.plot( list(range(0,upper_x)),[fixed_costs[cost]+start_y]*upper_x, color=colors[cost], lw=3,label=names[cost] )
        start_y += fixed_costs[cost]
    ax.legend()
    return fig
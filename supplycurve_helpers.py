
import os
import math
import logging
import matplotlib.pyplot as plt

import numpy as np
import pandas as pd
import yaml
from yaml.loader import SafeLoader

logger = logging.getLogger('layerstack.layers.DispatchAgainstPricesWithMappingInfoInDeviceMetadata').setLevel(logging.INFO)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def flatten(xss):
    return [x for xs in xss for x in xs]

class InputYMLHandler(): #handling for supply curve inputs yml

    def __init__(self, ymlpath='supplycurveconfig.yml'):
        #TODO: unpack this directly to variables
        with open(ymlpath) as f:
            self.DATA = yaml.load(f,Loader=SafeLoader)
        self.reeds_bins = self.DATA['user_inputs']['reeds_bins']
        # self.reeds_techs = self.DATA['user_inputs']['reeds_techs']
        self.year = self.DATA['user_inputs']['year']
        self.customer_type = self.DATA['user_inputs']['customer_type'].lower()
        self.ev_type = self.DATA['user_inputs']['ev_type'].upper()
        self.scenario = self.DATA['user_inputs']['scenario']
        # self.tech = self.DATA['user_inputs']['tech']

        self.TRIPWEIGHT = self.DATA['TEMPO_data']['TRIPWEIGHT']
        self.EVCOUNT = self.DATA['TEMPO_data']['EVCOUNT']*self.TRIPWEIGHT
        self.MWPEREV = self.DATA['TEMPO_data']['MWPEREV']
        self.REGIONSFROMTEMPO = self.DATA['TEMPO_data']['REGIONSFROMTEMPO']

        self.costs_filename = self.DATA['cost_filename']

        self._check_inputs() 

    
    def _check_inputs(self):
        if self.customer_type not in ['new','recurring']:
            return ValueError(f"customer type is {self.customer_type}, but only valid inputs are currently new and recurring.")
        if self.year < 2025 or self.year > 2050:
            return ValueError(f"year is {self.year}, but only valid inputs are 2025-2050.")
        if self.scenario not in ['low','mid', 'high', 'flat']:
            return ValueError(f"scenario name is {self.scenario}, valid input must be 'low','mid', 'high', or 'flat'")
       
        logger.info(" ...checked inputs without error!")
        return None
    
    def select_params(self,path, tech, filename): 
        #this is currently a weird way to specify up tech/program. Why not just specify program instead of tech?
        #leaving this with "tech" as an arg to anticipate ReEDS-ness but might make sense to change

        #look up program corresponding to tech
        tech_df = pd.read_csv(os.path.join(path, 'costs','tech_to_program_lookup.csv'))
        self.program=tech_df.loc[tech_df.tech==tech].program.values[0]
        #look up scenario variables corresponding to inputs
        df = pd.read_csv(os.path.join(path, 'costs',f'{filename}.csv'))
        vars_row = df.loc[(df.ev_type==self.ev_type)&(df.year==self.year)&\
                          (df.scenario==self.scenario)&(df.program==self.program)]
        return vars_row
    
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
        """given an incentive and enrollment, anchor fn to this value"""
        temp=(self.enrollment_anch-self.upper_limit)/(self.lower_limit-self.upper_limit)
        if ((self.program == 'TOU')&(self.ev_type=='LDV')): 
            if self.marketing > 0:
                self.no_install_beta=math.log(temp)/(-self.marketing)
                self.install_beta = None #install never required for TOU
            else:
                self.no_install_beta = None
                self.install_beta = None #install never required for TOU
        else:
            if self.incentive_new_install > 0: 
                self.install_beta=math.log(temp)/(-self.incentive_new_install) 
            else:
                self.install_beta = None
            
            if self.incentive_annual > 0: 
                self.no_install_beta=math.log(temp)/(-self.incentive_annual) 
            else:
                self.no_install_beta = None

                
    def df_by_required_install(self, install_type, num_customers=1000):
        #TODO: rewrite to return new installs + no new installs (not called 2x, no install_type arg needed)
        """return df: each row is a customer with columns of associated costs
        and resulting enrollment probability"""

        assert install_type in ['new_install','no_install']

        customer_df=pd.DataFrame(columns=['incentive','op_and_admin','marketing'])

        """set install ratio to proportion of customers requiring a new charger or not"""
        #recurring customers should not need a new charger???
        if install_type=='new_install':
            install = self.new_install
            incentive = self.incentive_new_install
            if self.customer_type=='recurring':
                install=0
        else:
            install = self.no_install
            incentive = self.incentive_annual

        if self.customer_type=='new':
            op_and_admin=self.program_op+self.init_admin
        elif self.customer_type=='recurring':
            op_and_admin=self.program_op
        install_type_df=pd.DataFrame(
            {'incentive': incentive,
             'op_and_admin': op_and_admin,
             'marketing':self.marketing}, index=[0])
        
        customer_df=customer_df._append([install_type_df]*int(num_customers*install))
      
        """add incentive and resulting enrollemnt columns (enrollemnt will be x-axis)"""
        enrollment = [i*(self.upper_limit/int(num_customers*install))\
                    for i in list(range(int(num_customers*install)))]
        
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


def plot_incentives_v_enrollment(curve_params_dict, ax, incentives=list(range(0,1000))):
    """add a plot line of x = incentives and y = % enrollements given curve parameters
    decaying exponential response of enrollements"""
    enrollements=[curve_params_dict['lower_limit']+(curve_params_dict['upper_limit']-curve_params_dict['lower_limit'])\
                   *(1-math.exp(-curve_params_dict['beta']*i)) for i in incentives]
    ax.plot(incentives, [100*p for p in enrollements], \
         label='Assume {:.0f}% enrollment with ${} incentive\n    (Upper limit of {:.0f}%)'\
            .format( (curve_params_dict['enrollment_anch']*100),(curve_params_dict['incentive']),(curve_params_dict['upper_limit']*100) ))


def calc_enrollment(incentives, curve_params_dict):
    """ use decaying exponential fn, defined by curve parameters,
        to calculate a list of enrollments given a list of incentive values"""
    enrollements=[curve_params_dict['lower_limit']+(curve_params_dict['upper_limit']-curve_params_dict['lower_limit'])\
                   *(1-math.exp(-curve_params_dict['beta']*i)) for i in incentives]
    return enrollements

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
    if INPUTS.DATA['user_inputs']['ev_type']=='MHDV':
        ymax=16000
    else:
        ymax=800
    plt.ylim(0,ymax)
    plt.xlim(0,80)
    plt.ylabel('Cost ($/Vehicle)')
    plt.xlabel('Percent of EVs Participating')
    plt.title('{}-Flexibility Scenario: {} {}, {} {} Customers'
            .format(INPUTS.DATA['user_inputs']['scenario'].capitalize(), \
                    INPUTS.program,
                    INPUTS.DATA['user_inputs']['year'], \
                    INPUTS.DATA['user_inputs']['customer_type'].capitalize(),\
                    INPUTS.DATA['user_inputs']['ev_type']))
    colors={    'op_and_admin': 'dodgerblue',
                # 'firmware_updates': 'darkorchid',
                # 'admin_op': 'mediumslateblue',
                'marketing':'crimson',
            }
    names={     'op_and_admin': 'Administrative and operating',
                'marketing':'Marketing',
            }
    fixed_costs={}
    upper_x=int(np.ceil(customer_df['enrollment'].max()))
    if ((INPUTS.program=='TOU')&(INPUTS.DATA['user_inputs']['ev_type']=='LDV')):
        costs_list=['op_and_admin']
        ax.plot( customer_df['evs_enrolled'], customer_df['total_cost'], lw=1.5, color='crimson',linestyle='--', label='Marketing', )
    else: 
        costs_list=['op_and_admin', 'marketing']

    for cost in costs_list:
        fixed_costs[cost]=customer_df[cost].values[0]
    
    start_y=0
    # start_y= [0]*len(customer_df)
    for cost in fixed_costs.keys():
        if fixed_costs[cost]==0:
            pass
        else:
            ax.plot( list(range(0,upper_x)),[fixed_costs[cost]+start_y]*upper_x, color=colors[cost], lw=3,label=names[cost] )
            # ax.plot( list(range(0,upper_x)), list(customer_df[cost].values+ start_y),color=colors[cost], lw=1.5,label=names[cost] )
        start_y += fixed_costs[cost]
    # if ((((customer_df.total_cost.max()-customer_df.total_cost.min())/customer_df.total_cost.min()))<0.1):
    #     ax.set_ylim([0,(customer_df.total_cost.max()*1.5)])
    ax.legend()
    return fig
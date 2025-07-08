from evmc_supply_curves.supplycurve_helpers import SupplyCurves

if __name__ == "__main__":
    #User specified variables
    ENROLLMENT_RESOLUTION = 20 #percent
    
    #create tables
    sc=SupplyCurves()
    sc.create_betas_table()
    sc.load_existing_table()

    sc2=SupplyCurves(enrollment_resolution=ENROLLMENT_RESOLUTION)
    sc2.create_cost_table()
 

    """get cost per vehicles"""
    
    PERCENT=20

    # If costs table with 1% enrollment resolution passed, use that. Otherwise, make table
    # User can specify any of 'EV_Type','Program','Scenario', 'Year', 'Customer_Type'
    example_1=sc2.cost_per_EV(PERCENT, EV_Type='LDV')
    print(f"A dataframe of costs per EV of enabling 20% of LDVs to provide managed charging\
           \nin all scenarios and years:\n{example_1}") 
    
    example_2=sc2.cost_per_EV(15, EV_Type='LDV', Program='DLC',Scenario='high', Year=2025, Customer_Type='new')
    print(f"The cost per EV of enabling 15% of LDVs to participate in direct load control\
          \nprograms in a High-Flexibility scenario in 2025 is ${example_2['15%'].values[0]}") 
 

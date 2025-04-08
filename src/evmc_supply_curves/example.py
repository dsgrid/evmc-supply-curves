from .supplycurve_helpers import SupplyCurves

if __name__ == "__main__":
    #User specified variables
    ENROLLMENT_RESOLUTION = 10 #percent
    
    #create tables
    sc=SupplyCurves()
    sc.load_existing_table()

    sc2=SupplyCurves(enrollment_resolution=ENROLLMENT_RESOLUTION)
    sc2.create_cost_table()
 

    """get cost per vehicles"""
    
    PERCENT=20

    # If costs table with 1% enrollment resolution passed, use that. Otherwise, make table
    # User can specify any of 'EV_Type','Program','Scenario', 'Year', 'Customer_Type'
    example_1=sc2.cost_per_EV(PERCENT, EV_Type='LDV')
    example_2=sc2.cost_per_EV(15, EV_Type='LDV', Program='DLC',Scenario='high', Year=2025, Customer_Type='new')
 

    """get percent enrollment given per vehicle budget"""
    COST=200
    # User can specify +/- how many dollars per vehicle
    PRECISION=1
    participation_200=sc2.participation_given_cost(COST, PRECISION)

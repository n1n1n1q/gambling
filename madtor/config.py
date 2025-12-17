"""
MADTOR Configuration Parameters
Based on Operation Beluga data (2008-2010)
"""

# ============================================================================
# TEMPORAL PARAMETERS
# ============================================================================
SIMULATION_YEARS = 5
TICKS_PER_YEAR = 365
TOTAL_TICKS = SIMULATION_YEARS * TICKS_PER_YEAR
TICK_DURATION_HOURS = 24

# ============================================================================
# AGENT INITIALIZATION PARAMETERS
# ============================================================================
INITIAL_TRAFFICKERS = 5
INITIAL_PACKAGERS = 5
INITIAL_RETAILERS = 34
INITIAL_TOTAL_MEMBERS = INITIAL_TRAFFICKERS + INITIAL_PACKAGERS + INITIAL_RETAILERS

# Calibration targets (2008 vs 2010)
TRAFFICKERS_2008 = 5
TRAFFICKERS_2010 = 16
PACKAGERS_2008 = 5
PACKAGERS_2010 = 13
RETAILERS_2008 = 34
RETAILERS_2010 = 37

# ============================================================================
# DRUG TRAFFICKING PARAMETERS
# ============================================================================
# Unit doses (cocaine 0.25g per dose)
GRAM_PER_DOSE = 0.25
UNIT_DOSE_2008 = 580
UNIT_DOSE_2010 = 1500
UNIT_DOSE_MIN_2008 = 530
UNIT_DOSE_MIN_2010 = 1370
UNIT_DOSE_MAX_2008 = 900
UNIT_DOSE_MAX_2010 = 2340

# Drug package sizes (grams)
DRUG_PACKAGE_RETAILERS = 23 * GRAM_PER_DOSE  # 5.75g per package

# Wholesale and retail prices (€/gram, UNODC data)
WHOLESALE_PRICE_2008 = 40.20
WHOLESALE_PRICE_2009 = 40.68
WHOLESALE_PRICE_2010 = 43.90

RETAIL_PRICE_2008 = 70.26
RETAIL_PRICE_2009 = 70.47
RETAIL_PRICE_2010 = 75.36

# Price per unit dose (€)
PRICE_PER_DOSE = 32

# ============================================================================
# FINANCIAL PARAMETERS
# ============================================================================
# Daily costs and profits (€)
COST_PER_DAY_2008 = 10300
COST_PER_DAY_2010 = 26900

WEEKLY_PROFIT_2008 = 5000 * 7
WEEKLY_PROFIT_2010 = 12900 * 7

# Start-up parameters
START_UP_MONTHS = 2
START_UP_MONEY = 26900 * PACKAGERS_2008 / PACKAGERS_2010 * START_UP_MONTHS * 30

# Profit shares and constraints
TRAFFICKERS_SHARE_OF_PROFITS = 0.7
RETAILERS_SHARE_OF_PROFITS = 0.18
PROFIT_OF_RETAILERS_MAX = 500

# Wage parameters
ARRESTED_RETAILERS_WEEKLY_WAGE = 225
ARRESTED_OTHER_WEEKLY_WAGE = 500
ARRESTED_HOMICIDE_FAMILY_WAGES = 2 * 3500

# Max workload
DRUG_MAX_OF_PACKAGERS = 500  # grams per day
MAX_RETAILER_PROFIT = 500

# ============================================================================
# LAW ENFORCEMENT PARAMETERS
# ============================================================================
# Disruption timing
MAJOR_DISRUPTION_YEAR = 2
MAJOR_DISRUPTION_TICK = MAJOR_DISRUPTION_YEAR * TICKS_PER_YEAR

# Arrest percentages to test
ARREST_SCENARIOS = [0, 5, 10, 20, 30, 40, 50, 60, 70, 80, 90]

# Monthly minor arrests probability
MINOR_ARREST_PROBABILITY = 0.5
STOP_ACQUIRE_DAYS_DEFAULT = 60

# ============================================================================
# NETWORK PARAMETERS
# ============================================================================
# Criminal expertise distribution
CRIMINAL_EXPERTISE_MEAN = 0.5
CRIMINAL_EXPERTISE_STD = 0.3
CRIMINAL_EXPERTISE_MIN = 0.1
CRIMINAL_EXPERTISE_MAX = 1.0

# ============================================================================
# DISRUPTION SCENARIO MODES
# ============================================================================
DISRUPTION_MODES = ["scenario1", "scenario2", "scenario3"]

# Scenario 3 disruption timeslots (ticks)
SCENARIO3_DISRUPTION_TICKS = [450, 630, 810, 990, 1170, 1350, 1530]

# ============================================================================
# EFFICIENCY VS SECURITY SETTINGS
# ============================================================================
EFFICIENCY_VS_SECURITY_VALUES = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]

# Profit ranges by efficiency-vs-security level
PROFIT_RANGES = {
    0.0: {
        "traffickers_min": 350,
        "traffickers_max": 400,
        "packagers_min": 175,
        "packagers_max": 200,
    },
    0.2: {
        "traffickers_min": 400,
        "traffickers_max": 466,
        "packagers_min": 200,
        "packagers_max": 233,
    },
    0.4: {
        "traffickers_min": 450,
        "traffickers_max": 533,
        "packagers_min": 225,
        "packagers_max": 266,
    },
    0.5: {
        "traffickers_min": 475,
        "traffickers_max": 566,
        "packagers_min": 237,
        "packagers_max": 283,
    },
    0.6: {
        "traffickers_min": 500,
        "traffickers_max": 600,
        "packagers_min": 250,
        "packagers_max": 300,
    },
    0.8: {
        "traffickers_min": 200,
        "traffickers_max": 700,
        "packagers_min": 50,
        "packagers_max": 350,
    },
    1.0: {
        "traffickers_min": 200,
        "traffickers_max": 800,
        "packagers_min": 50,
        "packagers_max": 400,
    },
}

# ============================================================================
# SIMULATION CONTROL
# ============================================================================
NUM_SIMULATIONS_PER_SCENARIO = 100
RANDOM_SEED = None  # Set to None for random, or int for reproducibility

# ============================================================================
# OUTPUT PARAMETERS
# ============================================================================
COLLECT_STATISTICS = True
STATISTICS_FREQUENCY = 1  # Collect every N ticks
VERBOSE_OUTPUT = False

"""
Main MADTOR simulation engine
Orchestrates the complete simulation loop
"""

import random
import math
import logging
from typing import Dict, List, Tuple
import json
from datetime import datetime

import madtor.config as config
from madtor.agents import Trafficker, Packager, Retailer, Agent, Network
from madtor.activities import DrugTraffickingActivities
from madtor.law_enforcement import LawEnforcement
from madtor.statistics import NetworkStatistics, DataCollector


class MADTORSimulation:
    """Main simulation controller"""
    
    def __init__(self, arrest_scenario: int = 0, disruption_mode: str = "scenario1", 
                 efficiency_vs_security: float = 0.5, seed: int = None):
        """
        Initialize simulation
        
        Args:
            arrest_scenario: Percentage of members to arrest in major disruption
            disruption_mode: "scenario1", "scenario2", or "scenario3"
            efficiency_vs_security: Trade-off parameter (0.0 to 1.0)
            seed: Random seed for reproducibility
        """
        self.seed = seed if seed is not None else random.randint(0, 2**32 - 1)
        random.seed(self.seed)
        
        self.arrest_scenario = arrest_scenario
        self.disruption_mode = disruption_mode
        self.efficiency_vs_security = efficiency_vs_security
        
        self.tick = 0
        self.running = True
        
        # Initialize data structures
        self.network = None
        self.global_state = self._initialize_global_state()
        self.activities = None
        self.law_enforcement = None
        self.statistics = None
        self.data_collector = DataCollector()
        
        # Setup
        self._setup()
    
    def _initialize_global_state(self) -> Dict:
        """Initialize global state variables"""
        return {
            # Temporal
            'tick': 0,
            'current_year': 1,
            
            # Agent counts
            'n_active_traffickers': config.INITIAL_TRAFFICKERS,
            'n_active_packagers': config.INITIAL_PACKAGERS,
            'n_active_retailers': config.INITIAL_RETAILERS,
            
            # Drug trafficking
            'drug_package_of_traffickers': 0,
            'drug_package_of_packagers': 0,
            'drug_package_of_retailers': config.DRUG_PACKAGE_RETAILERS,
            'gram_per_dose': config.GRAM_PER_DOSE,
            'unit_dose': config.UNIT_DOSE_2008,
            'unit_dose_min': config.UNIT_DOSE_MIN_2008,
            'unit_dose_max': config.UNIT_DOSE_MAX_2008,
            'unit_dose_now': 0,
            
            # Stock tracking
            'stock_drug': 0,
            'stock_drug_traffickers': 0,
            'stock_drug_packagers': 0,
            'stock_drug_retailers': 0,
            'target_stock_drug': 0,
            
            # Prices
            'wholesale_price': config.WHOLESALE_PRICE_2008,
            'wholesale_price_now': config.WHOLESALE_PRICE_2008,
            'retail_price': config.RETAIL_PRICE_2008,
            'price_per_dose': config.PRICE_PER_DOSE,
            
            # Financial
            'cash_box': 0,
            'revenues': 0,
            'expenses': 0,
            'profit_of_traffickers': 0,
            'profit_of_packagers': 0,
            'profit_of_retailers': 0,
            'weekly_profit': config.WEEKLY_PROFIT_2008,
            'weekly_profit_now': 0,
            'cost_per_day': config.COST_PER_DAY_2008,
            
            # Profit tracking
            'profit_of_traffickers_min': config.PROFIT_RANGES[self.efficiency_vs_security]['traffickers_min'],
            'profit_of_traffickers_max': config.PROFIT_RANGES[self.efficiency_vs_security]['traffickers_max'],
            'profit_of_packagers_min': config.PROFIT_RANGES[self.efficiency_vs_security]['packagers_min'],
            'profit_of_packagers_max': config.PROFIT_RANGES[self.efficiency_vs_security]['packagers_max'],
            'profit_of_retailers_max': config.PROFIT_OF_RETAILERS_MAX,
            
            # Profit shares
            'traffickers_share_of_profits': config.TRAFFICKERS_SHARE_OF_PROFITS,
            'retailers_share_of_profits': config.RETAILERS_SHARE_OF_PROFITS,
            
            # Activity tracking
            'n_acquisition': 0,
            'n_exhaust_traffickers': 0,
            'n_exhaust_packagers': 0,
            'n_exhaust_retailers': 0,
            'n_exhaust_retailers_90': 0,
            
            # Law enforcement
            'arrested_mode': 'arrested%',
            'arrested%': self.arrest_scenario,
            'arrested#': 0,
            'target_of_disruption': 'turtles',
            'disruption_mode': self.disruption_mode,
            'efficiency_vs_security': self.efficiency_vs_security,
            'ticks_disruption': None,
            'stop_acquire_days': config.STOP_ACQUIRE_DAYS_DEFAULT,
            'stop_acquiring_until': None,
            
            # Arrest tracking
            'n_arrested_traffickers_minor': 0,
            'n_arrested_packagers_minor': 0,
            'n_arrested_retailers_minor': 0,
            'n_arrested_traffickers_major': 0,
            'n_arrested_packagers_major': 0,
            'n_arrested_retailers_major': 0,
            
            # Calibration values
            'traffickers_2008': config.TRAFFICKERS_2008,
            'traffickers_2010': config.TRAFFICKERS_2010,
            'packagers_2008': config.PACKAGERS_2008,
            'packagers_2010': config.PACKAGERS_2010,
            'retailers_2008': config.RETAILERS_2008,
            'retailers_2010': config.RETAILERS_2010,
            
            # Min/max tracking
            'minw': float('inf'),
            'maxw': float('-inf'),
            'minacq_ind': float('inf'),
            'maxacq_ind': float('-inf'),
            'mincash': float('inf'),
            'maxcash': float('-inf'),
        }
    
    def _setup(self):
        """Initialize simulation"""
        # Create agents
        agents = []
        
        # Create traffickers
        for i in range(config.INITIAL_TRAFFICKERS):
            agents.append(Trafficker(f"trafficker_{i}"))
        
        # Create packagers
        for i in range(config.INITIAL_PACKAGERS):
            agents.append(Packager(f"packager_{i}"))
        
        # Create retailers
        for i in range(config.INITIAL_RETAILERS):
            agents.append(Retailer(f"retailer_{i}"))
        
        # Create network
        self.network = Network(agents)
        
        # Initialize activities and law enforcement
        self.activities = DrugTraffickingActivities(self.network, self.global_state)
        self.law_enforcement = LawEnforcement(self.network, self.global_state)
        self.statistics = NetworkStatistics(self.network)
        
        # Calculate initial parameters
        self._calculate_initial_parameters()
        
        # Initialize drug stocks
        self._initialize_drug_stocks()
        
        # Create initial network links (from data file in real scenario)
        self._create_initial_links()
    
    def _calculate_initial_parameters(self):
        """Calculate drug package sizes and financial parameters"""
        efficiency_factor = self.efficiency_vs_security / 3
        
        # Drug packages
        unit_dose_range = self.global_state['unit_dose_max'] - self.global_state['unit_dose_min']
        avg_dose = self.global_state['unit_dose_min'] + unit_dose_range * efficiency_factor
        
        gram_per_dose = self.global_state['gram_per_dose']
        
        # Package for traffickers (monthly)
        n_traffickers = max(1, self.global_state['n_active_traffickers'])
        self.global_state['drug_package_of_traffickers'] = (
            avg_dose * gram_per_dose / n_traffickers * 30
        )
        
        # Package for packagers (daily)
        n_packagers = max(1, self.global_state['n_active_packagers'])
        self.global_state['drug_package_of_packagers'] = (
            avg_dose * gram_per_dose / n_packagers
        )
        
        # Financial parameters
        supply_costs = self.global_state['wholesale_price'] / self.global_state['retail_price']
        cost_per_day = self.global_state['cost_per_day']
        
        # Trafficker profits
        n_traffickers = max(1, self.global_state['n_active_traffickers'])
        profit_t = (cost_per_day - cost_per_day * supply_costs) * config.TRAFFICKERS_SHARE_OF_PROFITS / n_traffickers
        profit_t = max(self.global_state['profit_of_traffickers_min'],
                      min(self.global_state['profit_of_traffickers_max'], profit_t))
        self.global_state['profit_of_traffickers'] = profit_t
        
        # Packager profits
        n_packagers = max(1, self.global_state['n_active_packagers'])
        profit_p = (cost_per_day - cost_per_day * supply_costs) * (1 - config.TRAFFICKERS_SHARE_OF_PROFITS) / n_packagers
        profit_p = max(self.global_state['profit_of_packagers_min'],
                      min(self.global_state['profit_of_packagers_max'], profit_p))
        self.global_state['profit_of_packagers'] = profit_p
        
        # Retailer profits
        n_retailers = max(1, self.global_state['n_active_retailers'])
        profit_r = self.global_state['unit_dose'] * config.PRICE_PER_DOSE * config.RETAILERS_SHARE_OF_PROFITS / n_retailers
        profit_r = min(self.global_state['profit_of_retailers_max'], profit_r)
        self.global_state['profit_of_retailers'] = profit_r
        
        # Target stock
        start_up_months = 2
        self.global_state['target_stock_drug'] = self.global_state['unit_dose'] * gram_per_dose * start_up_months * 30
        
        # Cash box
        self.global_state['cash_box'] = config.START_UP_MONEY
    
    def _initialize_drug_stocks(self):
        """Distribute initial drug stocks"""
        target_stock = self.global_state['target_stock_drug']
        
        packagers = self.network.get_active_agents_by_type('packager')
        retailers = self.network.get_active_agents_by_type('retailer')
        
        if packagers:
            packager_stock = target_stock - 2 * self.global_state['unit_dose'] * self.global_state['gram_per_dose']
            per_packager = packager_stock / len(packagers)
            for packager in packagers:
                packager.drug = per_packager
            self.global_state['stock_drug_packagers'] = packager_stock
        
        if retailers:
            retailer_stock = target_stock - self.global_state['stock_drug_packagers']
            per_retailer = retailer_stock / len(retailers)
            for retailer in retailers:
                retailer.drug = per_retailer
            self.global_state['stock_drug_retailers'] = retailer_stock
        
        self.global_state['stock_drug'] = target_stock
    
    def _create_initial_links(self):
        """Create initial network links"""
        # In real model, this would load from T2_Links.prn file
        # For now, create random links between traffickers and packagers, packagers and retailers
        
        traffickers = self.network.get_active_agents_by_type('trafficker')
        packagers = self.network.get_active_agents_by_type('packager')
        retailers = self.network.get_active_agents_by_type('retailer')
        
        # Create some trafficker-packager links
        for packager in packagers:
            if traffickers:
                trafficker = random.choice(traffickers)
                self.network.add_link(trafficker.agent_id, packager.agent_id, "trafficker-packager")
        
        # Create some packager-retailer links
        for retailer in retailers:
            if packagers:
                packager = random.choice(packagers)
                self.network.add_link(packager.agent_id, retailer.agent_id, "packager-retailer")
    
    def step(self):
        """Execute one simulation tick (one day)"""
        self.tick += 1
        self.global_state['tick'] = self.tick
        
        # Reset daily aggregates
        self.global_state['revenues'] = 0
        self.global_state['expenses'] = 0
        self.global_state['weekly_profit_now'] = 0
        
        # Drug trafficking activities
        self.activities.acquire_drug(self.tick)
        self.activities.package_drug(self.tick)
        self.activities.sell_drug(self.tick)
        
        # Law enforcement
        self.law_enforcement.perform_minor_arrests(self.tick)
        
        # Major disruption at end of year 2
        if self.tick == config.MAJOR_DISRUPTION_TICK:
            self.law_enforcement.perform_major_arrest(self.tick, self.arrest_scenario)
        
        # Check acquisition disruption
        if not self.law_enforcement.apply_acquisition_disruption(self.tick):
            pass  # Already handled in acquire_drug
        
        # Weekly expenses (every 7 days)
        if self.tick % 7 == 0:
            self._account_for_expenses()
        
        # Update parameters (every 30 days)
        if self.tick % 30 == 0 and self.tick > 0:
            self._update_parameters()
        
        # Collect statistics
        network_stats = self.statistics.compute_all_statistics()
        self._update_agent_counts()
        self.data_collector.record(self.tick, self.global_state, network_stats)
        
        # Check organization viability
        if not self.law_enforcement.check_organization_viability():
            self.running = False
            return False
        
        # Check year-end status
        if self.tick % config.TICKS_PER_YEAR == 0:
            self._check_yearly_status()
        
        return True
    
    def _account_for_expenses(self):
        """Account for weekly wages and expenses"""
        traffickers = self.network.get_active_agents_by_type('trafficker')
        packagers = self.network.get_active_agents_by_type('packager')
        
        # Wages
        wage_cost = (self.global_state['profit_of_traffickers'] * len(traffickers) * 7 +
                    self.global_state['profit_of_packagers'] * len(packagers) * 7)
        
        self.global_state['cash_box'] -= wage_cost
        self.global_state['expenses'] += wage_cost
        self.global_state['weekly_profit_now'] -= wage_cost
    
    def _update_parameters(self):
        """Update model parameters monthly"""
        tick_year = self.tick / config.TICKS_PER_YEAR
        
        # Update unit doses using logarithmic function
        if tick_year <= 2:
            # Interpolate between 2008 and 2010 values
            y_range = config.UNIT_DOSE_2010 - config.UNIT_DOSE_2008
            new_unit_dose = config.UNIT_DOSE_2008 + y_range * (tick_year / 2)
            self.global_state['unit_dose'] = int(new_unit_dose)
            
            # Update min/max similarly
            y_range_min = config.UNIT_DOSE_MIN_2010 - config.UNIT_DOSE_MIN_2008
            self.global_state['unit_dose_min'] = int(config.UNIT_DOSE_MIN_2008 + y_range_min * (tick_year / 2))
            
            y_range_max = config.UNIT_DOSE_MAX_2010 - config.UNIT_DOSE_MAX_2008
            self.global_state['unit_dose_max'] = int(config.UNIT_DOSE_MAX_2008 + y_range_max * (tick_year / 2))
        
        # Update costs
        if tick_year <= 2:
            y_range = config.COST_PER_DAY_2010 - config.COST_PER_DAY_2008
            self.global_state['cost_per_day'] = int(config.COST_PER_DAY_2008 + y_range * (tick_year / 2))
        
        # Update weekly profit
        if tick_year <= 2:
            y_range = config.WEEKLY_PROFIT_2010 - config.WEEKLY_PROFIT_2008
            self.global_state['weekly_profit'] = int(config.WEEKLY_PROFIT_2008 + y_range * (tick_year / 2))
        
        # Update prices based on year
        if self.tick > config.TICKS_PER_YEAR:
            self.global_state['wholesale_price'] = config.WHOLESALE_PRICE_2009
            self.global_state['retail_price'] = config.RETAIL_PRICE_2009
        
        if self.tick > 2 * config.TICKS_PER_YEAR:
            self.global_state['wholesale_price'] = config.WHOLESALE_PRICE_2010
            self.global_state['retail_price'] = config.RETAIL_PRICE_2010
        
        # Recalculate drug packages and profits
        self._calculate_initial_parameters()
    
    def _update_agent_counts(self):
        """Update active agent counts"""
        self.global_state['n_active_traffickers'] = len(self.network.get_active_agents_by_type('trafficker'))
        self.global_state['n_active_packagers'] = len(self.network.get_active_agents_by_type('packager'))
        self.global_state['n_active_retailers'] = len(self.network.get_active_agents_by_type('retailer'))
    
    def _check_yearly_status(self):
        """Check and log yearly status"""
        year = self.tick // config.TICKS_PER_YEAR
        if config.VERBOSE_OUTPUT:
            print(f"\nYear {year}:")
            print(f"  Cash box: €{self.global_state['cash_box']:.2f}")
            print(f"  Members: T={self.global_state['n_active_traffickers']}, "
                  f"P={self.global_state['n_active_packagers']}, "
                  f"R={self.global_state['n_active_retailers']}")
            print(f"  Stock: {self.global_state['stock_drug']:.2f}g")
    
    def run(self, max_ticks: int = None):
        """Run simulation for specified number of ticks"""
        if max_ticks is None:
            max_ticks = config.TOTAL_TICKS
        
        while self.tick < max_ticks and self.running:
            if not self.step():
                break
            
            if self.tick % 100 == 0 and config.VERBOSE_OUTPUT:
                print(f"Tick {self.tick}...", end='\r')
        
        return self.data_collector.get_data()
    
    def get_results(self) -> Dict:
        """Get simulation results"""
        return {
            'arrest_scenario': self.arrest_scenario,
            'disruption_mode': self.disruption_mode,
            'efficiency_vs_security': self.efficiency_vs_security,
            'total_ticks': self.tick,
            'final_running': self.running,
            'final_cash_box': self.global_state['cash_box'],
            'data': self.data_collector.get_data(),
            'seed': self.seed,
        }


def run_single_simulation(arrest_scenario: int = 0, num_runs: int = 1) -> Dict:
    """
    Run single simulation scenario multiple times
    
    Args:
        arrest_scenario: Percentage to arrest
        num_runs: Number of simulations to run
    
    Returns:
        Aggregated results
    """
    results = {
        'arrest_scenario': arrest_scenario,
        'runs': [],
        'n_active_at_end': 0,
    }
    
    for run_num in range(num_runs):
        sim = MADTORSimulation(arrest_scenario=arrest_scenario)
        data = sim.run()
        results['runs'].append(sim.get_results())
        
        # Check if active at end
        if sim.running:
            results['n_active_at_end'] += 1
    
    return results


if __name__ == "__main__":
    # Run example simulation
    print("Starting MADTOR simulation...")
    sim = MADTORSimulation(arrest_scenario=10)
    data = sim.run()
    
    print(f"\nSimulation completed at tick {sim.tick}")
    print(f"Running: {sim.running}")
    print(f"Cash box: €{sim.global_state['cash_box']:.2f}")
    print(f"Members: T={sim.global_state['n_active_traffickers']}, "
          f"P={sim.global_state['n_active_packagers']}, "
          f"R={sim.global_state['n_active_retailers']}")

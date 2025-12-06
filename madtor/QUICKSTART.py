"""
QUICK START GUIDE for MADTOR Python Implementation
"""

# ============================================================================
# INSTALLATION
# ============================================================================

"""
1. Install Python 3.7 or higher
2. Install dependencies:
   
   pip install -r requirements.txt
   
   Or install individually:
   - pip install numpy
   - pip install scipy
   - pip install matplotlib (optional, for plots)
"""

# ============================================================================
# RUNNING SIMULATIONS
# ============================================================================

# Quick Example 1: Single Simulation
if __name__ == "__main__":
    from madtor import MADTORSimulation
    
    # Create simulation
    sim = MADTORSimulation(arrest_scenario=10)
    
    # Run for full 5 years (1825 ticks)
    data = sim.run()
    
    # Check results
    print(f"Organization survived: {sim.running}")
    print(f"Final members: {sim.global_state['n_active_traffickers'] + sim.global_state['n_active_packagers'] + sim.global_state['n_active_retailers']}")
    print(f"Final cash: €{sim.global_state['cash_box']:,.2f}")


# ============================================================================
# BATCH EXPERIMENTS
# ============================================================================

def run_batch_experiment():
    """Run multiple scenarios"""
    from madtor import ExperimentRunner
    
    runner = ExperimentRunner()
    
    # Test arrest scenarios from 0% to 90%
    results = runner.run_arrest_scenarios(
        arrest_scenarios=[0, 5, 10, 20, 30, 40, 50, 60, 70, 80, 90],
        num_simulations=100,  # Run 100 simulations per scenario
        num_workers=4,        # Use 4 parallel processes
    )
    
    # Print summary
    runner.print_summary()
    
    # Save results
    runner.save_results()


# ============================================================================
# CUSTOM SIMULATIONS
# ============================================================================

def custom_simulation():
    """Run simulation with custom parameters"""
    from madtor import MADTORSimulation
    
    # Different efficiency-vs-security values: 0.0 (secure) to 1.0 (efficient)
    for efficiency in [0.0, 0.5, 1.0]:
        sim = MADTORSimulation(
            arrest_scenario=20,
            disruption_mode="scenario1",
            efficiency_vs_security=efficiency
        )
        sim.run()
        
        print(f"\nEfficiency={efficiency}:")
        print(f"  Survived: {sim.running}")
        print(f"  Cash: €{sim.global_state['cash_box']:,.2f}")


# ============================================================================
# DATA ANALYSIS
# ============================================================================

def analyze_results():
    """Analyze simulation results"""
    from madtor import ExperimentRunner
    from madtor.utils import calculate_statistics
    
    runner = ExperimentRunner()
    results = runner.run_arrest_scenarios(
        arrest_scenarios=[0, 10, 50],
        num_simulations=50,
    )
    
    # Compare scenarios
    for scenario_pct in [0, 10, 50]:
        scenario_results = results[scenario_pct]
        
        # Extract financial data
        active_runs = [r for r in scenario_results['individual_results'] if r['final_running']]
        cash_values = [r['final_cash_box'] for r in active_runs]
        
        # Calculate statistics
        stats = calculate_statistics(cash_values)
        
        print(f"\nScenario {scenario_pct}% arrest:")
        print(f"  Mean cash: €{stats['mean']:,.2f}")
        print(f"  Median cash: €{stats['median']:,.2f}")
        print(f"  Std dev: €{stats['std']:,.2f}")
        print(f"  Active organizations: {len(active_runs)}/{scenario_results['num_simulations']}")


# ============================================================================
# CONFIGURATION
# ============================================================================

def modify_config():
    """Modify simulation parameters"""
    import madtor.config as config
    
    # View current parameters
    print(f"Simulation duration: {config.SIMULATION_YEARS} years")
    print(f"Initial members: {config.INITIAL_TOTAL_MEMBERS}")
    print(f"Start-up money: €{config.START_UP_MONEY:,.2f}")
    
    # To modify, edit config.py directly or override before creating simulation
    # Example:
    # config.INITIAL_TRAFFICKERS = 10  # More traffickers
    # config.SIMULATION_YEARS = 10     # Longer simulation


# ============================================================================
# COMPARISON STUDIES
# ============================================================================

def compare_efficiency_levels():
    """Compare simulations at different efficiency-vs-security levels"""
    from madtor import MADTORSimulation
    
    efficiency_levels = [0.0, 0.5, 1.0]
    arrest_pcts = [10, 50, 90]
    
    for efficiency in efficiency_levels:
        print(f"\n=== Efficiency-vs-Security: {efficiency} ===")
        
        for arrest_pct in arrest_pcts:
            sim = MADTORSimulation(
                arrest_scenario=arrest_pct,
                efficiency_vs_security=efficiency
            )
            sim.run()
            
            status = "Active" if sim.running else "Disrupted"
            print(f"  {arrest_pct}% arrest: {status} | Cash: €{sim.global_state['cash_box']:,.2f}")


# ============================================================================
# FILE OUTPUTS
# ============================================================================

def export_results():
    """Export simulation results to files"""
    from madtor import MADTORSimulation
    from madtor.utils import export_to_csv, plot_results
    
    # Run simulation
    sim = MADTORSimulation(arrest_scenario=20)
    data = sim.run()
    
    # Export to CSV
    export_to_csv(data, "my_simulation.csv")
    
    # Try to create plot (requires matplotlib)
    try:
        plot_results({20: {'survival_rate': 0.75}})
    except:
        print("Matplotlib not installed, skipping plot")


# ============================================================================
# COMMON SCENARIOS FROM PAPER
# ============================================================================

def replicate_paper_experiments():
    """Replicate experiments from the research paper"""
    from madtor import ExperimentRunner
    
    print("Replicating Paper Experiments...")
    print("This will take significant time!")
    
    runner = ExperimentRunner()
    
    # Main results: 11 scenarios × 1000 simulations
    results = runner.run_arrest_scenarios(
        arrest_scenarios=[0, 5, 10, 20, 30, 40, 50, 60, 70, 80, 90],
        num_simulations=1000,  # Large number for statistical validity
        num_workers=4,
    )
    
    runner.print_summary()
    runner.save_results("full_experiment_results.json")


# ============================================================================
# DEBUGGING
# ============================================================================

def debug_simulation():
    """Debug a single simulation with verbose output"""
    import madtor.config as config
    
    # Enable verbose output
    config.VERBOSE_OUTPUT = True
    
    from madtor import MADTORSimulation
    
    sim = MADTORSimulation(arrest_scenario=50)
    
    # Run in steps to observe behavior
    for i in range(100):
        if not sim.step():
            print(f"Organization disrupted at tick {sim.tick}")
            break
    
    print(f"\nFinal state at tick {sim.tick}:")
    print(f"  Cash box: €{sim.global_state['cash_box']:,.2f}")
    print(f"  Stock drug: {sim.global_state['stock_drug']:.2f}g")
    print(f"  Members: {len(sim.network.get_active_agents())}")


# ============================================================================
# GETTING HELP
# ============================================================================

"""
For more information:
1. Read README.md
2. Review config.py for available parameters
3. Check demo.py for more examples
4. Look at individual module docstrings
5. Refer to the original paper: https://doi.org/10.18564/jasss.5430

Main modules:
- simulation.py: Core simulation engine
- agents.py: Agent definitions
- activities.py: Drug trafficking operations
- law_enforcement.py: Arrest and disruption
- statistics.py: Network metrics and data collection
- experiment.py: Batch experiment runner
- config.py: Configuration parameters

Key classes:
- MADTORSimulation: Main simulation class
- ExperimentRunner: Run batch experiments
- Network: Manages agents and connections
- DrugTraffickingActivities: Operations
- LawEnforcement: Disruptions and arrests
- NetworkStatistics: SNA metrics
"""

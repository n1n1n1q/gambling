"""
Demo and test script for MADTOR
Shows how to use the model and validate it works correctly
"""

import sys
from pathlib import Path

# Add madtor to path
sys.path.insert(0, str(Path(__file__).parent))

from simulation import MADTORSimulation
from experiment import ExperimentRunner
from utils import calculate_statistics, export_to_csv, plot_results
import config


def demo_single_simulation():
    """Demo: Run a single simulation"""
    print("="*70)
    print("DEMO 1: Single Simulation")
    print("="*70)
    
    print("\nInitializing simulation with 10% arrest scenario...")
    sim = MADTORSimulation(arrest_scenario=10)
    
    print("Running simulation...")
    data = sim.run()
    
    print(f"\nSimulation Results:")
    print(f"  Total ticks: {sim.tick}")
    print(f"  Still running: {sim.running}")
    print(f"  Final cash box: €{sim.global_state['cash_box']:,.2f}")
    print(f"  Total members remaining:")
    print(f"    - Traffickers: {sim.global_state['n_active_traffickers']}")
    print(f"    - Packagers: {sim.global_state['n_active_packagers']}")
    print(f"    - Retailers: {sim.global_state['n_active_retailers']}")
    print(f"  Total drug stock: {sim.global_state['stock_drug']:.2f}g")
    print(f"  Total acquisitions: {sim.global_state['n_acquisition']}")
    
    return data


def demo_multiple_runs():
    """Demo: Run multiple simulations in batch"""
    print("\n" + "="*70)
    print("DEMO 2: Batch Experiments (Multiple Scenarios)")
    print("="*70)
    
    print("\nRunning multiple arrest scenarios...")
    runner = ExperimentRunner()
    
    # Run with fewer simulations for demo
    results = runner.run_arrest_scenarios(
        arrest_scenarios=[0, 10, 30, 50, 90],
        num_simulations=5,  # Small number for demo
        num_workers=2,
    )
    
    print("\nBatch Results Summary:")
    print("-" * 70)
    print(f"{'Arrest %':<12} {'Simulations':<15} {'Active':<12} {'Survival %':<15}")
    print("-" * 70)
    
    for scenario in sorted(results.keys()):
        data = results[scenario]
        print(f"{data['arrest_scenario']:<12.0f} {data['num_simulations']:<15} "
              f"{data['num_active_at_end']:<12} {data['survival_rate']*100:<15.1f}")
    
    print("-" * 70)
    
    # Save results
    runner.save_results("demo_results.json")
    
    return results


def demo_data_analysis():
    """Demo: Analyze simulation data"""
    print("\n" + "="*70)
    print("DEMO 3: Data Analysis")
    print("="*70)
    
    # Run a simulation
    print("\nRunning simulation for analysis...")
    sim = MADTORSimulation(arrest_scenario=20)
    data = sim.run()
    
    # Analyze cash box values over time
    cash_values = data['cash_box']
    
    print(f"\nCash Box Analysis:")
    print(f"  First value: €{cash_values[0]:,.2f}")
    print(f"  Last value: €{cash_values[-1]:,.2f}")
    print(f"  Min value: €{min(cash_values):,.2f}")
    print(f"  Max value: €{max(cash_values):,.2f}")
    
    # Export to CSV
    print("\nExporting data to CSV...")
    export_to_csv(data, "demo_data.csv")
    
    return data


def demo_configuration():
    """Demo: Show configuration parameters"""
    print("\n" + "="*70)
    print("DEMO 4: Configuration Parameters")
    print("="*70)
    
    print(f"\nSimulation Parameters:")
    print(f"  Duration: {config.SIMULATION_YEARS} years ({config.TOTAL_TICKS} ticks)")
    print(f"  Initial members: {config.INITIAL_TOTAL_MEMBERS}")
    print(f"    - Traffickers: {config.INITIAL_TRAFFICKERS}")
    print(f"    - Packagers: {config.INITIAL_PACKAGERS}")
    print(f"    - Retailers: {config.INITIAL_RETAILERS}")
    
    print(f"\nDrug Trafficking Parameters:")
    print(f"  Gram per dose: {config.GRAM_PER_DOSE}g")
    print(f"  Unit doses 2008: {config.UNIT_DOSE_2008}")
    print(f"  Unit doses 2010: {config.UNIT_DOSE_2010}")
    print(f"  Wholesale price 2008: €{config.WHOLESALE_PRICE_2008}/g")
    print(f"  Wholesale price 2010: €{config.WHOLESALE_PRICE_2010}/g")
    print(f"  Price per dose: €{config.PRICE_PER_DOSE}")
    
    print(f"\nFinancial Parameters:")
    print(f"  Start-up money: €{config.START_UP_MONEY:,.2f}")
    print(f"  Daily cost 2008: €{config.COST_PER_DAY_2008:,.2f}")
    print(f"  Daily cost 2010: €{config.COST_PER_DAY_2010:,.2f}")
    print(f"  Max retailer profit: €{config.PROFIT_OF_RETAILERS_MAX}")
    
    print(f"\nLaw Enforcement Parameters:")
    print(f"  Major disruption year: {config.MAJOR_DISRUPTION_YEAR}")
    print(f"  Arrest scenarios: {config.ARREST_SCENARIOS}")
    print(f"  Stop acquire days: {config.STOP_ACQUIRE_DAYS_DEFAULT}")


def validate_model():
    """Validate model basic functionality"""
    print("\n" + "="*70)
    print("DEMO 5: Model Validation")
    print("="*70)
    
    tests_passed = 0
    tests_total = 0
    
    # Test 1: Basic initialization
    tests_total += 1
    try:
        sim = MADTORSimulation(arrest_scenario=0)
        assert sim.tick == 0
        assert len(sim.network.get_active_agents()) == config.INITIAL_TOTAL_MEMBERS
        print("✓ Test 1: Model initialization")
        tests_passed += 1
    except Exception as e:
        print(f"✗ Test 1 failed: {e}")
    
    # Test 2: Single step execution
    tests_total += 1
    try:
        sim = MADTORSimulation(arrest_scenario=0)
        sim.step()
        assert sim.tick == 1
        print("✓ Test 2: Single step execution")
        tests_passed += 1
    except Exception as e:
        print(f"✗ Test 2 failed: {e}")
    
    # Test 3: Full simulation run
    tests_total += 1
    try:
        sim = MADTORSimulation(arrest_scenario=0)
        sim.run(max_ticks=100)  # Run 100 ticks
        assert sim.tick == 100
        print("✓ Test 3: Full simulation run (100 ticks)")
        tests_passed += 1
    except Exception as e:
        print(f"✗ Test 3 failed: {e}")
    
    # Test 4: Agent counts tracking
    tests_total += 1
    try:
        sim = MADTORSimulation(arrest_scenario=0)
        initial_count = len(sim.network.get_active_agents())
        sim.run(max_ticks=50)
        assert len(sim.network.get_active_agents()) > 0
        print("✓ Test 4: Agent counting")
        tests_passed += 1
    except Exception as e:
        print(f"✗ Test 4 failed: {e}")
    
    # Test 5: Data collection
    tests_total += 1
    try:
        sim = MADTORSimulation(arrest_scenario=0)
        sim.run(max_ticks=30)
        data = sim.data_collector.get_data()
        assert len(data['tick']) > 0
        assert len(data['cash_box']) > 0
        print("✓ Test 5: Data collection")
        tests_passed += 1
    except Exception as e:
        print(f"✗ Test 5 failed: {e}")
    
    print(f"\nValidation Results: {tests_passed}/{tests_total} tests passed")
    return tests_passed == tests_total


def main():
    """Run all demos"""
    print("\n" + "="*70)
    print("MADTOR - Drug Trafficking Organization Resilience Model")
    print("Python Implementation Demo and Validation")
    print("="*70)
    
    # Run demos
    demo_configuration()
    validate_model()
    demo_single_simulation()
    demo_multiple_runs()
    demo_data_analysis()
    
    print("\n" + "="*70)
    print("Demo completed successfully!")
    print("Check output/ directory for generated files")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()

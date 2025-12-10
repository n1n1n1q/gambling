# Single simulation
from madtor import MADTORSimulation
from madtor import ExperimentRunner
from madtor import config

if __name__ == "__main__":
    # Test single sim first
    print("Testing single simulation...")
    sim = MADTORSimulation(arrest_scenario=0)
    data = sim.run()

    print(f"\nSingle simulation results:")
    print(f"Ticks run: {sim.tick}")
    print(f"Running: {sim.running}")
    print(f"Final cash: €{sim.global_state['cash_box']:.2f}")
    print(
        f"Final members: T={sim.global_state['n_active_traffickers']}, P={sim.global_state['n_active_packagers']}, R={sim.global_state['n_active_retailers']}"
    )
    print(
        f"Total revenues: €{sim.data_collector.data['revenues'][-1] if sim.data_collector.data['revenues'] else 0:.2f}"
    )
    print(
        f"Total expenses: €{sim.data_collector.data['expenses'][-1] if sim.data_collector.data['expenses'] else 0:.2f}"
    )

    # Now run batch experiments
    print("\n" + "=" * 60)
    print("Running batch experiments...")
    runner = ExperimentRunner()
    results = runner.run_arrest_scenarios(
        disruption_mode=config.DISRUPTION_MODES[0],
        efficiency_vs_security=config.EFFICIENCY_VS_SECURITY_VALUES[3],
    )

    runner.print_summary()
    if config.COLLECT_STATISTICS:
        runner.save_results()

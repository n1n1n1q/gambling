# MADTOR: Model for Assessing Drug Trafficking Organizations Resilience

A Python implementation of the agent-based model for simulating drug trafficking organizations and their responses to law enforcement interventions.

**Original Paper:** 
Manzi, D., & Calderoni, F. (2024). An Agent-Based Model for Assessing the Resilience of Drug Trafficking Organizations to Law Enforcement Interventions. *Journal of Artificial Societies and Social Simulation*, 27(3), 3. https://doi.org/10.18564/jasss.5430

## Overview

MADTOR is an agent-based model that simulates the operations of a drug trafficking organization (DTO) across a 5-year period. The model incorporates:

- **Agent-based modeling**: Individual traffickers, packagers, and retailers with distinct roles and behaviors
- **Network dynamics**: Social relationships and trust-based decision making for drug distribution
- **Economic simulation**: Financial tracking of revenues, expenses, and profits
- **Law enforcement interventions**: Realistic modeling of arrests and disruptions
- **Network analysis**: Computation of social network metrics (centrality, components, geodesic distance)

## Key Features

### Drug Trafficking Activities
- **Drug Acquisition**: Traffickers acquire drugs monthly based on a composite index of market conditions, stock levels, and wholesale prices
- **Drug Processing**: Packagers receive drugs from traffickers and prepare them for retail distribution
- **Drug Sales**: Retailers sell unit-doses to consumers, with profit constraints and availability limits
- **Financial Management**: Organization-wide tracking of revenues, expenses, and profit distribution

### Law Enforcement
- **Minor Arrests**: Stochastic monthly arrests of individual members
- **Major Disruptions**: Coordinated arrests of specified percentage of members at a fixed time (Year 2)
- **Disruption Scenarios**: Three different law enforcement intervention patterns (scenario1, scenario2, scenario3)
- **Adaptation**: Organization stops acquiring drugs and recruiting after major disruptions

### Network Analysis
- Weak component clustering
- Degree centrality (min, max, average, centralization)
- Betweenness centrality (min, max, average, centralization)
- Average geodesic distance (average path length)

### Calibration
Model is calibrated to real-world data from Operation Beluga (2008-2010), an Italian police operation against the Di Lauro Camorra clan

## Installation

```bash
pip install -r requirements.txt
```

## Quick Start

### Running a Single Simulation

```python
from madtor import MADTORSimulation

# Create and run a simulation with 10% arrest scenario
sim = MADTORSimulation(arrest_scenario=10)
data = sim.run()

# Access results
print(f"Final cash box: €{sim.global_state['cash_box']:.2f}")
print(f"Members: T={sim.global_state['n_active_traffickers']}, "
      f"P={sim.global_state['n_active_packagers']}, "
      f"R={sim.global_state['n_active_retailers']}")
```

### Running Multiple Scenarios (Batch Experiment)

```python
from madtor import ExperimentRunner

runner = ExperimentRunner()

# Run arrest scenarios from 0% to 90%
results = runner.run_arrest_scenarios(
    arrest_scenarios=[0, 5, 10, 20, 30, 40, 50, 60, 70, 80, 90],
    num_simulations=100,
    num_workers=4,
)

# Save results
runner.save_results()
runner.print_summary()
```

### Analyzing Results

```python
from madtor.utils import calculate_statistics, perform_ttest

# Extract data from results
scenario_10_results = results[10]['runs']

# Calculate statistics
survival_rates = [r['final_running'] for r in scenario_10_results]
cash_boxes = [r['final_cash_box'] for r in scenario_10_results]

stats = calculate_statistics(cash_boxes)
print(f"Average final cash box: €{stats['mean']:.2f}")
print(f"Median: €{stats['median']:.2f}")

# Compare scenarios with t-test
group1_cash = [r['final_cash_box'] for r in results[10]['runs'] if r['final_running']]
group2_cash = [r['final_cash_box'] for r in results[20]['runs'] if r['final_running']]

ttest_result = perform_ttest(group1_cash, group2_cash, num_permutations=100)
print(f"Significant difference: {ttest_result['significant']}")
```

## Model Components

### Core Modules

- **`agents.py`**: Agent definitions (Trafficker, Packager, Retailer, Network)
- **`activities.py`**: Drug trafficking operations (acquire, package, sell)
- **`law_enforcement.py`**: Law enforcement interventions and arrests
- **`statistics.py`**: Network statistics and data collection
- **`simulation.py`**: Main simulation engine
- **`experiment.py`**: Experiment runner for batch simulations
- **`config.py`**: Configuration parameters
- **`utils.py`**: Utility functions

### Configuration Parameters

Edit `config.py` to modify:
- Simulation duration and parameters
- Agent counts and initial configuration
- Drug trafficking parameters (prices, quantities, etc.)
- Law enforcement parameters (arrest scenarios)
- Efficiency-vs-security settings
- Network analysis metrics

## Output

Simulations generate:

- **Time series data**: Daily tracking of organization metrics
- **Financial data**: Cash box, revenues, expenses, profits
- **Activity metrics**: Drug acquisitions, sales, stock levels
- **Network metrics**: Centrality measures, component analysis, path lengths
- **Event logs**: Arrests, disruptions, recruitment

Results can be exported to:
- JSON format
- CSV format
- HTML reports

## Model Calibration

The model uses real-world data from Operation Beluga (2008-2010):

- Initial organization size: 44 members (5 traffickers, 5 packagers, 34 retailers)
- Calibration targets: Member counts, daily sales volumes, financial metrics
- Prices: UNODC wholesale and retail cocaine prices (2008-2010)
- Financial: Court-documented costs and profits

See paper for detailed calibration methodology.

## Key Findings (from Original Paper)

1. **Non-linear disruption**: Arresting even 5-10% of members disrupts ~50% of organizations
2. **Diminishing returns**: Increasing arrests from 40% to 80% produces only ~20% additional disruption
3. **Recovery difficulties**: Surviving organizations face increasing challenges with higher arrest percentages
4. **Role importance**: Loss of traffickers more disruptive than other roles

## Citation

If you use this model, please cite the original paper:

```bibtex
@article{manzi2024madtor,
  title={An Agent-Based Model for Assessing the Resilience of Drug Trafficking Organizations to Law Enforcement Interventions},
  author={Manzi, Deborah and Calderoni, Francesco},
  journal={Journal of Artificial Societies and Social Simulation},
  volume={27},
  number={3},
  pages={3},
  year={2024},
  doi={10.18564/jasss.5430}
}
```

## License

This Python implementation is provided for research purposes.

## References

- Manzi, D., & Calderoni, F. (2024). MADTOR: Model for assessing drug trafficking organizations resilience. https://doi.org/10.25937/XT1V-6B16
- Tribunale di Napoli (2013). Ordinanza Applicativa di Misure Cautelari Personali (Operation Beluga court order)
- UNODC (2008-2010). Heroin and cocaine prices in Europe and USA

## Development Notes

### Requirements
- Python 3.7+
- numpy, scipy, matplotlib
- Optional: multiprocessing for parallel simulations

### Performance
- Single simulation: ~5-10 seconds
- 1000 simulations per scenario: ~1-2 hours (with 4 workers)
- Full experiment (11 scenarios × 1000 sims): ~11-22 hours

### Extending the Model
The model can be extended to:
- Different drug types
- Alternative organizational structures  
- Multiple competing organizations
- Alternative law enforcement strategies
- Geographic/spatial elements

See source code comments for extension points.

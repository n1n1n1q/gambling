# Single simulation
from madtor import MADTORSimulation
sim = MADTORSimulation(arrest_scenario=10)
data = sim.run()

# Batch experiments
from madtor import ExperimentRunner
runner = ExperimentRunner()
results = runner.run_arrest_scenarios()
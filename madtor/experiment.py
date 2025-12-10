"""
Experiment runner for MADTOR simulations
Manages large-scale simulation studies with multiple scenarios
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional
import time
from multiprocessing import Pool, cpu_count
import logging

import polars as pl

import madtor.config as config
from madtor.simulation import MADTORSimulation


# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class ExperimentRunner:
    """Manages experiment execution and data collection"""

    def __init__(self, output_dir: str = "output"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.results = {}
        self.start_time = None

    def run_arrest_scenarios(
        self,
        arrest_scenarios: Optional[List[int]] = None,
        num_simulations: int = 10,
        num_workers: Optional[int] = None,
        disruption_mode: str = "scenario1",
        efficiency_vs_security: float = 0.6,
    ) -> Dict:
        """
        Run simulations across different arrest scenarios

        Args:
            arrest_scenarios: List of arrest percentages to test
            num_simulations: Number of simulations per scenario
            num_workers: Number of parallel processes (None = auto)
            disruption_mode: Which disruption scenario to use
            efficiency_vs_security: Efficiency-security trade-off

        Returns:
            Dictionary with aggregated results
        """
        if arrest_scenarios is None:
            arrest_scenarios = config.ARREST_SCENARIOS

        if num_workers is None:
            num_workers = max(1, cpu_count() - 1)

        self.start_time = time.time()
        logger.info(f"Starting experiment with {len(arrest_scenarios)} scenarios")
        logger.info(f"Simulations per scenario: {num_simulations}")
        logger.info(f"Workers: {num_workers}")

        results = {}

        for scenario in arrest_scenarios:
            logger.info(f"Running scenario: {scenario}% arrest")

            # Create list of simulation tasks
            tasks = [
                (scenario, disruption_mode, efficiency_vs_security)
                for _ in range(num_simulations)
            ]

            # Run simulations in parallel
            with Pool(num_workers) as pool:
                scenario_results = pool.starmap(run_single_sim, tasks)

            # Aggregate results
            results[scenario] = self._aggregate_scenario_results(
                scenario_results, scenario
            )

            active_count = sum(1 for r in scenario_results if r["final_running"])
            logger.info(
                f"  Active organizations at end: {active_count}/{num_simulations}"
            )

        self.results = results
        elapsed = time.time() - self.start_time
        logger.info(f"Experiment completed in {elapsed:.2f} seconds")

        return results

    def _aggregate_scenario_results(
        self, scenario_results: List[Dict], scenario: int
    ) -> Dict:
        """Aggregate results across simulations in a scenario"""

        active_count = sum(1 for r in scenario_results if r["final_running"])

        # Aggregate financial metrics
        cash_boxes = [
            r["final_cash_box"] for r in scenario_results if r["final_running"]
        ]

        aggregated = {
            "arrest_scenario": scenario,
            "num_simulations": len(scenario_results),
            "num_active_at_end": active_count,
            "survival_rate": active_count / len(scenario_results),
            "avg_final_cash_box": sum(cash_boxes) / len(cash_boxes)
            if cash_boxes
            else 0,
            "median_final_cash_box": sorted(cash_boxes)[len(cash_boxes) // 2]
            if cash_boxes
            else 0,
            "individual_results": scenario_results,
        }

        return aggregated

    def save_results(self, filename: str = "madtor_results.json"):
        """Save aggregated JSON and per-run parquet (per tick) files."""
        output_path = self.output_dir / filename

        # Convert results to JSON-serializable format (summary only)
        json_results = {}
        for scenario, data in self.results.items():
            json_results[str(scenario)] = {
                "arrest_scenario": data["arrest_scenario"],
                "num_simulations": data["num_simulations"],
                "num_active_at_end": data["num_active_at_end"],
                "survival_rate": data["survival_rate"],
                "avg_final_cash_box": data["avg_final_cash_box"],
                "median_final_cash_box": data["median_final_cash_box"],
            }

            # Save per-run tick data to parquet
            runs = data.get("individual_results", [])

            # Include disruption/efficiency in directory name for clarity
            first_run = runs[0] if runs else {}
            mode_label = str(first_run.get("disruption_mode", "unknown")).replace(
                " ", "_"
            )
            eff_label = str(first_run.get("efficiency_vs_security", "na")).replace(
                ".", "_"
            )
            scenario_dir = self.output_dir / f"scenario_{scenario}_mode_{mode_label}_eff_{eff_label}"
            scenario_dir.mkdir(parents=True, exist_ok=True)
            for idx, run_data in enumerate(runs):
                tick_data = run_data.get("data")
                if not tick_data:
                    continue

                # Build dataframe with simulation metadata columns; allow mixed int/float columns
                df = pl.DataFrame(tick_data, strict=False)
                df = df.with_columns(
                    pl.lit(run_data.get("seed")).alias("seed"),
                    pl.lit(run_data.get("arrest_scenario", scenario)).alias(
                        "arrest_scenario"
                    ),
                    pl.lit(run_data.get("disruption_mode")).alias("disruption_mode"),
                    pl.lit(run_data.get("efficiency_vs_security")).alias(
                        "efficiency_vs_security"
                    ),
                    pl.lit(idx).alias("run_index"),
                )

                parquet_path = scenario_dir / f"run_{idx}.parquet"
                df.write_parquet(parquet_path)

        with open(output_path, "w") as f:
            json.dump(json_results, f, indent=2)

        logger.info(
            f"Results saved to {output_path} and parquet files in {self.output_dir}"
        )
        return output_path

    def print_summary(self):
        """Print summary of results"""
        print("\n" + "=" * 70)
        print("MADTOR EXPERIMENT SUMMARY")
        print("=" * 70)

        for scenario in sorted(self.results.keys()):
            data = self.results[scenario]
            print(f"\nArrest Scenario: {scenario}%")
            print(f"  Simulations: {data['num_simulations']}")
            print(
                f"  Active Organizations (end): {data['num_active_at_end']} ({data['survival_rate'] * 100:.1f}%)"
            )
            print(f"  Avg Final Cash Box: €{data['avg_final_cash_box']:,.2f}")
            print(f"  Median Final Cash Box: €{data['median_final_cash_box']:,.2f}")


def run_single_sim(
    arrest_scenario: int, disruption_mode: str, efficiency_vs_security: float
) -> Dict:
    """
    Run a single simulation
    Used as target for multiprocessing
    """
    sim = MADTORSimulation(
        arrest_scenario=arrest_scenario,
        disruption_mode=disruption_mode,
        efficiency_vs_security=efficiency_vs_security,
    )
    sim.run()
    return sim.get_results()


class SimulationComparison:
    """Compare simulations across different parameters"""

    def __init__(self):
        self.comparisons = {}

    def compare_efficiency_levels(
        self, arrest_scenarios: Optional[List[int]] = None, num_simulations: int = 5
    ) -> Dict:
        """
        Compare simulations across different efficiency-vs-security levels
        """
        if arrest_scenarios is None:
            arrest_scenarios = [10, 20, 50, 80]

        results = {}

        for efficiency in config.EFFICIENCY_VS_SECURITY_VALUES:
            logger.info(f"Testing efficiency-vs-security: {efficiency}")

            runner = ExperimentRunner()
            scenario_results = runner.run_arrest_scenarios(
                arrest_scenarios=arrest_scenarios,
                num_simulations=num_simulations,
                efficiency_vs_security=efficiency,
            )

            results[efficiency] = scenario_results

        self.comparisons["efficiency_levels"] = results
        return results

    def save_comparison(self, filename: str = "comparison_results.json"):
        """Save comparison results"""
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        output_path = output_dir / filename

        # Serialize comparison data
        json_data = {}
        for efficiency, results in self.comparisons["efficiency_levels"].items():
            json_data[str(efficiency)] = {}
            for scenario, data in results.items():
                json_data[str(efficiency)][str(scenario)] = {
                    "survival_rate": data["survival_rate"],
                    "num_active_at_end": data["num_active_at_end"],
                }

        with open(output_path, "w") as f:
            json.dump(json_data, f, indent=2)

        logger.info(f"Comparison saved to {output_path}")


if __name__ == "__main__":
    # Example: Run standard experiments
    runner = ExperimentRunner()

    # Run core scenarios
    results = runner.run_arrest_scenarios(
        arrest_scenarios=[0, 5, 10, 20, 30, 40, 50, 60, 70, 80, 90],
        num_simulations=10,  # Use smaller number for demo
        num_workers=4,
    )

    # Print and save results
    runner.print_summary()
    runner.save_results()

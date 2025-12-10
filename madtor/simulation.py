"""
Main MADTOR simulation engine
Orchestrates the complete simulation loop
"""

import random
import math
import logging
from typing import Dict, List, Tuple, Optional
import json
from datetime import datetime
from pathlib import Path

import madtor.config as config
from madtor.agents import Trafficker, Packager, Retailer, Agent, Network
from madtor.activities import DrugTraffickingActivities
from madtor.law_enforcement import LawEnforcement
from madtor.statistics import NetworkStatistics, DataCollector
from madtor.utils import load_nodes_file, load_links_file, infer_agent_type


class MADTORSimulation:
    """Main simulation controller"""

    def __init__(
        self,
        arrest_scenario: int = 0,
        disruption_mode: str = "scenario1",
        efficiency_vs_security: float = 0.5,
        seed: int = None,
    ):
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
            "tick": 0,
            "current_year": 1,
            # Agent counts
            "n_active_traffickers": config.INITIAL_TRAFFICKERS,
            "n_active_packagers": config.INITIAL_PACKAGERS,
            "n_active_retailers": config.INITIAL_RETAILERS,
            # Drug trafficking
            "drug_package_of_traffickers": 0,
            "drug_package_of_packagers": 0,
            "drug_package_of_retailers": config.DRUG_PACKAGE_RETAILERS,
            "gram_per_dose": config.GRAM_PER_DOSE,
            "unit_dose": config.UNIT_DOSE_2008,
            "unit_dose_min": config.UNIT_DOSE_MIN_2008,
            "unit_dose_max": config.UNIT_DOSE_MAX_2008,
            "unit_dose_now": config.UNIT_DOSE_2008,
            # Stock tracking
            "stock_drug": 0,
            "stock_drug_traffickers": 0,
            "stock_drug_packagers": 0,
            "stock_drug_retailers": 0,
            "target_stock_drug": 0,
            # Prices
            "wholesale_price": config.WHOLESALE_PRICE_2008,
            "wholesale_price_now": config.WHOLESALE_PRICE_2008,
            "retail_price": config.RETAIL_PRICE_2008,
            "price_per_dose": config.PRICE_PER_DOSE,
            # Financial
            "cash_box": 0,
            "revenues": 0,
            "expenses": 0,
            "profit_of_traffickers": 0,
            "profit_of_packagers": 0,
            "profit_of_retailers": 0,
            "weekly_profit": config.WEEKLY_PROFIT_2008,
            "weekly_profit_now": 0,
            "cost_per_day": config.COST_PER_DAY_2008,
            # Profit tracking
            "profit_of_traffickers_min": config.PROFIT_RANGES[
                self.efficiency_vs_security
            ]["traffickers_min"],
            "profit_of_traffickers_max": config.PROFIT_RANGES[
                self.efficiency_vs_security
            ]["traffickers_max"],
            "profit_of_packagers_min": config.PROFIT_RANGES[
                self.efficiency_vs_security
            ]["packagers_min"],
            "profit_of_packagers_max": config.PROFIT_RANGES[
                self.efficiency_vs_security
            ]["packagers_max"],
            "profit_of_retailers_max": config.PROFIT_OF_RETAILERS_MAX,
            # Profit shares
            "traffickers_share_of_profits": config.TRAFFICKERS_SHARE_OF_PROFITS,
            "retailers_share_of_profits": config.RETAILERS_SHARE_OF_PROFITS,
            # Activity tracking
            "n_acquisition": 0,
            "n_exhaust_traffickers": 0,
            "n_exhaust_packagers": 0,
            "n_exhaust_retailers": 0,
            "n_exhaust_retailers_90": 0,
            # Family wage/support tracking
            "arrested_retailers_family": 0,
            "dead_members_family": 0,
            "fm_traffickers_wage": 0,
            "fm_packagers_wage": 0,
            "fm_retailers_wage": 0,
            "arrested_retailers_family_wages": 0,
            "dead_members_family_wages": 0,
            "arrested_homicide_family_wages": config.ARRESTED_HOMICIDE_FAMILY_WAGES
            if hasattr(config, "ARRESTED_HOMICIDE_FAMILY_WAGES")
            else 2 * 3500,
            "n_weekly_profit_min": 0,
            "n_weekly_profit_max": 0,
            "n_weekly_profit_neg": 0,
            # Law enforcement
            "arrested_mode": "arrested%",
            "arrested%": self.arrest_scenario,
            "arrested#": 0,
            "target_of_disruption": "turtles",
            "disruption_mode": self.disruption_mode,
            "efficiency_vs_security": self.efficiency_vs_security,
            "ticks_disruption": None,
            "stop_acquire_days": config.STOP_ACQUIRE_DAYS_DEFAULT,
            "stop_acquiring_until": None,
            # Arrest tracking
            "n_arrested_traffickers_minor": 0,
            "n_arrested_packagers_minor": 0,
            "n_arrested_retailers_minor": 0,
            "n_arrested_traffickers_major": 0,
            "n_arrested_packagers_major": 0,
            "n_arrested_retailers_major": 0,
            # Calibration values
            "traffickers_2008": config.TRAFFICKERS_2008,
            "traffickers_2010": config.TRAFFICKERS_2010,
            "packagers_2008": config.PACKAGERS_2008,
            "packagers_2010": config.PACKAGERS_2010,
            "retailers_2008": config.RETAILERS_2008,
            "retailers_2010": config.RETAILERS_2010,
            # Min/max tracking
            "minw": float("inf"),
            "maxw": float("-inf"),
            "minacq_ind": float("inf"),
            "maxacq_ind": float("-inf"),
            "mincash": float("inf"),
            "maxcash": float("-inf"),
        }

    def _setup(self):
        """Initialize simulation"""
        # Try to load from real data files
        nodes_file = Path("madtor/data/T2_Nodes.prn")
        links_file = Path("madtor/data/T2_Links.prn")

        if nodes_file.exists() and links_file.exists():
            self._setup_from_real_data(nodes_file, links_file)
        else:
            self._setup_with_random_initialization()

    def _setup_from_real_data(self, nodes_file: Path, links_file: Path):
        """Initialize simulation from real data files"""
        # Load data
        nodes_data = load_nodes_file(str(nodes_file))
        links_data = load_links_file(str(links_file))

        # Create agents based on node data
        agents = []
        agent_map = {}  # Map node_id -> Agent

        for node_id, roles in nodes_data.items():
            agent_type = infer_agent_type(node_id, {node_id: roles})

            if agent_type == "trafficker":
                agent = Trafficker(f"{node_id}")
            elif agent_type == "packager":
                agent = Packager(f"{node_id}")
            else:
                agent = Retailer(f"{node_id}")

            agent.node_id = node_id
            agent.role_category = roles.get("role_category1", "n/a")
            agents.append(agent)
            agent_map[node_id] = agent

        # Create network
        self.network = Network(agents)

        # Add links based on link data
        for link in links_data:
            source_id = link["source"]
            target_id = link["target"]
            familiarity = link["familiarity"]

            if source_id in agent_map and target_id in agent_map:
                self.network.add_link(
                    agent_map[source_id].agent_id,
                    agent_map[target_id].agent_id,
                    f"{link['role1']}-{link['role2']}",
                    familiarity,
                )

        # Initialize activities and law enforcement
        self.activities = DrugTraffickingActivities(self.network, self.global_state)
        self.law_enforcement = LawEnforcement(self.network, self.global_state)
        self.statistics = NetworkStatistics(self.network)

        # Update agent counts in global state
        traffickers = self.network.get_active_agents_by_type("trafficker")
        packagers = self.network.get_active_agents_by_type("packager")
        retailers = self.network.get_active_agents_by_type("retailer")

        self.global_state["n_active_traffickers"] = len(traffickers)
        self.global_state["n_active_packagers"] = len(packagers)
        self.global_state["n_active_retailers"] = len(retailers)

        # Calculate initial parameters
        self._calculate_initial_parameters()

        # Initialize drug stocks
        self._initialize_drug_stocks()

    def _setup_with_random_initialization(self):
        """Initialize simulation with random agents (fallback)"""
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

        # Create initial network links (random)
        self._create_initial_links()

    def _calculate_initial_parameters(self):
        """Calculate drug package sizes and financial parameters"""
        efficiency_factor = self.efficiency_vs_security / 3

        # Drug packages
        unit_dose_range = (
            self.global_state["unit_dose_max"] - self.global_state["unit_dose_min"]
        )
        avg_dose = (
            self.global_state["unit_dose_min"] + unit_dose_range * efficiency_factor
        )

        gram_per_dose = self.global_state["gram_per_dose"]

        # Package for traffickers (monthly)
        n_traffickers = max(1, self.global_state["n_active_traffickers"])
        self.global_state["drug_package_of_traffickers"] = (
            avg_dose * gram_per_dose / n_traffickers * 30
        )

        # Package for packagers (daily)
        n_packagers = max(1, self.global_state["n_active_packagers"])
        self.global_state["drug_package_of_packagers"] = (
            avg_dose * gram_per_dose / n_packagers
        )

        # Financial parameters
        supply_costs = (
            self.global_state["wholesale_price"] / self.global_state["retail_price"]
        )
        cost_per_day = self.global_state["cost_per_day"]

        # Trafficker profits
        n_traffickers = max(1, self.global_state["n_active_traffickers"])
        profit_t = (
            (cost_per_day - cost_per_day * supply_costs)
            * config.TRAFFICKERS_SHARE_OF_PROFITS
            / n_traffickers
        )
        profit_t = max(
            self.global_state["profit_of_traffickers_min"],
            min(self.global_state["profit_of_traffickers_max"], profit_t),
        )
        self.global_state["profit_of_traffickers"] = profit_t

        # Packager profits
        n_packagers = max(1, self.global_state["n_active_packagers"])
        profit_p = (
            (cost_per_day - cost_per_day * supply_costs)
            * (1 - config.TRAFFICKERS_SHARE_OF_PROFITS)
            / n_packagers
        )
        profit_p = max(
            self.global_state["profit_of_packagers_min"],
            min(self.global_state["profit_of_packagers_max"], profit_p),
        )
        self.global_state["profit_of_packagers"] = profit_p

        # Retailer profits
        n_retailers = max(1, self.global_state["n_active_retailers"])
        profit_r = (
            self.global_state["unit_dose"]
            * config.PRICE_PER_DOSE
            * config.RETAILERS_SHARE_OF_PROFITS
            / n_retailers
        )
        profit_r = min(self.global_state["profit_of_retailers_max"], profit_r)
        self.global_state["profit_of_retailers"] = profit_r

        # Target stock
        start_up_months = 2
        self.global_state["target_stock_drug"] = (
            self.global_state["unit_dose"] * gram_per_dose * start_up_months * 30
        )

        # Cash box
        self.global_state["cash_box"] = config.START_UP_MONEY

    def _initialize_drug_stocks(self):
        """Distribute initial drug stocks"""
        target_stock = self.global_state["target_stock_drug"]

        packagers = self.network.get_active_agents_by_type("packager")
        retailers = self.network.get_active_agents_by_type("retailer")

        if packagers:
            packager_stock = (
                target_stock
                - 2
                * self.global_state["unit_dose"]
                * self.global_state["gram_per_dose"]
            )
            per_packager = packager_stock / len(packagers)
            for packager in packagers:
                packager.drug = per_packager
            self.global_state["stock_drug_packagers"] = packager_stock

        if retailers:
            retailer_stock = target_stock - self.global_state["stock_drug_packagers"]
            per_retailer = retailer_stock / len(retailers)
            for retailer in retailers:
                retailer.drug = per_retailer
            self.global_state["stock_drug_retailers"] = retailer_stock

        self.global_state["stock_drug"] = target_stock

    def _create_initial_links(self):
        """Create initial network links"""
        # In real model, this would load from T2_Links.prn file
        # For now, create random links between traffickers and packagers, packagers and retailers

        traffickers = self.network.get_active_agents_by_type("trafficker")
        packagers = self.network.get_active_agents_by_type("packager")
        retailers = self.network.get_active_agents_by_type("retailer")

        # Create some trafficker-packager links
        for packager in packagers:
            if traffickers:
                trafficker = random.choice(traffickers)
                self.network.add_link(
                    trafficker.agent_id, packager.agent_id, "trafficker-packager"
                )

        # Create some packager-retailer links
        for retailer in retailers:
            if packagers:
                packager = random.choice(packagers)
                self.network.add_link(
                    packager.agent_id, retailer.agent_id, "packager-retailer"
                )

    def step(self):
        """Execute one simulation tick (one day)"""
        self.tick += 1
        self.global_state["tick"] = self.tick

        # Reset daily aggregates
        self.global_state["revenues"] = 0
        self.global_state["expenses"] = 0
        self.global_state["weekly_profit_now"] = 0

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
        """Account for weekly wages, family support, and bounded profit."""
        traffickers = self.network.get_active_agents_by_type("trafficker")
        packagers = self.network.get_active_agents_by_type("packager")
        retailers = self.network.get_active_agents_by_type("retailer")

        weekly_profit_now = self.global_state.get("weekly_profit_now", 0)

        def apply_expense(amount: float):
            self.global_state["cash_box"] -= amount
            self.global_state["expenses"] += amount

        # Weekly operational costs
        cost_per_day = self.global_state["cost_per_day"]
        weekly_cost = cost_per_day * 7
        apply_expense(weekly_cost)

        # Wages for traffickers and packagers
        wage_traff_pack = (
            (self.global_state["profit_of_traffickers"] * len(traffickers))
            + (self.global_state["profit_of_packagers"] * len(packagers))
        ) * 7
        apply_expense(wage_traff_pack)

        # Support for families of arrested retailers
        arrested_retailers_family = self.global_state.get(
            "arrested_retailers_family", 0
        )
        expected_arrested_retailers = len(retailers) * 0.56
        base_retailer_support = max(
            expected_arrested_retailers, arrested_retailers_family
        )
        retailer_family_wage = (
            base_retailer_support * config.ARRESTED_RETAILERS_WEEKLY_WAGE
            + self.global_state.get("fm_retailers_wage", 0)
            * config.ARRESTED_RETAILERS_WEEKLY_WAGE
        )
        self.global_state["arrested_retailers_family_wages"] = retailer_family_wage
        apply_expense(retailer_family_wage)

        # Support for families of dead members (all roles)
        dead_members_family = self.global_state.get("dead_members_family", 0)
        expected_dead_members = (
            len(traffickers) + len(packagers) + len(retailers)
        ) * 0.10
        base_dead_support = max(expected_dead_members, dead_members_family)
        dead_members_wage = (
            base_dead_support * config.ARRESTED_OTHER_WEEKLY_WAGE
            + (
                self.global_state.get("fm_traffickers_wage", 0)
                + self.global_state.get("fm_packagers_wage", 0)
            )
            * config.ARRESTED_OTHER_WEEKLY_WAGE
        )
        self.global_state["dead_members_family_wages"] = dead_members_wage
        apply_expense(dead_members_wage)

        # Support for homicide-related families
        homicide_family_wages = self.global_state.get(
            "arrested_homicide_family_wages", 0
        )
        apply_expense(homicide_family_wages)

        # Bound profit with random noise
        weekly_profit = self.global_state["weekly_profit"]
        weekly_profit_max = weekly_profit
        weekly_profit_min = weekly_profit * 0.9

        # Add symmetric random fluctuation (~Uniform[-0.1, 0.1])
        fluctuation = random.uniform(-0.1 * weekly_profit_now, 0.1 * weekly_profit_now)
        weekly_profit_now += fluctuation

        if weekly_profit_now > weekly_profit_max:
            self.global_state["n_weekly_profit_max"] += 1
            weekly_profit_now = weekly_profit_max
        elif weekly_profit_now < weekly_profit_min:
            self.global_state["n_weekly_profit_min"] += 1
            weekly_profit_now = weekly_profit_min

        if weekly_profit_now < 0:
            self.global_state["n_weekly_profit_neg"] += 1

        # Reset accumulator; cash_box already reflects daily revenues/expenses adjustments
        self.global_state["weekly_profit_now"] = 0

    def _is_recruitment_paused(self, tick: int) -> bool:
        """Mirror NetLogo stop logic during disruption for recruitment/updates."""
        ticks_disruption = self.global_state.get("ticks_disruption")
        stop_acquire_days = self.global_state.get("stop_acquire_days", 0)
        arrest_mode = self.global_state.get("arrested_mode", "arrested%")

        if ticks_disruption is None:
            return False

        if tick > ticks_disruption and tick <= ticks_disruption + stop_acquire_days:
            if arrest_mode == "arrested%":
                arrested_pct = self.global_state.get("arrested%", 0)
                if arrested_pct != 0:
                    if tick <= ticks_disruption + stop_acquire_days / 2:
                        rd1 = random.randint(0, 99)
                        if rd1 <= arrested_pct:
                            return True
                        rd = random.uniform(0, 1.1)
                        if rd <= (1 - self.efficiency_vs_security):
                            return True
                    else:
                        rd = random.uniform(0, 1.1)
                        if rd <= (1 - self.efficiency_vs_security):
                            return True
            else:
                arrested_num = self.global_state.get("arrested#", 0)
                if arrested_num != 0:
                    total_agents = (
                        len(self.network.get_active_agents()) if self.network else 0
                    )
                    if tick <= ticks_disruption + stop_acquire_days / 2:
                        rd1 = random.randint(0, max(total_agents, 1))
                        if rd1 <= arrested_num:
                            return True
                        rd = random.uniform(0, 1.1)
                        if rd <= (1 - self.efficiency_vs_security):
                            return True
                    else:
                        rd = random.uniform(0, 1.1)
                        if rd <= (1 - self.efficiency_vs_security):
                            return True

        return False

    def _update_parameters(self):
        """Update parameters and recruitment following NetLogo update-parameters."""
        tick = self.tick
        tick_max = 2 * config.TICKS_PER_YEAR

        # Scenario 3 stop-acquire schedule adjustments
        if self.disruption_mode == "scenario3":
            scenario3_schedule = {
                450: 90,
                630: 90,
                810: 60,
                990: 60,
                1170: 30,
                1350: 30,
                1530: 0,
            }
            ticks_disruption = self.global_state.get("ticks_disruption")
            if ticks_disruption in scenario3_schedule:
                self.global_state["stop_acquire_days"] = scenario3_schedule[
                    ticks_disruption
                ]

        # During disruption pauses, skip recruitment/updates according to NetLogo stop checks
        if self._is_recruitment_paused(tick):
            return

        # Helpers
        def log_growth(base_val: float, target_val: float, ticks_counter: int) -> float:
            y_range = target_val - base_val
            if y_range <= 0:
                return base_val
            return base_val + (
                math.log(1 + ticks_counter * y_range / tick_max, y_range + 1) * y_range
            )

        # Current counts
        traffickers = self.network.get_active_agents_by_type("trafficker")
        packagers = self.network.get_active_agents_by_type("packager")
        retailers = self.network.get_active_agents_by_type("retailer")

        # Supply costs based on current prices (before price updates later in this step)
        supply_costs = (
            self.global_state["wholesale_price"] / self.global_state["retail_price"]
        )

        # Trafficker recruitment
        y_traffickers = round(
            log_growth(config.TRAFFICKERS_2008, config.TRAFFICKERS_2010, tick)
        )
        if len(traffickers) == 0 or y_traffickers > len(traffickers):
            profit_of_traffickers = (
                (
                    self.global_state["cost_per_day"]
                    - self.global_state["cost_per_day"] * supply_costs
                )
                * self.global_state["traffickers_share_of_profits"]
                / (len(traffickers) + 1)
            )
            rd = random.uniform(0, 1.1)
            if profit_of_traffickers > self.global_state[
                "profit_of_traffickers_min"
            ] and rd > (1 - self.efficiency_vs_security):
                new_trafficker = Trafficker(role_category=f"new-traffickers-{tick}")
                self.network.add_agent(new_trafficker)
                if packagers:
                    partner = random.choice(packagers)
                    self.network.add_link(
                        new_trafficker.agent_id, partner.agent_id, "trafficker-packager"
                    )
                else:
                    self.running = False
                    return
                traffickers.append(new_trafficker)
                self.global_state["n_active_traffickers"] = len(traffickers)

        # Packager recruitment
        y_packagers = round(
            log_growth(config.PACKAGERS_2008, config.PACKAGERS_2010, tick)
        )
        if len(packagers) == 0 or y_packagers > len(packagers):
            profit_of_packagers = (
                (
                    self.global_state["cost_per_day"]
                    - self.global_state["cost_per_day"] * supply_costs
                )
                * (1 - self.global_state["traffickers_share_of_profits"])
                / (len(packagers) + 1)
            )
            rd = random.uniform(0, 1.5)
            if profit_of_packagers > self.global_state[
                "profit_of_packagers_min"
            ] and rd > (1 - self.efficiency_vs_security):
                new_packager = Packager(role_category=f"new-packagers-{tick}")
                self.network.add_agent(new_packager)
                if random.randint(0, 1) == 1:
                    if traffickers:
                        partner = random.choice(traffickers)
                        self.network.add_link(
                            partner.agent_id,
                            new_packager.agent_id,
                            "trafficker-packager",
                        )
                    else:
                        self.running = False
                        return
                else:
                    if retailers:
                        partner = random.choice(retailers)
                        self.network.add_link(
                            new_packager.agent_id, partner.agent_id, "packager-retailer"
                        )
                    else:
                        self.running = False
                        return
                packagers.append(new_packager)
                self.global_state["n_active_packagers"] = len(packagers)

        # Retailer recruitment
        y_retailers = round(
            log_growth(config.RETAILERS_2008, config.RETAILERS_2010, tick)
        )
        rd = random.uniform(0, 2)
        if len(retailers) == 0 or (
            int(y_retailers) > len(retailers) and rd > (1 - self.efficiency_vs_security)
        ):
            new_retailer = Retailer(role_category=f"new-retailers-{tick}")
            self.network.add_agent(new_retailer)
            if packagers:
                partner = random.choice(packagers)
                self.network.add_link(
                    partner.agent_id, new_retailer.agent_id, "packager-retailer"
                )
            else:
                self.running = False
                return
            retailers.append(new_retailer)
            self.global_state["n_active_retailers"] = len(retailers)

        # Unit doses (logarithmic growth over two years)
        self.global_state["unit_dose"] = round(
            log_growth(config.UNIT_DOSE_2008, config.UNIT_DOSE_2010, tick)
        )
        self.global_state["unit_dose_min"] = round(
            log_growth(config.UNIT_DOSE_MIN_2008, config.UNIT_DOSE_MIN_2010, tick)
        )
        self.global_state["unit_dose_max"] = round(
            log_growth(config.UNIT_DOSE_MAX_2008, config.UNIT_DOSE_MAX_2010, tick)
        )

        # Drug packages per role
        efficiency_vs_security_pack = self.efficiency_vs_security
        gram_per_dose = self.global_state["gram_per_dose"]

        if len(traffickers) > 0:
            self.global_state["drug_package_of_traffickers"] = (
                (
                    self.global_state["unit_dose_min"]
                    + (
                        self.global_state["unit_dose_max"]
                        - self.global_state["unit_dose_min"]
                    )
                    * efficiency_vs_security_pack
                )
                * gram_per_dose
                / len(traffickers)
                * 30
            )
        else:
            self.running = False
            return

        if len(packagers) > 0:
            self.global_state["drug_package_of_packagers"] = (
                (
                    self.global_state["unit_dose_min"]
                    + (
                        self.global_state["unit_dose_max"]
                        - self.global_state["unit_dose_min"]
                    )
                    * efficiency_vs_security_pack
                )
                * gram_per_dose
                / len(packagers)
            )
        else:
            self.running = False
            return

        if len(retailers) == 0:
            self.running = False
            return

        # Target stock considering current unit doses
        start_up_months = config.START_UP_MONTHS
        self.global_state["target_stock_drug"] = (
            self.global_state["unit_dose"] * gram_per_dose * start_up_months * 30
        )

        # Cost per day (logarithmic growth to 2010)
        self.global_state["cost_per_day"] = round(
            log_growth(config.COST_PER_DAY_2008, config.COST_PER_DAY_2010, tick)
        )

        # Profits (clamped)
        self.global_state["profit_of_traffickers"] = max(
            self.global_state["profit_of_traffickers_min"],
            min(
                self.global_state["profit_of_traffickers_max"],
                (
                    self.global_state["cost_per_day"]
                    - self.global_state["cost_per_day"] * supply_costs
                )
                * self.global_state["traffickers_share_of_profits"]
                / len(traffickers),
            ),
        )

        self.global_state["profit_of_packagers"] = max(
            self.global_state["profit_of_packagers_min"],
            min(
                self.global_state["profit_of_packagers_max"],
                (
                    self.global_state["cost_per_day"]
                    - self.global_state["cost_per_day"] * supply_costs
                )
                * (1 - self.global_state["traffickers_share_of_profits"])
                / len(packagers),
            ),
        )

        self.global_state["profit_of_retailers"] = min(
            self.global_state["profit_of_retailers_max"],
            self.global_state["unit_dose"]
            * self.global_state["price_per_dose"]
            * self.global_state["retailers_share_of_profits"]
            / len(retailers),
        )

        # Weekly profit (logarithmic growth to 2010)
        self.global_state["weekly_profit"] = round(
            log_growth(config.WEEKLY_PROFIT_2008, config.WEEKLY_PROFIT_2010, tick)
        )

        # Wholesale and retail prices (year-based updates)
        if tick > config.TICKS_PER_YEAR:
            self.global_state["wholesale_price"] = config.WHOLESALE_PRICE_2009
            self.global_state["retail_price"] = config.RETAIL_PRICE_2009
        if tick > 2 * config.TICKS_PER_YEAR:
            self.global_state["wholesale_price"] = config.WHOLESALE_PRICE_2010
            self.global_state["retail_price"] = config.RETAIL_PRICE_2010

        # Update supply costs based on updated prices
        self.global_state["wholesale_price_now"] = self.global_state["wholesale_price"]
        self.global_state["retail_price_now"] = self.global_state["retail_price"]
        self.global_state["supply_costs"] = (
            self.global_state["wholesale_price"] / self.global_state["retail_price"]
        )

    def _update_agent_counts(self):
        """Update active agent counts"""
        self.global_state["n_active_traffickers"] = len(
            self.network.get_active_agents_by_type("trafficker")
        )
        self.global_state["n_active_packagers"] = len(
            self.network.get_active_agents_by_type("packager")
        )
        self.global_state["n_active_retailers"] = len(
            self.network.get_active_agents_by_type("retailer")
        )

    def _check_yearly_status(self):
        """Check and log yearly status"""
        year = self.tick // config.TICKS_PER_YEAR
        if config.VERBOSE_OUTPUT:
            print(f"\nYear {year}:")
            print(f"  Cash box: €{self.global_state['cash_box']:.2f}")
            print(
                f"  Members: T={self.global_state['n_active_traffickers']}, "
                f"P={self.global_state['n_active_packagers']}, "
                f"R={self.global_state['n_active_retailers']}"
            )
            print(f"  Stock: {self.global_state['stock_drug']:.2f}g")

    def run(self, max_ticks: Optional[int] = None):
        """Run simulation for specified number of ticks"""
        if max_ticks is None:
            max_ticks = config.TOTAL_TICKS

        while self.tick < max_ticks and self.running:
            if not self.step():
                break

            if self.tick % 100 == 0 and config.VERBOSE_OUTPUT:
                print(f"Tick {self.tick}...", end="\r")

        return self.data_collector.get_data()

    def get_results(self) -> Dict:
        """Get simulation results"""
        return {
            "arrest_scenario": self.arrest_scenario,
            "disruption_mode": self.disruption_mode,
            "efficiency_vs_security": self.efficiency_vs_security,
            "total_ticks": self.tick,
            "final_running": self.running,
            "final_cash_box": self.global_state["cash_box"],
            "data": self.data_collector.get_data(),
            "seed": self.seed,
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
        "arrest_scenario": arrest_scenario,
        "runs": [],
        "n_active_at_end": 0,
    }

    for run_num in range(num_runs):
        sim = MADTORSimulation(arrest_scenario=arrest_scenario)
        sim.run()
        results["runs"].append(sim.get_results())

        # Check if active at end
        if sim.running:
            results["n_active_at_end"] += 1

    return results


if __name__ == "__main__":
    # Run example simulation
    print("Starting MADTOR simulation...")
    sim = MADTORSimulation(arrest_scenario=10)
    sim.run()

    print(f"\nSimulation completed at tick {sim.tick}")
    print(f"Running: {sim.running}")
    print(f"Cash box: €{sim.global_state['cash_box']:.2f}")
    print(
        f"Members: T={sim.global_state['n_active_traffickers']}, "
        f"P={sim.global_state['n_active_packagers']}, "
        f"R={sim.global_state['n_active_retailers']}"
    )

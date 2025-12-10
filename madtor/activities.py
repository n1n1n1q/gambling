"""
Drug trafficking activities: acquisition, packaging, and selling
"""

import random
import math
from typing import List, Tuple, Optional
import madtor.config as config
from madtor.agents import Agent, Network


class DrugTraffickingActivities:
    """Manages drug trafficking operations"""

    def __init__(self, network: Network, global_state: dict):
        self.network = network
        self.state = global_state

    def acquire_drug(self, tick: int):
        """
        Drug acquisition by traffickers.
        Based on composite index of: stock level, market conditions, wholesale price
        """
        if tick % 30 != 0:
            return

        disruption_mode = self.state.get("disruption_mode", "scenario1")
        ticks_disruption = self.state.get("ticks_disruption", None)
        stop_acquire_days = self.state.get("stop_acquire_days", 0)
        efficiency_vs_security = self.state.get("efficiency_vs_security", 0.5)
        arrested_mode = self.state.get("arrested_mode", "arrested%")

        # Scenario3 start-up-months schedule mirrors NetLogo thresholds
        if disruption_mode == "scenario3" and ticks_disruption is not None:
            scenario3_windows = {
                450: 90,
                630: 90,
                810: 60,
                990: 60,
                1170: 30,
                1350: 30,
                1530: 0,
            }
            if ticks_disruption in scenario3_windows:
                stop_acquire_days = scenario3_windows[ticks_disruption]
                self.state["stop_acquire_days"] = stop_acquire_days

        # Disruption window gating (arrest-driven and security-weighted)
        if ticks_disruption is not None:
            in_window = (
                tick > ticks_disruption and tick <= ticks_disruption + stop_acquire_days
            )
            first_half = (
                tick > ticks_disruption
                and tick <= ticks_disruption + stop_acquire_days / 2
            )

            if in_window:
                if arrested_mode == "arrested%":
                    arrested_pct = self.state.get("arrested%", 0)
                    if arrested_pct != 0 and first_half:
                        rd1 = random.randint(0, 99)
                        if rd1 <= arrested_pct:
                            return
                    rd = random.uniform(0, 1.1)
                    if rd <= (1 - efficiency_vs_security):
                        return
                else:
                    arrested_num = self.state.get("arrested#", 0)
                    if arrested_num != 0 and first_half:
                        active_agents_count = len(self.network.get_active_agents())
                        upper = max(active_agents_count - 1, 0)
                        rd1 = random.randint(0, upper)
                        if rd1 <= arrested_num:
                            return
                    rd = random.uniform(0, 1.1)
                    if rd <= (1 - efficiency_vs_security):
                        return

        # Calculate stock-drug-index (0-1): how full are warehouses
        target_stock = self.state.get("target_stock_drug", 1000)
        current_stock = self.state.get("stock_drug", 0)
        stock_drug_index = (
            min(1.0, current_stock / target_stock) if target_stock > 0 else 0
        )

        # Calculate market-condition-index (0-1 normal dist)
        market_condition_index = random.normalvariate(0, 1)
        market_condition_index = (market_condition_index + 3) / 6
        market_condition_index = max(0, min(1, market_condition_index))
        # Weight by efficiency-vs-security
        efficiency_vs_security = self.state.get("efficiency_vs_security", 0.5)
        market_condition_index *= 1 - efficiency_vs_security

        # Calculate wholesale-price-index (0-1)
        wholesale_price = self.state.get("wholesale_price", 40)
        wholesale_price_now = wholesale_price + random.normalvariate(0, 8.73 * 0.5)

        # Track min/max wholesale prices
        if "minw" not in self.state:
            self.state["minw"] = wholesale_price_now
        if "maxw" not in self.state:
            self.state["maxw"] = wholesale_price_now

        self.state["minw"] = min(self.state["minw"], wholesale_price_now)
        self.state["maxw"] = max(self.state["maxw"], wholesale_price_now)
        self.state["wholesale_price_now"] = wholesale_price_now

        # Normalize price index
        min_price = wholesale_price - 10
        max_price = wholesale_price + 10
        price_range = max_price - min_price
        wholesale_price_index = (
            (wholesale_price_now - min_price) / price_range if price_range > 0 else 0.5
        )
        wholesale_price_index = max(0, min(1, wholesale_price_index))

        # Composite acquisition index
        acquisition_index = (
            stock_drug_index * market_condition_index * wholesale_price_index
        )

        # Track min/max acquisition index
        if "minacq_ind" not in self.state:
            self.state["minacq_ind"] = acquisition_index
        if "maxacq_ind" not in self.state:
            self.state["maxacq_ind"] = acquisition_index

        self.state["minacq_ind"] = min(self.state["minacq_ind"], acquisition_index)
        self.state["maxacq_ind"] = max(self.state["maxacq_ind"], acquisition_index)

        # If warehouses too full, don't acquire
        if current_stock >= target_stock * 2:
            acquisition_index = 999  # Signal: don't acquire

        # Each trafficker tries to acquire
        traffickers = self.network.get_active_agents_by_type("trafficker")
        cash_box = self.state.get("cash_box", 0)
        drug_package_of_traffickers = self.state.get("drug_package_of_traffickers", 100)
        n_acquisition = self.state.get("n_acquisition", 0)

        for trafficker in traffickers:
            if acquisition_index == 999:
                continue

            # Probability based on criminal expertise
            rd = random.random() * random.random() * random.random()
            if trafficker.attractiveness / 100 + rd > acquisition_index:
                # Successful acquisition
                trafficker.attempt_acquisition(wholesale_price_now, success=True)

                # Check if enough cash
                acquisition_cost = wholesale_price_now * drug_package_of_traffickers
                if acquisition_cost <= cash_box * 0.5:
                    # Full acquisition
                    trafficker.drug += drug_package_of_traffickers
                    self.state["stock_drug_traffickers"] = (
                        self.state.get("stock_drug_traffickers", 0)
                        + drug_package_of_traffickers
                    )
                    self.state["stock_drug"] = (
                        self.state.get("stock_drug", 0) + drug_package_of_traffickers
                    )
                    self.state["cash_box"] = cash_box - acquisition_cost
                    self.state["expenses"] = (
                        self.state.get("expenses", 0) + acquisition_cost
                    )
                else:
                    # Partial acquisition with available cash
                    available_amount = cash_box * 0.5 / wholesale_price_now
                    trafficker.drug += available_amount
                    self.state["stock_drug_traffickers"] = (
                        self.state.get("stock_drug_traffickers", 0) + available_amount
                    )
                    self.state["stock_drug"] = (
                        self.state.get("stock_drug", 0) + available_amount
                    )
                    self.state["expenses"] = (
                        self.state.get("expenses", 0) + cash_box * 0.5
                    )
                    self.state["cash_box"] = cash_box * 0.5

                n_acquisition += 1
            else:
                # Failed acquisition decreases attractiveness
                if trafficker.attractiveness > 0.8:
                    trafficker.attractiveness = 0.8
                else:
                    trafficker.attractiveness = max(
                        0.0,
                        trafficker.attractiveness
                        - (0.0001 ** (1 - trafficker.attractiveness)),
                    )
                trafficker.attempt_acquisition(wholesale_price_now, success=False)

        self.state["n_acquisition"] = n_acquisition
        if self.state.get("stock_drug_traffickers", 0) < 0:
            self.state["stock_drug_traffickers"] = 0

    def package_drug(self, tick: int):
        """
        Daily drug packaging and delivery from traffickers to packagers,
        then from packagers to retailers
        """
        packagers = self.network.get_active_agents_by_type("packager")
        drug_max_packagers = self.state.get(
            "drug_max_of_packagers", config.DRUG_MAX_OF_PACKAGERS
        )

        # Update packager availability and attractiveness (NetLogo double-random update)
        for packager in packagers:
            packager.update_availability(packager.drug, drug_max_packagers)
            packager.update_attractiveness()

        stock_drug_traffickers = self.state.get("stock_drug_traffickers", 0)

        # Traffickers to packagers transfer
        if stock_drug_traffickers <= 0:
            self.state["n_exhaust_traffickers"] = (
                self.state.get("n_exhaust_traffickers", 0) + 1
            )
        else:
            self._transfer_trafficker_to_packagers(drug_max_packagers)

        # Update retailer availability
        retailers = self.network.get_active_agents_by_type("retailer")
        price_per_dose = self.state.get("price_per_dose", config.PRICE_PER_DOSE)
        retailers_share = self.state.get(
            "retailers_share_of_profits", config.RETAILERS_SHARE_OF_PROFITS
        )
        gram_per_dose = self.state.get("gram_per_dose", config.GRAM_PER_DOSE)
        profit_cap = self.state.get(
            "profit_of_retailers_max", config.PROFIT_OF_RETAILERS_MAX
        )
        # Drug amount that yields profit_cap for a retailer in a day
        drug_max_retailers = (
            profit_cap / (price_per_dose * retailers_share) * gram_per_dose
            if price_per_dose * retailers_share > 0
            else 0
        )

        for retailer in retailers:
            retailer.update_availability(retailer.drug, drug_max_retailers)
            retailer.update_attractiveness()

        stock_drug_packagers = self.state.get("stock_drug_packagers", 0)
        drug_package_retailers = self.state.get("drug_package_of_retailers", 5.75)

        # Packagers to retailers transfer
        if stock_drug_packagers < drug_package_retailers:
            self.state["n_exhaust_packagers"] = (
                self.state.get("n_exhaust_packagers", 0) + 1
            )
        else:
            self._transfer_packagers_to_retailers(
                drug_package_retailers, drug_max_retailers
            )

    def _transfer_trafficker_to_packagers(self, drug_max_packagers: float):
        """Transfer drugs from traffickers to packagers based on trust-appeal"""
        traffickers = self.network.get_active_agents_by_type("trafficker")
        packagers = self.network.get_active_agents_by_type("packager")

        if not packagers:
            return

        drug_package = self.state.get("drug_package_of_packagers", 50)

        # Visibility normalization (degree-based proxy)
        active_agents = self.network.get_active_agents()
        total_agents = len(active_agents)
        if total_agents <= 1:
            min_vis = max_vis = 1.0
        else:
            vis_values = [
                agent.get_degree() / (total_agents - 1) for agent in active_agents
            ]
            min_vis = min(vis_values)
            max_vis = max(vis_values)
            if max_vis - min_vis == 0:
                min_vis = 0.0
                max_vis = 1.0

        for trafficker in traffickers:
            if trafficker.drug <= 0:
                continue

            # Calculate trust-appeal for each packager
            best_packager = None
            best_trust_appeal = -1

            # Determine familiarity bounds across available packagers
            min_fam = 0
            max_fam = 1
            for packager in packagers:
                if packager.availability <= 0:
                    continue
                fam = trafficker.get_connection_familiarity(packager.agent_id)
                if fam > 0:
                    min_fam = min(min_fam, fam)
                    max_fam = max(max_fam, fam)

            for packager in packagers:
                if packager.availability <= 0:
                    continue

                fam = trafficker.get_connection_familiarity(packager.agent_id)
                if max_fam - min_fam == 0:
                    trust_appeal = 1
                else:
                    trust_appeal = (fam - min_fam) / (max_fam - min_fam)

                # Visibility component normalized
                vis_raw = (
                    packager.get_degree() / (total_agents - 1)
                    if total_agents > 1
                    else 1.0
                )
                if max_vis - min_vis == 0:
                    visibility_norm = 1
                else:
                    visibility_norm = (vis_raw - min_vis) / (max_vis - min_vis)

                trust_appeal += visibility_norm
                trust_appeal = (
                    trust_appeal
                    / 2
                    * (1 - self.state.get("efficiency_vs_security", 0.5))
                )

                appeal_part = (
                    (packager.attractiveness + visibility_norm)
                    / 2
                    * self.state.get("efficiency_vs_security", 0.5)
                )
                total_trust_appeal = trust_appeal + appeal_part

                if total_trust_appeal > best_trust_appeal:
                    best_trust_appeal = total_trust_appeal
                    best_packager = packager

            # Transfer drug to best packager
            if best_packager:
                transfer_amount = min(drug_package, trafficker.drug)
                best_packager.drug += transfer_amount
                trafficker.drug -= transfer_amount

                # Update familiarity
                trafficker.add_connection(best_packager.agent_id, "trafficker-packager")
                best_packager.add_connection(trafficker.agent_id, "trafficker-packager")

                # Update stocks
                self.state["stock_drug_traffickers"] = (
                    self.state.get("stock_drug_traffickers", 0) - transfer_amount
                )
                self.state["stock_drug_packagers"] = (
                    self.state.get("stock_drug_packagers", 0) + transfer_amount
                )

                if self.state["stock_drug_traffickers"] < 0:
                    self.state["stock_drug_traffickers"] = 0
                if trafficker.drug < 0:
                    trafficker.drug = 0
                if best_packager.drug >= drug_max_packagers:
                    best_packager.availability = 0
                else:
                    best_packager.availability = 1

    def _transfer_packagers_to_retailers(
        self, drug_package: float, drug_max_retailers: float
    ):
        """Transfer drugs from packagers to retailers based on trust-appeal"""
        packagers = self.network.get_active_agents_by_type("packager")
        retailers = self.network.get_active_agents_by_type("retailer")

        if not retailers:
            return

        efficiency_vs_security = self.state.get("efficiency_vs_security", 0.5)
        unit_dose_min = self.state.get("unit_dose_min", 530)
        unit_dose_max = self.state.get("unit_dose_max", 900)
        gram_per_dose = self.state.get("gram_per_dose", 0.25)

        target_amount = (
            unit_dose_min + (unit_dose_max - unit_dose_min) * efficiency_vs_security
        ) * gram_per_dose

        # Visibility normalization (degree-based proxy)
        active_agents = self.network.get_active_agents()
        total_agents = len(active_agents)
        if total_agents <= 1:
            min_vis = max_vis = 1.0
        else:
            vis_values = [
                agent.get_degree() / (total_agents - 1) for agent in active_agents
            ]
            min_vis = min(vis_values)
            max_vis = max(vis_values)
            if max_vis - min_vis == 0:
                min_vis = 0.0
                max_vis = 1.0

        for packager in packagers:
            if packager.drug <= 0:
                continue

            # Determine familiarity bounds across available retailers
            min_fam = 0
            max_fam = 1
            for retailer in retailers:
                if retailer.availability <= 0:
                    continue
                fam = packager.get_connection_familiarity(retailer.agent_id)
                if fam > 0:
                    min_fam = min(min_fam, fam)
                    max_fam = max(max_fam, fam)

            best_retailer = None
            best_trust_appeal = -1

            for retailer in retailers:
                if retailer.availability <= 0:
                    continue

                fam = packager.get_connection_familiarity(retailer.agent_id)
                if max_fam - min_fam == 0:
                    trust_appeal = 1
                else:
                    trust_appeal = (fam - min_fam) / (max_fam - min_fam)

                vis_raw = (
                    retailer.get_degree() / (total_agents - 1)
                    if total_agents > 1
                    else 1.0
                )
                if max_vis - min_vis == 0:
                    visibility_norm = 1
                else:
                    visibility_norm = (vis_raw - min_vis) / (max_vis - min_vis)

                trust_appeal += visibility_norm
                trust_appeal = trust_appeal / 2 * (1 - efficiency_vs_security)

                appeal_part = (
                    (retailer.attractiveness + visibility_norm)
                    / 2
                    * efficiency_vs_security
                )
                total_trust_appeal = trust_appeal + appeal_part

                if total_trust_appeal > best_trust_appeal:
                    best_trust_appeal = total_trust_appeal
                    best_retailer = retailer

            if best_retailer is None:
                continue

            num_packages = 0
            while num_packages * drug_package < target_amount and packager.drug > 0:
                transfer_amount = min(drug_package, packager.drug)
                best_retailer.drug += transfer_amount
                packager.drug -= transfer_amount

                # Update familiarity
                packager.add_connection(best_retailer.agent_id, "packager-retailer")
                best_retailer.add_connection(packager.agent_id, "packager-retailer")

                # Update stocks
                self.state["stock_drug_packagers"] = (
                    self.state.get("stock_drug_packagers", 0) - transfer_amount
                )
                self.state["stock_drug_retailers"] = (
                    self.state.get("stock_drug_retailers", 0) + transfer_amount
                )

                if self.state["stock_drug_packagers"] < 0:
                    self.state["stock_drug_packagers"] = 0
                if packager.drug < 0:
                    packager.drug = 0
                best_retailer.availability = (
                    0 if best_retailer.drug >= drug_max_retailers else 1
                )

                num_packages += 1

                if packager.drug <= 0:
                    break

    def sell_drug(self, tick: int):
        """
        Daily drug sales by retailers to consumers.
        Each retailer tries to sell doses up to their profit limit.
        """
        retailers = self.network.get_active_agents_by_type("retailer")

        # Reset daily profits and availability (NetLogo: profit=0, availability=1)
        for retailer in retailers:
            retailer.profit = 0.0
            retailer.availability = 1

        # Randomize number of doses to sell (NetLogo: base + two random spans)
        unit_dose = self.state.get("unit_dose", self.state.get("unit_dose_min", 530))
        unit_dose_min = self.state.get("unit_dose_min", 530)
        unit_dose_max = self.state.get("unit_dose_max", 900)
        span1 = max(0, int(unit_dose_min - unit_dose))
        span2 = max(0, int(unit_dose_max - unit_dose))
        unit_dose_now = unit_dose
        unit_dose_now += random.randrange(span1) if span1 > 0 else 0
        unit_dose_now += random.randrange(span2) if span2 > 0 else 0
        self.state["unit_dose_now"] = unit_dose_now

        # Calculate per-retailer profit target
        price_per_dose = self.state.get("price_per_dose", 32)
        retailers_share = self.state.get("retailers_share_of_profits", 0.18)
        profit_max = self.state.get("profit_of_retailers_max", 500)

        if not retailers:
            return

        profit_per_retailer = (
            unit_dose_now * price_per_dose * retailers_share / len(retailers)
            if len(retailers) > 0
            else 0
        )
        profit_per_retailer = min(profit_per_retailer, profit_max)
        self.state["profit_of_retailers"] = profit_per_retailer

        gram_per_dose = self.state.get("gram_per_dose", 0.25)
        wholesale_price_now = self.state.get("wholesale_price_now", 40)
        stock_drug_retailers = self.state.get("stock_drug_retailers", 0)
        cash_box = self.state.get("cash_box", 0)

        # Sell doses (NetLogo while loop)
        n_sold = 0
        while n_sold < unit_dose_now:
            n_sold += 1
            if stock_drug_retailers <= 0:
                break

            # Select retailer with highest availability*drug
            best_retailer = max(
                retailers,
                key=lambda r: r.availability * r.drug,
                default=None,
            )

            if best_retailer is None:
                break

            if best_retailer.drug >= gram_per_dose and best_retailer.availability > 0:
                best_retailer.drug -= gram_per_dose
                best_retailer.profit += price_per_dose * retailers_share
                if best_retailer.profit >= profit_max:
                    best_retailer.availability = 0

                stock_drug_retailers -= gram_per_dose
                cash_box += price_per_dose - price_per_dose * retailers_share
                self.state["revenues"] = (
                    self.state.get("revenues", 0)
                    + price_per_dose
                    - price_per_dose * retailers_share
                )
                self.state["weekly_profit_now"] = (
                    self.state.get("weekly_profit_now", 0)
                    + price_per_dose
                    - price_per_dose * retailers_share
                    - gram_per_dose * wholesale_price_now
                )
            else:
                # Exhausted retailers mid-day
                self.state["n_exhaust_retailers"] = (
                    self.state.get("n_exhaust_retailers", 0) + 1
                )
                if n_sold < unit_dose_now * 0.9:
                    self.state["n_exhaust_retailers_90"] = (
                        self.state.get("n_exhaust_retailers_90", 0) + 1
                    )
                break

        self.state["stock_drug_retailers"] = stock_drug_retailers
        self.state["stock_drug"] = (
            self.state.get("stock_drug_traffickers", 0)
            + self.state.get("stock_drug_packagers", 0)
            + stock_drug_retailers
        )
        self.state["cash_box"] = cash_box

    def _calculate_visibility(self, agent: Agent) -> float:
        """Calculate normalized visibility (closeness centrality proxy)"""
        total_agents = len([a for a in self.network.get_active_agents()])
        if total_agents <= 1:
            return 1.0

        agent_degree = agent.get_degree()
        return agent_degree / (total_agents - 1)

"""
Law enforcement interventions and disruption mechanisms
"""

import random
import math
from typing import List
import madtor.config as config
from madtor.agents import Network, Trafficker, Packager, Retailer, Agent


class LawEnforcement:
    """Manages law enforcement interventions and arrests"""
    
    def __init__(self, network: Network, global_state: dict):
        self.network = network
        self.state = global_state
    
    def perform_minor_arrests(self, tick: int):
        """
        Perform minor periodic arrests (monthly probability-based).
        Arrests a maximum of one random member per call.
        """
        if tick % 30 != 15:  # Day 15 of each month
            return
        
        efficiency_vs_security = self.state.get('efficiency_vs_security', 0.5)

        # Probability draw mirroring NetLogo piecewise ranges
        rd = random.uniform(0, 9.99)
        if efficiency_vs_security == 0.0:
            rd = random.uniform(0, 1.01)
        elif efficiency_vs_security == 0.2:
            rd = random.uniform(0, 0.84)
        elif efficiency_vs_security == 0.4:
            rd = random.uniform(0, 0.67)
        elif efficiency_vs_security == 0.6:
            rd = random.uniform(0, 0.80)
        elif efficiency_vs_security == 0.8:
            rd = random.uniform(0, 2.00)
        elif efficiency_vs_security == 1.0:
            rd = random.uniform(0, 0.99)

        if rd > (1 - efficiency_vs_security):
            active_agents = self.network.get_active_agents()
            if active_agents:
                arrested = random.choice(active_agents)
                self._arrest_agent(arrested, tick, is_major=False)
                self._update_arrest_counts(arrested, is_major=False)

                # Update fm wages (NetLogo logic)
                if arrested.agent_type == 'trafficker':
                    self.state['fm_traffickers_wage'] = self.state.get('fm_traffickers_wage', 0) + 1
                elif arrested.agent_type == 'packager':
                    self.state['fm_packagers_wage'] = self.state.get('fm_packagers_wage', 0) + 1
                elif arrested.agent_type == 'retailer':
                    self.state['fm_retailers_wage'] = self.state.get('fm_retailers_wage', 0) + 1

                # Remove drug from arrested agent and recalc stocks as NetLogo does after removal
                arrested.drug = 0
                self._recalculate_drug_stocks()
    
    def perform_major_arrest(self, tick: int, arrest_percentage: int):
        """
        Perform major law enforcement action - arrest specified percentage of members.
        Matches NetLogo 'attempt-of-disruption' procedure.
        
        Args:
            tick: Current simulation tick
            arrest_percentage: Percentage of members to arrest (0-100)
        """
        # Determine target group
        target_of_disruption = self.state.get('target_of_disruption', 'turtles')
        if target_of_disruption == 'traffickers':
            target_agents = self.network.get_active_agents_by_type('trafficker')
        elif target_of_disruption == 'packagers':
            target_agents = self.network.get_active_agents_by_type('packager')
        elif target_of_disruption == 'retailers':
            target_agents = self.network.get_active_agents_by_type('retailer')
        else:
            target_agents = self.network.get_active_agents()

        if not target_agents:
            return

        # Save counts before disruption
        traffickers = self.network.get_active_agents_by_type('trafficker')
        packagers = self.network.get_active_agents_by_type('packager')
        retailers = self.network.get_active_agents_by_type('retailer')
        
        ntra = len(traffickers)
        npac = len(packagers)
        nret = len(retailers)
        
        arrested_retailers_family = self.state.get('arrested_retailers_family', 0)
        # In NetLogo: set arrested-retailers-family count retailers
        # But arrested-retailers-family is a cumulative counter in Python state?
        # NetLogo: set arrested-retailers-family count retailers (resets it to current count before disruption)
        # Then updates it after.
        # Let's follow NetLogo exactly for this procedure's local logic, but we need to be careful about state persistence.
        # In NetLogo 'arrested-retailers-family' is a global.
        self.state['arrested_retailers_family'] = nret
        
        dead_members_family = self.state.get('dead_members_family', 0)
        # NetLogo: set dead-members-family count turtles
        self.state['dead_members_family'] = len(self.network.get_active_agents())

        # Calculate number to arrest
        disruption_mode = self.state.get('disruption_mode', 'scenario1')
        arrest_mode = self.state.get('arrested_mode', 'arrested%')
        efficiency_vs_security = self.state.get('efficiency_vs_security', 0.5)
        
        arrested_count = 0
        rd = random.random() # random-float 1
        
        if disruption_mode == "scenario1":
            if arrest_mode == "arrested%":
                modified_arrested = arrest_percentage
                arrested_count = int(modified_arrested / 100 * len(target_agents))
            else:
                arrested_num = self.state.get('arrested#', 0)
                modified_arrested = arrested_num
                arrested_count = arrested_num
        else:
            # Scenario 2 logic (and others)
            if arrest_mode == "arrested%":
                if efficiency_vs_security < 0.6:
                    rd = 10 + rd * 10
                    modified_arrested = arrest_percentage - (arrest_percentage * rd / 100)
                    arrested_count = int(modified_arrested / 100 * len(target_agents))
                elif efficiency_vs_security == 0.6:
                    rd = -5 + rd * 10
                    modified_arrested = arrest_percentage + (arrest_percentage * rd / 100)
                    arrested_count = int(modified_arrested / 100 * len(target_agents))
                else:
                    rd = 10 + rd * 10
                    modified_arrested = arrest_percentage + (arrest_percentage * rd / 100)
                    arrested_count = int(modified_arrested / 100 * len(target_agents))
            else:
                arrested_num = self.state.get('arrested#', 0)
                if efficiency_vs_security < 0.6:
                    rd = 10 + rd * 10
                    modified_arrested = arrested_num - (arrested_num * rd / 100)
                    arrested_count = int(modified_arrested)
                elif efficiency_vs_security == 0.6:
                    rd = -5 + rd * 10
                    modified_arrested = arrested_num + (arrested_num * rd / 100)
                    arrested_count = int(modified_arrested)
                else:
                    rd = 10 + rd * 10
                    modified_arrested = arrested_num + (arrested_num * rd / 100)
                    arrested_count = int(modified_arrested)

        if arrested_count > len(target_agents):
            arrested_count = len(target_agents)
            
        # Randomly select agents to arrest
        if arrested_count > 0:
            arrested_agents = random.sample(target_agents, arrested_count)
            
            # Arrest them
            for agent in arrested_agents:
                self._arrest_agent(agent, tick, is_major=True)
                # Note: _update_arrest_counts is called inside _arrest_agent in original code? No, separate call.
                # But here we want to track major arrests specifically.
                # The original python code called _update_arrest_counts.
                # NetLogo updates n-arrested-traffickers-major etc. based on count difference.
            
            # Confiscate their drugs
            self._confiscate_drugs(arrested_agents)

        # Update major arrest counters based on count difference (NetLogo logic)
        current_traffickers = len(self.network.get_active_agents_by_type('trafficker'))
        current_packagers = len(self.network.get_active_agents_by_type('packager'))
        current_retailers = len(self.network.get_active_agents_by_type('retailer'))
        current_total = len(self.network.get_active_agents())

        if ntra > current_traffickers:
            self.state['n_arrested_traffickers_major'] = self.state.get('n_arrested_traffickers_major', 0) + (ntra - current_traffickers)
        if npac > current_packagers:
            self.state['n_arrested_packagers_major'] = self.state.get('n_arrested_packagers_major', 0) + (npac - current_packagers)
        if nret > current_retailers:
            self.state['n_arrested_retailers_major'] = self.state.get('n_arrested_retailers_major', 0) + (nret - current_retailers)

        # Update family support counts
        # NetLogo: set dead-members-family dead-members-family * 0.1 + (dead-members-family - count turtles) - (arrested-retailers-family - count retailers)
        dmf = self.state['dead_members_family']
        arf = self.state['arrested_retailers_family']
        
        self.state['dead_members_family'] = dmf * 0.1 + (dmf - current_total) - (arf - current_retailers)
        
        # NetLogo: set arrested-retailers-family arrested-retailers-family * 0.56 + (arrested-retailers-family - count retailers)
        self.state['arrested_retailers_family'] = arf * 0.56 + (arf - current_retailers)

        # Recalculate drug stocks
        self._recalculate_drug_stocks()

        # Update tick counters for recruitment (resetting growth curves)
        tick_max = 2 * 365
        
        # Update ticks-traffickers
        y_range_t = config.TRAFFICKERS_2010 - config.TRAFFICKERS_2008
        if y_range_t != 0:
            count_t = current_traffickers
            # Formula: int (((y-range + 1) ^ ((count traffickers - traffickers-2008) / y-range) - 1) * tick-max / y-range)
            # Note: NetLogo ^ is power.
            try:
                exponent = (count_t - config.TRAFFICKERS_2008) / y_range_t
                base = y_range_t + 1
                term = math.pow(base, exponent) - 1
                self.state['ticks_traffickers'] = int(term * tick_max / y_range_t)
            except (ValueError, ZeroDivisionError):
                self.state['ticks_traffickers'] = 0
        
        # Update ticks-packagers
        y_range_p = config.PACKAGERS_2010 - config.PACKAGERS_2008
        if y_range_p != 0:
            count_p = current_packagers
            try:
                exponent = (count_p - config.PACKAGERS_2008) / y_range_p
                base = y_range_p + 1
                term = math.pow(base, exponent) - 1
                self.state['ticks_packagers'] = int(term * tick_max / y_range_p)
            except (ValueError, ZeroDivisionError):
                self.state['ticks_packagers'] = 0

        # Update ticks-retailers
        y_range_r = config.RETAILERS_2010 - config.RETAILERS_2008
        if y_range_r != 0:
            count_r = current_retailers
            try:
                exponent = (count_r - config.RETAILERS_2008) / y_range_r
                base = y_range_r + 1
                term = math.pow(base, exponent) - 1
                self.state['ticks_retailers'] = int(term * tick_max / y_range_r)
            except (ValueError, ZeroDivisionError):
                self.state['ticks_retailers'] = 0

        # Update wage multipliers based on disruption count (Scenario 3 logic mostly)
        n_disruptions_obs = self.state.get('n_disruptions_obs', 1) # Default 1 for scenario 1/2
        # In scenario 1/2, n_disruptions_obs is usually 1.
        # If this function is called for scenario 3, n_disruptions_obs might be > 1.
        
        fm = 1
        if n_disruptions_obs == 2:
            fm = 15
        elif n_disruptions_obs == 3:
            fm = 20
        elif n_disruptions_obs == 4:
            fm = 25
        elif n_disruptions_obs == 5:
            fm = 30
            
        if n_disruptions_obs > 1:
            if ntra > current_traffickers:
                self.state['fm_traffickers_wage'] = self.state.get('fm_traffickers_wage', 0) + (ntra - current_traffickers) * fm
            if npac > current_packagers:
                self.state['fm_packagers_wage'] = self.state.get('fm_packagers_wage', 0) + (npac - current_packagers) * fm
            if nret > current_retailers:
                self.state['fm_retailers_wage'] = self.state.get('fm_retailers_wage', 0) + (nret - current_retailers) * fm

        # Trigger adaptation period
        stop_acquire_days = self.state.get('stop_acquire_days', 60)
        self.state['ticks_disruption'] = tick
        self.state['stop_acquiring_until'] = tick + stop_acquire_days
    
    def apply_acquisition_disruption(self, tick: int) -> bool:
        """
        Check if organization should stop acquiring drugs due to disruption.
        
        Returns:
            True if should continue acquiring, False if should stop
        """
        arrest_mode = self.state.get('arrested_mode', 'arrested%')
        ticks_disruption = self.state.get('ticks_disruption', None)
        stop_acquire_days = self.state.get('stop_acquire_days', 0)
        efficiency_vs_security = self.state.get('efficiency_vs_security', 0.5)
        
        if ticks_disruption is None:
            return True  # No disruption active
        
        if tick > ticks_disruption and tick <= ticks_disruption + stop_acquire_days:
            # Within disruption period
            if tick > ticks_disruption and tick <= ticks_disruption + stop_acquire_days / 2:
                # First half: stronger restrictions
                if arrest_mode == 'arrested%':
                    arrested_pct = self.state.get('arrested%', 0)
                    rd1 = random.randint(0, 99)
                    if rd1 <= arrested_pct:
                        return False  # Stop acquiring
                else:
                    arrested_num = self.state.get('arrested#', 0)
                    rd1 = random.randint(0, len(self.network.get_active_agents()))
                    if rd1 <= arrested_num:
                        return False
                
                # Additional security-based check
                rd = random.uniform(0, 1.1)
                if rd <= (1 - efficiency_vs_security):
                    return False
            else:
                # Second half: lighter restrictions
                rd = random.uniform(0, 1.1)
                if rd <= (1 - efficiency_vs_security):
                    return False
        
        return True
    
    def _arrest_agent(self, agent: Agent, tick: int, is_major: bool):
        """Mark agent as arrested"""
        agent.is_arrested = True
        agent.arrest_date = tick
    
    def _update_arrest_counts(self, agent: Agent, is_major: bool):
        """Update arrest statistics"""
        if is_major:
            if agent.agent_type == 'trafficker':
                self.state['n_arrested_traffickers_major'] = self.state.get('n_arrested_traffickers_major', 0) + 1
            elif agent.agent_type == 'packager':
                self.state['n_arrested_packagers_major'] = self.state.get('n_arrested_packagers_major', 0) + 1
            elif agent.agent_type == 'retailer':
                self.state['n_arrested_retailers_major'] = self.state.get('n_arrested_retailers_major', 0) + 1
        else:
            if agent.agent_type == 'trafficker':
                self.state['n_arrested_traffickers_minor'] = self.state.get('n_arrested_traffickers_minor', 0) + 1
            elif agent.agent_type == 'packager':
                self.state['n_arrested_packagers_minor'] = self.state.get('n_arrested_packagers_minor', 0) + 1
            elif agent.agent_type == 'retailer':
                self.state['n_arrested_retailers_minor'] = self.state.get('n_arrested_retailers_minor', 0) + 1
    
    def _confiscate_drugs(self, arrested_agents: List[Agent]):
        """Confiscate drugs from arrested agents"""
        total_confiscated = 0
        
        for agent in arrested_agents:
            total_confiscated += agent.drug
            agent.drug = 0
        
        # Update stocks
        stock_drug = self.state.get('stock_drug', 0)
        self.state['stock_drug'] = max(0, stock_drug - total_confiscated)
        
        # Update individual stocks
        self._recalculate_drug_stocks()
    
    def _recalculate_drug_stocks(self):
        """Recalculate drug stocks by role after arrests"""
        stock_drug_traffickers = 0
        stock_drug_packagers = 0
        stock_drug_retailers = 0
        
        for agent in self.network.get_active_agents():
            if agent.agent_type == 'trafficker':
                stock_drug_traffickers += agent.drug
            elif agent.agent_type == 'packager':
                stock_drug_packagers += agent.drug
            elif agent.agent_type == 'retailer':
                stock_drug_retailers += agent.drug
        
        self.state['stock_drug_traffickers'] = stock_drug_traffickers
        self.state['stock_drug_packagers'] = stock_drug_packagers
        self.state['stock_drug_retailers'] = stock_drug_retailers
        self.state['stock_drug'] = stock_drug_traffickers + stock_drug_packagers + stock_drug_retailers
    
    def check_organization_viability(self) -> bool:
        """
        Check if organization can continue operating.
        
        Returns:
            True if organization can continue, False if disrupted
        """
        active_traffickers = self.network.get_active_agents_by_type('trafficker')
        active_packagers = self.network.get_active_agents_by_type('packager')
        active_retailers = self.network.get_active_agents_by_type('retailer')
        
        # Check if all members of any role are arrested
        if len(active_traffickers) == 0:
            return False  # Can't acquire drugs
        
        if len(active_packagers) == 0:
            return False  # Can't package drugs
        
        if len(active_retailers) == 0:
            return False  # Can't sell drugs
        
        # Check if cash box is negative
        cash_box = self.state.get('cash_box', 0)
        if cash_box < 0:
            return False
        
        return True
    
    def handle_recruitment_freeze(self, tick: int) -> bool:
        """
        After disruption, organization can't recruit for a period.
        
        Returns:
            True if can recruit, False if frozen
        """
        ticks_disruption = self.state.get('ticks_disruption', None)
        stop_acquire_days = self.state.get('stop_acquire_days', 60)
        
        if ticks_disruption is None:
            return True
        
        if tick > ticks_disruption and tick <= ticks_disruption + stop_acquire_days:
            return False
        
        return True

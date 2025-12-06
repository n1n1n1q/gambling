"""
Law enforcement interventions and disruption mechanisms
"""

import random
from typing import List
from agents import Network, Trafficker, Packager, Retailer, Agent


class LawEnforcement:
    """Manages law enforcement interventions and arrests"""
    
    def __init__(self, network: Network, global_state: dict):
        self.network = network
        self.state = global_state
    
    def perform_minor_arrests(self, tick: int):
        """
        Perform minor periodic arrests (monthly probability-based).
        Arrests a maximum of one random member per month.
        """
        if tick % 30 != 15:  # Day 15 of each month
            return
        
        efficiency_vs_security = self.state.get('efficiency_vs_security', 0.5)
        
        # Probability based on efficiency-vs-security
        if efficiency_vs_security == 0.0:
            probability = 1.01
        elif efficiency_vs_security == 0.2:
            probability = 0.84
        elif efficiency_vs_security == 0.4:
            probability = 0.67
        elif efficiency_vs_security == 0.6:
            probability = 0.80
        elif efficiency_vs_security == 0.8:
            probability = 2.00
        else:  # 1.0
            probability = 0.99
        
        rd = random.uniform(0, 9.99)
        
        if rd > (1 - efficiency_vs_security):
            # Arrest one random agent
            active_agents = self.network.get_active_agents()
            if active_agents:
                arrested = random.choice(active_agents)
                self._arrest_agent(arrested, tick, is_major=False)
                
                # Update counts
                self._update_arrest_counts(arrested, is_major=False)
    
    def perform_major_arrest(self, tick: int, arrest_percentage: int):
        """
        Perform major law enforcement action - arrest specified percentage of members.
        
        Args:
            tick: Current simulation tick
            arrest_percentage: Percentage of members to arrest (0-100)
        """
        active_agents = self.network.get_active_agents()
        if not active_agents:
            return
        
        # Calculate number to arrest
        num_to_arrest = int(len(active_agents) * arrest_percentage / 100)
        if num_to_arrest == 0 and arrest_percentage > 0:
            num_to_arrest = 1
        
        if num_to_arrest == 0:
            return
        
        # Randomly select agents to arrest
        arrested_agents = random.sample(active_agents, min(num_to_arrest, len(active_agents)))
        
        # Arrest them
        for agent in arrested_agents:
            self._arrest_agent(agent, tick, is_major=True)
            self._update_arrest_counts(agent, is_major=True)
        
        # Confiscate their drugs
        self._confiscate_drugs(arrested_agents)
        
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

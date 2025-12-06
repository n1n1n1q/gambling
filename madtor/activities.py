"""
Drug trafficking activities: acquisition, packaging, and selling
"""

import random
import math
from typing import List, Tuple, Optional
from madtor.agents import Trafficker, Packager, Retailer, Agent, Network


class DrugTraffickingActivities:
    """Manages drug trafficking operations"""
    
    def __init__(self, network: Network, global_state: dict):
        self.network = network
        self.state = global_state
        
    def acquire_drug(self, tick: int):
        """
        Monthly drug acquisition by traffickers.
        Based on composite index of: stock level, market conditions, wholesale price
        """
        if tick % 30 != 0:  # Once per month (30 ticks)
            return
        
        # Calculate stock-drug-index (0-1): how full are warehouses
        target_stock = self.state.get('target_stock_drug', 1000)
        current_stock = self.state.get('stock_drug', 0)
        stock_drug_index = min(1.0, current_stock / target_stock) if target_stock > 0 else 0
        
        # Calculate market-condition-index (0-1 normal dist)
        market_condition_index = random.normalvariate(0, 1)
        market_condition_index = (market_condition_index + 3) / 6
        market_condition_index = max(0, min(1, market_condition_index))
        # Weight by efficiency-vs-security
        efficiency_vs_security = self.state.get('efficiency_vs_security', 0.5)
        market_condition_index *= (1 - efficiency_vs_security)
        
        # Calculate wholesale-price-index (0-1)
        wholesale_price = self.state.get('wholesale_price', 40)
        wholesale_price_now = wholesale_price + random.normalvariate(0, 8.73 * 0.5)
        
        # Track min/max wholesale prices
        if 'minw' not in self.state:
            self.state['minw'] = wholesale_price_now
        if 'maxw' not in self.state:
            self.state['maxw'] = wholesale_price_now
        
        self.state['minw'] = min(self.state['minw'], wholesale_price_now)
        self.state['maxw'] = max(self.state['maxw'], wholesale_price_now)
        self.state['wholesale_price_now'] = wholesale_price_now
        
        # Normalize price index
        min_price = wholesale_price - 10
        max_price = wholesale_price + 10
        price_range = max_price - min_price
        wholesale_price_index = (wholesale_price_now - min_price) / price_range if price_range > 0 else 0.5
        wholesale_price_index = max(0, min(1, wholesale_price_index))
        
        # Composite acquisition index
        acquisition_index = stock_drug_index * market_condition_index * wholesale_price_index
        
        # Track min/max acquisition index
        if 'minacq_ind' not in self.state:
            self.state['minacq_ind'] = acquisition_index
        if 'maxacq_ind' not in self.state:
            self.state['maxacq_ind'] = acquisition_index
        
        self.state['minacq_ind'] = min(self.state['minacq_ind'], acquisition_index)
        self.state['maxacq_ind'] = max(self.state['maxacq_ind'], acquisition_index)
        
        # If warehouses too full, don't acquire
        if current_stock >= target_stock * 2:
            acquisition_index = 999  # Signal: don't acquire
        
        # Each trafficker tries to acquire
        traffickers = self.network.get_active_agents_by_type('trafficker')
        cash_box = self.state.get('cash_box', 0)
        drug_package_of_traffickers = self.state.get('drug_package_of_traffickers', 100)
        n_acquisition = self.state.get('n_acquisition', 0)
        
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
                    self.state['stock_drug_traffickers'] = self.state.get('stock_drug_traffickers', 0) + drug_package_of_traffickers
                    self.state['stock_drug'] = self.state.get('stock_drug', 0) + drug_package_of_traffickers
                    self.state['cash_box'] = cash_box - acquisition_cost
                    self.state['expenses'] = self.state.get('expenses', 0) + acquisition_cost
                else:
                    # Partial acquisition with available cash
                    available_amount = cash_box * 0.5 / wholesale_price_now
                    trafficker.drug += available_amount
                    self.state['stock_drug_traffickers'] = self.state.get('stock_drug_traffickers', 0) + available_amount
                    self.state['stock_drug'] = self.state.get('stock_drug', 0) + available_amount
                    self.state['expenses'] = self.state.get('expenses', 0) + cash_box * 0.5
                    self.state['cash_box'] = cash_box * 0.5
                
                n_acquisition += 1
            else:
                # Failed acquisition
                trafficker.attempt_acquisition(wholesale_price_now, success=False)
        
        self.state['n_acquisition'] = n_acquisition
        if self.state.get('stock_drug_traffickers', 0) < 0:
            self.state['stock_drug_traffickers'] = 0
    
    def package_drug(self, tick: int):
        """
        Daily drug packaging and delivery from traffickers to packagers,
        then from packagers to retailers
        """
        # Update packager availability
        packagers = self.network.get_active_agents_by_type('packager')
        drug_max_packagers = 500
        for packager in packagers:
            packager.update_availability(packager.drug, drug_max_packagers)
            packager.update_attractiveness()
        
        stock_drug_traffickers = self.state.get('stock_drug_traffickers', 0)
        
        # Traffickers to packagers transfer
        if stock_drug_traffickers <= 0:
            self.state['n_exhaust_traffickers'] = self.state.get('n_exhaust_traffickers', 0) + 1
        else:
            self._transfer_trafficker_to_packagers()
        
        # Update retailer availability
        retailers = self.network.get_active_agents_by_type('retailer')
        drug_max_retailers = self.state.get('drug_max_retailers', 200)
        for retailer in retailers:
            retailer.update_availability(retailer.drug, drug_max_retailers)
            retailer.update_attractiveness()
        
        stock_drug_packagers = self.state.get('stock_drug_packagers', 0)
        drug_package_retailers = self.state.get('drug_package_of_retailers', 5.75)
        
        # Packagers to retailers transfer
        if stock_drug_packagers < drug_package_retailers:
            self.state['n_exhaust_packagers'] = self.state.get('n_exhaust_packagers', 0) + 1
        else:
            self._transfer_packagers_to_retailers()
    
    def _transfer_trafficker_to_packagers(self):
        """Transfer drugs from traffickers to packagers based on trust-appeal"""
        traffickers = self.network.get_active_agents_by_type('trafficker')
        packagers = self.network.get_active_agents_by_type('packager')
        
        if not packagers:
            return
        
        drug_package = self.state.get('drug_package_of_packagers', 50)
        
        for trafficker in traffickers:
            if trafficker.drug <= 0:
                continue
            
            # Calculate trust-appeal for each packager
            best_packager = None
            best_trust_appeal = -1
            
            for packager in packagers:
                if packager.availability <= 0:
                    continue
                
                # Trust component (familiarity + visibility)
                familiarity = trafficker.get_connection_familiarity(packager.agent_id)
                visibility = self._calculate_visibility(packager)
                
                # Normalize trust component
                trust_score = (familiarity + visibility) / 2
                trust_score *= (1 - self.state.get('efficiency_vs_security', 0.5))
                
                # Appeal component (attractiveness + closeness centrality)
                appeal_score = (packager.attractiveness + visibility) / 2
                appeal_score *= self.state.get('efficiency_vs_security', 0.5)
                
                # Total trust-appeal
                total_trust_appeal = trust_score + appeal_score
                
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
                self.state['stock_drug_traffickers'] = self.state.get('stock_drug_traffickers', 0) - transfer_amount
                self.state['stock_drug_packagers'] = self.state.get('stock_drug_packagers', 0) + transfer_amount
    
    def _transfer_packagers_to_retailers(self):
        """Transfer drugs from packagers to retailers based on trust-appeal"""
        packagers = self.network.get_active_agents_by_type('packager')
        retailers = self.network.get_active_agents_by_type('retailer')
        
        if not retailers:
            return
        
        drug_package = self.state.get('drug_package_of_retailers', 5.75)
        efficiency_vs_security = self.state.get('efficiency_vs_security', 0.5)
        unit_dose_min = self.state.get('unit_dose_min', 530)
        unit_dose_max = self.state.get('unit_dose_max', 900)
        gram_per_dose = self.state.get('gram_per_dose', 0.25)
        
        target_amount = (unit_dose_min + (unit_dose_max - unit_dose_min) * efficiency_vs_security / 3) * gram_per_dose
        
        for packager in packagers:
            if packager.drug <= 0:
                continue
            
            # Find best retailers to deliver to
            num_packages = 0
            while num_packages * drug_package < target_amount and packager.drug > 0:
                best_retailer = None
                best_trust_appeal = -1
                
                for retailer in retailers:
                    if retailer.availability <= 0:
                        continue
                    
                    # Trust component
                    familiarity = packager.get_connection_familiarity(retailer.agent_id)
                    visibility = self._calculate_visibility(retailer)
                    trust_score = (familiarity + visibility) / 2
                    trust_score *= (1 - efficiency_vs_security)
                    
                    # Appeal component
                    appeal_score = (retailer.attractiveness + visibility) / 2
                    appeal_score *= efficiency_vs_security
                    
                    total_trust_appeal = trust_score + appeal_score
                    
                    if total_trust_appeal > best_trust_appeal:
                        best_trust_appeal = total_trust_appeal
                        best_retailer = retailer
                
                if best_retailer:
                    transfer_amount = min(drug_package, packager.drug)
                    best_retailer.drug += transfer_amount
                    packager.drug -= transfer_amount
                    
                    # Update familiarity
                    packager.add_connection(best_retailer.agent_id, "packager-retailer")
                    best_retailer.add_connection(packager.agent_id, "packager-retailer")
                    
                    # Update stocks
                    self.state['stock_drug_packagers'] = self.state.get('stock_drug_packagers', 0) - transfer_amount
                    self.state['stock_drug_retailers'] = self.state.get('stock_drug_retailers', 0) + transfer_amount
                    
                    num_packages += 1
                else:
                    break
    
    def sell_drug(self, tick: int):
        """
        Daily drug sales by retailers to consumers.
        Each retailer tries to sell doses up to their profit limit.
        """
        retailers = self.network.get_active_agents_by_type('retailer')
        
        # Reset daily profits
        for retailer in retailers:
            retailer.reset_daily_profit()
        
        # Randomize number of doses to sell
        unit_dose_min = self.state.get('unit_dose_min', 530)
        unit_dose_max = self.state.get('unit_dose_max', 900)
        unit_dose_now = unit_dose_min + random.randint(0, int(unit_dose_max - unit_dose_min))
        self.state['unit_dose_now'] = unit_dose_now
        
        # Calculate per-retailer profit target
        price_per_dose = self.state.get('price_per_dose', 32)
        retailers_share = self.state.get('retailers_share_of_profits', 0.18)
        profit_max = self.state.get('profit_of_retailers_max', 500)
        
        if retailers:
            profit_per_retailer = unit_dose_now * price_per_dose * retailers_share / len(retailers)
            profit_per_retailer = min(profit_per_retailer, profit_max)
            self.state['profit_of_retailers'] = profit_per_retailer
        else:
            return
        
        gram_per_dose = self.state.get('gram_per_dose', 0.25)
        wholesale_price_now = self.state.get('wholesale_price_now', 40)
        stock_drug_retailers = self.state.get('stock_drug_retailers', 0)
        cash_box = self.state.get('cash_box', 0)
        
        # Sell doses
        for dose_num in range(unit_dose_now):
            if stock_drug_retailers <= 0:
                break
            
            # Find retailer with most drug available
            available_retailers = [r for r in retailers if r.drug >= gram_per_dose and r.availability > 0]
            
            if not available_retailers:
                self.state['n_exhaust_retailers'] = self.state.get('n_exhaust_retailers', 0) + 1
                if dose_num < unit_dose_now * 0.9:
                    self.state['n_exhaust_retailers_90'] = self.state.get('n_exhaust_retailers_90', 0) + 1
                break
            
            # Sort by drug amount
            best_retailer = max(available_retailers, key=lambda r: r.drug * r.availability)
            
            # Execute sale
            best_retailer.drug -= gram_per_dose
            best_retailer.profit += price_per_dose * retailers_share
            
            if best_retailer.profit >= profit_max:
                best_retailer.availability = 0
            
            # Update stocks
            stock_drug_retailers -= gram_per_dose
            
            # Update cash and revenues
            cash_box += price_per_dose - price_per_dose * retailers_share
            self.state['revenues'] = self.state.get('revenues', 0) + price_per_dose - price_per_dose * retailers_share
            
            # Update weekly profit
            self.state['weekly_profit_now'] = self.state.get('weekly_profit_now', 0) + price_per_dose - price_per_dose * retailers_share - gram_per_dose * wholesale_price_now
        
        self.state['stock_drug_retailers'] = stock_drug_retailers
        self.state['stock_drug'] = (self.state.get('stock_drug_traffickers', 0) + 
                                    self.state.get('stock_drug_packagers', 0) + 
                                    stock_drug_retailers)
        self.state['cash_box'] = cash_box
    
    def _calculate_visibility(self, agent: Agent) -> float:
        """Calculate normalized visibility (closeness centrality proxy)"""
        total_agents = len([a for a in self.network.get_active_agents()])
        if total_agents <= 1:
            return 1.0
        
        agent_degree = agent.get_degree()
        return agent_degree / (total_agents - 1)

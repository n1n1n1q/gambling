"""
Agent classes for MADTOR model
Represents traffickers, packagers, and retailers
"""

import random
from dataclasses import dataclass, field
from typing import Optional, Set
import math

@dataclass
class Link:
    """Represents a connection between two agents with familiarity metric"""
    agent_id_1: int
    agent_id_2: int
    familiarity: float = 1.0
    link_type: str = "neutral"  # "trafficker-packager", "packager-retailer"


class Agent:
    """Base class for criminal organization members"""
    
    _id_counter = 0
    
    def __init__(self, agent_type: str, role_category: str = ""):
        self.agent_id = Agent._id_counter
        Agent._id_counter += 1
        
        self.agent_type = agent_type  # "trafficker", "packager", "retailer"
        self.role_category = role_category
        self.node_id = f"N0{self.agent_id:04d}"
        
        # Physical attributes
        self.drug = 0.0  # grams of drug in possession
        self.attractiveness = self._initialize_attractiveness()
        self.availability = 1 if agent_type != "trafficker" else None
        
        # Network attributes
        self.connections: Set[int] = set()  # Set of agent IDs connected to this agent
        self.link_data: dict = {}  # {agent_id: Link object}
        
        # Financial attributes (for packagers and retailers)
        self.profit = 0.0
        
        # Behavioral attributes
        self.is_arrested = False
        self.arrest_date = None
        
    @staticmethod
    def _initialize_attractiveness() -> float:
        """Initialize criminal expertise following normal distribution, normalized 0-1"""
        attractiveness = random.normalvariate(0, 1)
        attractiveness = (attractiveness + 3) / 6  # Normalize
        attractiveness = max(0.1, min(1.0, attractiveness))  # Clip to [0.1, 1.0]
        return attractiveness
    
    def add_connection(self, other_agent_id: int, link_type: str = "neutral", familiarity: float = 1.0):
        """Add or update a connection to another agent"""
        self.connections.add(other_agent_id)
        
        if other_agent_id not in self.link_data:
            self.link_data[other_agent_id] = Link(
                self.agent_id, other_agent_id, familiarity, link_type
            )
        else:
            self.link_data[other_agent_id].familiarity += 1
    
    def get_connection_familiarity(self, other_agent_id: int) -> float:
        """Get familiarity with another agent, 0 if no connection"""
        if other_agent_id in self.link_data:
            return self.link_data[other_agent_id].familiarity
        return 0.0
    
    def get_degree(self) -> int:
        """Get number of connections (degree centrality raw value)"""
        return len(self.connections)
    
    def __repr__(self):
        return f"{self.__class__.__name__}(id={self.agent_id}, node_id={self.node_id}, drug={self.drug:.2f})"


class Trafficker(Agent):
    """Drug trafficker - acquires drugs at wholesale"""
    
    def __init__(self, role_category: str = "trafficker"):
        super().__init__("trafficker", role_category)
        self.num_acquisitions = 0
    
    def attempt_acquisition(self, wholesale_price: float, success: bool):
        """Update attractiveness based on acquisition attempt"""
        if success:
            if self.attractiveness < 0.2:
                self.attractiveness = 0.2
            else:
                # Exponential increase in skills
                self.attractiveness = min(1.0, self.attractiveness + 0.0001 ** self.attractiveness)
        else:
            if self.attractiveness > 0.8:
                self.attractiveness = 0.8
            else:
                # Exponential decrease in skills
                self.attractiveness = max(0, self.attractiveness - 0.0001 ** (1 - self.attractiveness))


class Packager(Agent):
    """Drug packager - processes drugs from traffickers and delivers to retailers"""
    
    def __init__(self, role_category: str = "packager"):
        super().__init__("packager", role_category)
        self.availability = 1
    
    def update_availability(self, drug_amount: float, drug_max: float):
        """Update availability based on current drug load"""
        if drug_amount >= drug_max:
            self.availability = 0
        else:
            self.availability = 1
    
    def update_attractiveness(self):
        """Update attractiveness with random variation"""
        variation = random.uniform(-self.attractiveness * 0.1, self.attractiveness * 0.1)
        self.attractiveness = max(0.1, min(1.0, self.attractiveness + variation))


class Retailer(Agent):
    """Drug retailer - sells drugs to consumers"""
    
    def __init__(self, role_category: str = "retailer"):
        super().__init__("retailer", role_category)
        self.availability = 1
        self.profit = 0.0
    
    def update_availability(self, drug_amount: float, drug_max: float):
        """Update availability based on current drug load"""
        if drug_amount >= drug_max:
            self.availability = 0
        else:
            self.availability = 1
    
    def update_attractiveness(self):
        """Update attractiveness with random variation"""
        variation = random.uniform(-self.attractiveness * 0.1, self.attractiveness * 0.1)
        self.attractiveness = max(0.1, min(1.0, self.attractiveness + variation))
    
    def reset_daily_profit(self):
        """Reset profit at start of each day"""
        self.profit = 0.0


class Network:
    """Manages network structure and SNA metrics"""
    
    def __init__(self, agents: list):
        self.agents = {agent.agent_id: agent for agent in agents}
        self.links = []
    
    def add_link(self, agent_id_1: int, agent_id_2: int, link_type: str = "neutral"):
        """Create bidirectional link between two agents"""
        if agent_id_1 in self.agents and agent_id_2 in self.agents:
            self.agents[agent_id_1].add_connection(agent_id_2, link_type)
            self.agents[agent_id_2].add_connection(agent_id_1, link_type)
            self.links.append(Link(agent_id_1, agent_id_2, 1.0, link_type))
            return True
        return False
    
    def get_agents_by_type(self, agent_type: str) -> list:
        """Get all agents of a specific type"""
        return [a for a in self.agents.values() if a.agent_type == agent_type]
    
    def count_agents_by_type(self) -> dict:
        """Count agents by type"""
        counts = {"trafficker": 0, "packager": 0, "retailer": 0}
        for agent in self.agents.values():
            if agent.agent_type in counts:
                counts[agent.agent_type] += 1
        return counts
    
    def get_active_agents(self) -> list:
        """Get all non-arrested agents"""
        return [a for a in self.agents.values() if not a.is_arrested]
    
    def get_active_agents_by_type(self, agent_type: str) -> list:
        """Get active agents of a specific type"""
        return [a for a in self.agents.values() 
                if not a.is_arrested and a.agent_type == agent_type]

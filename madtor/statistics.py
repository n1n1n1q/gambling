"""
Network statistics and Social Network Analysis metrics
"""

import math
from typing import List, Dict, Set
from collections import deque
from madtor.agents import Agent, Network


class NetworkStatistics:
    """Calculates SNA metrics for the criminal network"""
    
    def __init__(self, network: Network):
        self.network = network
        self.metrics = {}
    
    def compute_all_statistics(self) -> Dict:
        """Compute all network statistics"""
        stats = {}
        
        active_agents = self.network.get_active_agents()
        if not active_agents:
            return self._empty_stats()
        
        # Component analysis
        stats.update(self._compute_components())
        
        # Centrality measures
        stats.update(self._compute_degree_centrality(active_agents))
        stats.update(self._compute_betweenness_centrality(active_agents))
        
        # Path length
        stats.update(self._compute_geodesic(active_agents))
        
        return stats
    
    def _compute_components(self) -> Dict:
        """
        Compute number of connected components and largest component size
        Using weak component clustering (undirected)
        """
        active_agents = self.network.get_active_agents()
        visited = set()
        components = []
        
        for agent in active_agents:
            if agent.agent_id in visited:
                continue
            
            # BFS to find component
            component = set()
            queue = deque([agent.agent_id])
            
            while queue:
                agent_id = queue.popleft()
                if agent_id in visited:
                    continue
                
                visited.add(agent_id)
                component.add(agent_id)
                
                if agent_id in self.network.agents:
                    for neighbor_id in self.network.agents[agent_id].connections:
                        if neighbor_id not in visited:
                            queue.append(neighbor_id)
            
            if component:
                components.append(component)
        
        max_component = max(len(c) for c in components) if components else 0
        
        return {
            'n_components': len(components),
            'max_component': max_component,
        }
    
    def _compute_degree_centrality(self, active_agents: List[Agent]) -> Dict:
        """Compute normalized degree centrality and centralization"""
        if not active_agents:
            return {
                'min_ndegree': 0, 'avg_ndegree': 0, 'max_ndegree': 0,
                'cen_ndegree': 0
            }
        
        n = len(active_agents)
        degrees = [agent.get_degree() / (n - 1) if n > 1 else 0 for agent in active_agents]
        
        if not degrees:
            return {
                'min_ndegree': 0, 'avg_ndegree': 0, 'max_ndegree': 0,
                'cen_ndegree': 0
            }
        
        min_deg = min(degrees)
        avg_deg = sum(degrees) / len(degrees)
        max_deg = max(degrees)
        
        # Degree centralization
        if max_deg > 0 and n > 2:
            centralization = sum(max_deg - d for d in degrees) / ((n - 1) * (n - 2))
        else:
            centralization = 0
        
        return {
            'min_ndegree': min_deg,
            'avg_ndegree': avg_deg,
            'max_ndegree': max_deg,
            'cen_ndegree': centralization,
        }
    
    def _compute_betweenness_centrality(self, active_agents: List[Agent]) -> Dict:
        """Compute normalized betweenness centrality"""
        if len(active_agents) < 2:
            return {
                'min_nbetweenness': 0, 'avg_nbetweenness': 0, 'max_nbetweenness': 0,
                'cen_nbetweenness': 0
            }
        
        n = len(active_agents)
        betweenness_scores = {}
        active_ids = set()
        
        # Initialize
        for agent in active_agents:
            betweenness_scores[agent.agent_id] = 0.0
            active_ids.add(agent.agent_id)
        
        # Calculate shortest paths between all pairs (Floyd-Warshall inspired)
        for source in active_agents:
            # BFS from source to find shortest paths
            distances = self._bfs_distances(source, active_agents)
            
            # Count paths through each node
            for target in active_agents:
                if source.agent_id == target.agent_id:
                    continue
                
                # Simple betweenness: count geodesic paths (simplified)
                # Full betweenness would require counting ALL shortest paths
                path = self._find_shortest_path(source, target, active_agents)
                if path:
                    for intermediate_id in path[1:-1]:  # Exclude source and target
                        # Only count if intermediate node is in active set
                        if intermediate_id in active_ids:
                            betweenness_scores[intermediate_id] += 1
        
        # Normalize
        if n > 2:
            norm_factor = 2 / ((n - 1) * (n - 2))
        else:
            norm_factor = 1
        
        normalized_betweenness = {k: v * norm_factor for k, v in betweenness_scores.items()}
        
        values = list(normalized_betweenness.values())
        if not values:
            return {
                'min_nbetweenness': 0, 'avg_nbetweenness': 0, 'max_nbetweenness': 0,
                'cen_nbetweenness': 0
            }
        
        min_bet = min(values)
        avg_bet = sum(values) / len(values)
        max_bet = max(values)
        
        # Betweenness centralization
        if max_bet > 0:
            centralization = sum(max_bet - b for b in values) / ((n - 1) * (n - 2)) if n > 1 else 0
        else:
            centralization = 0
        
        return {
            'min_nbetweenness': min_bet,
            'avg_nbetweenness': avg_bet,
            'max_nbetweenness': max_bet,
            'cen_nbetweenness': centralization,
        }
    
    def _compute_geodesic(self, active_agents: List[Agent]) -> Dict:
        """Compute average geodesic distance (average shortest path length)"""
        if len(active_agents) < 2:
            return {'average_path_length': 0}
        
        total_distance = 0
        count = 0
        infinity = 999999
        
        for source in active_agents:
            distances = self._bfs_distances(source, active_agents)
            
            for target in active_agents:
                if source.agent_id != target.agent_id:
                    dist = distances.get(target.agent_id, infinity)
                    if dist == infinity:
                        # Disconnected: add max distance + 1
                        dist = max(distances.values()) + 1 if distances else 2
                    total_distance += dist
                    count += 1
        
        avg_path_length = total_distance / count if count > 0 else 0
        
        return {'average_path_length': avg_path_length}
    
    def _bfs_distances(self, source: Agent, agents: List[Agent]) -> Dict[int, int]:
        """Use BFS to find shortest distances from source to all other agents"""
        distances = {}
        visited = set()
        queue = deque([(source.agent_id, 0)])
        
        while queue:
            agent_id, dist = queue.popleft()
            
            if agent_id in visited:
                continue
            
            visited.add(agent_id)
            distances[agent_id] = dist
            
            if agent_id in self.network.agents:
                for neighbor_id in self.network.agents[agent_id].connections:
                    if neighbor_id not in visited:
                        queue.append((neighbor_id, dist + 1))
        
        return distances
    
    def _find_shortest_path(self, source: Agent, target: Agent, agents: List[Agent]) -> List[int]:
        """Find shortest path between two agents using BFS, only through active agents"""
        if source.agent_id == target.agent_id:
            return [source.agent_id]
        
        # Create set of active agent IDs for fast lookup
        active_ids = {agent.agent_id for agent in agents}
        
        visited = set()
        queue = deque([(source.agent_id, [source.agent_id])])
        
        while queue:
            agent_id, path = queue.popleft()
            
            if agent_id in visited:
                continue
            visited.add(agent_id)
            
            if agent_id == target.agent_id:
                return path
            
            if agent_id in self.network.agents:
                for neighbor_id in self.network.agents[agent_id].connections:
                    # Only traverse through active agents
                    if neighbor_id not in visited and neighbor_id in active_ids:
                        queue.append((neighbor_id, path + [neighbor_id]))
        
        return []  # No path found
    
    def _empty_stats(self) -> Dict:
        """Return empty statistics dictionary"""
        return {
            'n_components': 0,
            'max_component': 0,
            'min_ndegree': 0,
            'avg_ndegree': 0,
            'max_ndegree': 0,
            'cen_ndegree': 0,
            'min_nbetweenness': 0,
            'avg_nbetweenness': 0,
            'max_nbetweenness': 0,
            'cen_nbetweenness': 0,
            'average_path_length': 0,
        }


class DataCollector:
    """Collects data from simulations"""
    
    def __init__(self):
        self.data = {
            'tick': [],
            'n_active_organizations': [],
            'n_traffickers': [],
            'n_packagers': [],
            'n_retailers': [],
            'n_total_members': [],
            'cash_box': [],
            'revenues': [],
            'expenses': [],
            'stock_drug': [],
            'stock_drug_traffickers': [],
            'stock_drug_packagers': [],
            'stock_drug_retailers': [],
            'profit_of_traffickers': [],
            'profit_of_packagers': [],
            'profit_of_retailers': [],
            'n_acquisition': [],
            'unit_dose_now': [],
            'n_exhaust_traffickers': [],
            'n_exhaust_packagers': [],
            'n_exhaust_retailers': [],
            'weekly_profit_now': [],
        }
        # Add SNA metrics
        sna_metrics = [
            'n_components', 'max_component', 'min_ndegree', 'avg_ndegree', 'max_ndegree',
            'cen_ndegree', 'min_nbetweenness', 'avg_nbetweenness', 'max_nbetweenness',
            'cen_nbetweenness', 'average_path_length'
        ]
        for metric in sna_metrics:
            self.data[metric] = []
    
    def record(self, tick: int, global_state: dict, network_stats: dict):
        """Record data at current tick"""
        self.data['tick'].append(tick)
        
        # Count agents
        counts = self._get_agent_counts(global_state)
        self.data['n_active_organizations'].append(1)  # Active if running
        self.data['n_traffickers'].append(counts['trafficker'])
        self.data['n_packagers'].append(counts['packager'])
        self.data['n_retailers'].append(counts['retailer'])
        self.data['n_total_members'].append(sum(counts.values()))
        
        # Financial data
        self.data['cash_box'].append(global_state.get('cash_box', 0))
        self.data['revenues'].append(global_state.get('revenues', 0))
        self.data['expenses'].append(global_state.get('expenses', 0))
        
        # Drug stock
        self.data['stock_drug'].append(global_state.get('stock_drug', 0))
        self.data['stock_drug_traffickers'].append(global_state.get('stock_drug_traffickers', 0))
        self.data['stock_drug_packagers'].append(global_state.get('stock_drug_packagers', 0))
        self.data['stock_drug_retailers'].append(global_state.get('stock_drug_retailers', 0))
        
        # Profits
        self.data['profit_of_traffickers'].append(global_state.get('profit_of_traffickers', 0))
        self.data['profit_of_packagers'].append(global_state.get('profit_of_packagers', 0))
        self.data['profit_of_retailers'].append(global_state.get('profit_of_retailers', 0))
        
        # Activity metrics
        self.data['n_acquisition'].append(global_state.get('n_acquisition', 0))
        self.data['unit_dose_now'].append(global_state.get('unit_dose_now', 0))
        self.data['n_exhaust_traffickers'].append(global_state.get('n_exhaust_traffickers', 0))
        self.data['n_exhaust_packagers'].append(global_state.get('n_exhaust_packagers', 0))
        self.data['n_exhaust_retailers'].append(global_state.get('n_exhaust_retailers', 0))
        self.data['weekly_profit_now'].append(global_state.get('weekly_profit_now', 0))
        
        # Network statistics
        for metric, value in network_stats.items():
            if metric in self.data:
                self.data[metric].append(value)
    
    def _get_agent_counts(self, global_state: dict) -> dict:
        """Extract agent counts from global state"""
        return {
            'trafficker': global_state.get('n_active_traffickers', 0),
            'packager': global_state.get('n_active_packagers', 0),
            'retailer': global_state.get('n_active_retailers', 0),
        }
    
    def get_data(self) -> Dict:
        """Get collected data"""
        return self.data

"""
Utility functions for MADTOR
"""

import json
import csv
import re
from pathlib import Path
from typing import Dict, List, Tuple
import numpy as np
from scipy import stats


def parse_prn_file(filepath: str) -> List[Dict]:
    """
    Parse .prn file (tab/space-separated quoted strings)
    Returns list of dictionaries with column headers as keys
    Handles mixed quoted and unquoted values
    """
    try:
        with open(filepath, 'r', encoding='latin-1') as f:
            lines = f.readlines()
    except Exception:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    
    if not lines:
        return []
    
    # Parse header
    header_line = lines[0].strip()
    # Extract quoted values
    headers = re.findall(r'"([^"]*)"', header_line)
    
    # Parse data rows
    data = []
    for line in lines[1:]:
        if line.strip():
            # Extract quoted values
            quoted_values = re.findall(r'"([^"]*)"', line)
            
            # If we have fewer quoted values than headers, last value might be unquoted
            if len(quoted_values) < len(headers):
                # Extract the unquoted last part
                last_quote_pos = line.rfind('"')
                if last_quote_pos >= 0:
                    after_quotes = line[last_quote_pos + 1:].strip()
                    if after_quotes:
                        quoted_values.append(after_quotes)
            
            if len(quoted_values) == len(headers):
                row_dict = dict(zip(headers, quoted_values))
                data.append(row_dict)
    
    return data


def load_nodes_file(nodes_file: str) -> Dict[str, Dict]:
    """
    Load nodes from T2_Nodes.prn
    Returns dict mapping node_id -> {'role1': ..., 'role2': ...}
    """
    nodes_data = parse_prn_file(nodes_file)
    nodes = {}
    
    for row in nodes_data:
        node_id = row.get('node-id', '').strip()
        role1 = row.get('role-category1', '').strip()
        role2 = row.get('role-category2', '').strip()
        
        if node_id:
            nodes[node_id] = {
                'role_category1': role1,
                'role_category2': role2,
            }
    
    return nodes


def load_links_file(links_file: str) -> List[Dict]:
    """
    Load links from T2_Links.prn
    Returns list of dicts with link information
    """
    links_data = parse_prn_file(links_file)
    links = []
    
    for row in links_data:
        node_id1 = row.get('node-id1', '').strip()
        node_id2 = row.get('node-id2', '').strip()
        role1 = row.get('role-category2-id1', '').strip()
        role2 = row.get('role-category2-id2', '').strip()
        
        # Try to parse familiarity (handle special chars)
        familiarity_str = row.get('Familiarit\u00e9', '').strip()
        if not familiarity_str:
            familiarity_str = row.get('Familiarit', '').strip()
        
        try:
            familiarity = int(familiarity_str) if familiarity_str else 1
        except ValueError:
            familiarity = 1
        
        if node_id1 and node_id2:
            links.append({
                'source': node_id1,
                'target': node_id2,
                'role1': role1,
                'role2': role2,
                'familiarity': familiarity,
            })
    
    return links


def infer_agent_type(node_id: str, roles: Dict) -> str:
    """
    Infer agent type from node roles
    Returns 'trafficker', 'packager', or 'retailer'
    """
    if node_id not in roles:
        return 'retailer'  # Default
    
    role_data = roles[node_id]
    role2 = role_data.get('role_category2', '').lower()
    
    if 'trafficker' in role2:
        return 'trafficker'
    elif 'packager' in role2 or 'refining' in role2:
        return 'packager'
    else:
        return 'retailer'


def export_to_csv(data: Dict, filename: str = "madtor_data.csv"):
    """Export simulation data to CSV"""
    output_path = Path("output") / filename
    output_path.parent.mkdir(exist_ok=True)
    
    # Get column names from first data series
    if not data or not data.get('tick'):
        return
    
    columns = list(data.keys())
    num_rows = len(data['tick'])
    
    with open(output_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(columns)
        
        for i in range(num_rows):
            row = [data[col][i] if i < len(data[col]) else '' for col in columns]
            writer.writerow(row)
    
    print(f"Data exported to {output_path}")


def calculate_statistics(values: List[float]) -> Dict:
    """Calculate basic statistics"""
    if not values:
        return {
            'mean': 0, 'median': 0, 'std': 0, 'min': 0, 'max': 0,
            'q25': 0, 'q75': 0, 'count': 0
        }
    
    return {
        'mean': np.mean(values),
        'median': np.median(values),
        'std': np.std(values),
        'min': np.min(values),
        'max': np.max(values),
        'q25': np.percentile(values, 25),
        'q75': np.percentile(values, 75),
        'count': len(values),
    }


def perform_ttest(group1: List[float], group2: List[float], 
                  num_permutations: int = 100) -> Dict:
    """
    Perform randomization-based t-test
    (as done in paper with 100 repetitions)
    """
    if len(group1) < 2 or len(group2) < 2:
        return {
            'statistic': 0,
            'p_value': 1.0,
            'significant': False,
        }
    
    # Calculate observed difference
    observed_diff = np.mean(group1) - np.mean(group2)
    
    # Combine groups
    combined = np.concatenate([group1, group2])
    
    # Permutation test
    count = 0
    for _ in range(num_permutations):
        np.random.shuffle(combined)
        perm_group1 = combined[:len(group1)]
        perm_group2 = combined[len(group1):]
        perm_diff = np.mean(perm_group1) - np.mean(perm_group2)
        
        if abs(perm_diff) >= abs(observed_diff):
            count += 1
    
    p_value = count / num_permutations
    
    return {
        'statistic': observed_diff,
        'p_value': p_value,
        'significant': p_value < 0.05,
        'permutations': num_permutations,
    }


def plot_results(results: Dict, filename: str = "results_plot.png"):
    """
    Plot simulation results
    Requires matplotlib
    """
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib not installed. Skipping plot generation.")
        return
    
    # Extract scenarios and survival rates
    scenarios = []
    survival_rates = []
    
    for scenario in sorted(results.keys()):
        if isinstance(scenario, (int, float)):
            scenarios.append(scenario)
            survival_rates.append(results[scenario]['survival_rate'] * 100)
    
    # Create plot
    fig, ax = plt.subplots(figsize=(10, 6))
    
    ax.plot(scenarios, survival_rates, marker='o', linewidth=2, markersize=8)
    ax.set_xlabel('Arrest Scenario (%)', fontsize=12)
    ax.set_ylabel('Active Organizations (%)', fontsize=12)
    ax.set_title('MADTOR: Organization Survival by Arrest Scenario', fontsize=14)
    ax.grid(True, alpha=0.3)
    ax.set_ylim([0, 105])
    
    output_path = Path("output") / filename
    output_path.parent.mkdir(exist_ok=True)
    
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"Plot saved to {output_path}")
    plt.close()


def calculate_resilience_metrics(data: Dict) -> Dict:
    """
    Calculate resilience metrics from simulation data
    
    Returns metrics for:
    - Endure disruption (share of active organizations)
    - React quickly (number of members recovery)
    - Maintain function (revenue recovery)
    """
    
    metrics = {
        'organization_survival': [],
        'member_recovery': [],
        'revenue_recovery': [],
    }
    
    # Calculate organization survival
    if 'tick' in data and len(data['tick']) > 0:
        disruption_tick = 2 * 365  # Year 2
        
        # Count organizations still active at different timepoints
        for i, tick in enumerate(data['tick']):
            if tick > disruption_tick:
                active = 1 if data.get('n_total_members', [0])[i] > 0 else 0
                metrics['organization_survival'].append(active)
    
    return metrics


class SimulationReport:
    """Generate reports from simulation data"""
    
    def __init__(self, results: Dict):
        self.results = results
    
    def generate_html_report(self, filename: str = "madtor_report.html"):
        """Generate HTML report of results"""
        output_path = Path("output") / filename
        output_path.parent.mkdir(exist_ok=True)
        
        html_content = """
<!DOCTYPE html>
<html>
<head>
    <title>MADTOR Simulation Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        h1 { color: #333; }
        table { border-collapse: collapse; width: 100%; margin: 20px 0; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #4CAF50; color: white; }
        tr:nth-child(even) { background-color: #f2f2f2; }
    </style>
</head>
<body>
    <h1>MADTOR - Drug Trafficking Organization Resilience Model</h1>
    <h2>Simulation Results Summary</h2>
    <table>
        <tr>
            <th>Arrest Scenario (%)</th>
            <th>Simulations</th>
            <th>Active at End</th>
            <th>Survival Rate (%)</th>
            <th>Avg Final Cash (€)</th>
        </tr>
"""
        
        for scenario in sorted(self.results.keys()):
            data = self.results[scenario]
            html_content += f"""
        <tr>
            <td>{data['arrest_scenario']}</td>
            <td>{data['num_simulations']}</td>
            <td>{data['num_active_at_end']}</td>
            <td>{data['survival_rate']*100:.1f}</td>
            <td>€{data['avg_final_cash_box']:,.0f}</td>
        </tr>
"""
        
        html_content += """
    </table>
</body>
</html>
"""
        
        with open(output_path, 'w') as f:
            f.write(html_content)
        
        print(f"Report generated: {output_path}")


if __name__ == "__main__":
    print("MADTOR utilities module")

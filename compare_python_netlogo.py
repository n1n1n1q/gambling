#!/usr/bin/env python3
"""
Compare Python simulation against NetLogo expectations
Tests network structure, initialization, and basic dynamics
"""

import json
from pathlib import Path
from madtor import MADTORSimulation
from madtor.utils import load_nodes_file, load_links_file

print("=" * 80)
print("MADTOR: PYTHON vs NETLOGO COMPARISON")
print("=" * 80)

# Initialize
sim = MADTORSimulation(seed=42, arrest_scenario=0)

# Load raw data for comparison
nodes_data = load_nodes_file("madtor/data/T2_Nodes.prn")
links_data = load_links_file("madtor/data/T2_Links.prn")

print("\n[1] NETWORK STRUCTURE COMPARISON")
print("-" * 80)

# Check agent counts
traffickers = sim.network.get_active_agents_by_type('trafficker')
packagers = sim.network.get_active_agents_by_type('packager')
retailers = sim.network.get_active_agents_by_type('retailer')

print(f"\nAgent Composition:")
print(f"  Expected nodes in data:      {len(nodes_data)}")
print(f"  Actual Python agents:        {len(sim.network.agents)}")
print(f"  Status: {'✓ MATCH' if len(sim.network.agents) == len(nodes_data) else '✗ MISMATCH'}")

print(f"\nAgent Type Distribution:")
print(f"  Traffickers: {len(traffickers)} (Python) vs 5 (data)")
print(f"  Packagers:   {len(packagers)} (Python) vs 5 (data)")
print(f"  Retailers:   {len(retailers)} (Python) vs {len(nodes_data) - 10} (data)")

type_counts = {'trafficker': len(traffickers), 'packager': len(packagers), 'retailer': len(retailers)}
expected = {'trafficker': 5, 'packager': 5, 'retailer': len(nodes_data) - 10}

for atype in ['trafficker', 'packager', 'retailer']:
    status = "✓" if type_counts[atype] == expected[atype] else "✗"
    print(f"  {status} {atype.capitalize()}: {type_counts[atype]} == {expected[atype]}")

# Check network links
print(f"\nNetwork Connectivity:")
print(f"  Expected links in data:      {len(links_data)}")
print(f"  Actual Python links:         {len(sim.network.links)}")
print(f"  Status: {'✓ MATCH' if len(sim.network.links) == len(links_data) else '✗ MISMATCH'}")

# Analyze link types
print(f"\nLink Type Distribution:")
link_types = {}
for link in sim.network.links:
    link_types[link.link_type] = link_types.get(link.link_type, 0) + 1

for role_pair in ['retailer-retailer', 'packager-retailer', 'trafficker-packager', 'trafficker-retailer']:
    count = link_types.get(role_pair, 0)
    if count > 0:
        print(f"  {role_pair}: {count}")

print("\n[2] NODE IDENTITY PRESERVATION")
print("-" * 80)

# Check that node IDs are preserved
print(f"\nSample Node IDs:")
sample_size = min(10, len(sim.network.agents))
sample_agents = list(sim.network.agents.values())[:sample_size]

for agent in sample_agents:
    print(f"  {agent.node_id}: {agent.agent_type:10s} (role: {agent.role_category})")

# Verify all node IDs from data are in Python simulation
missing_nodes = []
for node_id in nodes_data.keys():
    found = any(a.node_id == node_id for a in sim.network.agents.values())
    if not found:
        missing_nodes.append(node_id)

if missing_nodes:
    print(f"\n✗ Missing nodes: {missing_nodes}")
else:
    print(f"\n✓ All {len(nodes_data)} node IDs preserved correctly")

print("\n[3] FINANCIAL PARAMETERS")
print("-" * 80)

print(f"\nInitial Financial State:")
print(f"  Cash box:           €{sim.global_state['cash_box']:>12,.0f}")
print(f"  Wholesale price:    €{sim.global_state['wholesale_price']:>12,.0f}/g")
print(f"  Retail price:       €{sim.global_state['retail_price']:>12,.0f}/dose")
print(f"  Price per dose:     €{sim.global_state['price_per_dose']:>12,.0f}")
print(f"  Target stock:       {sim.global_state['target_stock_drug']:>12,.0f}g")

print(f"\nActive Agent Counts:")
print(f"  Active traffickers: {sim.global_state['n_active_traffickers']:>12}")
print(f"  Active packagers:   {sim.global_state['n_active_packagers']:>12}")
print(f"  Active retailers:   {sim.global_state['n_active_retailers']:>12}")

print("\n[4] SIMULATION DYNAMICS")
print("-" * 80)

print(f"\nRunning 5 simulation ticks...")
cash_history = [sim.global_state['cash_box']]
revenue_history = []

for tick in range(1, 6):
    sim.step()
    cash_history.append(sim.global_state['cash_box'])
    revenue_history.append(sim.global_state['revenues'])
    print(f"  Tick {tick}: Cash €{sim.global_state['cash_box']:>12,.0f} | Revenue €{sim.global_state['revenues']:>10,.0f}")

print(f"\nCash Flow Analysis:")
print(f"  Initial cash:       €{cash_history[0]:>12,.0f}")
print(f"  Final cash (tick 5): €{cash_history[5]:>12,.0f}")
print(f"  Net change:         €{cash_history[5] - cash_history[0]:>12,.0f}")
print(f"  Total revenues:     €{sum(revenue_history):>12,.0f}")

print("\n[5] DATA CONSISTENCY CHECKS")
print("-" * 80)

# Check that traffickers are only connected to specific types
print(f"\nNetwork Role Constraints:")
trafficker_connections = set()
for agent in traffickers:
    for target_id in agent.connections:
        target_agent = sim.network.agents[target_id]
        trafficker_connections.add(f"{agent.agent_type}-{target_agent.agent_type}")

packager_connections = set()
for agent in packagers:
    for target_id in agent.connections:
        target_agent = sim.network.agents[target_id]
        packager_connections.add(f"{agent.agent_type}-{target_agent.agent_type}")

retailer_connections = set()
for agent in retailers:
    for target_id in agent.connections:
        target_agent = sim.network.agents[target_id]
        retailer_connections.add(f"{agent.agent_type}-{target_agent.agent_type}")

print(f"  Trafficker connects to: {trafficker_connections}")
print(f"  Packager connects to:   {packager_connections}")
print(f"  Retailer connects to:   {retailer_connections}")

print("\n[6] COMPARISON VERDICT")
print("-" * 80)

checks = {
    'Agent count': len(sim.network.agents) == len(nodes_data),
    'Link count': len(sim.network.links) == len(links_data),
    'Trafficker count': len(traffickers) == 5,
    'Packager count': len(packagers) == 5,
    'Retailer count': len(retailers) == len(nodes_data) - 10,
    'All node IDs preserved': len(missing_nodes) == 0,
    'Simulation executable': sim.tick == 5,
}

all_pass = all(checks.values())

for check_name, result in checks.items():
    status = "✓" if result else "✗"
    print(f"  {status} {check_name}")

print("\n" + "=" * 80)
if all_pass:
    print("✓ SUCCESS: Python simulation matches NetLogo data structure and runs correctly")
    print("  Ready for experimental scenarios and comparison with NetLogo output")
else:
    print("✗ ISSUES FOUND: See above for details")
print("=" * 80)

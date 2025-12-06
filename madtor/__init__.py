"""
MADTOR: Model for Assessing Drug Trafficking Organizations Resilience

A Python implementation of the agent-based model from:
Manzi, D., & Calderoni, F. (2024). "An Agent-Based Model for Assessing 
the Resilience of Drug Trafficking Organizations to Law Enforcement Interventions"
Journal of Artificial Societies and Social Simulation, 27(3), 3.

https://doi.org/10.18564/jasss.5430
"""

__version__ = "1.0.0"
__author__ = "Python Implementation"
__all__ = [
    'MADTORSimulation',
    'ExperimentRunner',
    'NetworkStatistics',
    'LawEnforcement',
]

from .simulation import MADTORSimulation
from .experiment import ExperimentRunner
from .statistics import NetworkStatistics
from .law_enforcement import LawEnforcement

"""
simulation — EV Charging Station Simulation Package
====================================================

Re-exports the key classes and functions from the three submodules:

- **nhpp**: Non-Homogeneous Poisson Process arrival generation
- **analytical**: M/M/c/K steady-state analytical formulas
- **des_engine**: SimPy-based Discrete Event Simulation engine
"""

# --- NHPP module ---
from .nhpp import get_arrival_rate, generate_nhpp_arrivals

# --- Analytical module ---
from .analytical import compute_steady_state_probs, compute_metrics

# --- DES engine module ---
from .des_engine import EVChargingSimulation, SimulationResult

__all__ = [
    # nhpp
    "get_arrival_rate",
    "generate_nhpp_arrivals",
    # analytical
    "compute_steady_state_probs",
    "compute_metrics",
    # des_engine
    "EVChargingSimulation",
    "SimulationResult",
]

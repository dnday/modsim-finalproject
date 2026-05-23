"""
Analytical M/M/c/K queuing model with state-dependent balking.

Computes steady-state probabilities via balance equations and derives
standard performance metrics (utilization, queue length, wait time, etc.).
"""

import numpy as np
from math import factorial


def compute_steady_state_probs(
    c: int,
    K: int,
    lam: float,
    mu: float,
) -> np.ndarray:
    """
    Compute steady-state probabilities P(n) for n = 0, 1, ..., K.

    Uses the birth-death process formulation with state-dependent
    balking:

        Birth rate:  λ_n = λ * (1 - n/K)   for n < K
                     λ_n = 0                for n >= K

        Death rate:  μ_n = min(n, c) * μ

    The probabilities are computed via the recursive relation:

        P(n) = (∏_{i=0}^{n-1} λ_i) / (∏_{i=1}^{n} μ_i)  *  P(0)

    and then normalised so that ∑ P(n) = 1.

    Parameters
    ----------
    c : int
        Number of chargers (servers).
    K : int
        System capacity (chargers + waiting spaces).
    lam : float
        Base (un-thinned) arrival rate λ in vehicles/hour.
    mu : float
        Per-server service rate μ in vehicles/hour.

    Returns
    -------
    np.ndarray
        Array of length K + 1 with P(n) for n = 0 .. K.
    """
    if lam <= 0 or mu <= 0:
        # Degenerate case: no arrivals or no service
        probs = np.zeros(K + 1)
        probs[0] = 1.0
        return probs

    # Compute ratios P(n)/P(0) = ∏ (λ_i / μ_{i+1}) for i = 0..n-1
    ratios = np.zeros(K + 1)
    ratios[0] = 1.0  # P(0)/P(0)

    for n in range(1, K + 1):
        # λ_{n-1} = λ * (1 - (n-1)/K)
        lambda_n_minus_1 = lam * (1.0 - (n - 1) / K)
        # μ_n = min(n, c) * μ
        mu_n = min(n, c) * mu

        ratios[n] = ratios[n - 1] * (lambda_n_minus_1 / mu_n)

    # Normalise
    total = ratios.sum()
    probs = ratios / total

    return probs


def compute_metrics(
    c: int,
    K: int,
    lam: float,
    mu: float,
) -> dict:
    """
    Derive M/M/c/K performance metrics from the steady-state distribution.

    Parameters
    ----------
    c : int
        Number of chargers (servers).
    K : int
        System capacity.
    lam : float
        Base arrival rate λ (vehicles/hour).
    mu : float
        Per-server service rate μ (vehicles/hour).

    Returns
    -------
    dict
        Keys:
            rho         – server utilization (fraction of busy servers)
            Lq          – average number of customers in the queue
            Wq          – average waiting time in the queue (minutes)
            L           – average number of customers in the system
            W           – average time in the system (minutes)
            P0          – probability that the system is empty
            Pb          – blocking probability P(K)
            throughput  – effective throughput (vehicles/hour)
            lambda_eff  – effective arrival rate (vehicles/hour)
    """
    probs = compute_steady_state_probs(c, K, lam, mu)

    # ---- Effective arrival rate ----
    # λ_eff = Σ_{n=0}^{K-1} λ_n * P(n)   where λ_n = λ * (1 - n/K)
    lambda_eff = 0.0
    for n in range(K):
        lambda_n = lam * (1.0 - n / K)
        lambda_eff += lambda_n * probs[n]

    # ---- Handle degenerate case ----
    if lambda_eff < 1e-12:
        return {
            "rho": 0.0,
            "Lq": 0.0,
            "Wq": 0.0,
            "L": 0.0,
            "W": 0.0,
            "P0": float(probs[0]),
            "Pb": float(probs[K]),
            "throughput": 0.0,
            "lambda_eff": 0.0,
        }

    # ---- Average system size L = Σ n * P(n) ----
    n_values = np.arange(K + 1)
    L = float(np.dot(n_values, probs))

    # ---- Average queue length Lq = Σ_{n=c+1}^{K} (n - c) * P(n) ----
    Lq = 0.0
    for n in range(c + 1, K + 1):
        Lq += (n - c) * probs[n]
    Lq = float(Lq)

    # ---- Little's law ----
    # W = L / λ_eff  (hours),  convert to minutes
    W = (L / lambda_eff) * 60.0   # minutes
    # Wq = Lq / λ_eff (hours), convert to minutes
    Wq = (Lq / lambda_eff) * 60.0  # minutes

    # ---- Utilization ----
    # Average number of busy servers = Σ min(n, c) * P(n)
    busy_servers = sum(min(n, c) * probs[n] for n in range(K + 1))
    rho = float(busy_servers / c) if c > 0 else 0.0

    # ---- Throughput = λ_eff (same as effective arrival rate in steady state) ----
    throughput = lambda_eff

    return {
        "rho": rho,
        "Lq": Lq,
        "Wq": Wq,
        "L": L,
        "W": W,
        "P0": float(probs[0]),
        "Pb": float(probs[K]),
        "throughput": throughput,
        "lambda_eff": lambda_eff,
    }

"""
Non-Homogeneous Poisson Process (NHPP) arrival generator.

Implements a time-varying arrival rate with peak/off-peak periods
and uses the Lewis-Shedler thinning algorithm to generate arrivals.
"""

import numpy as np
from numpy.random import Generator


def get_arrival_rate(
    t_minutes: float,
    start_hour: float,
    lambda_peak: float,
    lambda_off: float,
) -> float:
    """
    Compute the instantaneous arrival rate λ(t) in vehicles/hour.

    Converts elapsed simulation time to clock time and returns the
    appropriate rate depending on whether the current time falls
    within a peak or off-peak window.

    Peak windows:
        - Morning:  07:00 – 09:00
        - Evening:  17:00 – 19:00

    Parameters
    ----------
    t_minutes : float
        Elapsed simulation time in minutes.
    start_hour : float
        Clock hour at which the simulation starts (e.g. 6.0 for 06:00).
    lambda_peak : float
        Arrival rate during peak hours (vehicles/hour).
    lambda_off : float
        Arrival rate during off-peak hours (vehicles/hour).

    Returns
    -------
    float
        λ(t) in vehicles/hour.
    """
    # Convert elapsed minutes to a clock hour in [0, 24)
    clock_hour = (start_hour + t_minutes / 60.0) % 24.0

    # Check if clock_hour falls within a peak window
    is_peak = (7.0 <= clock_hour < 9.0) or (17.0 <= clock_hour < 19.0)

    return lambda_peak if is_peak else lambda_off


def generate_nhpp_arrivals(
    duration_hours: float,
    start_hour: float,
    lambda_peak: float,
    lambda_off: float,
    rng: Generator,
) -> list[float]:
    """
    Generate arrival times from a Non-Homogeneous Poisson Process
    using the Lewis-Shedler thinning algorithm.

    Algorithm overview:
        1. Generate candidate arrivals from a homogeneous Poisson
           process with rate λ_max = max(λ_peak, λ_off).
        2. Accept each candidate independently with probability
           λ(t) / λ_max (thinning step).

    Parameters
    ----------
    duration_hours : float
        Length of the simulation window in hours.
    start_hour : float
        Clock hour at which the simulation starts (e.g. 6.0 for 06:00).
    lambda_peak : float
        Arrival rate during peak hours (vehicles/hour).
    lambda_off : float
        Arrival rate during off-peak hours (vehicles/hour).
    rng : numpy.random.Generator
        A NumPy random number generator instance for reproducibility.

    Returns
    -------
    list[float]
        Sorted list of accepted arrival times in **minutes** from
        simulation start.
    """
    duration_minutes = duration_hours * 60.0

    # Upper-bound rate for the thinning envelope (vehicles/minute)
    lambda_max = max(lambda_peak, lambda_off) / 60.0  # convert to per-minute

    arrivals: list[float] = []
    t = 0.0  # current time in minutes

    while True:
        # Draw inter-arrival time from exponential(1 / λ_max)
        if lambda_max <= 0:
            break
        u1 = rng.exponential(1.0 / lambda_max)
        t += u1

        # Stop if we exceed the simulation window
        if t >= duration_minutes:
            break

        # Thinning: accept with probability λ(t) / λ_max_per_min
        current_rate = get_arrival_rate(t, start_hour, lambda_peak, lambda_off)
        current_rate_per_min = current_rate / 60.0  # convert to per-minute
        acceptance_prob = current_rate_per_min / lambda_max

        u2 = rng.uniform()
        if u2 <= acceptance_prob:
            arrivals.append(t)

    return arrivals

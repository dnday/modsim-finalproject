"""
Discrete Event Simulation engine for an M/M/c/K EV charging station.

Built on top of SimPy, this module models vehicle arrivals (via NHPP),
state-dependent balking, exponential-patience reneging, and exponential
service times.  It collects a detailed event log and per-minute snapshots
that can be used for visualisation and comparison with analytical results.
"""

from __future__ import annotations

import simpy
import numpy as np
import pandas as pd
from dataclasses import dataclass, field

from .nhpp import generate_nhpp_arrivals


# ---------------------------------------------------------------------------
# Result container
# ---------------------------------------------------------------------------

@dataclass
class SimulationResult:
    """
    Container for the output of a single simulation run.

    Attributes
    ----------
    event_log : pd.DataFrame
        Per-event log with columns:
        time, vehicle_id, event_type, queue_length, busy_servers.
    snapshots : pd.DataFrame
        Per-minute system snapshots with columns:
        time, queue_length, busy_servers, total_served,
        total_balked, total_reneged, utilization.
    metrics : dict
        Aggregate performance metrics computed from the completed
        simulation (same key set as the analytical model).
    """

    event_log: pd.DataFrame
    snapshots: pd.DataFrame
    metrics: dict


# ---------------------------------------------------------------------------
# Main simulation class
# ---------------------------------------------------------------------------

class EVChargingSimulation:
    """
    SimPy-based DES of an M/M/c/K EV charging station with NHPP
    arrivals, state-dependent balking, and exponential reneging.

    Parameters
    ----------
    c : int
        Number of chargers (servers / resource capacity).
    K : int
        Total system capacity (chargers + waiting spaces).
    lambda_peak : float
        Arrival rate during peak hours (vehicles/hour).
    lambda_off : float
        Arrival rate during off-peak hours (vehicles/hour).
    service_rate_per_min : float
        Service rate μ per charger (services/minute).
        Expected service time = 1 / service_rate_per_min minutes.
    reneging_rate : float, default 0.05
        Reneging rate γ (1/minute).  A waiting vehicle's patience
        is Exp(1/γ) minutes.
    duration_hours : float, default 8.0
        Simulation horizon in hours.
    start_hour : float, default 6.0
        Clock hour at which the simulation starts.
    seed : int, default 42
        Random seed for reproducibility.
    """

    def __init__(
        self,
        c: int,
        K: int,
        lambda_peak: float,
        lambda_off: float,
        service_rate_per_min: float,
        reneging_rate: float = 0.05,
        duration_hours: float = 8.0,
        start_hour: float = 6.0,
        seed: int = 42,
    ) -> None:
        self.c = c
        self.K = K
        self.lambda_peak = lambda_peak
        self.lambda_off = lambda_off
        self.service_rate_per_min = service_rate_per_min
        self.reneging_rate = reneging_rate
        self.duration_hours = duration_hours
        self.start_hour = start_hour
        self.seed = seed

        # Random generator (seeded)
        self.rng = np.random.default_rng(seed)

        # --- Counters & trackers ---
        self._system_size: int = 0          # current number in system (queue + service)
        self._total_served: int = 0
        self._total_balked: int = 0
        self._total_reneged: int = 0
        self._total_arrivals: int = 0

        # Accumulators for time-weighted metrics
        self._wait_times: list[float] = []   # individual wait times (minutes)
        self._system_times: list[float] = [] # individual system times (minutes)

        # Raw log records (will be converted to DataFrames)
        self._event_records: list[dict] = []
        self._snapshot_records: list[dict] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self) -> SimulationResult:
        """
        Execute the simulation and return a ``SimulationResult``.

        Returns
        -------
        SimulationResult
            Contains the event log, per-minute snapshots, and
            aggregate metrics dictionary.
        """
        env = simpy.Environment()

        # Shared resource: chargers with capacity c
        station = simpy.Resource(env, capacity=self.c)

        # Launch processes
        env.process(self._arrival_generator(env, station))
        env.process(self._snapshot_collector(env, station))

        # Run until the simulation horizon
        env.run(until=self.duration_hours * 60.0)

        # Build DataFrames
        event_log = pd.DataFrame(self._event_records)
        if event_log.empty:
            event_log = pd.DataFrame(
                columns=["time", "vehicle_id", "event_type",
                          "queue_length", "busy_servers"]
            )

        snapshots = pd.DataFrame(self._snapshot_records)
        if snapshots.empty:
            snapshots = pd.DataFrame(
                columns=["time", "queue_length", "busy_servers",
                          "total_served", "total_balked",
                          "total_reneged", "utilization"]
            )

        # Compute aggregate metrics
        metrics = self._compute_metrics()

        return SimulationResult(
            event_log=event_log,
            snapshots=snapshots,
            metrics=metrics,
        )

    # ------------------------------------------------------------------
    # Internal SimPy processes
    # ------------------------------------------------------------------

    def _arrival_generator(
        self,
        env: simpy.Environment,
        station: simpy.Resource,
    ):
        """
        Generate vehicle arrivals according to the NHPP schedule and
        spawn a ``_vehicle_process`` for each one.
        """
        # Pre-generate all arrival times using NHPP
        arrival_times = generate_nhpp_arrivals(
            duration_hours=self.duration_hours,
            start_hour=self.start_hour,
            lambda_peak=self.lambda_peak,
            lambda_off=self.lambda_off,
            rng=self.rng,
        )

        vehicle_id = 0
        for arrival_time in arrival_times:
            # Wait until the scheduled arrival time
            delay = arrival_time - env.now
            if delay > 0:
                yield env.timeout(delay)

            vehicle_id += 1
            self._total_arrivals += 1

            # Spawn a separate process for this vehicle
            env.process(self._vehicle_process(env, vehicle_id, station))

    def _vehicle_process(
        self,
        env: simpy.Environment,
        vehicle_id: int,
        station: simpy.Resource,
    ):
        """
        Lifecycle of a single vehicle at the charging station.

        Steps:
            1. **Balking check** – the vehicle may balk (leave immediately)
               with probability n/K, where n is the current system size.
            2. **Enter system** – increment system size, join the queue.
            3. **Reneging** – while waiting for a charger the vehicle may
               lose patience (exponential with rate γ) and leave.
            4. **Service** – if a charger is obtained, the vehicle charges
               for an exponential service time and then departs.
        """
        arrival_time = env.now
        current_queue = len(station.queue)
        busy_servers = station.count

        # --- Log arrival ---
        self._log_event(env.now, vehicle_id, "arrival",
                        current_queue, busy_servers)

        # --- Balking ---
        n = self._system_size
        balk_prob = n / self.K if self.K > 0 else 1.0
        if self.rng.uniform() < balk_prob:
            self._total_balked += 1
            self._log_event(env.now, vehicle_id, "balk",
                            current_queue, busy_servers)
            return

        # --- Enter the system ---
        self._system_size += 1

        # Request a charger
        req = station.request()

        if self.reneging_rate > 0:
            # Patience drawn from Exp(1/γ) minutes
            patience = self.rng.exponential(1.0 / self.reneging_rate)
            patience_timeout = env.timeout(patience)

            # Race: charger grant vs. patience expiry
            result = yield req | patience_timeout

            if req not in result:
                # --- Reneging: patience expired before getting a charger ---
                self._total_reneged += 1
                self._system_size -= 1

                # Cancel the pending resource request
                if req in station.queue:
                    station.release(req)
                # If somehow already granted, also release
                elif req.triggered:
                    station.release(req)

                self._log_event(
                    env.now, vehicle_id, "renege",
                    len(station.queue), station.count,
                )
                return
        else:
            # No reneging – just wait indefinitely
            yield req

        # --- Start service ---
        wait_time = env.now - arrival_time
        self._wait_times.append(wait_time)

        self._log_event(
            env.now, vehicle_id, "start_service",
            len(station.queue), station.count,
        )

        # Service duration ~ Exp(1 / service_rate_per_min)
        if self.service_rate_per_min > 0:
            service_duration = self.rng.exponential(
                1.0 / self.service_rate_per_min
            )
        else:
            service_duration = 0.0

        yield env.timeout(service_duration)

        # --- End service ---
        station.release(req)
        self._system_size -= 1
        self._total_served += 1

        system_time = env.now - arrival_time
        self._system_times.append(system_time)

        self._log_event(
            env.now, vehicle_id, "end_service",
            len(station.queue), station.count,
        )

    def _snapshot_collector(
        self,
        env: simpy.Environment,
        station: simpy.Resource,
    ):
        """
        Record a system snapshot every simulated minute.
        """
        while True:
            queue_length = len(station.queue)
            busy_servers = station.count
            utilization = busy_servers / self.c if self.c > 0 else 0.0

            self._snapshot_records.append({
                "time": env.now,
                "queue_length": queue_length,
                "busy_servers": busy_servers,
                "total_served": self._total_served,
                "total_balked": self._total_balked,
                "total_reneged": self._total_reneged,
                "utilization": utilization,
            })

            yield env.timeout(1.0)  # 1 simulated minute

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _log_event(
        self,
        time: float,
        vehicle_id: int,
        event_type: str,
        queue_length: int,
        busy_servers: int,
    ) -> None:
        """Append a record to the internal event log."""
        self._event_records.append({
            "time": round(time, 4),
            "vehicle_id": vehicle_id,
            "event_type": event_type,
            "queue_length": queue_length,
            "busy_servers": busy_servers,
        })

    def _compute_metrics(self) -> dict:
        """
        Compute aggregate performance metrics from the completed
        simulation run.

        Returns
        -------
        dict
            Keys: rho, Lq, Wq, L, W, P0, Pb, throughput.
        """
        duration_minutes = self.duration_hours * 60.0

        # --- Utilization (rho) ---
        if self._snapshot_records:
            snap_df = pd.DataFrame(self._snapshot_records)
            rho = float(snap_df["utilization"].mean())
            avg_queue = float(snap_df["queue_length"].mean())
            avg_busy = float(snap_df["busy_servers"].mean())
        else:
            rho = 0.0
            avg_queue = 0.0
            avg_busy = 0.0

        # --- Average queue length (Lq) ---
        Lq = avg_queue

        # --- Average system size (L) ---
        L = avg_queue + avg_busy

        # --- Average wait time in queue (Wq, minutes) ---
        if self._wait_times:
            Wq = float(np.mean(self._wait_times))
        else:
            Wq = 0.0

        # --- Average time in system (W, minutes) ---
        if self._system_times:
            W = float(np.mean(self._system_times))
        else:
            W = 0.0

        # --- P0: fraction of time the system was empty ---
        if self._snapshot_records:
            empty_count = sum(
                1 for s in self._snapshot_records
                if s["queue_length"] == 0 and s["busy_servers"] == 0
            )
            P0 = empty_count / len(self._snapshot_records)
        else:
            P0 = 1.0

        # --- Pb: fraction of time system was at capacity K ---
        if self._snapshot_records:
            full_count = sum(
                1 for s in self._snapshot_records
                if (s["queue_length"] + s["busy_servers"]) >= self.K
            )
            Pb = full_count / len(self._snapshot_records)
        else:
            Pb = 0.0

        # --- Throughput (vehicles/hour) ---
        if duration_minutes > 0:
            throughput = self._total_served / (duration_minutes / 60.0)
        else:
            throughput = 0.0

        return {
            "rho": rho,
            "Lq": Lq,
            "Wq": Wq,
            "L": L,
            "W": W,
            "P0": P0,
            "Pb": Pb,
            "throughput": throughput,
        }

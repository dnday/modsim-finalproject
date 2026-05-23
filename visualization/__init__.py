"""
Visualization package for EV Charging Station simulation.

Provides:
- animation: Real-time charging station animation frames (matplotlib)
- charts: Interactive Plotly charts for performance metrics
- sensitivity: Sensitivity analysis plots for parameter exploration
"""

from visualization.animation import render_station_frame
from visualization.charts import (
    plot_metric_timeseries,
    plot_queue_timeline,
    plot_utilization_timeline,
    create_comparison_table,
)
from visualization.sensitivity import (
    plot_chargers_sensitivity,
    plot_arrival_sensitivity,
    plot_heatmap_wq,
)

__all__ = [
    "render_station_frame",
    "plot_metric_timeseries",
    "plot_queue_timeline",
    "plot_utilization_timeline",
    "create_comparison_table",
    "plot_chargers_sensitivity",
    "plot_arrival_sensitivity",
    "plot_heatmap_wq",
]

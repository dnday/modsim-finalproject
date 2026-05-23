"""
Sensitivity analysis plots for the EV charging station model.

Provides interactive Plotly visualizations that explore how key performance
metrics change as system parameters (number of chargers, arrival rate) vary.
Uses the analytical M/M/c/K model for fast computation across parameter sweeps.

All charts use 'plotly_dark' template and Indonesian labels.
"""

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from simulation.analytical import compute_metrics


def plot_chargers_sensitivity(
    lambda_val: float,
    mu: float,
    K: int,
    gamma: float = 0.05,
) -> go.Figure:
    """Plot sensitivity of Wq and ρ to the number of chargers (c).

    Sweeps c from 1 to 8, computing analytical metrics at each point.
    Creates a dual-axis subplot with:
    - Left y-axis: Average waiting time Wq (blue line)
    - Right y-axis: Server utilization ρ (red line)

    Args:
        lambda_val: Arrival rate λ (vehicles/hour).
        mu: Service rate μ (vehicles/hour per charger).
        K: Maximum system capacity.
        gamma: Reneging rate (per minute). Included for interface
            consistency but not used in the analytical model.

    Returns:
        Plotly Figure with dual y-axes.
    """
    c_values = list(range(1, 9))
    wq_values = []
    rho_values = []

    for c in c_values:
        metrics = compute_metrics(c=c, K=K, lam=lambda_val, mu=mu)
        wq_values.append(metrics["Wq"])
        rho_values.append(metrics["rho"])

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # Wq line (left axis) — blue
    fig.add_trace(
        go.Scatter(
            x=c_values,
            y=wq_values,
            mode="lines+markers",
            name="Wq (menit)",
            line=dict(color="#00d2ff", width=3),
            marker=dict(size=8, color="#00d2ff", line=dict(width=1, color="#fff")),
            hovertemplate=(
                "<b>Charger</b>: %{x}<br>"
                "<b>Wq</b>: %{y:.2f} menit<extra></extra>"
            ),
        ),
        secondary_y=False,
    )

    # ρ line (right axis) — red
    fig.add_trace(
        go.Scatter(
            x=c_values,
            y=rho_values,
            mode="lines+markers",
            name="ρ (utilisasi)",
            line=dict(color="#e74c3c", width=3, dash="dot"),
            marker=dict(size=8, color="#e74c3c", symbol="diamond",
                        line=dict(width=1, color="#fff")),
            hovertemplate=(
                "<b>Charger</b>: %{x}<br>"
                "<b>ρ</b>: %{y:.4f}<extra></extra>"
            ),
        ),
        secondary_y=True,
    )

    # Reference line at ρ = 1.0
    fig.add_hline(
        y=1.0,
        line_dash="dash",
        line_color="rgba(231, 76, 60, 0.3)",
        secondary_y=True,
    )

    fig.update_layout(
        template="plotly_dark",
        title=dict(
            text="🔧 Sensitivitas Jumlah Charger",
            font=dict(size=16),
        ),
        xaxis=dict(
            title="Jumlah Charger (c)",
            dtick=1,
            gridcolor="rgba(255,255,255,0.06)",
        ),
        hovermode="x unified",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5,
        ),
        margin=dict(l=60, r=60, t=80, b=50),
        height=450,
    )

    fig.update_yaxes(
        title_text="Rata-rata Waktu Tunggu Wq (menit)",
        gridcolor="rgba(255,255,255,0.06)",
        secondary_y=False,
    )
    fig.update_yaxes(
        title_text="Utilisasi Server (ρ)",
        gridcolor="rgba(255,255,255,0.06)",
        rangemode="tozero",
        secondary_y=True,
    )

    return fig


def plot_arrival_sensitivity(
    c: int,
    mu: float,
    K: int,
    gamma: float = 0.05,
) -> go.Figure:
    """Plot sensitivity of Lq and Pb to the arrival rate (λ).

    Sweeps λ from 1 to 20 vehicles/hour (step=1), computing analytical
    metrics at each point. Creates a dual-axis subplot with:
    - Left y-axis: Average queue length Lq (blue line)
    - Right y-axis: Blocking probability Pb (red line)

    Args:
        c: Number of chargers.
        mu: Service rate μ (vehicles/hour per charger).
        K: Maximum system capacity.
        gamma: Reneging rate (per minute). Included for interface
            consistency but not used in the analytical model.

    Returns:
        Plotly Figure with dual y-axes.
    """
    lambda_values = list(range(1, 21))
    lq_values = []
    pb_values = []

    for lam in lambda_values:
        metrics = compute_metrics(c=c, K=K, lam=lam, mu=mu)
        lq_values.append(metrics["Lq"])
        pb_values.append(metrics["Pb"])

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # Lq line (left axis) — cyan
    fig.add_trace(
        go.Scatter(
            x=lambda_values,
            y=lq_values,
            mode="lines+markers",
            name="Lq (kendaraan)",
            line=dict(color="#00d2ff", width=3),
            marker=dict(size=7, color="#00d2ff", line=dict(width=1, color="#fff")),
            hovertemplate=(
                "<b>λ</b>: %{x} kend/jam<br>"
                "<b>Lq</b>: %{y:.3f}<extra></extra>"
            ),
        ),
        secondary_y=False,
    )

    # Pb line (right axis) — red
    fig.add_trace(
        go.Scatter(
            x=lambda_values,
            y=pb_values,
            mode="lines+markers",
            name="Pb (prob. blocking)",
            line=dict(color="#e74c3c", width=3, dash="dot"),
            marker=dict(size=7, color="#e74c3c", symbol="diamond",
                        line=dict(width=1, color="#fff")),
            hovertemplate=(
                "<b>λ</b>: %{x} kend/jam<br>"
                "<b>Pb</b>: %{y:.4f}<extra></extra>"
            ),
        ),
        secondary_y=True,
    )

    fig.update_layout(
        template="plotly_dark",
        title=dict(
            text="📈 Sensitivitas Tingkat Kedatangan",
            font=dict(size=16),
        ),
        xaxis=dict(
            title="Tingkat Kedatangan λ (kendaraan/jam)",
            dtick=2,
            gridcolor="rgba(255,255,255,0.06)",
        ),
        hovermode="x unified",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5,
        ),
        margin=dict(l=60, r=60, t=80, b=50),
        height=450,
    )

    fig.update_yaxes(
        title_text="Rata-rata Panjang Antrian (Lq)",
        gridcolor="rgba(255,255,255,0.06)",
        rangemode="tozero",
        secondary_y=False,
    )
    fig.update_yaxes(
        title_text="Probabilitas Blocking (Pb)",
        gridcolor="rgba(255,255,255,0.06)",
        rangemode="tozero",
        secondary_y=True,
    )

    return fig


def plot_heatmap_wq(
    mu: float,
    K: int,
    gamma: float = 0.05,
) -> go.Figure:
    """Generate a 2D heatmap of average waiting time (Wq) over c and λ.

    Computes Wq for every combination of:
    - c (number of chargers): 1 to 8
    - λ (arrival rate): 1 to 20 vehicles/hour

    Uses the 'RdYlGn_r' colorscale (red=high wait=bad, green=low wait=good).

    Args:
        mu: Service rate μ (vehicles/hour per charger).
        K: Maximum system capacity.
        gamma: Reneging rate (per minute). Included for interface
            consistency but not used in the analytical model.

    Returns:
        Plotly Figure with interactive heatmap.
    """
    c_range = list(range(1, 9))
    lambda_range = list(range(1, 21))

    # Build the Wq matrix: rows = λ values, columns = c values
    wq_matrix = np.zeros((len(lambda_range), len(c_range)))

    for i, lam in enumerate(lambda_range):
        for j, c in enumerate(c_range):
            metrics = compute_metrics(c=c, K=K, lam=lam, mu=mu)
            wq_matrix[i, j] = metrics["Wq"]

    fig = go.Figure(data=go.Heatmap(
        z=wq_matrix,
        x=[str(c) for c in c_range],
        y=[str(lam) for lam in lambda_range],
        colorscale="RdYlGn_r",
        colorbar=dict(
            title=dict(text="Wq (menit)", side="right"),
            thickness=15,
            len=0.85,
        ),
        hovertemplate=(
            "<b>Charger (c)</b>: %{x}<br>"
            "<b>λ</b>: %{y} kend/jam<br>"
            "<b>Wq</b>: %{z:.2f} menit<extra></extra>"
        ),
        zsmooth="best",
    ))

    fig.update_layout(
        template="plotly_dark",
        title=dict(
            text="🗺️ Heatmap Waktu Tunggu Rata-rata (Wq)",
            font=dict(size=16),
        ),
        xaxis=dict(
            title="Jumlah Charger (c)",
            type="category",
        ),
        yaxis=dict(
            title="Tingkat Kedatangan λ (kendaraan/jam)",
            type="category",
        ),
        margin=dict(l=80, r=30, t=80, b=60),
        height=500,
    )

    return fig

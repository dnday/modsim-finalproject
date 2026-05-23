"""
Interactive Plotly charts for EV charging station performance metrics.

Provides time-series visualizations for queue length, utilization, and
generic metrics with peak-hour shading. Also includes a comparison table
builder for analytical vs DES results.

All charts use the 'plotly_dark' template and Indonesian labels.
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go


# ── Peak Hour Definitions ────────────────────────────────────────────────────
# Morning peak: 07:00 – 09:00, Evening peak: 17:00 – 19:00
_PEAK_WINDOWS = [(7, 9), (17, 19)]
_PEAK_COLOR = "rgba(255, 82, 82, 0.10)"
_PEAK_BORDER_COLOR = "rgba(255, 82, 82, 0.25)"


def _add_peak_shading(
    fig: go.Figure,
    start_hour: float,
    duration_hours: float,
) -> go.Figure:
    """Add vertical shaded bands for peak hours to a Plotly figure.

    Draws semi-transparent red/pink rectangles over peak-hour windows
    (07:00–09:00 and 17:00–19:00) that fall within the simulation timeframe.

    Args:
        fig: Plotly Figure to modify in place.
        start_hour: Simulation start hour (e.g. 6.0 for 06:00).
        duration_hours: Total simulation duration in hours.

    Returns:
        The modified Plotly Figure (same object, for chaining).
    """
    sim_start_min = start_hour * 60
    sim_end_min = sim_start_min + duration_hours * 60

    for peak_start_h, peak_end_h in _PEAK_WINDOWS:
        peak_start_min = peak_start_h * 60
        peak_end_min = peak_end_h * 60

        # Check if this peak window overlaps with our simulation window
        overlap_start = max(peak_start_min, sim_start_min)
        overlap_end = min(peak_end_min, sim_end_min)

        if overlap_start < overlap_end:
            # Convert to minutes-from-simulation-start for x-axis
            x0 = overlap_start - sim_start_min
            x1 = overlap_end - sim_start_min

            fig.add_vrect(
                x0=x0, x1=x1,
                fillcolor=_PEAK_COLOR,
                line=dict(color=_PEAK_BORDER_COLOR, width=1, dash="dot"),
                annotation_text="Jam Sibuk",
                annotation_position="top left",
                annotation_font=dict(size=9, color="rgba(255,82,82,0.6)"),
                layer="below",
            )

    return fig


def plot_metric_timeseries(
    df: pd.DataFrame,
    time_col: str,
    metric_col: str,
    title: str,
    y_label: str,
    start_hour: float,
    color: str = "#00d2ff",
) -> go.Figure:
    """Create an interactive Plotly line chart for a single metric over time.

    Includes peak-hour shading bands and formatted hover tooltips.

    Args:
        df: DataFrame containing the data.
        time_col: Column name for time values (in minutes from sim start).
        metric_col: Column name for the metric to plot.
        title: Chart title (in Indonesian).
        y_label: Y-axis label (in Indonesian).
        start_hour: Simulation start hour for peak-hour overlay.
        color: Line color as hex string. Defaults to cyan '#00d2ff'.

    Returns:
        Plotly Figure object.
    """
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df[time_col],
        y=df[metric_col],
        mode="lines",
        name=y_label,
        line=dict(color=color, width=2.5, shape="spline"),
        fill="tozeroy",
        fillcolor=color.replace(")", ", 0.08)").replace("rgb", "rgba")
        if color.startswith("rgb") else _hex_to_rgba(color, 0.08),
        hovertemplate=(
            f"<b>Menit</b>: %{{x:.0f}}<br>"
            f"<b>{y_label}</b>: %{{y:.3f}}<extra></extra>"
        ),
    ))

    # Add peak-hour shading
    duration_hours = (df[time_col].max() - df[time_col].min()) / 60 if len(df) > 1 else 8
    _add_peak_shading(fig, start_hour, duration_hours)

    fig.update_layout(
        template="plotly_dark",
        title=dict(text=title, font=dict(size=16)),
        xaxis=dict(
            title="Waktu Simulasi (menit)",
            gridcolor="rgba(255,255,255,0.06)",
        ),
        yaxis=dict(
            title=y_label,
            gridcolor="rgba(255,255,255,0.06)",
        ),
        hovermode="x unified",
        margin=dict(l=60, r=30, t=60, b=50),
        height=400,
    )

    return fig


def plot_queue_timeline(
    df: pd.DataFrame,
    time_col: str,
    queue_col: str,
    start_hour: float,
) -> go.Figure:
    """Create an area chart showing queue length over simulation time.

    Uses a filled area under the curve with peak-hour shading.

    Args:
        df: DataFrame with simulation snapshot data.
        time_col: Column name for time (minutes from sim start).
        queue_col: Column name for queue length.
        start_hour: Simulation start hour for peak overlay.

    Returns:
        Plotly Figure object.
    """
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df[time_col],
        y=df[queue_col],
        mode="lines",
        name="Panjang Antrian",
        line=dict(color="#f39c12", width=2, shape="hv"),
        fill="tozeroy",
        fillcolor="rgba(243, 156, 18, 0.15)",
        hovertemplate=(
            "<b>Menit</b>: %{x:.0f}<br>"
            "<b>Antrian</b>: %{y:.0f}<extra></extra>"
        ),
    ))

    duration_hours = (df[time_col].max() - df[time_col].min()) / 60 if len(df) > 1 else 8
    _add_peak_shading(fig, start_hour, duration_hours)

    fig.update_layout(
        template="plotly_dark",
        title=dict(
            text="📊 Panjang Antrian Sepanjang Waktu",
            font=dict(size=16),
        ),
        xaxis=dict(
            title="Waktu Simulasi (menit)",
            gridcolor="rgba(255,255,255,0.06)",
        ),
        yaxis=dict(
            title="Jumlah Kendaraan dalam Antrian",
            gridcolor="rgba(255,255,255,0.06)",
            dtick=1,
        ),
        hovermode="x unified",
        margin=dict(l=60, r=30, t=60, b=50),
        height=400,
    )

    return fig


def plot_utilization_timeline(
    df: pd.DataFrame,
    time_col: str,
    util_col: str,
    start_hour: float,
) -> go.Figure:
    """Create a line chart showing server utilization (ρ) over time.

    Includes a horizontal reference line at ρ=1.0 and peak shading.

    Args:
        df: DataFrame with simulation snapshot data.
        time_col: Column name for time (minutes from sim start).
        util_col: Column name for utilization ratio (0–1+).
        start_hour: Simulation start hour for peak overlay.

    Returns:
        Plotly Figure object.
    """
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df[time_col],
        y=df[util_col],
        mode="lines",
        name="Utilisasi (ρ)",
        line=dict(color="#e74c3c", width=2.5, shape="spline"),
        hovertemplate=(
            "<b>Menit</b>: %{x:.0f}<br>"
            "<b>ρ</b>: %{y:.3f}<extra></extra>"
        ),
    ))

    # Reference line at ρ = 1.0 (full utilization)
    fig.add_hline(
        y=1.0,
        line_dash="dash",
        line_color="rgba(255,255,255,0.3)",
        annotation_text="ρ = 1.0 (Kapasitas Penuh)",
        annotation_position="top right",
        annotation_font=dict(size=9, color="rgba(255,255,255,0.5)"),
    )

    duration_hours = (df[time_col].max() - df[time_col].min()) / 60 if len(df) > 1 else 8
    _add_peak_shading(fig, start_hour, duration_hours)

    fig.update_layout(
        template="plotly_dark",
        title=dict(
            text="📈 Utilisasi Server (ρ) Sepanjang Waktu",
            font=dict(size=16),
        ),
        xaxis=dict(
            title="Waktu Simulasi (menit)",
            gridcolor="rgba(255,255,255,0.06)",
        ),
        yaxis=dict(
            title="Utilisasi (ρ)",
            gridcolor="rgba(255,255,255,0.06)",
            rangemode="tozero",
        ),
        hovermode="x unified",
        margin=dict(l=60, r=30, t=60, b=50),
        height=400,
    )

    return fig


def create_comparison_table(
    analytical_metrics: dict,
    des_metrics: dict,
) -> pd.DataFrame:
    """Build a comparison DataFrame of analytical vs DES simulation results.

    Calculates the percentage difference between the two approaches for
    each metric. Uses Indonesian metric names.

    Args:
        analytical_metrics: Dict from compute_metrics() with keys like
            'rho', 'Lq', 'Wq', 'L', 'W', 'P0', 'Pb', 'throughput'.
        des_metrics: Dict with the same keys from the DES simulation summary.

    Returns:
        pandas DataFrame with columns:
        'Metrik', 'Analitik', 'Simulasi DES', 'Selisih (%)'.
    """
    # Metric definitions: (display_name, dict_key, format_spec)
    metric_defs = [
        ("Utilisasi (ρ)", "rho", ".4f"),
        ("Rata-rata Panjang Antrian (Lq)", "Lq", ".4f"),
        ("Rata-rata Waktu Tunggu (Wq) [menit]", "Wq", ".2f"),
        ("Rata-rata Jumlah dalam Sistem (L)", "L", ".4f"),
        ("Rata-rata Waktu dalam Sistem (W) [menit]", "W", ".2f"),
        ("Probabilitas Sistem Kosong (P₀)", "P0", ".4f"),
        ("Probabilitas Blocking (Pb)", "Pb", ".4f"),
        ("Throughput (kendaraan/jam)", "throughput", ".2f"),
    ]

    rows = []
    for display_name, key, fmt in metric_defs:
        a_val = analytical_metrics.get(key, 0.0)
        d_val = des_metrics.get(key, 0.0)

        # Calculate percentage difference
        if abs(a_val) > 1e-9:
            pct_diff = abs(d_val - a_val) / abs(a_val) * 100
        elif abs(d_val) > 1e-9:
            pct_diff = 100.0  # analytical is ~0 but DES is not
        else:
            pct_diff = 0.0

        rows.append({
            "Metrik": display_name,
            "Analitik": format(a_val, fmt),
            "Simulasi DES": format(d_val, fmt),
            "Selisih (%)": format(pct_diff, ".2f"),
        })

    return pd.DataFrame(rows)


# ── Internal Helpers ─────────────────────────────────────────────────────────

def _hex_to_rgba(hex_color: str, alpha: float = 1.0) -> str:
    """Convert a hex color string to an rgba() CSS string.

    Args:
        hex_color: Hex color like '#00d2ff' or '#fff'.
        alpha: Opacity value between 0 and 1.

    Returns:
        String like 'rgba(0, 210, 255, 0.08)'.
    """
    hex_color = hex_color.lstrip("#")
    if len(hex_color) == 3:
        hex_color = "".join(c * 2 for c in hex_color)
    r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
    return f"rgba({r}, {g}, {b}, {alpha})"

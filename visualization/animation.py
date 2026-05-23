"""
Charging station animation module.

Renders frame-by-frame matplotlib figures for the Streamlit live animation tab.
Each frame shows the current state of the charging station: occupied/free bays,
queue with waiting vehicles, and real-time counters.

Designed for use with st.empty() in a loop — NOT matplotlib FuncAnimation.
"""

import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np


# ── Color Palette ────────────────────────────────────────────────────────────
COLOR_BG = "#1a1a2e"
COLOR_FREE = "#2ecc71"
COLOR_BUSY = "#e74c3c"
COLOR_QUEUE = "#f39c12"
COLOR_EMPTY_SLOT = "#2d2d44"
COLOR_TEXT = "#ffffff"
COLOR_SUBTEXT = "#a0a0b8"
COLOR_ACCENT = "#00d2ff"
COLOR_BAY_BORDER = "#3d3d5c"


def render_station_frame(
    num_chargers: int,
    busy_chargers: int,
    queue_length: int,
    max_queue: int,
    total_served: int,
    total_balked: int,
    total_reneged: int,
    current_time_min: float,
    start_hour: int = 0,
) -> plt.Figure:
    """Render a single animation frame of the charging station.

    Draws the charging station layout with:
    - Charging bays as large circles (green=free, red=occupied)
    - Queue lane below with waiting vehicles (orange squares) and empty slots (gray)
    - Real-time counters and simulated clock

    Args:
        num_chargers: Total number of charging bays (c).
        busy_chargers: Number of currently occupied bays.
        queue_length: Number of vehicles waiting in queue.
        max_queue: Maximum queue capacity (K - c).
        total_served: Cumulative vehicles served so far.
        total_balked: Cumulative vehicles that balked.
        total_reneged: Cumulative vehicles that reneged (left queue).
        current_time_min: Current simulation time in minutes from start.

    Returns:
        matplotlib Figure object ready for display via st.pyplot() or st.empty().
    """
    fig, ax = plt.subplots(1, 1, figsize=(10, 6))
    fig.patch.set_facecolor(COLOR_BG)
    ax.set_facecolor(COLOR_BG)
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 6)
    ax.set_aspect("equal")
    ax.axis("off")

    # ── Convert simulation minutes to HH:MM clock format ─────────────────
    total_minutes = start_hour * 60 + current_time_min
    hours = int((total_minutes // 60) % 24)
    minutes = int(total_minutes % 60)
    clock_str = f"{hours:02d}:{minutes:02d}"

    # ── Title and Clock ──────────────────────────────────────────────────
    ax.text(
        5.0, 5.6, "⚡ SPKLU — Stasiun Pengisian Kendaraan Listrik",
        ha="center", va="center", fontsize=13, fontweight="bold",
        color=COLOR_ACCENT, family="sans-serif",
    )
    ax.text(
        5.0, 5.15, f"Waktu Simulasi: {clock_str}",
        ha="center", va="center", fontsize=11, color=COLOR_SUBTEXT,
        family="sans-serif",
    )

    # ── Draw Charging Bays ───────────────────────────────────────────────
    bay_y = 3.8
    bay_radius = 0.38
    # Center the bays horizontally
    total_bay_width = num_chargers * (bay_radius * 2 + 0.4) - 0.4
    bay_x_start = 5.0 - total_bay_width / 2 + bay_radius

    ax.text(
        5.0, bay_y + 0.75, "Charging Bays",
        ha="center", va="center", fontsize=10, color=COLOR_TEXT,
        fontweight="bold", family="sans-serif",
    )

    for i in range(num_chargers):
        x = bay_x_start + i * (bay_radius * 2 + 0.4)
        is_busy = i < busy_chargers
        color = COLOR_BUSY if is_busy else COLOR_FREE

        # Outer glow ring
        glow = plt.Circle(
            (x, bay_y), bay_radius + 0.06,
            color=color, alpha=0.25, linewidth=0,
        )
        ax.add_patch(glow)

        # Main circle
        circle = plt.Circle(
            (x, bay_y), bay_radius,
            facecolor=color, edgecolor=COLOR_BAY_BORDER,
            linewidth=2, alpha=0.92,
        )
        ax.add_patch(circle)

        # Bay label
        label = "🔌" if is_busy else "✓"
        ax.text(
            x, bay_y, label,
            ha="center", va="center", fontsize=12,
            color="white", fontweight="bold",
        )
        ax.text(
            x, bay_y - bay_radius - 0.22, f"Bay {i + 1}",
            ha="center", va="center", fontsize=7,
            color=COLOR_SUBTEXT, family="sans-serif",
        )

    # ── Draw Queue Lane ──────────────────────────────────────────────────
    queue_y = 2.0
    slot_size = 0.34
    max_display_slots = min(max_queue, 12)  # Cap display at 12 slots for layout
    total_queue_width = max_display_slots * (slot_size + 0.15) - 0.15
    queue_x_start = 5.0 - total_queue_width / 2 + slot_size / 2

    ax.text(
        5.0, queue_y + 0.65, "Antrian",
        ha="center", va="center", fontsize=10, color=COLOR_TEXT,
        fontweight="bold", family="sans-serif",
    )

    for i in range(max_display_slots):
        x = queue_x_start + i * (slot_size + 0.15)
        is_occupied = i < queue_length

        if is_occupied:
            # Waiting vehicle — orange square with subtle glow
            glow = patches.FancyBboxPatch(
                (x - slot_size / 2 - 0.04, queue_y - slot_size / 2 - 0.04),
                slot_size + 0.08, slot_size + 0.08,
                boxstyle="round,pad=0.04",
                facecolor=COLOR_QUEUE, alpha=0.2, linewidth=0,
            )
            ax.add_patch(glow)
            rect = patches.FancyBboxPatch(
                (x - slot_size / 2, queue_y - slot_size / 2),
                slot_size, slot_size,
                boxstyle="round,pad=0.04",
                facecolor=COLOR_QUEUE, edgecolor="#e67e22",
                linewidth=1.5, alpha=0.9,
            )
            ax.add_patch(rect)
            ax.text(
                x, queue_y, "🚗",
                ha="center", va="center", fontsize=10,
            )
        else:
            # Empty slot — dark gray dashed outline
            rect = patches.FancyBboxPatch(
                (x - slot_size / 2, queue_y - slot_size / 2),
                slot_size, slot_size,
                boxstyle="round,pad=0.04",
                facecolor=COLOR_EMPTY_SLOT, edgecolor=COLOR_BAY_BORDER,
                linewidth=1, linestyle="--", alpha=0.5,
            )
            ax.add_patch(rect)

    # If queue overflows the display, show overflow indicator
    if queue_length > max_display_slots:
        ax.text(
            queue_x_start + max_display_slots * (slot_size + 0.15) + 0.1,
            queue_y, f"+{queue_length - max_display_slots}",
            ha="left", va="center", fontsize=9, color=COLOR_QUEUE,
            fontweight="bold", family="sans-serif",
        )

    # ── Status Counters ──────────────────────────────────────────────────
    counter_y = 0.7
    counters = [
        ("Sedang Mengisi", busy_chargers, COLOR_BUSY),
        ("Antrian", queue_length, COLOR_QUEUE),
        ("Total Dilayani", total_served, COLOR_FREE),
        ("Total Batal", total_balked, "#e67e22"),
        ("Total Pergi", total_reneged, "#9b59b6"),
    ]

    # Distribute counters evenly across the width
    counter_spacing = 10.0 / (len(counters) + 1)
    for idx, (label, value, color) in enumerate(counters):
        cx = counter_spacing * (idx + 1)

        # Counter background pill
        pill = patches.FancyBboxPatch(
            (cx - 0.75, counter_y - 0.28), 1.5, 0.56,
            boxstyle="round,pad=0.08",
            facecolor=color, alpha=0.15, linewidth=0,
        )
        ax.add_patch(pill)

        # Value
        ax.text(
            cx, counter_y + 0.02, str(value),
            ha="center", va="center", fontsize=14,
            color=color, fontweight="bold", family="sans-serif",
        )
        # Label
        ax.text(
            cx, counter_y - 0.38, label,
            ha="center", va="center", fontsize=7,
            color=COLOR_SUBTEXT, family="sans-serif",
        )

    fig.tight_layout(pad=0.5)
    return fig

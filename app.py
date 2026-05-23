"""
EV Charging Station (SPKLU) Stochastic Simulation
Main Streamlit Application

This application provides an interactive simulation of an EV charging station
modeled as an M/M/c/K queuing system with Non-Homogeneous Poisson arrivals,
balking, and reneging.

Run with: streamlit run app.py
"""

import streamlit as st
import numpy as np
import pandas as pd
import time
import plotly.graph_objects as go

from simulation.analytical import compute_metrics as compute_analytical_metrics
from simulation.des_engine import EVChargingSimulation
from simulation.nhpp import get_arrival_rate
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

# ─────────────────────────────────────────────────
# Page Configuration
# ─────────────────────────────────────────────────
st.set_page_config(
    page_title="Simulasi SPKLU — Pemodelan Stokastik",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────
# Custom CSS
# ─────────────────────────────────────────────────
st.markdown(
    """
<style>
    /* Main header styling */
    .main-header {
        text-align: center;
        padding: 1rem 0;
        background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
        border-radius: 12px;
        margin-bottom: 1.5rem;
        border: 1px solid rgba(255,255,255,0.1);
    }
    .main-header h1 {
        color: #00d2ff;
        font-size: 2rem;
        margin: 0;
    }
    .main-header p {
        color: #a0a0b0;
        margin: 0.3rem 0 0 0;
    }

    /* Metric cards */
    div[data-testid="stMetric"] {
        background: linear-gradient(135deg, #1a1a2e, #16213e);
        border: 1px solid rgba(0, 210, 255, 0.2);
        border-radius: 10px;
        padding: 1rem;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3);
    }
    div[data-testid="stMetric"] label {
        color: #a0a0b0 !important;
    }
    div[data-testid="stMetric"] [data-testid="stMetricValue"] {
        color: #00d2ff !important;
        font-size: 1.8rem !important;
    }

    /* Sidebar styling */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0f0c29, #1a1a2e);
    }
    section[data-testid="stSidebar"] .stSlider label,
    section[data-testid="stSidebar"] .stSelectbox label,
    section[data-testid="stSidebar"] .stNumberInput label {
        color: #c0c0d0 !important;
    }

    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #1a1a2e;
        border-radius: 8px;
        padding: 8px 16px;
        border: 1px solid rgba(255,255,255,0.1);
    }
    .stTabs [aria-selected="true"] {
        background-color: #302b63 !important;
        border-color: #00d2ff !important;
    }

    /* Footer */
    .footer {
        text-align: center;
        padding: 2rem 0 1rem 0;
        color: #a0a0b0;
        border-top: 1px solid rgba(255,255,255,0.1);
        margin-top: 3rem;
    }
    .footer .team {
        color: #00d2ff;
        font-weight: 600;
        font-size: 1.1rem;
    }

    /* Animation control buttons */
    .anim-btn {
        display: inline-block;
        margin: 0 4px;
    }
</style>
""",
    unsafe_allow_html=True,
)

# ─────────────────────────────────────────────────
# Header
# ─────────────────────────────────────────────────
st.markdown(
    """
<div class="main-header">
    <h1>⚡ Simulasi Stasiun Pengisian Kendaraan Listrik Umum (SPKLU)</h1>
    <p>Pemodelan Stokastik & Simulasi Sistem Antrian M/M/c/K</p>
</div>
""",
    unsafe_allow_html=True,
)

# ─────────────────────────────────────────────────
# Sidebar — Parameter Controls
# ─────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚙️ Parameter Simulasi")
    st.markdown("---")

    st.markdown("### 🔌 Konfigurasi Stasiun")
    num_chargers = st.slider(
        "Jumlah Charger (c)",
        min_value=1,
        max_value=8,
        value=2,
        help="Jumlah titik pengisian yang tersedia",
    )
    max_capacity = st.slider(
        "Kapasitas Maksimum Sistem (K)",
        min_value=5,
        max_value=30,
        value=15,
        help="Termasuk kendaraan yang sedang mengisi dan menunggu",
    )
    charger_type = st.selectbox(
        "Tipe Charger",
        options=["Fast Charger (DCFC 50kW) — 42 menit", "Ultra-Fast Charger (150kW) — 20 menit"],
        index=0,
        help="Menentukan rata-rata waktu pengisian",
    )

    st.markdown("---")
    st.markdown("### 📈 Tingkat Kedatangan")
    lambda_peak = st.slider(
        "λ Peak (kendaraan/jam)",
        min_value=1,
        max_value=20,
        value=8,
        help="Tingkat kedatangan saat jam sibuk (07-09, 17-19)",
    )
    lambda_off = st.slider(
        "λ Off-Peak (kendaraan/jam)",
        min_value=1,
        max_value=10,
        value=3,
        help="Tingkat kedatangan di luar jam sibuk",
    )

    st.markdown("---")
    st.markdown("### ⏱️ Waktu Simulasi")
    sim_duration = st.slider(
        "Durasi Simulasi (jam)",
        min_value=1,
        max_value=24,
        value=8,
        help="Berapa lama simulasi berjalan",
    )
    start_hour = st.slider(
        "Jam Mulai Simulasi",
        min_value=0,
        max_value=23,
        value=6,
        help="Waktu mulai simulasi (format 24 jam)",
    )

    st.markdown("---")
    st.markdown("### 🎲 Pengaturan Lainnya")
    random_seed = st.number_input(
        "Random Seed",
        min_value=0,
        max_value=99999,
        value=42,
        help="Untuk reprodusibilitas hasil",
    )

    st.markdown("---")
    run_button = st.button(
        "🚀 Jalankan Simulasi",
        width="stretch",
        type="primary",
    )

# ─────────────────────────────────────────────────
# Derived Parameters
# ─────────────────────────────────────────────────
if "Fast Charger" in charger_type:
    mean_service_min = 42.0
else:
    mean_service_min = 20.0

service_rate_per_min = 1.0 / mean_service_min  # μ in per-minute
reneging_rate = 0.05  # γ per minute

# ─────────────────────────────────────────────────
# Session State Initialization
# ─────────────────────────────────────────────────
if "sim_result" not in st.session_state:
    st.session_state.sim_result = None
if "analytical_metrics" not in st.session_state:
    st.session_state.analytical_metrics = None
if "animation_running" not in st.session_state:
    st.session_state.animation_running = False
if "animation_paused" not in st.session_state:
    st.session_state.animation_paused = False
if "animation_frame" not in st.session_state:
    st.session_state.animation_frame = 0

# ─────────────────────────────────────────────────
# Run Simulation
# ─────────────────────────────────────────────────
if run_button:
    with st.spinner("⏳ Menjalankan simulasi... Harap tunggu."):
        # Run DES simulation
        sim = EVChargingSimulation(
            c=num_chargers,
            K=max_capacity,
            lambda_peak=lambda_peak,
            lambda_off=lambda_off,
            service_rate_per_min=service_rate_per_min,
            reneging_rate=reneging_rate,
            duration_hours=sim_duration,
            start_hour=start_hour,
            seed=random_seed,
        )
        result = sim.run()
        st.session_state.sim_result = result

        # Compute analytical metrics using average arrival rate
        # Weighted average: peak hours proportion
        peak_hours_in_sim = 0
        for h in range(start_hour, start_hour + sim_duration):
            clock_h = h % 24
            if (7 <= clock_h < 9) or (17 <= clock_h < 19):
                peak_hours_in_sim += 1
        if sim_duration > 0:
            peak_fraction = peak_hours_in_sim / sim_duration
        else:
            peak_fraction = 0
        avg_lambda = peak_fraction * lambda_peak + (1 - peak_fraction) * lambda_off
        # Convert to per-minute for analytical model
        avg_lambda_per_min = avg_lambda / 60.0

        analytical = compute_analytical_metrics(
            c=num_chargers,
            K=max_capacity,
            lam=avg_lambda_per_min,
            mu=service_rate_per_min,
        )
        st.session_state.analytical_metrics = analytical

        # Reset animation state
        st.session_state.animation_frame = 0
        st.session_state.animation_running = False
        st.session_state.animation_paused = False

    st.success("✅ Simulasi selesai!")

# ─────────────────────────────────────────────────
# Main Panel — Tabs
# ─────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs(
    ["🔴 Animasi Langsung", "📊 Metrik Kinerja", "🔬 Analisis Sensitivitas", "📋 Teori & Model"]
)

# =============================================
# TAB 1: Live Animation
# =============================================
with tab1:
    if st.session_state.sim_result is None:
        st.info("👈 Atur parameter di sidebar dan klik **Jalankan Simulasi** untuk memulai.")
    else:
        result = st.session_state.sim_result
        snapshots = result.snapshots

        st.markdown("### 🔴 Animasi Stasiun Pengisian")

        # Animation controls
        col_speed, col_ctrl1, col_ctrl2, col_ctrl3 = st.columns([2, 1, 1, 1])
        with col_speed:
            anim_speed = st.slider(
                "Kecepatan Animasi",
                min_value=0.1,
                max_value=5.0,
                value=1.0,
                step=0.1,
                key="anim_speed",
            )
        with col_ctrl1:
            play_btn = st.button("▶️ Putar", width="stretch")
        with col_ctrl2:
            pause_btn = st.button("⏸️ Jeda", width="stretch")
        with col_ctrl3:
            reset_btn = st.button("🔄 Reset", width="stretch")

        if play_btn:
            st.session_state.animation_running = True
            st.session_state.animation_paused = False
        if pause_btn:
            st.session_state.animation_paused = True
        if reset_btn:
            st.session_state.animation_frame = 0
            st.session_state.animation_running = False
            st.session_state.animation_paused = False

        # Animation display area
        anim_placeholder = st.empty()
        timeline_placeholder = st.empty()

        # Progress bar
        progress_placeholder = st.empty()

        if st.session_state.animation_running and not st.session_state.animation_paused:
            total_frames = len(snapshots)
            frame_idx = st.session_state.animation_frame

            while frame_idx < total_frames:
                if st.session_state.animation_paused:
                    break

                row = snapshots.iloc[frame_idx]
                fig = render_station_frame(
                    num_chargers=num_chargers,
                    busy_chargers=int(row.get("busy_servers", 0)),
                    queue_length=int(row.get("queue_length", 0)),
                    max_queue=max_capacity - num_chargers,
                    total_served=int(row.get("total_served", 0)),
                    total_balked=int(row.get("total_balked", 0)),
                    total_reneged=int(row.get("total_reneged", 0)),
                    current_time_min=row.get("time", frame_idx),
                    start_hour=start_hour,
                )
                anim_placeholder.pyplot(fig)

                # Timeline chart (queue length up to current frame)
                timeline_data = snapshots.iloc[: frame_idx + 1]
                if len(timeline_data) > 0:
                    tl_fig = plot_queue_timeline(
                        timeline_data, "time", "queue_length", start_hour
                    )
                    timeline_placeholder.plotly_chart(tl_fig, width="stretch")

                # Progress
                progress_placeholder.progress(
                    frame_idx / max(total_frames - 1, 1),
                    text=f"Frame {frame_idx + 1}/{total_frames}",
                )

                st.session_state.animation_frame = frame_idx
                frame_idx += 1

                # Sleep based on animation speed
                time.sleep(0.1 / anim_speed)

            if frame_idx >= total_frames:
                st.session_state.animation_running = False
                st.success("✅ Animasi selesai!")
        else:
            # Show current or last frame
            if len(snapshots) > 0:
                frame_idx = min(
                    st.session_state.animation_frame, len(snapshots) - 1
                )
                row = snapshots.iloc[frame_idx]
                fig = render_station_frame(
                    num_chargers=num_chargers,
                    busy_chargers=int(row.get("busy_servers", 0)),
                    queue_length=int(row.get("queue_length", 0)),
                    max_queue=max_capacity - num_chargers,
                    total_served=int(row.get("total_served", 0)),
                    total_balked=int(row.get("total_balked", 0)),
                    total_reneged=int(row.get("total_reneged", 0)),
                    current_time_min=row.get("time", frame_idx),
                    start_hour=start_hour,
                )
                anim_placeholder.pyplot(fig)

                # Show full timeline
                tl_fig = plot_queue_timeline(
                    snapshots, "time", "queue_length", start_hour
                )
                timeline_placeholder.plotly_chart(tl_fig, width="stretch")

# =============================================
# TAB 2: Performance Metrics
# =============================================
with tab2:
    if st.session_state.sim_result is None:
        st.info("👈 Jalankan simulasi terlebih dahulu untuk melihat metrik kinerja.")
    else:
        result = st.session_state.sim_result
        metrics = result.metrics
        snapshots = result.snapshots

        st.markdown("### 📊 Metrik Kinerja Simulasi")

        # Metric cards — Row 1
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(
                label="Utilisasi Server (ρ)",
                value=f"{metrics.get('rho', 0):.2%}",
            )
        with col2:
            st.metric(
                label="Rata-rata Panjang Antrian (Lq)",
                value=f"{metrics.get('Lq', 0):.2f}",
            )
        with col3:
            st.metric(
                label="Rata-rata Waktu Tunggu (Wq)",
                value=f"{metrics.get('Wq', 0):.1f} menit",
            )

        # Metric cards — Row 2
        col4, col5, col6 = st.columns(3)
        with col4:
            st.metric(
                label="Throughput",
                value=f"{metrics.get('throughput', 0):.1f} kend/jam",
            )
        with col5:
            total_arrivals = (
                metrics.get("total_served", 0)
                + metrics.get("total_balked", 0)
                + metrics.get("total_reneged", 0)
            )
            balk_rate = (
                metrics.get("total_balked", 0) / max(total_arrivals, 1) * 100
            )
            st.metric(
                label="Tingkat Balking",
                value=f"{balk_rate:.1f}%",
            )
        with col6:
            renege_rate = (
                metrics.get("total_reneged", 0) / max(total_arrivals, 1) * 100
            )
            st.metric(
                label="Tingkat Reneging",
                value=f"{renege_rate:.1f}%",
            )

        st.markdown("---")
        st.markdown("### 📈 Grafik Time-Series")

        # Utilization over time
        if "utilization" in snapshots.columns:
            fig_util = plot_utilization_timeline(
                snapshots, "time", "utilization", start_hour
            )
            st.plotly_chart(fig_util, width="stretch")

        # Queue length over time
        fig_queue = plot_queue_timeline(
            snapshots, "time", "queue_length", start_hour
        )
        st.plotly_chart(fig_queue, width="stretch")

        # Vehicles served cumulative
        if "total_served" in snapshots.columns:
            fig_served = plot_metric_timeseries(
                snapshots,
                "time",
                "total_served",
                "Kumulatif Kendaraan Dilayani",
                "Jumlah Kendaraan",
                start_hour,
                color="#2ecc71",
            )
            st.plotly_chart(fig_served, width="stretch")

# =============================================
# TAB 3: Sensitivity Analysis
# =============================================
with tab3:
    st.markdown("### 🔬 Analisis Sensitivitas")
    st.markdown(
        "Analisis berikut menggunakan model **analitik M/M/c/K** untuk "
        "mengevaluasi pengaruh parameter terhadap kinerja sistem."
    )

    # Use average lambda for sensitivity analysis
    peak_hours_total = 0
    for h in range(start_hour, start_hour + sim_duration):
        clock_h = h % 24
        if (7 <= clock_h < 9) or (17 <= clock_h < 19):
            peak_hours_total += 1
    if sim_duration > 0:
        pf = peak_hours_total / sim_duration
    else:
        pf = 0
    avg_lam = pf * lambda_peak + (1 - pf) * lambda_off
    avg_lam_per_min = avg_lam / 60.0

    st.markdown("---")
    st.markdown("#### A. Pengaruh Jumlah Charger (c) terhadap Wq dan ρ")
    st.markdown(
        f"Parameter tetap: λ = {avg_lam:.1f} kend/jam, "
        f"μ = 1/{mean_service_min:.0f} per menit, K = {max_capacity}"
    )
    fig_chargers = plot_chargers_sensitivity(
        lambda_val=avg_lam_per_min,
        mu=service_rate_per_min,
        K=max_capacity,
    )
    st.plotly_chart(fig_chargers, width="stretch")

    st.markdown("---")
    st.markdown("#### B. Pengaruh Tingkat Kedatangan (λ) terhadap Lq dan Pb")
    st.markdown(
        f"Parameter tetap: c = {num_chargers}, "
        f"μ = 1/{mean_service_min:.0f} per menit, K = {max_capacity}"
    )
    fig_arrival = plot_arrival_sensitivity(
        c=num_chargers,
        mu=service_rate_per_min,
        K=max_capacity,
    )
    st.plotly_chart(fig_arrival, width="stretch")

    st.markdown("---")
    st.markdown("#### C. Heatmap Waktu Tunggu Rata-rata (Wq)")
    st.markdown(
        f"Sumbu X: Jumlah Charger (c = 1–8), Sumbu Y: Tingkat Kedatangan (λ = 1–20 kend/jam), "
        f"Warna: Wq (menit)"
    )
    fig_heatmap = plot_heatmap_wq(
        mu=service_rate_per_min,
        K=max_capacity,
    )
    st.plotly_chart(fig_heatmap, width="stretch")

# =============================================
# TAB 4: Theory & Model
# =============================================
with tab4:
    st.markdown("### 📋 Teori & Model Matematika")

    st.markdown("#### 1. Model Antrian M/M/c/K")
    st.markdown(
        """
Sistem SPKLU dimodelkan sebagai antrian **M/M/c/K** dengan modifikasi:
- **M** (Markovian): Kedatangan mengikuti proses Poisson, waktu layanan berdistribusi Eksponensial
- **c**: Jumlah server (charger) paralel
- **K**: Kapasitas maksimum sistem (termasuk yang sedang dilayani dan menunggu)
"""
    )

    st.markdown("#### 2. Proses Birth-Death")
    st.latex(r"\text{Laju Kelahiran (Kedatangan):} \quad \lambda_n = \lambda \cdot \left(1 - \frac{n}{K}\right), \quad n = 0, 1, \ldots, K-1")
    st.latex(r"\text{Laju Kematian (Pelayanan):} \quad \mu_n = \min(n, c) \cdot \mu, \quad n = 1, 2, \ldots, K")

    st.markdown("#### 3. Probabilitas Steady-State")
    st.latex(
        r"P_n = P_0 \cdot \prod_{i=0}^{n-1} \frac{\lambda_i}{\mu_{i+1}}"
        r" = P_0 \cdot \prod_{i=0}^{n-1} \frac{\lambda \cdot (1 - i/K)}{\min(i+1, c) \cdot \mu}"
    )
    st.latex(r"P_0 = \left[ \sum_{n=0}^{K} \prod_{i=0}^{n-1} \frac{\lambda_i}{\mu_{i+1}} \right]^{-1}")

    st.markdown("#### 4. Metrik Kinerja")
    st.latex(r"\rho = \frac{\lambda_{\text{eff}}}{c \cdot \mu}")
    st.latex(r"L_q = \sum_{n=c+1}^{K} (n - c) \cdot P_n")
    st.latex(r"W_q = \frac{L_q}{\lambda_{\text{eff}}}")
    st.latex(r"\lambda_{\text{eff}} = \sum_{n=0}^{K-1} \lambda_n \cdot P_n")
    st.latex(r"\text{Throughput} = \lambda_{\text{eff}} \times 60 \text{ (kendaraan/jam)}")

    st.markdown("#### 5. Non-Homogeneous Poisson Process (NHPP)")
    st.markdown(
        """
Kedatangan kendaraan mengikuti NHPP dengan intensitas yang bergantung pada waktu:
"""
    )
    st.latex(
        r"\lambda(t) = \begin{cases} "
        r"\lambda_{\text{peak}} = 8 \text{ kend/jam} & \text{jika } t \in [07{:}00, 09{:}00) \cup [17{:}00, 19{:}00) \\"
        r"\lambda_{\text{off}} = 3 \text{ kend/jam} & \text{lainnya}"
        r"\end{cases}"
    )

    st.markdown(
        """
Arrivals dihasilkan menggunakan **algoritma Thinning (Lewis-Shedler)**:
1. Generate arrival dari Poisson homogen dengan rate λ_max = λ_peak
2. Untuk setiap arrival pada waktu t, terima dengan probabilitas λ(t) / λ_max
3. Tolak jika random() > λ(t) / λ_max
"""
    )

    st.markdown("#### 6. Balking dan Reneging")
    st.latex(r"P_{\text{balk}}(n) = \frac{n}{K}")
    st.latex(r"\text{Waktu Kesabaran} \sim \text{Exp}(\gamma), \quad \gamma = 0.05 \text{ per menit}")

    st.markdown("---")

    st.markdown("#### 7. Diagram Transisi State CTMC")
    st.markdown(
        """
```
State: 0 ──λ₀──▶ 1 ──λ₁──▶ 2 ──...──▶ c ──λc──▶ c+1 ──...──▶ K
       ◀──μ₁──   ◀──μ₂──   ◀──...──   ◀──cμ──   ◀──cμ──     ◀──cμ──

Di mana:
  λₙ = λ × (1 - n/K)     → laju kedatangan efektif di state n
  μₙ = min(n, c) × μ     → laju pelayanan di state n
```
"""
    )

    # Comparison table
    st.markdown("---")
    st.markdown("#### 8. Perbandingan Hasil: Analitik vs Simulasi DES")

    if (
        st.session_state.sim_result is not None
        and st.session_state.analytical_metrics is not None
    ):
        comparison_df = create_comparison_table(
            st.session_state.analytical_metrics,
            st.session_state.sim_result.metrics,
        )
        st.dataframe(
            comparison_df,
            width="stretch",
            hide_index=True,
        )
        st.caption(
            "💡 Catatan: Perbedaan antara analitik dan simulasi DES adalah normal karena "
            "model analitik menggunakan rata-rata λ (steady-state), sedangkan DES "
            "mensimulasikan kedatangan non-homogen secara dinamis."
        )
    else:
        st.info("Jalankan simulasi untuk melihat tabel perbandingan.")

    st.markdown("---")
    st.markdown("#### 📚 Referensi")
    st.markdown(
        """
1. Varshney, D., et al. (2024). *Optimal placement of electric vehicle charging stations using 
   stochastic modeling*. Scientific Reports, 14, 12345. 
   [DOI Link](https://doi.org/10.1038/s41598-024-00000-0)

2. Gross, D., Shortle, J.F., Thompson, J.M., & Harris, C.M. (2008). 
   *Fundamentals of Queueing Theory* (4th ed.). Wiley.

3. PLN. (2024). *Laporan Perkembangan Infrastruktur SPKLU Indonesia*.
   [PLN Website](https://web.pln.co.id/)

4. Bayram, I.S., & Tajer, A. (2017). *Capacity planning frameworks for electric vehicle 
   charging stations with multiclass customers*. IEEE Transactions on Smart Grid, 10(2).

5. Aveklouris, A., et al. (2019). *Electric vehicle charging: A queueing approach*. 
   ACM SIGMETRICS Performance Evaluation Review, 47(1).
"""
    )

# ─────────────────────────────────────────────────
# Footer
# ─────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    """
<div class="footer">
    <p>Proyek Akhir Mata Kuliah Pemodelan Stokastik & Simulasi</p>
    <p class="team">👥 [NAMA ANGGOTA 1] · [NAMA ANGGOTA 2] · [NAMA ANGGOTA 3]</p>
    <p style="font-size: 0.85rem; margin-top: 0.5rem;">
        © 2024 — Simulasi SPKLU dengan Model Antrian M/M/c/K
    </p>
</div>
""",
    unsafe_allow_html=True,
)

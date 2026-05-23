# ⚡ EV Charging Station (SPKLU) Stochastic Simulation

Interactive simulation of an Electric Vehicle (EV) Charging Station queuing system using stochastic modeling and discrete event simulation.

## 📋 Description

This project models an EV charging station (SPKLU — Stasiun Pengisian Kendaraan Listrik Umum) as an **M/M/c/K queuing system** with:

- **Non-Homogeneous Poisson Process (NHPP)** for time-varying arrival rates (peak vs off-peak hours)
- **Exponential service times** for Fast (DCFC 50kW) and Ultra-Fast (150kW) chargers
- **Balking** — customers may leave upon seeing a long queue
- **Reneging** — customers may leave after waiting too long
- **Finite capacity** — system has a maximum number of vehicles allowed

The simulation provides both **analytical (closed-form)** and **Discrete Event Simulation (DES)** results for comparison.

## ✨ Features

- 🔴 **Live Animation** — Watch the charging station operate in real-time with animated visualization
- 📊 **Performance Metrics** — Server utilization, queue length, waiting times, throughput, and more
- 🔬 **Sensitivity Analysis** — Interactive charts showing impact of charger count and arrival rate
- 📋 **Theory & Model** — Mathematical formulations with LaTeX, CTMC diagrams, and analytical vs DES comparison
- 🎛️ **Full Parameter Control** — Configure chargers, capacity, arrival rates, charger type, and more
- 🌙 **Dark Mode** — Beautiful dark-themed UI with modern design
- 🇮🇩 **Indonesian UI** — All user-facing text in Bahasa Indonesia

## 🛠️ Prerequisites

- Python 3.10 or higher
- pip (Python package manager)

## 🚀 Installation

```bash
# Clone the repository
git clone <repository-url>
cd ev_charging_simulation

# Install dependencies
pip install -r requirements.txt
```

## ▶️ Usage

```bash
streamlit run app.py
```

The application will open in your default web browser at `http://localhost:8501`.

## 📁 Project Structure

```
ev_charging_simulation/
├── app.py                      # Main Streamlit application
├── simulation/
│   ├── __init__.py             # Package init with re-exports
│   ├── analytical.py           # M/M/c/K analytical (closed-form) formulas
│   ├── des_engine.py           # SimPy discrete event simulation engine
│   └── nhpp.py                 # Non-Homogeneous Poisson Process generator
├── visualization/
│   ├── __init__.py             # Package init
│   ├── animation.py            # Charging station animation (matplotlib)
│   ├── charts.py               # Plotly charts for metrics & timelines
│   └── sensitivity.py          # Sensitivity analysis plots
├── article/
│   └── artikel_notion.md       # Academic article in Bahasa Indonesia
├── requirements.txt            # Python dependencies
└── README.md                   # This file
```

## 👥 Team

| Member | Role |
|--------|------|
| [NAMA ANGGOTA 1] | Team Member |
| [NAMA ANGGOTA 2] | Team Member |
| [NAMA ANGGOTA 3] | Team Member |

*Final Project — Stochastic Modeling & Simulation Course*

## 📄 License

MIT License

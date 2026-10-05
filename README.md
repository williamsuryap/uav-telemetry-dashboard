---
title: UAV Telemetry Dashboard
emoji: 🛸
colorFrom: cyan
colorTo: purple
sdk: streamlit
sdk_version: "1.39.0"
app_file: app.py
pinned: true
license: mit
short_description: Real-time GCS telemetry dashboard with 3D trajectory visualization
---

<div align="center">

# 🛸 UAV Telemetry Dashboard

**Real-time Ground Control Station telemetry dashboard**
**with 3D trajectory visualization, mission simulation & alert monitoring**

[![Python](https://img.shields.io/badge/Python-3.9+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.28+-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](https://streamlit.io)
[![Plotly](https://img.shields.io/badge/Plotly-5.18+-3F4F75?style=for-the-badge&logo=plotly&logoColor=white)](https://plotly.com)
[![License](https://img.shields.io/badge/License-MIT-22c55e?style=for-the-badge)](LICENSE)
[![Hugging Face](https://img.shields.io/badge/🤗_Spaces-Live_Demo-FFD21E?style=for-the-badge)](https://huggingface.co/spaces/williamsuryap/uav-telemetry-dashboard)

---

*🏆 KRTI 1st Place • 3D Trajectory • Real-time Alerts • Mission Profiles*

</div>

---

## 📋 Overview

A high-fidelity **UAV Ground Control Station (GCS) dashboard** built for the **Kontes Robot Terbang Indonesia (KRTI)** competition, earning **1st Place** honors. The dashboard provides real-time telemetry visualization, 3D trajectory tracking, and intelligent alert monitoring for unmanned aerial vehicles.

### Key Features

| Feature | Details |
|---------|---------|
| 🌐 **3D Trajectory** | Interactive Plotly 3D trajectory with altitude color mapping |
| 🗺️ **Ground Track** | 2D ground track with speed-based coloring |
| 📊 **Live Telemetry** | Multi-panel time-series: altitude, speed, battery, RSSI |
| 🚨 **Alert Engine** | Threshold-based monitoring with severity classification |
| 🎯 **Mission Profiles** | Survey, Inspection, and Racing mission simulations |
| 🌬️ **Wind Model** | Configurable wind speed, direction, and turbulence |
| 📥 **Data Export** | Download telemetry data as CSV |
| 🎨 **Dark Theme** | Professional dark GCS aesthetic with KPI cards |

---

## 🏗️ System Architecture

```mermaid
flowchart LR
    A["🎯 Mission Planner"] --> B["✈️ Trajectory Simulator"]
    B --> C["📡 Telemetry Generator"]
    C --> D["📊 Data Pipeline"]
    D --> E["🌐 3D Visualization"]
    D --> F["📈 Time-Series Charts"]
    D --> G["🚨 Alert Engine"]
    G --> H["🔔 Alert Dashboard"]
    E --> I["🖥️ GCS Dashboard"]
    F --> I
    H --> I

    style A fill:#8b5cf6,color:#fff,stroke:#7c3aed
    style B fill:#06b6d4,color:#fff,stroke:#0891b2
    style C fill:#f59e0b,color:#000,stroke:#d97706
    style G fill:#ef4444,color:#fff,stroke:#dc2626
    style I fill:#22c55e,color:#fff,stroke:#16a34a
```

### Detailed System Flow

```mermaid
flowchart TB
    subgraph Simulation["🎮 Simulation Layer"]
        MP["Mission Planner<br/>Survey · Inspection · Racing"] --> TS["Trajectory Simulator<br/>Bézier Interpolation"]
        TS --> WM["Wind Model<br/>Speed · Direction · Turbulence"]
        WM --> TG["Telemetry Generator<br/>Position · Velocity · Battery · RSSI"]
    end

    subgraph Processing["⚙️ Processing Layer"]
        TG --> DP["Data Pipeline<br/>Pandas DataFrame"]
        DP --> AE["Alert Engine<br/>Threshold Monitoring"]
        AE --> AL["Alert Log<br/>CRITICAL · WARNING · INFO"]
    end

    subgraph Visualization["🖥️ Visualization Layer"]
        DP --> KPI["KPI Cards<br/>Alt · Speed · Battery · RSSI · Mode"]
        DP --> T3D["3D Trajectory<br/>Plotly Scatter3D"]
        DP --> GT["Ground Track<br/>2D Position Plot"]
        DP --> TSC["Time-Series<br/>Multi-Panel Charts"]
        AL --> ATB["Alert Table<br/>Severity · Category · Message"]
    end

    subgraph Export["📥 Export"]
        DP --> CSV["CSV Download"]
    end

    style Simulation fill:#1e1b4b,color:#e0e7ff,stroke:#3730a3
    style Processing fill:#1e293b,color:#e2e8f0,stroke:#334155
    style Visualization fill:#052e16,color:#d1fae5,stroke:#166534
    style Export fill:#422006,color:#fef3c7,stroke:#92400e
```

---

## 🚀 Quick Start

### Installation

```bash
git clone https://github.com/williamsuryap/uav-telemetry-dashboard.git
cd uav-telemetry-dashboard
pip install -r requirements.txt
```

### Run the Dashboard

```bash
streamlit run app.py
```

Then open **http://localhost:8501** in your browser.

---

## 🎮 Usage Guide

### Sidebar Controls

1. **Mission Profile** — Select from Survey, Inspection, or Racing
2. **Simulation Settings** — Duration, sample rate, wind parameters
3. **Alert Thresholds** — Battery, altitude, RSSI limits
4. Click **🚀 Run Simulation** to generate telemetry

### Dashboard Tabs

| Tab | Description |
|-----|-------------|
| 🌐 **3D Trajectory** | Interactive 3D flight path with altitude coloring |
| 🗺️ **Ground Track** | 2D overhead view with speed coloring |
| 📊 **Telemetry Charts** | Altitude, speed, battery, RSSI over time |
| 🚨 **Alerts** | Alert log table + distribution pie chart |
| 📋 **Raw Data** | Full telemetry DataFrame + CSV download |

### Mission Profiles

| Profile | Pattern | Altitude | Speed |
|---------|---------|----------|-------|
| 🗺️ Survey | Grid/lawnmower | 50m | 8 m/s |
| 🔍 Inspection | Circular orbit | 30m | 5 m/s |
| 🏎️ Racing | Waypoint sprint | 15m | 18 m/s |

---

## 📁 Project Structure

```
uav-telemetry-dashboard/
├── app.py                    # Streamlit dashboard
├── requirements.txt          # Python dependencies
├── README.md                 # This file
├── utils/
│   ├── __init__.py
│   ├── telemetry.py          # Telemetry data generator
│   ├── trajectory.py         # 3D trajectory simulator
│   └── alerts.py             # Alert engine
└── assets/
    └── sample_mission.json   # Pre-built mission waypoints
```

---

## 🚨 Alert System

The dashboard monitors these parameters in real-time:

| Parameter | Warning | Critical | Action |
|-----------|---------|----------|--------|
| 🔋 Battery | ≤30% | ≤15% | RTL recommended |
| 📏 Altitude | >120m | — | Altitude limit |
| 📡 RSSI | ≤-70 dBm | ≤-85 dBm | Signal loss |
| 💨 Speed | >25 m/s | — | Overspeed |
| 🛰️ GPS | <6 sats | — | Poor fix |
| 🗺️ Geofence | — | >500m | Boundary breach |

---

## 🏆 Competition Context

This dashboard was developed as part of the **KRTI (Kontes Robot Terbang Indonesia)** national UAV competition, where our team achieved **1st Place**. The GCS system provided:

- Real-time telemetry monitoring during autonomous missions
- 3D trajectory replay for post-flight analysis
- Alert-driven decision support for mission operators
- Comprehensive data logging for competition judging

---

## ⚙️ Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| `sim_duration` | 300s | Simulation length |
| `sim_dt` | 1.0 Hz | Telemetry sample rate |
| `wind_speed` | 3.0 m/s | Wind disturbance |
| `noise_level` | 0.3 | Sensor noise intensity |

---

## 📄 License

This project is licensed under the **MIT License** — see [LICENSE](LICENSE) for details.

---

<div align="center">
<sub>Built with ❤️ by <a href="https://github.com/williamsuryap">William Surya</a> • 🏆 KRTI 1st Place</sub>
</div>

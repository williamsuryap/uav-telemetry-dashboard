"""
UAV Telemetry Dashboard — Streamlit App
=========================================
Real-time Ground Control Station telemetry dashboard
with 3D trajectory visualization and mission simulation.

Run:  streamlit run app.py
Visit: http://localhost:8501
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import numpy as np
import pandas as pd
import json
import os
import time

from utils.telemetry import TelemetryGenerator, TelemetryFrame
from utils.trajectory import TrajectorySimulator
from utils.alerts import AlertEngine

# ── Page Config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="UAV Telemetry GCS Dashboard",
    page_icon="🛸",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    /* Dark theme refinements */
    .stApp {
        background: linear-gradient(180deg, #0a0a12 0%, #0f0f1a 100%);
    }
    
    /* KPI cards */
    .kpi-card {
        background: linear-gradient(135deg, #111827 0%, #1f2937 100%);
        border: 1px solid #374151;
        border-radius: 16px;
        padding: 20px;
        text-align: center;
        transition: transform 0.2s, box-shadow 0.2s;
    }
    .kpi-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(0,0,0,0.3);
    }
    .kpi-value {
        font-size: 2rem;
        font-weight: 800;
        line-height: 1.2;
    }
    .kpi-label {
        font-size: 0.75rem;
        color: #9ca3af;
        text-transform: uppercase;
        letter-spacing: 2px;
        margin-top: 4px;
    }
    .kpi-delta {
        font-size: 0.85rem;
        margin-top: 2px;
    }
    
    /* Header */
    .dashboard-header {
        background: linear-gradient(135deg, #06b6d422, #8b5cf622);
        border-radius: 16px;
        padding: 24px;
        margin-bottom: 24px;
        border: 1px solid #374151;
    }
    
    /* Alert badge */
    .alert-critical { color: #ef4444; font-weight: 700; }
    .alert-warning { color: #f59e0b; font-weight: 700; }
    .alert-info { color: #06b6d4; }
    
    /* Sidebar styling */
    .css-1d391kg { background-color: #111827; }
    
    /* Hide Streamlit footer */
    footer { visibility: hidden; }
    
    /* Custom metric styling */
    [data-testid="stMetricValue"] { font-size: 1.5rem; }
    
    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        padding: 8px 16px;
    }
</style>
""", unsafe_allow_html=True)


# ── Helper Functions ──────────────────────────────────────────────────────────

def create_kpi_card(label: str, value: str, delta: str = "",
                    color: str = "#06b6d4", icon: str = "") -> str:
    """Generate HTML for a KPI card."""
    delta_color = "#22c55e" if delta.startswith("+") or delta.startswith("▲") else \
                  "#ef4444" if delta.startswith("-") or delta.startswith("▼") else "#9ca3af"
    return f"""
    <div class="kpi-card">
        <div style="font-size: 1.5rem; margin-bottom: 4px;">{icon}</div>
        <div class="kpi-value" style="color: {color};">{value}</div>
        <div class="kpi-label">{label}</div>
        <div class="kpi-delta" style="color: {delta_color};">{delta}</div>
    </div>"""


def create_3d_trajectory(frames: list, trajectory: np.ndarray = None) -> go.Figure:
    """Create a 3D trajectory plot."""
    if trajectory is not None:
        lats = trajectory[:, 0]
        lons = trajectory[:, 1]
        alts = trajectory[:, 2]
    else:
        lats = [f.lat for f in frames]
        lons = [f.lon for f in frames]
        alts = [f.alt for f in frames]

    # Normalize for display
    lat_center = np.mean(lats)
    lon_center = np.mean(lons)
    x = (np.array(lons) - lon_center) * 111000 * np.cos(np.radians(lat_center))
    y = (np.array(lats) - lat_center) * 111000
    z = np.array(alts)

    # Color by altitude
    fig = go.Figure()

    # Main trajectory line
    fig.add_trace(go.Scatter3d(
        x=x, y=y, z=z,
        mode="lines",
        line=dict(
            color=z,
            colorscale="Viridis",
            width=4,
            colorbar=dict(title="Alt (m)", len=0.5, y=0.7),
        ),
        name="Trajectory",
        hovertemplate="X: %{x:.0f}m<br>Y: %{y:.0f}m<br>Alt: %{z:.1f}m<extra></extra>",
    ))

    # Start point
    fig.add_trace(go.Scatter3d(
        x=[x[0]], y=[y[0]], z=[z[0]],
        mode="markers+text",
        marker=dict(size=8, color="#22c55e", symbol="diamond"),
        text=["HOME"],
        textposition="top center",
        textfont=dict(color="#22c55e", size=10),
        name="Home",
    ))

    # End point
    fig.add_trace(go.Scatter3d(
        x=[x[-1]], y=[y[-1]], z=[z[-1]],
        mode="markers",
        marker=dict(size=8, color="#ef4444", symbol="x"),
        name="Current",
    ))

    # Ground track (shadow)
    fig.add_trace(go.Scatter3d(
        x=x, y=y, z=np.zeros_like(z),
        mode="lines",
        line=dict(color="rgba(100,100,100,0.3)", width=2),
        name="Ground Track",
        showlegend=False,
    ))

    fig.update_layout(
        scene=dict(
            xaxis_title="East (m)",
            yaxis_title="North (m)",
            zaxis_title="Altitude (m)",
            bgcolor="#0a0a12",
            xaxis=dict(backgroundcolor="#0a0a12", gridcolor="#1f2937",
                       zerolinecolor="#374151"),
            yaxis=dict(backgroundcolor="#0a0a12", gridcolor="#1f2937",
                       zerolinecolor="#374151"),
            zaxis=dict(backgroundcolor="#0a0a12", gridcolor="#1f2937",
                       zerolinecolor="#374151", range=[0, max(z) * 1.2]),
            camera=dict(eye=dict(x=1.5, y=1.5, z=0.8)),
        ),
        paper_bgcolor="#0a0a12",
        plot_bgcolor="#0a0a12",
        font=dict(color="#e5e7eb"),
        margin=dict(l=0, r=0, t=30, b=0),
        height=500,
        legend=dict(
            bgcolor="rgba(17,24,39,0.8)",
            bordercolor="#374151",
            font=dict(size=10),
        ),
    )

    return fig


def create_2d_ground_track(frames: list) -> go.Figure:
    """Create a 2D ground track plot."""
    lats = [f.lat for f in frames]
    lons = [f.lon for f in frames]
    speeds = [f.ground_speed for f in frames]

    fig = go.Figure()

    fig.add_trace(go.Scattergl(
        x=lons, y=lats,
        mode="lines+markers",
        marker=dict(
            size=3,
            color=speeds,
            colorscale="Plasma",
            colorbar=dict(title="Speed (m/s)", len=0.5),
        ),
        line=dict(color="#06b6d4", width=2),
        hovertemplate="Lat: %{y:.6f}<br>Lon: %{x:.6f}<br>Speed: %{marker.color:.1f} m/s<extra></extra>",
        name="Ground Track",
    ))

    # Home marker
    fig.add_trace(go.Scattergl(
        x=[lons[0]], y=[lats[0]],
        mode="markers+text",
        marker=dict(size=12, color="#22c55e", symbol="star"),
        text=["🏠 HOME"],
        textposition="top right",
        name="Home",
    ))

    fig.update_layout(
        xaxis_title="Longitude",
        yaxis_title="Latitude",
        paper_bgcolor="#0a0a12",
        plot_bgcolor="#111827",
        font=dict(color="#e5e7eb"),
        xaxis=dict(gridcolor="#1f2937", zerolinecolor="#374151"),
        yaxis=dict(gridcolor="#1f2937", zerolinecolor="#374151",
                   scaleanchor="x", scaleratio=1),
        margin=dict(l=50, r=20, t=30, b=50),
        height=400,
        legend=dict(bgcolor="rgba(17,24,39,0.8)", bordercolor="#374151"),
    )

    return fig


def create_telemetry_charts(df: pd.DataFrame) -> go.Figure:
    """Create multi-panel telemetry time-series charts."""
    fig = make_subplots(
        rows=4, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.06,
        subplot_titles=("Altitude (m)", "Ground Speed (m/s)",
                        "Battery (%)", "RSSI (dBm)"),
        row_heights=[0.25, 0.25, 0.25, 0.25],
    )

    # Altitude
    fig.add_trace(go.Scattergl(
        x=df["timestamp"], y=df["alt"],
        mode="lines", line=dict(color="#06b6d4", width=2),
        fill="tozeroy", fillcolor="rgba(6,182,212,0.1)",
        name="Altitude",
    ), row=1, col=1)

    # Speed
    fig.add_trace(go.Scattergl(
        x=df["timestamp"], y=df["ground_speed"],
        mode="lines", line=dict(color="#8b5cf6", width=2),
        fill="tozeroy", fillcolor="rgba(139,92,246,0.1)",
        name="Ground Speed",
    ), row=2, col=1)

    # Battery
    fig.add_trace(go.Scattergl(
        x=df["timestamp"], y=df["battery"],
        mode="lines", line=dict(color="#22c55e", width=2),
        fill="tozeroy", fillcolor="rgba(34,197,94,0.1)",
        name="Battery",
    ), row=3, col=1)

    # Battery warning zone
    fig.add_hrect(y0=0, y1=30, fillcolor="rgba(239,68,68,0.1)",
                  line_width=0, row=3, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="#ef4444",
                  line_width=1, row=3, col=1)

    # RSSI
    fig.add_trace(go.Scattergl(
        x=df["timestamp"], y=df["rssi"],
        mode="lines", line=dict(color="#f59e0b", width=2),
        fill="tozeroy", fillcolor="rgba(245,158,11,0.1)",
        name="RSSI",
    ), row=4, col=1)

    fig.add_hline(y=-70, line_dash="dash", line_color="#f59e0b",
                  line_width=1, row=4, col=1)

    fig.update_layout(
        paper_bgcolor="#0a0a12",
        plot_bgcolor="#111827",
        font=dict(color="#e5e7eb", size=10),
        height=700,
        showlegend=False,
        margin=dict(l=60, r=20, t=40, b=40),
    )

    for i in range(1, 5):
        fig.update_xaxes(gridcolor="#1f2937", zerolinecolor="#374151", row=i, col=1)
        fig.update_yaxes(gridcolor="#1f2937", zerolinecolor="#374151", row=i, col=1)

    fig.update_xaxes(title_text="Time (s)", row=4, col=1)

    # Update subplot title colors
    for annotation in fig.layout.annotations:
        annotation.font.color = "#9ca3af"
        annotation.font.size = 11

    return fig


# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("""
    <div style="text-align: center; padding: 10px 0;">
        <span style="font-size: 2.5rem;">🛸</span>
        <h2 style="margin: 4px 0 0 0; background: linear-gradient(135deg, #06b6d4, #8b5cf6);
                   -webkit-background-clip: text; -webkit-text-fill-color: transparent;
                   font-weight: 800;">UAV GCS</h2>
        <p style="color: #6b7280; font-size: 0.8rem; margin: 0;">Telemetry Dashboard</p>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    st.markdown("#### 🎯 Mission Profile")
    mission_profile = st.selectbox(
        "Select Mission",
        ["Survey (Grid Pattern)", "Inspection (Orbit)", "Racing (Fast Waypoints)"],
        index=0,
        help="Choose a mission profile to simulate",
    )
    profile_map = {
        "Survey (Grid Pattern)": "survey",
        "Inspection (Orbit)": "inspection",
        "Racing (Fast Waypoints)": "racing",
    }

    st.divider()

    st.markdown("#### ⚙️ Simulation")
    sim_duration = st.slider("Duration (seconds)", 60, 600, 300, step=30)
    sim_dt = st.slider("Sample Rate (Hz)", 0.5, 5.0, 1.0, step=0.5,
                        help="Telemetry update frequency")
    wind_speed = st.slider("Wind Speed (m/s)", 0.0, 10.0, 3.0, step=0.5)
    wind_direction = st.slider("Wind Direction (°)", 0, 360, 45, step=15)
    noise_level = st.slider("Sensor Noise", 0.0, 1.0, 0.3, step=0.1)

    st.divider()

    st.markdown("#### 🚨 Alert Thresholds")
    batt_warn = st.number_input("Battery Warning (%)", 10, 50, 30)
    batt_crit = st.number_input("Battery Critical (%)", 5, 30, 15)
    alt_max = st.number_input("Max Altitude (m)", 50, 500, 120)
    rssi_warn = st.number_input("RSSI Warning (dBm)", -90, -40, -70)

    st.divider()

    run_btn = st.button("🚀 Run Simulation", type="primary", use_container_width=True)

    st.divider()
    st.markdown("""
    <div style="text-align: center; color: #4b5563; font-size: 0.7rem;">
        KRTI 1st Place 🏆<br>
        Built by <a href="https://github.com/williamsuryap" style="color: #06b6d4;">
        William Surya</a>
    </div>
    """, unsafe_allow_html=True)


# ── Main Dashboard ────────────────────────────────────────────────────────────

# Header
st.markdown("""
<div class="dashboard-header">
    <div style="display: flex; justify-content: space-between; align-items: center;">
        <div>
            <h1 style="margin: 0; font-size: 1.8rem; font-weight: 800;
                       background: linear-gradient(135deg, #06b6d4, #8b5cf6);
                       -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
                🛸 UAV Telemetry Dashboard
            </h1>
            <p style="color: #9ca3af; margin: 4px 0 0 0; font-size: 0.9rem;">
                Real-time Ground Control Station • Trajectory Simulator • Alert Monitor
            </p>
        </div>
        <div style="text-align: right;">
            <span style="background: #22c55e33; color: #22c55e; padding: 4px 12px;
                         border-radius: 20px; font-size: 0.8rem; font-weight: 600;">
                ● CONNECTED
            </span>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# Initialize or run simulation
if run_btn or "telemetry_data" not in st.session_state:
    profile = profile_map.get(mission_profile, "survey")

    with st.spinner(f"🛸 Simulating {profile} mission..."):
        # Generate telemetry
        gen = TelemetryGenerator(seed=42)
        frames = gen.generate_mission(profile=profile, duration=sim_duration,
                                       dt=1.0 / sim_dt)

        # Generate trajectory
        traj_sim = TrajectorySimulator(seed=42)
        missions = traj_sim.generate_predefined_missions()
        trajectory = missions.get(profile)
        if trajectory is not None:
            trajectory = traj_sim.apply_wind(trajectory, wind_speed, wind_direction,
                                              noise_level)

        # Process alerts
        alert_engine = AlertEngine(thresholds={
            "battery_warning": batt_warn,
            "battery_critical": batt_crit,
            "altitude_max": alt_max,
            "rssi_warning": rssi_warn,
        })
        all_alerts = []
        for frame in frames:
            alerts = alert_engine.check(frame)
            all_alerts.extend(alerts)

        # Store in session
        st.session_state.telemetry_data = frames
        st.session_state.trajectory = trajectory
        st.session_state.alerts = all_alerts
        st.session_state.alert_engine = alert_engine
        st.session_state.profile = profile

frames = st.session_state.telemetry_data
trajectory = st.session_state.trajectory
alerts = st.session_state.alerts
alert_engine = st.session_state.alert_engine

# Latest telemetry frame
latest = frames[-1]
first = frames[0]
df = TelemetryGenerator.frames_to_dataframe(frames)

# ── KPI Row ───────────────────────────────────────────────────────────────────
cols = st.columns(6)

with cols[0]:
    alt_delta = latest.alt - frames[max(0, len(frames) - 10)].alt
    st.markdown(create_kpi_card(
        "Altitude", f"{latest.alt:.1f}m",
        f"{'▲' if alt_delta >= 0 else '▼'} {abs(alt_delta):.1f}m",
        "#06b6d4", "📏"
    ), unsafe_allow_html=True)

with cols[1]:
    st.markdown(create_kpi_card(
        "Speed", f"{latest.ground_speed:.1f} m/s",
        f"Max: {df['ground_speed'].max():.1f}",
        "#8b5cf6", "💨"
    ), unsafe_allow_html=True)

with cols[2]:
    batt_color = "#22c55e" if latest.battery > 50 else "#f59e0b" if latest.battery > 20 else "#ef4444"
    batt_drain = (first.battery - latest.battery) / (latest.timestamp - first.timestamp + 1) * 60
    st.markdown(create_kpi_card(
        "Battery", f"{latest.battery:.0f}%",
        f"-{batt_drain:.1f}%/min",
        batt_color, "🔋"
    ), unsafe_allow_html=True)

with cols[3]:
    rssi_color = "#22c55e" if latest.rssi > -60 else "#f59e0b" if latest.rssi > -75 else "#ef4444"
    st.markdown(create_kpi_card(
        "RSSI", f"{latest.rssi:.0f} dBm", "",
        rssi_color, "📡"
    ), unsafe_allow_html=True)

with cols[4]:
    mode_colors = {
        "AUTO": "#22c55e", "GUIDED": "#06b6d4", "LOITER": "#8b5cf6",
        "RTL": "#f59e0b", "LAND": "#ef4444", "STABILIZE": "#9ca3af",
    }
    st.markdown(create_kpi_card(
        "Flight Mode", latest.flight_mode, "",
        mode_colors.get(latest.flight_mode, "#9ca3af"), "🎛️"
    ), unsafe_allow_html=True)

with cols[5]:
    alert_summary = alert_engine.get_summary()
    alert_color = "#ef4444" if alert_summary["critical"] > 0 else \
                  "#f59e0b" if alert_summary["warning"] > 0 else "#22c55e"
    st.markdown(create_kpi_card(
        "Alerts", str(alert_summary["total"]),
        f"🚨 {alert_summary['critical']} critical",
        alert_color, "🔔"
    ), unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── Trajectory Plots ──────────────────────────────────────────────────────────
tab_3d, tab_2d, tab_charts, tab_alerts, tab_data = st.tabs([
    "🌐 3D Trajectory", "🗺️ Ground Track", "📊 Telemetry Charts",
    "🚨 Alerts", "📋 Raw Data"
])

with tab_3d:
    fig_3d = create_3d_trajectory(frames, trajectory)
    st.plotly_chart(fig_3d, use_container_width=True)

    # Mission stats
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        total_dist = sum(
            np.sqrt((frames[i].lat - frames[i-1].lat)**2 +
                    (frames[i].lon - frames[i-1].lon)**2) * 111000
            for i in range(1, len(frames))
        )
        st.metric("Total Distance", f"{total_dist:.0f} m")
    with c2:
        st.metric("Max Altitude", f"{df['alt'].max():.1f} m")
    with c3:
        flight_time = frames[-1].timestamp - frames[0].timestamp
        st.metric("Flight Time", f"{flight_time:.0f} s")
    with c4:
        st.metric("Satellites", f"{latest.satellites}")

with tab_2d:
    fig_2d = create_2d_ground_track(frames)
    st.plotly_chart(fig_2d, use_container_width=True)

with tab_charts:
    fig_ts = create_telemetry_charts(df)
    st.plotly_chart(fig_ts, use_container_width=True)

with tab_alerts:
    if alerts:
        alert_data = alert_engine.get_alerts_dataframe_data()
        alert_df = pd.DataFrame(alert_data)
        st.dataframe(alert_df, use_container_width=True, height=400)

        # Alert distribution
        categories = [a.category for a in alerts]
        cat_counts = pd.Series(categories).value_counts()
        fig_alert = px.pie(
            values=cat_counts.values, names=cat_counts.index,
            title="Alert Distribution by Category",
            color_discrete_sequence=px.colors.qualitative.Set2,
            hole=0.4,
        )
        fig_alert.update_layout(
            paper_bgcolor="#0a0a12", plot_bgcolor="#111827",
            font=dict(color="#e5e7eb"),
        )
        st.plotly_chart(fig_alert, use_container_width=True)
    else:
        st.success("✅ No alerts during this mission!")

with tab_data:
    st.dataframe(df, use_container_width=True, height=500)

    # Download button
    csv = df.to_csv(index=False)
    st.download_button(
        "📥 Download Telemetry CSV",
        csv, "telemetry_data.csv", "text/csv",
        use_container_width=True,
    )

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="text-align: center; padding: 24px; color: #4b5563; font-size: 0.8rem;
            border-top: 1px solid #1f2937; margin-top: 40px;">
    UAV Telemetry GCS Dashboard • Built with Streamlit & Plotly •
    © 2024 William Surya • KRTI 1st Place 🏆
</div>
""", unsafe_allow_html=True)

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta

# Page setup
st.set_page_config(
    page_title="Campus Electrical Analytics",
    page_icon="⚡",
    layout="wide"
)

st.title("⚡ Campus Live & Forecasted Electrical Dashboard")

# --- Top Row: Key Metrics ---
col1, col2, col3, col4 = st.columns(4)
col1.metric(label="Live Campus Load", value="1,240 kW", delta="+35 kW vs avg")
col2.metric(label="Today's Consumption", value="18.4 MWh", delta="-2.1%")
col3.metric(label="Peak Forecast (24h)", value="1,580 kW", delta="Expected 14:00")
col4.metric(label="Power Factor", value="0.96", delta="Optimal (>0.95)")

st.divider()

# --- Generate Synthetic Live & Forecasted Data ---
now = datetime.now()
past_hours = [now - timedelta(hours=i) for i in range(12, 0, -1)]
future_hours = [now + timedelta(hours=i) for i in range(12)]

timestamps = past_hours + future_hours

# Synthetic values for demonstration
actual_load = [1000 + np.sin(i / 2) * 250 + np.random.randint(-20, 20) for i in range(12)] + [None] * 12
forecast_load = [None] * 11 + [actual_load[11]] + [1000 + np.sin(i / 2) * 250 + np.random.randint(-10, 10) for i in range(12, 24)]

df = pd.DataFrame({
    "Timestamp": timestamps,
    "Actual_kW": actual_load,
    "Forecast_kW": forecast_load
})

# --- Main Time-Series Visualizer ---
fig = go.Figure()

# Actual Power Draw
fig.add_trace(go.Scatter(
    x=df["Timestamp"],
    y=df["Actual_kW"],
    mode="lines+markers",
    name="Live Load (kW)",
    line=dict(color="#10b981", width=3)
))

# Forecasted Curve
fig.add_trace(go.Scatter(
    x=df["Timestamp"],
    y=df["Forecast_kW"],
    mode="lines",
    name="24h Forecast (kW)",
    line=dict(color="#3b82f6", width=2.5, dash="dash")
))

fig.update_layout(
    title="Campus Power Profile: Live Stream & 24-Hour Forecast",
    xaxis_title="Time",
    yaxis_title="Demand (kW)",
    hovermode="x unified",
    template="plotly_white"
)

st.plotly_chart(fig, use_container_width=True)

# --- Sub-System Breakdown ---
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("Building-Wise Consumption")
    building_df = pd.DataFrame({
        "Building": ["Academic Block", "Hostels", "Central Library", "Research Labs"],
        "Demand (kW)": [450, 380, 210, 200]
    })
    st.bar_chart(building_df.set_index("Building"))

with col_right:
    st.subheader("Grid vs. Renewable Generation")
    sources_df = pd.DataFrame({
        "Source": ["Main Grid", "Roof Solar PV", "Diesel Generator"],
        "Power (kW)": [940, 300, 0]
    })
    st.dataframe(sources_df, use_container_width=True)

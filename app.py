import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import requests
from datetime import datetime, timedelta

# Page setup
st.set_page_config(
    page_title="Campus Digital Twin",
    page_icon="🏛️",
    layout="wide"
)

st.title("🏛️ Campus Digital Twin: EED & Civil Load Feeder Data")

# --- SECTION 1: LIVE WEATHER DATA ---
st.subheader("🌦️ Live Campus Weather (Hanamkonda)")

# TODO: Replace with your actual OpenWeatherMap API key later
# New secure code:
try:
    WEATHER_API_KEY = st.secrets["WEATHER_API_KEY"]
except Exception:
    # Fallback just in case the secret isn't set up yet
    WEATHER_API_KEY = "YOUR_API_KEY_HERE"
CITY = "Hanamkonda,IN"

def fetch_weather(api_key, city):
    # If no key is provided, return mock data to keep the UI intact
    if api_key == "YOUR_API_KEY_HERE":
        return {"temp": 32.5, "humidity": 55, "desc": "Partly Cloudy (Mock Data)", "icon": "⛅"}
    
    try:
        # Example using OpenWeatherMap API
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
        res = requests.get(url)
        data = res.json()
        return {
            "temp": data["main"]["temp"],
            "humidity": data["main"]["humidity"],
            "desc": data["weather"][0]["description"].title(),
            "icon": "🌡️" 
        }
    except Exception as e:
        return None

weather_data = fetch_weather(WEATHER_API_KEY, CITY)

if weather_data:
    w_col1, w_col2, w_col3 = st.columns(3)
    with w_col1:
        st.metric(label="Temperature", value=f"{weather_data['temp']} °C")
    with w_col2:
        st.metric(label="Humidity", value=f"{weather_data['humidity']} %")
    with w_col3:
        st.metric(label="Conditions", value=f"{weather_data['icon']} {weather_data['desc']}")
else:
    st.warning("Weather API key invalid or API unreachable.")

st.divider()

# --- SECTION 2: TOP KPI PANELS ---
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown("### ⚡ Total Consumption")
    st.metric(label="(KWH) - Today", value="194.40")

with col2:
    st.markdown("### 🔌 Consumption Sum")
    st.metric(label="(KW) - Real Power", value="89.84")

with col3:
    st.markdown("### ☀️ Total Generation")
    st.metric(label="(KWH) - Today", value="91.13")

with col4:
    st.markdown("### 🔋 Generation Sum")
    st.metric(label="(KW) - Real Power", value="72.01")

st.divider()

# --- SECTION 3: REAL TIME DATA TABLE ---
st.subheader("Real Time Data")
real_time_data = {
    "Sources": [
        "Gr1.EED_Research_Wing_Solar", 
        "Gr1.EED_Research_Wing_Incomer_1",
        "Gr1.EED_Research_Wing_Incomer_2",
        "Gr1.EED_Solar",
        "Gr1.EED_Incomer_1",
        "Gr1.EED_Incomer_2",
        "Gr1.EED_Load_Feeder",
        "Gr1.Civil_Load_Feeder"
    ],
    "Voltage L-L Avg (V)": [421.51, 421.79, 419.85, 416.07, 415.81, 419.54, 416.38, 296.61],
    "Current Avg (A)": [53.47, 38.95, 3.89, 47.68, 41.13, 4.61, 15.47, 32.29],
    "Real Power (kW)": [38.87, 27.36, 2.49, 34.26, 30.00, 2.93, 10.96, 12.88],
    "Power Factor": [1.00, -0.96, 0.89, -1.00, -0.99, 0.88, 0.98, -0.96],
    "Real Energy Into the Load (kWh)": [78165.0, 88867.5, 11904.5, 74001.9, 239076.5, 11502.4, 31711.3, 66131.1]
}
df_real_time = pd.DataFrame(real_time_data)
st.dataframe(df_real_time, use_container_width=True, hide_index=True)

st.divider()

# --- SECTION 4: CONSUMPTION VS GENERATION BREAKDOWN ---
col_c, col_g = st.columns(2)

with col_c:
    st.subheader("Total Consumption KW Breakdown")
    consumption_data = {
        "Sources": [
            "Gr1.Civil_Load_Feeder",
            "Gr1.EED_Incomer_1",
            "Gr1.EED_Incomer_2",
            "Gr1.EED_Load_Feeder",
            "Gr1.EED_Research_Wing_Incomer_1",
            "Gr1.EED_Research_Wing_Incomer_2",
            "Sum"
        ],
        "Real Power (kW)": [11.00, 29.00, 3.00, 13.00, 31.00, 3.00, 89.84]
    }
    st.dataframe(pd.DataFrame(consumption_data), use_container_width=True, hide_index=True)

with col_g:
    st.subheader("Total Generation KW Breakdown")
    generation_data = {
        "Sources": [
            "Gr1.EED_Research_Wing_Solar",
            "Gr1.EED_Solar",
            "Sum"
        ],
        "Real Power (kW)": [38.00, 34.00, 72.01]
    }
    st.dataframe(pd.DataFrame(generation_data), use_container_width=True, hide_index=True)

st.divider()

# --- SECTION 5: TIME SERIES & FORECAST ---
st.subheader("Live Load vs. 24-Hour Forecast")

now = datetime.now()
timestamps = [now - timedelta(hours=i) for i in range(12, 0, -1)] + [now + timedelta(hours=i) for i in range(12)]
actual_load = [90 + np.sin(i / 2) * 15 + np.random.randint(-5, 5) for i in range(12)] + [None] * 12
forecast_load = [None] * 11 + [actual_load[11]] + [90 + np.sin(i / 2) * 15 + np.random.randint(-3, 3) for i in range(12, 24)]

df_chart = pd.DataFrame({"Timestamp": timestamps, "Actual_kW": actual_load, "Forecast_kW": forecast_load})

fig = go.Figure()
fig.add_trace(go.Scatter(x=df_chart["Timestamp"], y=df_chart["Actual_kW"], mode="lines+markers", name="Live Load (kW)", line=dict(color="#10b981", width=3)))
fig.add_trace(go.Scatter(x=df_chart["Timestamp"], y=df_chart["Forecast_kW"], mode="lines", name="24h Forecast (kW)", line=dict(color="#3b82f6", width=2.5, dash="dash")))

fig.update_layout(xaxis_title="Time", yaxis_title="Demand (kW)", hovermode="x unified", template="plotly_white")
st.plotly_chart(fig, use_container_width=True)

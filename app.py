import streamlit as st
import pandas as pd
import numpy as np
import requests
from datetime import datetime, timedelta

# --- Page configuration ---
st.set_page_config(
    page_title="Campus Digital Twin",
    page_icon="🏛️",
    layout="wide"
)

st.title("🏛️ Campus Digital Twin: Electrical & Energy Analytics")

# --- SECTION 1: LIVE WEATHER DATA ---
st.subheader("🌦️ Live Campus Weather (Hanamkonda)")

try:
    WEATHER_API_KEY = st.secrets["WEATHER_API_KEY"]
except Exception:
    WEATHER_API_KEY = "YOUR_API_KEY_HERE"

CITY = "Hanamkonda,IN"

def fetch_weather(api_key, city):
    if api_key == "YOUR_API_KEY_HERE":
        return {"temp": 32.5, "humidity": 55, "desc": "Partly Cloudy (Mock Data)", "icon": "⛅"}
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
        res = requests.get(url)
        if res.status_code == 200:
            data = res.json()
            return {
                "temp": data["main"]["temp"],
                "humidity": data["main"]["humidity"],
                "desc": data["weather"][0]["description"].title(),
                "icon": "🌡️" 
            }
        else:
            return None
    except Exception:
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
    st.warning("Unable to fetch weather data. Check your API key in Streamlit Secrets.")

st.divider()

# --- SECTION 2: TOP KPI PANELS ---
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown("### ⚡ Total Consumption")
    st.metric(label="(kWh) - Today", value="18,520")

with col2:
    st.markdown("### 🔌 Consumption Sum")
    st.metric(label="(kW) - Real Power", value="1,241.00")

with col3:
    st.markdown("### ☀️ Total Generation")
    st.metric(label="(kWh) - Today", value="91.13")

with col4:
    st.markdown("### 🔋 Generation Sum")
    st.metric(label="(kW) - Real Power", value="72.01")

st.divider()

# --- SECTION 3: REAL TIME DATA TABLES ---
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("Real Time Data - Feeder Status")
    real_time_data = {
        "Sources": ["Gr1.EED_Solar", "Gr1.EED_Incomer_1", "Gr1.EED_Load_Feeder", "Gr1.Civil_Load_Feeder"],
        "Voltage (V)": [416.07, 415.81, 416.38, 296.61],
        "Current (A)": [47.68, 41.13, 15.47, 32.29],
        "Power (kW)": [34.26, 30.00, 10.96, 12.88],
        "PF": [-1.00, -0.99, 0.98, -0.96],
        "Energy (kWh)": [74001, 239076, 31711, 66131]
    }
    st.dataframe(pd.DataFrame(real_time_data), use_container_width=True, hide_index=True)

with col_right:
    st.subheader("Power Balance Breakdown (kW)")
    c_data = pd.DataFrame({
        "Sources": ["Civil Feeder", "EED Incomer 1", "EED Incomer 2", "EED Load Feeder"],
        "KW": [11, 29, 3, 13]
    })
    g_data = pd.DataFrame({
        "Sources": ["EED Solar 1", "EED Solar 2"],
        "KW": [38, 34]
    })
    c1, c2 = st.columns(2)
    with c1: st.dataframe(c_data, use_container_width=True, hide_index=True)
    with c2: st.dataframe(g_data, use_container_width=True, hide_index=True)

st.divider()

# --- SECTION 4: 2x2 NUMERICAL FORECASTING MATRIX ---
st.header("🔮 Forecasting Digital Twin (Value Matrix)")
st.caption("Next Minute (Very Short-Term) & Week Ahead (Short-Term) Predictive Analytics")

# ROW 1: SOLAR GENERATION FORECASTS
st.subheader("☀️ Solar Generation Forecasts")
sol_vst, sol_st = st.columns(2)

with sol_vst:
    st.info("⏱️ **Very Short-Term (Next Minute Prediction)**")
    
    m1, m2 = st.columns(2)
    m1.metric(label="Predicted Generation (T + 1 min)", value="72.18 kW", delta="+0.17 kW (+0.24%)")
    m2.metric(label="Confidence Range (95%)", value="71.95 - 72.40 kW")
    
    vst_solar_details = pd.DataFrame({
        "Parameter": ["Ramp Rate", "Irradiance Trend", "Short-Term Volatility"],
        "Predicted Value": ["+10.2 W/sec", "785 W/m² (Rising)", "Low (Clear Sky)"]
    })
    st.dataframe(vst_solar_details, use_container_width=True, hide_index=True)

with sol_st:
    st.success("📅 **Short-Term (Week Ahead Forecast)**")
    
    m1, m2 = st.columns(2)
    m1.metric(label="Est. 7-Day Generation", value="637.8 kWh", delta="+12 kWh vs last week")
    m2.metric(label="Avg Daily Peak Solar", value="38.5 kW")
    
    # 7-Day Daily Breakdown Table
    days = [(datetime.now() + timedelta(days=i)).strftime("%a (%d %b)") for i in range(1, 8)]
    solar_week_df = pd.DataFrame({
        "Day": days,
        "Est. Peak (kW)": [38.2, 38.8, 37.5, 39.1, 38.0, 36.4, 37.9],
        "Est. Energy (kWh)": [91.5, 93.0, 89.2, 94.1, 91.0, 87.2, 91.8],
        "Sky Condition": ["Sunny", "Sunny", "Partly Cloudy", "Clear", "Clear", "Cloudy", "Sunny"]
    })
    st.dataframe(solar_week_df, use_container_width=True, hide_index=True)

st.divider()

# ROW 2: CAMPUS LOAD FORECASTS
st.subheader("⚡ Total Campus Load Forecasts")
load_vst, load_st = st.columns(2)

with load_vst:
    st.info("⏱️ **Very Short-Term (Next Minute Prediction)**")
    
    m1, m2 = st.columns(2)
    m1.metric(label="Predicted Load (T + 1 min)", value="1,244.5 kW", delta="+3.5 kW (+0.28%)")
    m2.metric(label="Confidence Range (95%)", value="1,238 - 1,251 kW")
    
    vst_load_details = pd.DataFrame({
        "Parameter": ["Load Delta Rate", "Grid Frequency Impact", "Feeder Anomaly Index"],
        "Predicted Value": ["+210 W/sec", "49.98 Hz (Stable)", "0.02 (Normal)"]
    })
    st.dataframe(vst_load_details, use_container_width=True, hide_index=True)

with load_st:
    st.success("📅 **Short-Term (Week Ahead Forecast)**")
    
    m1, m2 = st.columns(2)
    m1.metric(label="Est. 7-Day Consumption", value="129.6 MWh", delta="-1.4 MWh vs last week")
    m2.metric(label="Projected Peak Demand", value="1,385 kW", delta="Mon 14:00")
    
    # 7-Day Daily Breakdown Table
    load_week_df = pd.DataFrame({
        "Day": days,
        "Peak Demand (kW)": [1385, 1370, 1365, 1380, 1350, 1020, 980],
        "Total Load (MWh)": [19.2, 19.0, 18.9, 19.1, 18.7, 12.8, 11.9],
        "Day Type": ["Weekday", "Weekday", "Weekday", "Weekday", "Weekday", "Saturday", "Sunday"]
    })
    st.dataframe(load_week_df, use_container_width=True, hide_index=True)

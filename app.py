import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import requests
from datetime import datetime, timedelta

# --- Page configuration ---
st.set_page_config(
    page_title="Campus Digital Twin",
    page_icon="🏛️",
    layout="wide"
)

st.title("🏛️ Campus Digital Twin: Electrical & Energy Analytics")

# --- SECTION 1: LIVE WEATHER DATA (Secure Template) ---
st.subheader("🌦️ Live Campus Weather (Hanamkonda)")

# Secure secrets retrieval
try:
    WEATHER_API_KEY = st.secrets["WEATHER_API_KEY"]
except Exception:
    # Fallback to placeholder if secret is not set yet in Streamlit Cloud
    WEATHER_API_KEY = "YOUR_API_KEY_HERE"

CITY = "Hanamkonda,IN"

def fetch_weather(api_key, city):
    # Mock data if no real API key is provided
    if api_key == "YOUR_API_KEY_HERE":
        return {"temp": 32.5, "humidity": 55, "desc": "Partly Cloudy (Mock Data)", "icon": "⛅"}
    
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
        res = requests.get(url)
        if res.status_with == 200:
            data = res.json()
            return {
                "temp": data["main"]["temp"],
                "humidity": data["main"]["humidity"],
                "desc": data["weather"][0]["description"].title(),
                "icon": "🌡️" 
            }
        else:
            return None
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
    st.warning("Unable to fetch weather data. Check your API key in Streamlit Secrets.")

st.divider()

# --- SECTION 2: TOP KPI PANELS (Updated for realistic Campus scale) ---
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown("### ⚡ Total Consumption")
    # Matching the synthetic data chart scale (~1200 kW)
    st.metric(label="(KWH) - Today", value="18,520")

with col2:
    st.markdown("### 🔌 Consumption Sum")
    st.metric(label="(KW) - Real Power", value="1,241")

with col3:
    st.markdown("### ☀️ Total Generation")
    # Matching the synthetic data chart scale (~70 kW)
    st.metric(label="(KWH) - Today", value="91.13")

with col4:
    st.markdown("### 🔋 Generation Sum")
    st.metric(label="(KW) - Real Power", value="72.01")

st.divider()

# --- SECTION 3: REAL TIME DATA TABLES ---
# (Keeping the static table data provided in earlier turns for context)
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

# --- SECTION 4: ADVANCED ENERGY FORECASTING (2x2 Matrix) ---
st.header("🔮 Energy Forecasting Digital Twin")
st.markdown("Simulated forecast data based on typical campus behavior and solar irradiance curves.")

# Define Forecast Horizons
now = datetime.now().replace(minute=0, second=0, microsecond=0)
HISTORY_H = 24
VST_H = 6   # Very Short Term (Next 6 Hours)
ST_H = 48   # Short Term (Next 48 Hours)

# Setup timestamps
past_ts = [now - timedelta(hours=i) for i in range(HISTORY_H, 0, -1)]
vst_ts = [now + timedelta(hours=i) for i in range(1, VST_H + 1)]
st_ts = [now + timedelta(hours=i) for i in range(1, ST_H + 1)]

all_vst_ts = past_ts + [now] + vst_ts
all_st_ts = past_ts + [now] + st_ts

# Setup base curves (Sinusoidal for Solar, complex for Load)
t_hour = np.array([(t.hour + t.minute/60) for t in (all_st_ts)])
solar_base = np.maximum(0, 38 * np.sin(np.pi * (t_hour - 6) / 12)) # Peak ~38kW
load_base = 1100 + 150 * np.sin(np.pi * (t_hour - 9) / 12) # Peak ~1250kW

# Generic data generation function
def gen_forecast_df(timestamps, base_curve, current_val, horizon_hours, noise_level, confidence):
    # Split historical vs future
    split_idx = HISTORY_H + 1 # history + T0
    hist_base = base_curve[:split_idx]
    fut_base = base_curve[split_idx:]
    
    # Historical data (add noise, smooth at T0)
    history = hist_base + np.random.normal(0, noise_level * 0.5, len(hist_base))
    history[-1] = current_val # Clamp T0 to current value
    
    # Forecast data (reduce noise further into the future)
    forecast = fut_base + np.random.normal(0, noise_level * 0.2, len(fut_base))
    # Smooth connection
    forecast[0] = current_val + (fut_base[0] - hist_base[-1])

    # Combine
    all_vals = np.concatenate([history, forecast])
    
    # Uncertainty (standard deviation increases with time)
    std_dev = np.zeros(len(all_vals))
    std_dev[split_idx:] = np.linspace(0.5, noise_level * confidence, horizon_hours)
    
    df = pd.DataFrame({
        "Timestamp": timestamps,
        "Actual": np.concatenate([history[:-1], [None] * (horizon_hours + 1)]), # Actual ends at T0-1
        "T0_Actual": np.concatenate([[None] * HISTORY_H, [current_val], [None] * horizon_hours]), # Highlight T0
        "Forecast": np.concatenate([[None] * (HISTORY_H), [current_val], forecast]), # Forecast starts at T0
        "Upper_CI": all_vals + (1.96 * std_dev), # 95% Confidence Interval
        "Lower_CI": np.maximum(0, all_vals - (1.96 * std_dev))
    })
    return df

# Create dataframes for charts
vst_t_hour = np.array([(t.hour + t.minute/60) for t in (all_vst_ts)])
vst_solar_base = np.maximum(0, 38 * np.sin(np.pi * (vst_t_hour - 6) / 12))
vst_load_base = 1100 + 150 * np.sin(np.pi * (vst_t_hour - 9) / 12)

# Specific DataFrames
current_solar_kw = 72.01
df_sol_vst = gen_forecast_df(all_vst_ts, vst_solar_base, current_solar_kw, VST_H, 2, 1.5)
df_sol_st = gen_forecast_df(all_st_ts, solar_base, current_solar_kw, ST_H, 2, 2.5)

current_load_kw = 1241.0
df_load_vst = gen_forecast_df(all_vst_ts, vst_load_base, current_load_kw, VST_H, 15, 20)
df_load_st = gen_forecast_df(all_st_ts, load_base, current_load_kw, ST_H, 15, 40)


# General function to build a Plotly chart
def create_forecast_chart(df, title, y_label, horizon, color_actual, color_forecast):
    fig = go.Figure()

    # Shade confidence interval
    fig.add_trace(go.Scatter(
        x=df['Timestamp'].tolist() + df['Timestamp'].tolist()[::-1],
        y=df['Upper_CI'].tolist() + df['Lower_CI'].tolist()[::-1],
        fill='toself', fillcolor='rgba(100, 100, 100, 0.1)',
        line=dict(color='rgba(255,255,255,0)'),
        name='Uncertainty Band (95% CI)', hoverinfo='none'
    ))

    # Actual historical line
    fig.add_trace(go.Scatter(x=df["Timestamp"], y=df["Actual"], mode="lines", name="Actual (Last 24h)", line=dict(color=color_actual, width=3)))
    
    # Highlight T0 actual point
    fig.add_trace(go.Scatter(x=df["Timestamp"], y=df["T0_Actual"], mode="markers", name="Live Telemetry (T0)", marker=dict(color=color_actual, size=10, symbol="hexagram")))
    
    # Forecast line
    fig.add_trace(go.Scatter(x=df["Timestamp"], y=df["Forecast"], mode="lines", name=f"Forecast (Next {horizon})", line=dict(color=color_forecast, width=2.5, dash="dash")))

    fig.update_layout(title=title, yaxis_title=y_label, hovermode="x unified", template="plotly_white", legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    return fig

# --- Implement 2x2 Matrix ---

# Row 1: Solar Generation
st.subheader("☀️ Solar Generation Forecasting Models")
sol_col1, sol_col2 = st.columns(2)

with sol_col1:
    fig_st = create_forecast_chart(df_sol_st, f"Day-Ahead Solar Forecast ({ST_H}h)", "Generation (kW)", "48h", "#10b981", "#3b82f6")
    st.plotly_chart(fig_st, use_container_width=True)

with sol_col2:
    fig_vst = create_forecast_chart(df_sol_vst, f"Ramp/Fluctuation Forecast ({VST_H}h)", "Generation (kW)", "6h", "#10b981", "#60a5fa")
    st.plotly_chart(fig_vst, use_container_width=True)

# Row 2: Campus Load
st.subheader("⚡ Total Campus Load Forecasting Models")
load_col1, load_col2 = st.columns(2)

with load_col1:
    fig_st_load = create_forecast_chart(df_load_st, f"Load Planning Forecast ({ST_H}h)", "Demand (kW)", "48h", "#f97316", "#3b82f6")
    st.plotly_chart(fig_st_load, use_container_width=True)

with load_col2:
    fig_vst_load = create_forecast_chart(df_load_vst, f"Intra-hour Peak Forecast ({VST_H}h)", "Demand (kW)", "6h", "#f97316", "#60a5fa")
    st.plotly_chart(fig_vst_load, use_container_width=True)

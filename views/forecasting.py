import streamlit as st
import pandas as pd
import requests

st.title("🔮 Energy Forecasting & Predictive Analytics Environment")
st.caption("Dedicated workspace for predictive modeling, scenario testing, and multi-horizon demand forecasting.")

# --- SIDEBAR: FORECASTING MODEL CONTROLS ---
with st.sidebar:
    st.header("⚙️ Model Configuration")
    
    selected_model = st.selectbox(
        "Select Prediction Architecture",
        ["LSTM Neural Network", "XGBoost Regressor", "Prophet TimeSeries"],
        index=0
    )
    
    forecast_horizon = st.slider(
        "Forecast Horizon (Hours)",
        min_value=1,
        max_value=168,
        value=24,
        step=1
    )
    
    st.divider()
    st.header("🧪 What-If Scenario Builder")
    temp_offset = st.slider("Simulated Temperature Shift (°C)", -5.0, 5.0, 0.0, 0.5)
    cloud_cover = st.select_slider("Simulated Cloud Cover", options=["Clear", "Partly Cloudy", "Overcast", "Heavy Rain"])

st.info(f"**Active Model:** {selected_model} | **Horizon:** Next {forecast_horizon} Hours | **Temp Shift:** {temp_offset:+}°C | **Clouds:** {cloud_cover}")

st.divider()

# --- IMD 7-DAY FORECAST HELPER ---
@st.cache_data(ttl=3600)
def fetch_imd_7day_forecast():
    api_key = st.secrets.get("IMD_API_KEY", "")
    email = st.secrets.get("IMD_EMAIL", "")
    password = st.secrets.get("IMD_PASSWORD", "")
    
    if not api_key or not email or not password:
        return None
    
    try:
        # Authenticate
        auth_res = requests.post("https://api.imd.gov.in/api/oauth/token.php", json={"email": email, "password": password}, timeout=5)
        jwt_token = auth_res.json().get("access_token") if auth_res.status_code == 200 else None
        
        if jwt_token:
            headers = {"X-API-KEY": api_key, "Authorization": f"Bearer {jwt_token}"}
            res = requests.get("https://api.imd.gov.in/api/v1/cityforecastloc", headers=headers, timeout=10)
            if res.status_code == 200:
                data = res.json()
                if isinstance(data, list):
                    for station in data:
                        name = str(station.get("station_name") or station.get("city") or "").lower()
                        if "hanamkonda" in name or "warangal" in name:
                            days = station.get("forecast") or []
                            return pd.DataFrame([{
                                "Date": d.get("date", "N/A"),
                                "Max Temp (°C)": d.get("max_temp", "N/A"),
                                "Min Temp (°C)": d.get("min_temp", "N/A"),
                                "Condition": d.get("weather_description", "Clear")
                            } for d in days[:7]])
    except Exception:
        pass
    return None

# --- SECTION 1: SOLAR GENERATION FORECASTS ---
st.subheader("☀️ Solar Generation Forecast Matrix")
sol_vst, sol_st = st.columns(2)

with sol_vst:
    st.markdown("##### ⏱️ Very Short-Term Prediction (T + 1 min)")
    m1, m2 = st.columns(2)
    
    # Calculate simple dynamic response to scenario builder sliders
    simulated_power = round(72.18 * (0.8 if cloud_cover == "Overcast" else 1.0), 2)
    m1.metric(label="Predicted Solar Power", value=f"{simulated_power} kW", delta="+0.17 kW")
    m2.metric(label="95% CI Range", value=f"{simulated_power-0.2:.2f} - {simulated_power+0.2:.2f} kW")

with sol_st:
    st.markdown("##### 📅 Short-Term Forecast (Week Ahead)")
    m1, m2 = st.columns(2)
    m1.metric(label="Est. 7-Day Solar Yield", value="637.8 kWh", delta="+12 kWh")
    m2.metric(label="Peak Solar Window", value="06:30 – 18:15 IST")

# Display Forecast Data Table
imd_df = fetch_imd_7day_forecast()
if imd_df is not None and not imd_df.empty:
    st.dataframe(imd_df, use_container_width=True, hide_index=True)
else:
    solar_week_df = pd.DataFrame({
        "Day": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
        "Est. Peak (kW)": [38.2, 38.8, 37.5, 39.1, 38.0, 36.4, 37.9],
        "Est. Energy (kWh)": [91.5, 93.0, 89.2, 94.1, 91.0, 87.2, 91.8],
        "Max Temp (°C)": [34.5 + temp_offset, 35.0 + temp_offset, 33.2 + temp_offset, 35.8 + temp_offset, 34.1 + temp_offset, 31.8 + temp_offset, 34.0 + temp_offset],
        "Min Temp (°C)": [24.1, 24.5, 23.8, 25.0, 24.2, 23.0, 23.9]
    })
    st.dataframe(solar_week_df, use_container_width=True, hide_index=True)

st.divider()

# --- SECTION 2: TOTAL CAMPUS LOAD FORECASTS ---
st.subheader("⚡ Total Campus Demand Forecast Matrix")
load_vst, load_st = st.columns(2)

with load_vst:
    st.markdown("##### ⏱️ Very Short-Term Prediction (T + 1 min)")
    m1, m2 = st.columns(2)
    
    # Adjust load metric dynamically based on temperature offset
    simulated_load = round(1244.5 + (temp_offset * 12.5), 1)
    m1.metric(label="Predicted Load", value=f"{simulated_load:,} kW", delta=f"{temp_offset * 12.5:+.1f} kW (HVAC load shift)")
    m2.metric(label="95% CI Range", value=f"{simulated_load-6:.0f} - {simulated_load+6:.0f} kW")

with load_st:
    st.markdown("##### 📅 Short-Term Forecast (Week Ahead)")
    m1, m2 = st.columns(2)
    m1.metric(label="Est. 7-Day Consumption", value="129.6 MWh", delta="-1.4 MWh")
    m2.metric(label="Projected Peak Demand", value="1,385 kW")

load_week_df = pd.DataFrame({
    "Day": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
    "Peak Demand (kW)": [1385, 1370, 1365, 1380, 1350, 1020, 980],
    "Total Load (MWh)": [19.2, 19.0, 18.9, 19.1, 18.7, 12.8, 11.9],
    "Day Type": ["Weekday", "Weekday", "Weekday", "Weekday", "Weekday", "Saturday", "Sunday"]
})
st.dataframe(load_week_df, use_container_width=True, hide_index=True)

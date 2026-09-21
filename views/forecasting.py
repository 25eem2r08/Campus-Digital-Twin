import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# Timezone support (Python 3.9+)
try:
    from zoneinfo import ZoneInfo
    IST = ZoneInfo("Asia/Kolkata")
except ImportError:
    import pytz
    IST = pytz.timezone("Asia/Kolkata")

st.title("📈 Energy Demand & Generation Forecasting")

# --- LIVE DATE & TIME FRAGMENT ---
@st.fragment(run_every="1s")
def render_live_clock():
    current_time = datetime.now(IST)
    formatted_date = current_time.strftime("%A, %d %B %Y")
    formatted_time = current_time.strftime("%H:%M:%S IST")
    
    time_col1, time_col2 = st.columns(2)
    with time_col1:
        st.markdown(f"📅 **System Date:** `{formatted_date}`")
    with time_col2:
        st.markdown(f"🕒 **Live System Time:** `{formatted_time}`")

render_live_clock()
st.divider()

# --- FORECAST HORIZON SELECTION ---
horizon = st.radio(
    "**Select Forecast Horizon:**",
    ["Next 24 Hours", "Next 7 Days"],
    horizontal=True
)

st.divider()

# --- FORECAST DISPLAY LOGIC ---
if horizon == "Next 24 Hours":
    # Top KPI Metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Predicted Total Consumption", "19,250 kWh", "+3.9% vs Today")
    with col2:
        st.metric("Expected Peak Demand", "1,310 kW", "At 14:00 IST")
    with col3:
        st.metric("Predicted Solar Yield", "105.4 kWh", "+15.6% vs Today")
    with col4:
        st.metric("Forecast Accuracy Rate", "96.4%", "High Confidence")

    st.divider()

    # 24-Hour Demand & Solar Curves
    st.subheader("⚡ 24-Hour Load Demand & Solar Generation Forecast")
    
    hours = [(datetime.now(IST) + timedelta(hours=i)).strftime("%H:00") for i in range(24)]
    load_forecast = [45, 42, 40, 38, 41, 55, 78, 110, 135, 140, 138, 142, 145, 141, 130, 122, 115, 98, 85, 72, 65, 58, 52, 48]
    solar_forecast = [0, 0, 0, 0, 0, 2, 8, 18, 28, 34, 38, 36, 32, 25, 15, 6, 1, 0, 0, 0, 0, 0, 0, 0]

    df_24h = pd.DataFrame({
        "Hour": hours,
        "Demand Forecast (kW)": load_forecast,
        "Solar Generation Forecast (kW)": solar_forecast
    }).set_index("Hour")

    st.line_chart(df_24h, height=350)

    st.subheader("📋 Hourly Forecast Breakdown Data")
    st.dataframe(df_24h, use_container_width=True)

else:
    # 7-Day Top KPI Metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("7-Day Projected Load", "134,750 kWh")
    with col2:
        st.metric("Average Daily Peak", "1,285 kW")
    with col3:
        st.metric("7-Day Solar Generation Yield", "728.0 kWh")
    with col4:
        st.metric("Forecast Reliability", "95.8%")

    st.divider()

    # 7-Day Trend Charts
    st.subheader("📆 7-Day Energy Outlook")
    
    days = [(datetime.now(IST) + timedelta(days=i)).strftime("%a (%b %d)") for i in range(7)]
    load_7d = [19250, 18900, 19500, 19100, 19800, 18400, 17800]
    solar_7d = [105.4, 98.2, 112.0, 108.5, 95.0, 102.3, 106.6]

    df_7d = pd.DataFrame({
        "Day": days,
        "Projected Consumption (kWh)": load_7d,
        "Projected Solar Yield (kWh)": solar_7d
    }).set_index("Day")

    st.bar_chart(df_7d, height=350)

    st.subheader("📋 7-Day Summary Data Table")
    st.dataframe(df_7d, use_container_width=True)

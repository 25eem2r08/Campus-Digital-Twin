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

st.title("📈 Real Power Demand & Generation Forecasting")

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
    ["24-Hour Predicted vs Actual Real Power", "7-Day Peak Real Power Outlook"],
    horizontal=True
)

st.divider()

# --- FORECAST VS ACTUAL DISPLAY LOGIC ---
if horizon == "24-Hour Predicted vs Actual Real Power":
    # Top KPI Metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Predicted Peak Real Power", "145.00 kW", delta="At 13:00 IST")
    with col2:
        st.metric("Actual Peak Real Power", "143.00 kW", delta="-1.38% Variance")
    with col3:
        st.metric("Predicted Peak Solar Power", "38.00 kW", delta="At 10:00 IST")
    with col4:
        st.metric("Forecast Accuracy", "96.4%", delta="High Precision")

    st.divider()

    # 24-Hour Overlay Chart: Predicted vs Actual Load Real Power
    st.subheader("⚡ 24-Hour Load Feeder Real Power: Predicted vs Actual (kW)")
    
    hours = [f"{h:02d}:00" for h in range(24)]
    
    # Real power curves in kW
    pred_demand = [45.0, 42.0, 40.0, 38.0, 41.0, 55.0, 78.0, 110.0, 135.0, 140.0, 138.0, 142.0, 145.0, 141.0, 130.0, 122.0, 115.0, 98.0, 85.0, 72.0, 65.0, 58.0, 52.0, 48.0]
    actual_demand = [43.0, 41.0, 39.0, 38.0, 42.0, 53.0, 75.0, 108.0, 132.0, 138.0, 135.0, 140.0, 143.0, 139.0, 128.0, 120.0, None, None, None, None, None, None, None, None]

    df_24h_demand = pd.DataFrame({
        "Hour": hours,
        "Predicted Real Power (kW)": pred_demand,
        "Actual Real Power (kW)": actual_demand
    }).set_index("Hour")

    st.line_chart(df_24h_demand, height=350)

    st.divider()

    # 24-Hour Overlay Chart: Predicted vs Actual Solar Real Power
    st.subheader("☀️ 24-Hour Solar Real Power: Predicted vs Actual (kW)")
    
    pred_solar = [0.0, 0.0, 0.0, 0.0, 0.0, 2.0, 8.0, 18.0, 28.0, 34.0, 38.0, 36.0, 32.0, 25.0, 15.0, 6.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    actual_solar = [0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 7.0, 16.0, 26.0, 33.0, 37.0, 34.0, 30.0, 23.0, 14.0, 5.0, None, None, None, None, None, None, None, None]

    df_24h_solar = pd.DataFrame({
        "Hour": hours,
        "Predicted Solar Power (kW)": pred_solar,
        "Actual Solar Power (kW)": actual_solar
    }).set_index("Hour")

    st.line_chart(df_24h_solar, height=300)

    # Data Table Breakdown
    st.subheader("📋 24-Hour Real Power Comparison Table (kW)")
    df_combined = pd.DataFrame({
        "Hour": hours,
        "Predicted Load Power (kW)": pred_demand,
        "Actual Load Power (kW)": actual_demand,
        "Predicted Solar Power (kW)": pred_solar,
        "Actual Solar Power (kW)": actual_solar
    })
    st.dataframe(df_combined, use_container_width=True, hide_index=True)

else:
    # 7-Day Top KPI Metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Avg Projected Peak Power", "142.5 kW")
    with col2:
        st.metric("Avg Actual Peak Power", "139.8 kW")
    with col3:
        st.metric("Peak Power Variance", "-1.89%")
    with col4:
        st.metric("7-Day Model Reliability", "95.8%")

    st.divider()

    # 7-Day Peak Real Power Overlay Chart
    st.subheader("📆 7-Day Peak Load Real Power: Predicted vs Actual (kW)")
    
    days = [(datetime.now(IST) - timedelta(days=3-i)).strftime("%a (%b %d)") for i in range(7)]
    pred_7d_peak = [140.0, 142.0, 145.0, 145.0, 148.0, 138.0, 135.0]
    actual_7d_peak = [138.0, 140.0, 143.0, 143.0, None, None, None]

    df_7d_peak = pd.DataFrame({
        "Day": days,
        "Predicted Peak Power (kW)": pred_7d_peak,
        "Actual Peak Power (kW)": actual_7d_peak
    }).set_index("Day")

    st.line_chart(df_7d_peak, height=350)

    st.divider()

    # 7-Day Peak Solar Power Comparison
    st.subheader("☀️ 7-Day Solar Peak Real Power: Predicted vs Actual (kW)")
    
    pred_solar_7d_peak = [38.0, 36.0, 39.0, 38.0, 35.0, 37.0, 38.0]
    actual_solar_7d_peak = [37.0, 35.0, 38.0, 37.0, None, None, None]

    df_7d_solar = pd.DataFrame({
        "Day": days,
        "Predicted Solar Peak (kW)": pred_solar_7d_peak,
        "Actual Solar Peak (kW)": actual_solar_7d_peak
    }).set_index("Day")

    st.bar_chart(df_7d_solar, height=320)

    st.subheader("📋 7-Day Real Power Comparison Table (kW)")
    df_7d_combined = pd.DataFrame({
        "Day": days,
        "Predicted Peak Load (kW)": pred_7d_peak,
        "Actual Peak Load (kW)": actual_7d_peak,
        "Predicted Peak Solar (kW)": pred_solar_7d_peak,
        "Actual Peak Solar (kW)": actual_solar_7d_peak
    })
    st.dataframe(df_7d_combined, use_container_width=True, hide_index=True)

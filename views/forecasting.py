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
    ["24-Hour Predicted vs Actual", "7-Day Predicted vs Actual"],
    horizontal=True
)

st.divider()

# --- FORECAST VS ACTUAL DISPLAY LOGIC ---
if horizon == "24-Hour Predicted vs Actual":
    # Top KPI Metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Predicted Load Today", "19,250 kWh", delta="Target")
    with col2:
        st.metric("Actual Load Today", "18,520 kWh", delta="-3.79% Variance")
    with col3:
        st.metric("Model MAPE (Error Rate)", "3.6%", delta="High Precision")
    with col4:
        st.metric("Forecast Accuracy", "96.4%")

    st.divider()

    # 24-Hour Overlay Chart: Predicted vs Actual Demand
    st.subheader("⚡ 24-Hour Load Demand: Predicted vs Actual Output (kW)")
    
    hours = [f"{h:02d}:00" for h in range(24)]
    
    # 24-Hour curves (Actual available up to current hour, e.g., 15:00 IST)
    pred_demand = [45, 42, 40, 38, 41, 55, 78, 110, 135, 140, 138, 142, 145, 141, 130, 122, 115, 98, 85, 72, 65, 58, 52, 48]
    actual_demand = [43, 41, 39, 38, 42, 53, 75, 108, 132, 138, 135, 140, 143, 139, 128, 120, None, None, None, None, None, None, None, None]

    df_24h_demand = pd.DataFrame({
        "Hour": hours,
        "Predicted Demand (kW)": pred_demand,
        "Actual Demand (kW)": actual_demand
    }).set_index("Hour")

    st.line_chart(df_24h_demand, height=350)

    st.divider()

    # 24-Hour Overlay Chart: Predicted vs Actual Solar
    st.subheader("☀️ 24-Hour Solar Generation: Predicted vs Actual Output (kW)")
    
    pred_solar = [0, 0, 0, 0, 0, 2, 8, 18, 28, 34, 38, 36, 32, 25, 15, 6, 1, 0, 0, 0, 0, 0, 0, 0]
    actual_solar = [0, 0, 0, 0, 0, 1, 7, 16, 26, 33, 37, 34, 30, 23, 14, 5, None, None, None, None, None, None, None, None]

    df_24h_solar = pd.DataFrame({
        "Hour": hours,
        "Predicted Solar (kW)": pred_solar,
        "Actual Solar (kW)": actual_solar
    }).set_index("Hour")

    st.line_chart(df_24h_solar, height=300)

    # Data Table Breakdown
    st.subheader("📋 24-Hour Detailed Comparison Table")
    df_combined = pd.DataFrame({
        "Hour": hours,
        "Predicted Demand (kW)": pred_demand,
        "Actual Demand (kW)": actual_demand,
        "Predicted Solar (kW)": pred_solar,
        "Actual Solar (kW)": actual_solar
    })
    st.dataframe(df_combined, use_container_width=True, hide_index=True)

else:
    # 7-Day Top KPI Metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("7-Day Projected Load", "134,750 kWh")
    with col2:
        st.metric("7-Day Actual Load (Past)", "131,200 kWh")
    with col3:
        st.metric("Total Consumption Variance", "-2.6%")
    with col4:
        st.metric("7-Day Model Reliability", "95.8%")

    st.divider()

    # 7-Day Trend Overlay Chart
    st.subheader("📆 7-Day Load Energy: Predicted vs Actual Output (kWh)")
    
    days = [(datetime.now(IST) - timedelta(days=3-i)).strftime("%a (%b %d)") for i in range(7)]
    pred_7d = [18800, 19100, 19500, 19250, 19800, 18400, 17800]
    actual_7d = [18650, 18950, 19300, 18520, None, None, None]

    df_7d = pd.DataFrame({
        "Day": days,
        "Predicted Load (kWh)": pred_7d,
        "Actual Load (kWh)": actual_7d
    }).set_index("Day")

    st.line_chart(df_7d, height=350)

    st.divider()

    # 7-Day Solar Generation Comparison
    st.subheader("☀️ 7-Day Solar Yield: Predicted vs Actual Output (kWh)")
    
    pred_solar_7d = [102.0, 98.5, 105.0, 105.4, 95.0, 102.3, 106.6]
    actual_solar_7d = [100.2, 96.8, 103.5, 91.1, None, None, None]

    df_7d_solar = pd.DataFrame({
        "Day": days,
        "Predicted Solar (kWh)": pred_solar_7d,
        "Actual Solar (kWh)": actual_solar_7d
    }).set_index("Day")

    st.bar_chart(df_7d_solar, height=320)

    st.subheader("📋 7-Day Comparison Table")
    df_7d_combined = pd.DataFrame({
        "Day": days,
        "Predicted Load (kWh)": pred_7d,
        "Actual Load (kWh)": actual_7d,
        "Predicted Solar (kWh)": pred_solar_7d,
        "Actual Solar (kWh)": actual_solar_7d
    })
    st.dataframe(df_7d_combined, use_container_width=True, hide_index=True)

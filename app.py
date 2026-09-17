import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import streamlit.components.v1 as components

# --- Page configuration ---
st.set_page_config(
    page_title="Campus Digital Twin",
    page_icon="🏛️",
    layout="wide"
)

st.title("🏛️ Campus Digital Twin: Electrical & Energy Analytics")

# --- LIVE DATE & TIME FRAGMENT (Updates every second independently) ---
@st.fragment(run_every="1s")
def render_live_clock():
    current_time = datetime.now()
    formatted_date = current_time.strftime("%A, %d %B %Y")
    formatted_time = current_time.strftime("%H:%M:%S IST")
    
    time_col1, time_col2 = st.columns(2)
    with time_col1:
        st.markdown(f"📅 **System Date:** `{formatted_date}`")
    with time_col2:
        st.markdown(f"🕒 **Live System Time:** `{formatted_time}`")

render_live_clock()

st.divider()

# --- SIDEBAR: GOOGLE CALENDAR ---
with st.sidebar:
    st.header("📅 Campus Calendar")
    selected_date = st.date_input("Select Date", datetime.now())
    
    st.subheader("📆 Google Calendar Integration")
    st.caption("Embedded Campus Maintenance & Load Shift Schedule")
    
    calendar_embed_url = (
        "https://calendar.google.com/calendar/embed?"
        "height=300&wkst=1&ctz=Asia%2FKolkata&showTitle=0&showNav=1&showDate=1"
        "&showPrint=0&showTabs=0&showCalendars=0&showTz=0&mode=AGENDA"
    )
    components.iframe(calendar_embed_url, height=320, scrolling=True)

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

# --- SECTION 4: FORECASTING MATRIX ---
st.header("🔮 Energy Forecasting Digital Twin")

# ROW 1: SOLAR GENERATION FORECASTS
st.subheader("☀️ Solar Generation Forecasts")
sol_vst, sol_st = st.columns(2)

with sol_vst:
    st.info("⏱️ **Very Short-Term Prediction (Next Minute)**")
    
    m1, m2 = st.columns(2)
    m1.metric(label="Predicted Power (T + 1 min)", value="72.18 kW", delta="+0.17 kW (+0.24%)")
    m2.metric(label="95% CI Range", value="71.95 - 72.40 kW")

with sol_st:
    st.success("📅 **Short-Term Forecast (Week Ahead)**")
    
    m1, m2 = st.columns(2)
    m1.metric(label="Est. 7-Day Generation", value="637.8 kWh", delta="+12 kWh vs prior week")
    m2.metric(label="Daily Solar Window", value="06:30 – 18:15 IST")
    
    solar_week_df = pd.DataFrame({
        "Day": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
        "Est. Peak (kW)": [38.2, 38.8, 37.5, 39.1, 38.0, 36.4, 37.9],
        "Est. Energy (kWh)": [91.5, 93.0, 89.2, 94.1, 91.0, 87.2, 91.8],
        "Max Temp (°C)": [34.5, 35.0, 33.2, 35.8, 34.1, 31.8, 34.0],
        "Min Temp (°C)": [24.1, 24.5, 23.8, 25.0, 24.2, 23.0, 23.9]
    })
    st.dataframe(solar_week_df, use_container_width=True, hide_index=True)

st.divider()

# ROW 2: CAMPUS LOAD FORECASTS
st.subheader("⚡ Total Campus Load Forecasts")
load_vst, load_st = st.columns(2)

with load_vst:
    st.info("⏱️ **Very Short-Term Prediction (Next Minute)**")
    
    m1, m2 = st.columns(2)
    m1.metric(label="Predicted Load (T + 1 min)", value="1,244.5 kW", delta="+3.5 kW (+0.28%)")
    m2.metric(label="95% CI Range", value="1,238 - 1,251 kW")

with load_st:
    st.success("📅 **Short-Term Forecast (Week Ahead)**")
    
    m1, m2 = st.columns(2)
    m1.metric(label="Est. 7-Day Consumption", value="129.6 MWh", delta="-1.4 MWh vs prior week")
    m2.metric(label="Projected Peak Demand", value="1,385 kW")
    
    load_week_df = pd.DataFrame({
        "Day": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
        "Peak Demand (kW)": [1385, 1370, 1365, 1380, 1350, 1020, 980],
        "Total Load (MWh)": [19.2, 19.0, 18.9, 19.1, 18.7, 12.8, 11.9],
        "Day Type": ["Weekday", "Weekday", "Weekday", "Weekday", "Weekday", "Saturday", "Sunday"]
    })
    st.dataframe(load_week_df, use_container_width=True, hide_index=True)

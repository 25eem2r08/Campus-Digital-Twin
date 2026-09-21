import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import streamlit.components.v1 as components

# Timezone support (Python 3.9+)
try:
    from zoneinfo import ZoneInfo
    IST = ZoneInfo("Asia/Kolkata")
except ImportError:
    import pytz
    IST = pytz.timezone("Asia/Kolkata")

st.title("📡 Real-Time Operations & Electrical Telemetry")

# --- LIVE DATE & TIME FRAGMENT (Updates every second in IST) ---
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

# --- SIDEBAR CONTROLS ---
with st.sidebar:
    st.header("📅 Campus Calendar")
    selected_date = st.date_input("Select Date", datetime.now(IST))
    
    st.subheader("📆 Google Calendar Integration")
    st.caption("Embedded Campus Maintenance & Load Shift Schedule")
    
    calendar_embed_url = (
        "https://calendar.google.com/calendar/embed?"
        "height=300&wkst=1&ctz=Asia%2FKolkata&showTitle=0&showNav=1&showDate=1"
        "&showPrint=0&showTabs=0&showCalendars=0&showTz=0&mode=AGENDA"
    )
    components.iframe(calendar_embed_url, height=320, scrolling=True)

# --- IMD WEATHER API FUNCTIONS ---
@st.cache_data(ttl=3480)
def get_imd_jwt_token():
    auth_url = "https://api.imd.gov.in/api/oauth/token.php"
    email = st.secrets.get("IMD_EMAIL", "")
    password = st.secrets.get("IMD_PASSWORD", "")
    
    if not email or not password:
        return None
    
    payload = {"email": email, "password": password}
    headers = {"Content-Type": "application/json"}
    
    try:
        response = requests.post(auth_url, json=payload, headers=headers, timeout=5)
        if response.status_code == 200:
            return response.json().get("access_token")
    except Exception:
        return None
    return None

@st.cache_data(ttl=3600)
def fetch_imd_weather():
    api_key = st.secrets.get("IMD_API_KEY", "")
    jwt_token = get_imd_jwt_token()
    
    if not api_key or not jwt_token:
        return {"temp": 32.5, "humidity": 55, "desc": "Partly Cloudy (Fallback)", "icon": "⛅"}
    
    url = "https://api.imd.gov.in/api/v1/cityforecast"
    headers = {
        "X-API-KEY": api_key,
        "Authorization": f"Bearer {jwt_token}"
    }
    
    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            data = res.json()
            target_station = None
            if isinstance(data, list):
                for station in data:
                    name = str(station.get("station_name") or station.get("City_Name") or station.get("city") or "").lower()
                    if "hanamkonda" in name or "warangal" in name:
                        target_station = station
                        break
            
            if target_station:
                temp = target_station.get("max_temp") or target_station.get("temp") or 32.5
                humidity = target_station.get("humidity") or 55
                desc = target_station.get("weather_description") or target_station.get("forecast") or "IMD Live Feed"
                
                return {
                    "temp": float(temp),
                    "humidity": int(humidity),
                    "desc": str(desc).title(),
                    "icon": "🏛️"
                }
    except Exception:
        pass
        
    return {"temp": 32.5, "humidity": 55, "desc": "Partly Cloudy (Fallback)", "icon": "⛅"}

# --- WEATHER DISPLAY ---
st.subheader("🌦️ Live Campus Weather (Hanamkonda - IMD Feed)")
weather_data = fetch_imd_weather()

w_col1, w_col2, w_col3 = st.columns(3)
with w_col1:
    st.metric(label="Temperature", value=f"{weather_data['temp']} °C")
with w_col2:
    st.metric(label="Humidity", value=f"{weather_data['humidity']} %")
with w_col3:
    st.metric(label="Data Source", value=f"{weather_data['icon']} {weather_data['desc']}")

st.divider()

# --- TOP OPERATIONAL KPI CARDS ---
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

# --- REAL-TIME TELEMETRY DATA TABLE ---
st.subheader("Real Time Data - Complete Feeder Network")

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
    "Real Energy Into the Load (kWh)": [78165.03, 88867.56, 11904.58, 74001.94, 239076.54, 11502.40, 31711.39, 66131.13]
}

st.dataframe(pd.DataFrame(real_time_data), use_container_width=True, hide_index=True)

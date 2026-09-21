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

st.title("📡 Real-Time Operational Telemetry")

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

# --- SIDEBAR: DASHBOARD LIBRARY MENU & CALENDAR ---
DASHBOARD_PAGES = [
    "1. Real Time Data",
    "3. EED Research Wing-Solar",
    "4. EED Research Wing-Incomer-1",
    "5. EED Research Wing-Incomer-2",
    "6. EED Solar",
    "7. EED Incomer-1",
    "8. EED Incomer-2",
    "9. EED Load Feeder",
    "10. Civil Load Feeder",
    "Consumption & Generation"
]

with st.sidebar:
    st.header("📂 Dashboard Library")
    selected_view = st.radio(
        "Select Feeder or View:",
        DASHBOARD_PAGES,
        index=0
    )
    
    st.divider()
    st.subheader("📆 Campus Calendar")
    calendar_embed_url = (
        "https://calendar.google.com/calendar/embed?"
        "height=300&wkst=1&ctz=Asia%2FKolkata&showTitle=0&showNav=1&showDate=1"
        "&showPrint=0&showTabs=0&showCalendars=0&showTz=0&mode=AGENDA"
    )
    components.iframe(calendar_embed_url, height=280, scrolling=True)

# --- IMD WEATHER API FUNCTIONS ---
@st.cache_data(ttl=3480)
def get_imd_jwt_token():
    auth_url = "https://api.imd.gov.in/api/oauth/token.php"
    email = st.secrets.get("IMD_EMAIL", "")
    password = st.secrets.get("IMD_PASSWORD", "")
    if not email or not password:
        return None
    try:
        res = requests.post(auth_url, json={"email": email, "password": password}, headers={"Content-Type": "application/json"}, timeout=5)
        if res.status_code == 200:
            return res.json().get("access_token")
    except Exception:
        return None
    return None

@st.cache_data(ttl=3600)
def fetch_imd_weather():
    api_key = st.secrets.get("IMD_API_KEY", "")
    jwt_token = get_imd_jwt_token()
    if not api_key or not jwt_token:
        return {"temp": 32.5, "humidity": 55, "desc": "Partly Cloudy (Fallback)", "icon": "⛅"}
    
    try:
        res = requests.get("https://api.imd.gov.in/api/v1/cityforecast", headers={"X-API-KEY": api_key, "Authorization": f"Bearer {jwt_token}"}, timeout=10)
        if res.status_code == 200:
            data = res.json()
            if isinstance(data, list):
                for station in data:
                    name = str(station.get("station_name") or station.get("city") or "").lower()
                    if "hanamkonda" in name or "warangal" in name:
                        return {
                            "temp": float(station.get("max_temp") or 32.5),
                            "humidity": int(station.get("humidity") or 55),
                            "desc": str(station.get("weather_description") or "IMD Live Feed").title(),
                            "icon": "🏛️"
                        }
    except Exception:
        pass
    return {"temp": 32.5, "humidity": 55, "desc": "Partly Cloudy (Fallback)", "icon": "⛅"}

# --- VIEW ROUTING ---

# ----------------------------------------------------
# OPTION 1: ALL FEEDERS REAL TIME DATA OVERVIEW
# ----------------------------------------------------
if selected_view == "1. Real Time Data":
    weather_data = fetch_imd_weather()
    w_col1, w_col2, w_col3 = st.columns(3)
    with w_col1: st.metric("Temperature", f"{weather_data['temp']} °C")
    with w_col2: st.metric("Humidity", f"{weather_data['humidity']} %")
    with w_col3: st.metric("Data Source", f"{weather_data['icon']} {weather_data['desc']}")

    st.divider()

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown("### ⚡ Total Consumption")
        st.metric("(kWh) - Today", "18,520")
    with col2:
        st.markdown("### 🔌 Consumption Sum")
        st.metric("(kW) - Real Power", "1,241.00")
    with col3:
        st.markdown("### ☀️ Total Generation")
        st.metric("(kWh) - Today", "91.13")
    with col4:
        st.markdown("### 🔋 Generation Sum")
        st.metric("(kW) - Real Power", "72.01")

    st.divider()

    st.subheader("Real Time Data — All Feeders")
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

# ----------------------------------------------------
# OPTION: CONSUMPTION & GENERATION
# ----------------------------------------------------
elif selected_view == "Consumption & Generation":
    st.subheader("⚖️ Power Balance & Feeder Breakdown")
    c_data = pd.DataFrame({
        "Load Feeder": ["Civil Feeder", "EED Incomer 1", "EED Incomer 2", "EED Load Feeder"],
        "Power (kW)": [12.88, 30.00, 2.93, 10.96]
    })
    g_data = pd.DataFrame({
        "Solar Source": ["EED Research Wing Solar", "EED Main Solar"],
        "Power (kW)": [38.87, 34.26]
    })
    c1, c2 = st.columns(2)
    with c1: 
        st.markdown("##### 🔌 Active Consumption (kW)")
        st.dataframe(c_data, use_container_width=True, hide_index=True)
    with c2: 
        st.markdown("##### ☀️ Active Generation (kW)")
        st.dataframe(g_data, use_container_width=True, hide_index=True)

# ----------------------------------------------------
# INDIVIDUAL FEEDER DASHBOARDS
# ----------------------------------------------------
else:
    feeder_name = selected_view.split(". ", 1)[-1]
    is_solar = "Solar" in feeder_name

    # Feeder metadata simulation
    if "Research Wing-Solar" in feeder_name:
        kwh_val, cost_val = "100.34", "315.08"
        kw_curve = [0, 0, 0, 0, 0, 0, 4, 11, 22, 25, 33, 25]
    elif "EED Solar" in feeder_name:
        kwh_val, cost_val = "91.13", "286.10"
        kw_curve = [0, 0, 0, 0, 0, 0, 3, 9, 18, 22, 34, 28]
    elif "Civil Load" in feeder_name:
        kwh_val, cost_val = "112.50", "900.00"
        kw_curve = [4, 4, 3, 3, 4, 6, 8, 12, 14, 13, 12, 11]
    else:
        kwh_val, cost_val = "240.00", "1,920.00"
        kw_curve = [10, 9, 8, 8, 12, 18, 24, 30, 28, 27, 29, 26]

    # TOP ROW: 3 CARDS
    top_col1, top_col2, top_col3 = st.columns([1, 1, 1.5])

    with top_col1:
        st.markdown(f"### {'Generation' if is_solar else 'Consumption'} (KWH)")
        st.caption("21-09-2026 00:00 - 11:17")
        st.markdown(f"## ☀️ **{kwh_val}**" if is_solar else f"## ⚡ **{kwh_val}**")

    with top_col2:
        st.markdown("### Cost")
        st.caption("21-09-2026 00:00 - 11:17")
        st.markdown(f"## **₹ {cost_val}**")

    with top_col3:
        st.markdown("### kw")
        st.caption("21-09-2026 00:00 - 11:17 (India Standard Time)")
        time_labels = ["01:00", "02:00", "03:00", "04:00", "05:00", "06:00", "07:00", "08:00", "09:00", "10:00", "11:00", "12:00"]
        kw_df = pd.DataFrame({"Hour": time_labels, f"{feeder_name} Real Power (kW)": kw_curve}).set_index("Hour")
        st.line_chart(kw_df, height=180)

    st.divider()

    # BOTTOM ROW: YESTERDAY VS TODAY COMPARISON BAR CHART
    st.markdown(f"### {'Generation' if is_solar else 'Consumption'} Comparison (KWH)")
    st.caption("20-09-2026 - 11:17 (India Standard Time)")

    hours_full = [f"{h:02d}:00" for h in range(24)]
    if is_solar:
        yesterday_vals = [0, 0, 0, 0, 0, 0, 2, 13, 13, 25, 31, 28, 9, 21, 35, 32, 22, 12, 3, 0, 0, 0, 0, 0]
        today_vals =     [0, 0, 0, 0, 0, 0, 3, 10, 21, 26, 31, 0,  0, 0,  0,  0,  0,  0,  0, 0, 0, 0, 0, 0]
    else:
        yesterday_vals = [5, 4, 4, 3, 5, 8, 12, 15, 18, 20, 22, 21, 19, 20, 22, 21, 18, 15, 12, 10, 8, 7, 6, 5]
        today_vals =     [4, 4, 3, 3, 4, 6, 10, 14, 16, 18, 21, 0,  0,  0,  0,  0,  0,  0,  0,  0, 0, 0, 0, 0]

    comp_df = pd.DataFrame({
        "Hour": hours_full,
        "Yesterday": yesterday_vals,
        "Today": today_vals
    }).set_index("Hour")

    st.bar_chart(comp_df, height=320, use_container_width=True)

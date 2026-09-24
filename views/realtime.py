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

# --- SIDEBAR: CAMPUS CALENDAR ---
with st.sidebar:
    st.header("📆 Campus Calendar")
    st.caption("Embedded Campus Maintenance & Load Schedule")
    calendar_embed_url = (
        "https://calendar.google.com/calendar/embed?"
        "height=320&wkst=1&ctz=Asia%2FKolkata&showTitle=0&showNav=1&showDate=1"
        "&showPrint=0&showTabs=0&showCalendars=0&showTz=0&mode=AGENDA"
    )
    components.iframe(calendar_embed_url, height=350, scrolling=True)

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

# --- IMD WEATHER API FUNCTIONS ---
from weather import render_weather_panel

sunrise, sunset = render_weather_panel()

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

# --- SECTION 1: ALL FEEDERS REAL TIME DATA TABLE ---
st.subheader("📊 Real Time Data — All Feeder Network")

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

st.divider()

# --- SECTION 2: INDIVIDUAL FEEDER DETAILED ANALYTICS (TABBED SINGLE PAGE) ---
st.subheader("⚡ Individual Feeder Analytics & Comparisons")

feeders_list = [
    "EED Research Wing Solar",
    "EED Research Wing Incomer 1",
    "EED Research Wing Incomer 2",
    "EED Solar",
    "EED Incomer 1",
    "EED Incomer 2",
    "EED Load Feeder",
    "Civil Load Feeder"
]

tabs = st.tabs(feeders_list)

def render_feeder_dashboard(feeder_name, is_solar, kwh_val, cost_val, kw_curve, yesterday_vals, today_vals):
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

    st.markdown(f"### {'Generation' if is_solar else 'Consumption'} Comparison (KWH)")
    st.caption("20-09-2026 - 11:17 (India Standard Time)")
    hours_full = [f"{h:02d}:00" for h in range(24)]
    comp_df = pd.DataFrame({
        "Hour": hours_full,
        "Yesterday": yesterday_vals,
        "Today": today_vals
    }).set_index("Hour")
    st.bar_chart(comp_df, height=300, use_container_width=True)

# Common hourly mock curves for rendering
solar_yesterday = [0, 0, 0, 0, 0, 0, 2, 13, 13, 25, 31, 28, 9, 21, 35, 32, 22, 12, 3, 0, 0, 0, 0, 0]
solar_today =     [0, 0, 0, 0, 0, 0, 3, 10, 21, 26, 31, 0,  0, 0,  0,  0,  0,  0,  0, 0, 0, 0, 0, 0]
load_yesterday =  [5, 4, 4, 3, 5, 8, 12, 15, 18, 20, 22, 21, 19, 20, 22, 21, 18, 15, 12, 10, 8, 7, 6, 5]
load_today =      [4, 4, 3, 3, 4, 6, 10, 14, 16, 18, 21, 0,  0,  0,  0,  0,  0,  0,  0,  0, 0, 0, 0, 0]

with tabs[0]:
    render_feeder_dashboard("EED Research Wing Solar", True, "100.34", "315.08", [0, 0, 0, 0, 0, 0, 4, 11, 22, 25, 33, 25], solar_yesterday, solar_today)

with tabs[1]:
    render_feeder_dashboard("EED Research Wing Incomer 1", False, "210.15", "1,681.20", [8, 8, 7, 7, 10, 15, 20, 26, 25, 24, 27, 22], load_yesterday, load_today)

with tabs[2]:
    render_feeder_dashboard("EED Research Wing Incomer 2", False, "19.50", "156.00", [1, 1, 1, 1, 2, 2, 3, 3, 2, 2, 3, 2], load_yesterday, load_today)

with tabs[3]:
    render_feeder_dashboard("EED Solar", True, "91.13", "286.10", [0, 0, 0, 0, 0, 0, 3, 9, 18, 22, 34, 28], solar_yesterday, solar_today)

with tabs[4]:
    render_feeder_dashboard("EED Incomer 1", False, "240.00", "1,920.00", [10, 9, 8, 8, 12, 18, 24, 30, 28, 27, 29, 26], load_yesterday, load_today)

with tabs[5]:
    render_feeder_dashboard("EED Incomer 2", False, "23.40", "187.20", [1, 1, 1, 1, 2, 3, 4, 5, 4, 3, 3, 3], load_yesterday, load_today)

with tabs[6]:
    render_feeder_dashboard("EED Load Feeder", False, "95.40", "763.20", [3, 3, 2, 2, 4, 6, 8, 11, 10, 10, 11, 9], load_yesterday, load_today)

with tabs[7]:
    render_feeder_dashboard("Civil Load Feeder", False, "112.50", "900.00", [4, 4, 3, 3, 4, 6, 8, 12, 14, 13, 12, 11], load_yesterday, load_today)

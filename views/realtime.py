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
"""
Weather data layer for the Campus Digital Twin.

Sources
-------
IMD (api.imd.gov.in)  : 7-day city forecast, station nowcast warnings, sun/moon times.
                        Current Weather (current_wx) and AWS/ARG (aws_data) are attempted
                        automatically IF the corresponding station IDs are present in
                        secrets -- add them once IMD grants access and nothing else
                        needs to change.
Open-Meteo            : current temperature / humidity / wind. No key required.

Every value rendered carries its own source label, so IMD forecast figures are never
passed off as live observations.
"""

import requests
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta, timezone

try:
    from zoneinfo import ZoneInfo
    IST = ZoneInfo("Asia/Kolkata")
except ImportError:
    import pytz
    IST = pytz.timezone("Asia/Kolkata")

# --- SITE CONSTANTS ---------------------------------------------------------
CAMPUS_LAT = 17.9838          # NIT Warangal
CAMPUS_LON = 79.5306
IMD_BASE = "https://api.imd.gov.in/api/v1"
OPEN_METEO = "https://api.open-meteo.com/v1/forecast"

EMPTY_VALUES = (None, "", "NA", "N/A", "-", "--", "null")


class IMDError(Exception):
    """Raised when an IMD endpoint fails or returns nothing usable."""


def pick(row, *keys):
    """First non-empty value among `keys`, else None."""
    for k in keys:
        if row.get(k) not in EMPTY_VALUES:
            return row[k]
    return None


def to_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


# --- IMD TRANSPORT ----------------------------------------------------------
@st.cache_data(ttl=3480, show_spinner=False)
def _imd_token():
    email = st.secrets.get("IMD_EMAIL")
    password = st.secrets.get("IMD_PASSWORD")
    if not email or not password:
        raise IMDError("IMD_EMAIL / IMD_PASSWORD missing from secrets")
    res = requests.post(
        "https://api.imd.gov.in/api/oauth/token.php",
        json={"email": email, "password": password},
        timeout=10,
    )
    if res.status_code != 200:
        raise IMDError(f"token: HTTP {res.status_code} - {res.text[:160]}")
    token = res.json().get("access_token")
    if not token:
        raise IMDError(f"token: no access_token in response - {res.text[:160]}")
    return token


@st.cache_data(ttl=1800, show_spinner=False)
def imd_get(endpoint, params=None):
    """GET an IMD endpoint. Raises IMDError; never returns a silent fallback."""
    api_key = st.secrets.get("IMD_API_KEY")
    if not api_key:
        raise IMDError("IMD_API_KEY missing from secrets")
    headers = {"X-API-KEY": api_key, "Authorization": f"Bearer {_imd_token()}"}
    r = requests.get(f"{IMD_BASE}/{endpoint}", params=params, headers=headers, timeout=12)
    if r.status_code != 200:
        raise IMDError(f"{endpoint}: HTTP {r.status_code} - {r.text[:160]}")
    payload = r.json()
    rows = payload if isinstance(payload, list) else payload.get("data", payload)
    if not rows:
        raise IMDError(f"{endpoint}: empty response")
    return rows


# --- OPEN-METEO CURRENT CONDITIONS -----------------------------------------
# Open-Meteo uses WMO codes, which are NOT the same as IMD's 01-99 weather codes.
OM_CODES = {
    0: ("Clear sky", "☀️"), 1: ("Mainly clear", "🌤️"), 2: ("Partly cloudy", "⛅"),
    3: ("Overcast", "☁️"), 45: ("Fog", "🌫️"), 48: ("Rime fog", "🌫️"),
    51: ("Light drizzle", "🌦️"), 53: ("Drizzle", "🌦️"), 55: ("Heavy drizzle", "🌦️"),
    61: ("Light rain", "🌧️"), 63: ("Moderate rain", "🌧️"), 65: ("Heavy rain", "🌧️"),
    66: ("Freezing rain", "🌧️"), 67: ("Freezing rain", "🌧️"),
    71: ("Light snow", "🌨️"), 73: ("Snow", "🌨️"), 75: ("Heavy snow", "🌨️"),
    80: ("Light showers", "🌦️"), 81: ("Showers", "🌧️"), 82: ("Violent showers", "⛈️"),
    95: ("Thunderstorm", "⛈️"), 96: ("Thunderstorm with hail", "⛈️"),
    99: ("Severe thunderstorm", "⛈️"),
}

# IMD's own weather codes, used only if current_wx / aws_data become available.
IMD_CODES = {
    1: "Clouds dissolving", 2: "Sky unchanged", 3: "Clouds developing", 5: "Haze",
    10: "Mist", 17: "Thunderstorm, no precipitation", 20: "Drizzle", 21: "Rain",
    25: "Rain showers", 28: "Fog", 29: "Thunderstorm", 45: "Fog",
    61: "Light rain", 63: "Moderate rain", 65: "Heavy rain",
    80: "Light showers", 81: "Heavy showers", 95: "Thunderstorm with rain",
    97: "Heavy thunderstorm",
}


@st.cache_data(ttl=900, show_spinner=False)
def fetch_open_meteo():
    r = requests.get(
        OPEN_METEO,
        params={
            "latitude": CAMPUS_LAT,
            "longitude": CAMPUS_LON,
            "current": "temperature_2m,relative_humidity_2m,apparent_temperature,"
                       "weather_code,wind_speed_10m,cloud_cover",
            "daily": "sunrise,sunset",
            "timezone": "Asia/Kolkata",
            "forecast_days": 1,
        },
        timeout=10,
    )
    r.raise_for_status()
    data = r.json()
    cur = data["current"]
    desc, icon = OM_CODES.get(cur.get("weather_code"), ("Unknown", "❓"))
    return {
        "temp": cur.get("temperature_2m"),
        "feels_like": cur.get("apparent_temperature"),
        "humidity": cur.get("relative_humidity_2m"),
        "wind": cur.get("wind_speed_10m"),
        "cloud": cur.get("cloud_cover"),
        "desc": desc,
        "icon": icon,
        "observed": cur.get("time"),
        "sunrise": data.get("daily", {}).get("sunrise", [None])[0],
        "sunset": data.get("daily", {}).get("sunset", [None])[0],
        "source": "Open-Meteo",
    }


# --- IMD CURRENT OBSERVATIONS (attempted only if station IDs are configured) --
def fetch_imd_current():
    """
    Live observations from IMD. Returns None if the endpoints are not yet granted.
    Populate IMD_CURRENT_STATION_ID (current_wx) or IMD_AWS_STATION_ID / IMD_STATE_ID
    (aws_data) in secrets once IMD enables them -- no other change is needed.
    """
    errors = []

    station_id = st.secrets.get("IMD_CURRENT_STATION_ID")
    if station_id:
        try:
            wx = imd_get("current_wx", {"id": station_id})[0]
            code = to_float(pick(wx, "Weather Code", "Weather_Code"))
            obs_utc = f"{pick(wx, 'Date of Observation', 'Date')} {pick(wx, 'Time of Observation')}"
            return {
                "temp": to_float(pick(wx, "Temperature")),
                "humidity": to_float(pick(wx, "Humidity")),
                "wind": to_float(pick(wx, "Wind Speed")),
                "desc": IMD_CODES.get(int(code), f"Code {int(code)}") if code else "—",
                "icon": "🏛️",
                "observed": _utc_text_to_ist(obs_utc),
                "source": f"IMD Current Weather · {pick(wx, 'Station') or station_id}",
            }, errors
        except Exception as e:
            errors.append(str(e))

    aws_id = st.secrets.get("IMD_AWS_STATION_ID")
    state_id = st.secrets.get("IMD_STATE_ID")  # 1 = Telangana
    if aws_id or state_id:
        try:
            rows = imd_get("aws_data", {"id": aws_id} if aws_id else {"sid": state_id})
            df = pd.DataFrame(rows)
            if not aws_id:
                mask = df.apply(
                    lambda r: r.astype(str).str.contains("warangal|hanamkonda",
                                                         case=False).any(), axis=1)
                df = df[mask]
            if df.empty:
                raise IMDError("aws_data: no Warangal/Hanamkonda station in response")
            row = df.iloc[0].to_dict()
            code = to_float(pick(row, "WEATHER_CODE"))
            return {
                "temp": to_float(pick(row, "CURR_TEMP")),
                "humidity": to_float(pick(row, "RH")),
                "wind": to_float(pick(row, "WIND_SPEED")),
                "desc": IMD_CODES.get(int(code), f"Code {int(code)}") if code else "—",
                "icon": "🏛️",
                "observed": f"{pick(row, 'DATE')} {pick(row, 'TIME')} IST",
                "source": f"IMD AWS · {pick(row, 'STATION') or aws_id}",
            }, errors
        except Exception as e:
            errors.append(str(e))

    return None, errors


def _utc_text_to_ist(text):
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d %H%M"):
        try:
            dt = datetime.strptime(text.strip(), fmt).replace(tzinfo=timezone.utc)
            return dt.astimezone(IST).strftime("%d-%m-%Y %H:%M IST")
        except (ValueError, AttributeError):
            continue
    return f"{text} UTC"


# --- IMD 7-DAY CITY FORECAST -----------------------------------------------
def fetch_imd_forecast():
    """7-day forecast. Tries cityforecastloc first (includes lat/lon), then cityforecast."""
    city_id = st.secrets.get("IMD_CITY_ID")
    if not city_id:
        return None, ["IMD_CITY_ID missing from secrets"]

    errors = []
    for endpoint in ("cityforecastloc", "cityforecast"):
        try:
            row = imd_get(endpoint, {"id": city_id})[0]
            days = [{
                "Day": "Today",
                "Max (°C)": to_float(pick(row, "Todays_Forecast_Max_Temp", "Today_Max_temp")),
                "Min (°C)": to_float(pick(row, "Todays_Forecast_Min_temp", "Today_Min_temp")),
                "Forecast": pick(row, "Todays_Forecast") or "—",
            }]
            base = datetime.now(IST).date()
            for n in range(2, 8):
                days.append({
                    "Day": (base + timedelta(days=n - 1)).strftime("%a %d %b"),
                    "Max (°C)": to_float(row.get(f"Day_{n}_Max_Temp")),
                    "Min (°C)": to_float(row.get(f"Day_{n}_Min_temp")),
                    "Forecast": row.get(f"Day_{n}_Forecast") or "—",
                })
            return {
                "station": pick(row, "Station_Name") or city_id,
                "issued": pick(row, "Date"),
                "rain_24h": to_float(pick(row, "Past_24_hrs_Rainfall")),
                "sunrise": pick(row, "Sunrise_time"),
                "sunset": pick(row, "Sunset_time"),
                "days": pd.DataFrame(days),
                "endpoint": endpoint,
            }, errors
        except Exception as e:
            errors.append(str(e))
    return None, errors


# --- IMD NOWCAST WARNINGS ---------------------------------------------------
NOWCAST_COLOURS = {1: ("🟢", "No significant weather"), 2: ("🟡", "Watch"),
                   3: ("🟠", "Alert"), 4: ("🔴", "Warning")}


def fetch_imd_nowcast():
    """Short-range warning for the campus station. Colour 1 = green (no weather)."""
    station = st.secrets.get("IMD_NOWCAST_STATION", "Warangal")
    try:
        row = imd_get("stationnowcast", {"id": station})[0]
        colour = int(to_float(pick(row, "color")) or 1)
        return {
            "colour": colour,
            "icon": NOWCAST_COLOURS.get(colour, ("⚪", "Unknown"))[0],
            "level": NOWCAST_COLOURS.get(colour, ("⚪", "Unknown"))[1],
            "message": pick(row, "message") or "No warning in force",
            "valid_upto": pick(row, "Vupto"),
            "issued": pick(row, "toi"),
            "station": pick(row, "Station") or station,
        }, []
    except Exception as e:
        return None, [str(e)]


# --- IMD SUN / MOON ---------------------------------------------------------
def fetch_imd_sunmoon():
    """Sunrise/sunset (and moon times) in IST for the campus coordinates."""
    try:
        rows = imd_get("sunmoon", {"lat": CAMPUS_LAT, "lon": CAMPUS_LON})
        merged = {}
        for entry in rows:
            if isinstance(entry, dict):
                merged.update(entry)
        if not merged.get("sunrise"):
            raise IMDError("sunmoon: no sunrise in response")
        return merged, []
    except Exception as e:
        return None, [str(e)]


# --- RENDERING --------------------------------------------------------------
def render_weather_panel():
    """Draws the full weather block. Returns (sunrise, sunset) as 'HH:MM' for chart use."""
    errors = []

    imd_current, e = fetch_imd_current()
    errors += e
    open_meteo = None
    if imd_current is None:
        try:
            open_meteo = fetch_open_meteo()
        except Exception as exc:
            errors.append(f"open-meteo: {exc}")

    current = imd_current or open_meteo
    forecast, e = fetch_imd_forecast(); errors += e
    nowcast, e = fetch_imd_nowcast();   errors += e
    sunmoon, e = fetch_imd_sunmoon();   errors += e

    # Nowcast banner, only when there is something to say
    if nowcast and nowcast["colour"] > 1:
        banner = st.error if nowcast["colour"] >= 3 else st.warning
        valid = f" · valid to {nowcast['valid_upto']} IST" if nowcast["valid_upto"] else ""
        banner(f"{nowcast['icon']} **IMD Nowcast — {nowcast['level']}:** "
               f"{nowcast['message']}{valid}")

    # Current conditions
    st.markdown("#### Current Conditions")
    c1, c2, c3, c4 = st.columns(4)
    if current:
        c1.metric("Temperature", f"{current['temp']} °C" if current["temp"] is not None else "—")
        c2.metric("Humidity", f"{current['humidity']} %" if current["humidity"] is not None else "—")
        c3.metric("Wind", f"{current['wind']} km/h" if current.get("wind") is not None else "—")
        c4.metric("Conditions", f"{current.get('icon', '')} {current['desc']}")
        st.caption(f"Observed: {current['observed']}  ·  Source: {current['source']}")
    else:
        c1.metric("Temperature", "—")
        c2.metric("Humidity", "—")
        st.caption("Current conditions unavailable — see diagnostics below.")

    # IMD forecast
    if forecast:
        st.markdown("#### IMD Forecast")
        today = forecast["days"].iloc[0]
        f1, f2, f3, f4 = st.columns(4)
        f1.metric("Today's Max", f"{today['Max (°C)']} °C" if today["Max (°C)"] else "—")
        f2.metric("Today's Min", f"{today['Min (°C)']} °C" if today["Min (°C)"] else "—")
        f3.metric("Rain (24 h)", f"{forecast['rain_24h']} mm"
                  if forecast["rain_24h"] is not None else "—")
        f4.metric("Outlook", today["Forecast"])

        sunrise = (sunmoon or {}).get("sunrise") or forecast.get("sunrise")
        sunset = (sunmoon or {}).get("sunset") or forecast.get("sunset")
        bits = [f"Station: {forecast['station']}", f"Issued: {forecast['issued']}"]
        if sunrise and sunset:
            bits.append(f"Sunrise {sunrise} · Sunset {sunset} IST")
        st.caption("  ·  ".join(bits) + "  ·  Data: India Meteorological Department")

        with st.expander("7-day IMD outlook"):
            st.dataframe(forecast["days"], use_container_width=True, hide_index=True)
    else:
        sunrise = sunset = None

    # Diagnostics
    with st.expander("Weather source diagnostics", expanded=False):
        granted = []
        if imd_current:
            granted.append(imd_current["source"])
        if forecast:
            granted.append(f"IMD {forecast['endpoint']}")
        if nowcast:
            granted.append("IMD stationnowcast")
        if sunmoon:
            granted.append("IMD sunmoon")
        if open_meteo:
            granted.append("Open-Meteo (current conditions)")
        st.success("Active: " + ", ".join(granted) if granted else "No source responded.")
        for err in errors:
            st.warning(err)
        st.caption(
            "current_wx / aws_data are attempted automatically once "
            "IMD_CURRENT_STATION_ID or IMD_AWS_STATION_ID is set in secrets."
        )
        if st.checkbox("Show raw IMD forecast response"):
            try:
                st.json(imd_get("cityforecast", {"id": st.secrets.get("IMD_CITY_ID")})[0])
            except Exception as exc:
                st.error(str(exc))

    return sunrise, sunset

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

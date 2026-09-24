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

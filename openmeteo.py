"""
Weather forecast panel — Open-Meteo (https://open-meteo.com), no API key needed.

render_forecast_panel() draws a 3-day outlook plus a 48-hour hourly forecast
(solar irradiance, cloud, temperature, rain) and returns today's
(sunrise, sunset) as "HH:MM" strings, or (None, None) if the call fails.
"""

from datetime import datetime

import altair as alt
import pandas as pd
import requests
import streamlit as st

# Campus coordinates and the API URL live in weather.py — one place to edit.
from weather import IST, CAMPUS_LAT, CAMPUS_LON, OPEN_METEO as API_URL

FORECAST_DAYS = 3
HOURS_AHEAD = 48
HOURLY_VARS = ["temperature_2m", "relative_humidity_2m", "cloud_cover",
               "precipitation_probability", "wind_speed_10m",
               "shortwave_radiation", "direct_radiation", "diffuse_radiation"]
DAILY_VARS = ["sunrise", "sunset", "temperature_2m_max", "temperature_2m_min",
              "precipitation_probability_max", "precipitation_sum",
              "shortwave_radiation_sum"]


@st.cache_data(ttl=900, show_spinner=False)   # Open-Meteo updates hourly
def fetch_forecast(lat=CAMPUS_LAT, lon=CAMPUS_LON, days=FORECAST_DAYS):
    """Return (hourly_df, daily_df), or (None, None) if the request fails."""
    params = {
        "latitude": lat, "longitude": lon,
        "hourly": ",".join(HOURLY_VARS),
        "daily": ",".join(DAILY_VARS),
        "timezone": "Asia/Kolkata",
        "forecast_days": days,
    }
    try:
        resp = requests.get(API_URL, params=params, timeout=10)
        resp.raise_for_status()
        payload = resp.json()
        hourly = pd.DataFrame(payload["hourly"])
        daily = pd.DataFrame(payload["daily"])
    except (requests.RequestException, KeyError, ValueError):
        return None, None

    hourly["time"] = pd.to_datetime(hourly["time"])
    daily["time"] = pd.to_datetime(daily["time"])
    # MJ/m² → kWh/m² (1 kWh = 3.6 MJ)
    daily["radiation_kwh_m2"] = daily["shortwave_radiation_sum"] / 3.6
    return hourly, daily


def _hhmm(iso_text):
    try:
        return pd.to_datetime(iso_text).strftime("%H:%M")
    except (ValueError, TypeError):
        return None


def _day_label(day, today):
    delta = (day.date() - today).days
    return {0: "Today", 1: "Tomorrow"}.get(delta, day.strftime("%A"))


def _hour_axis():
    return alt.X("time:T", title=None,
                 axis=alt.Axis(format="%d %b %H:%M", labelAngle=0, tickCount=8))


def render_forecast_panel():
    st.subheader("🌤️ Weather Forecast — Open-Meteo")

    hourly, daily = fetch_forecast()
    if hourly is None:
        st.warning("Weather forecast is unavailable right now. It will retry automatically.")
        return None, None

    now = datetime.now(IST).replace(tzinfo=None)
    today = now.date()

    # --- Daily outlook --------------------------------------------------------
    cols = st.columns(len(daily))
    for col, (_, d) in zip(cols, daily.iterrows()):
        with col.container(border=True):
            st.markdown(f"**{_day_label(d['time'], today)}** · {d['time']:%d %b}")
            st.metric("Temperature (max / min)",
                      f"{d['temperature_2m_max']:.0f}° / {d['temperature_2m_min']:.0f}°C")
            st.caption(
                f"☀️ {d['radiation_kwh_m2']:.2f} kWh/m² solar  \n"
                f"🌧️ {d['precipitation_probability_max']:.0f}% chance · "
                f"{d['precipitation_sum']:.1f} mm  \n"
                f"🌅 {_hhmm(d['sunrise'])} – {_hhmm(d['sunset'])}"
            )

    # --- Hourly forecast, next 48 h ---------------------------------------------
    start = now.replace(minute=0, second=0, microsecond=0)
    window = hourly[(hourly["time"] >= start) &
                    (hourly["time"] < start + pd.Timedelta(hours=HOURS_AHEAD))].copy()

    st.caption(f"Hourly forecast · next {HOURS_AHEAD} h from {start:%d-%m-%Y %H:%M} IST")
    t_solar, t_temp, t_rain = st.tabs(["☀️ Solar & cloud", "🌡️ Temperature & humidity",
                                       "🌧️ Rain & wind"])

    with t_solar:
        irr = window.melt(id_vars="time",
                          value_vars=["shortwave_radiation", "direct_radiation",
                                      "diffuse_radiation"],
                          var_name="Component", value_name="W/m²")
        irr["Component"] = irr["Component"].map({
            "shortwave_radiation": "Global (GHI)",
            "direct_radiation": "Direct",
            "diffuse_radiation": "Diffuse"})
        irr_chart = alt.Chart(irr).mark_line(strokeWidth=2).encode(
            x=_hour_axis(),
            y=alt.Y("W/m²:Q", title="Irradiance (W/m²)", axis=alt.Axis(orient="left")),
            color=alt.Color("Component:N", title=None,
                            scale=alt.Scale(domain=["Global (GHI)", "Direct", "Diffuse"],
                                            range=["#e8a10c", "#c4540c", "#7fa7d9"])),
            tooltip=[alt.Tooltip("time:T", title="Time", format="%d %b %H:%M"),
                     "Component:N", alt.Tooltip("W/m²:Q", format=".0f")],
        )
        cloud_chart = alt.Chart(window).mark_area(opacity=0.15, color="#52606d").encode(
            x=_hour_axis(),
            y=alt.Y("cloud_cover:Q", title="Cloud cover (%)",
                    scale=alt.Scale(domain=[0, 100]), axis=alt.Axis(orient="right")),
            tooltip=[alt.Tooltip("time:T", title="Time", format="%d %b %H:%M"),
                     alt.Tooltip("cloud_cover:Q", title="Cloud %", format=".0f")],
        )
        st.altair_chart(alt.layer(cloud_chart, irr_chart)
                        .resolve_scale(y="independent").properties(height=280),
                        width="stretch")
        st.caption("Shaded area = cloud cover (right axis).")

    with t_temp:
        temp = alt.Chart(window).mark_line(strokeWidth=2, color="#d64545").encode(
            x=_hour_axis(),
            y=alt.Y("temperature_2m:Q", title="Temperature (°C)",
                    scale=alt.Scale(zero=False)),
            tooltip=[alt.Tooltip("time:T", title="Time", format="%d %b %H:%M"),
                     alt.Tooltip("temperature_2m:Q", title="°C", format=".1f")],
        )
        rh = alt.Chart(window).mark_line(strokeWidth=1.5, strokeDash=[4, 3],
                                         color="#3e7cb1").encode(
            x=_hour_axis(),
            y=alt.Y("relative_humidity_2m:Q", title="Relative humidity (%)",
                    scale=alt.Scale(domain=[0, 100])),
            tooltip=[alt.Tooltip("time:T", title="Time", format="%d %b %H:%M"),
                     alt.Tooltip("relative_humidity_2m:Q", title="RH %", format=".0f")],
        )
        st.altair_chart(alt.layer(temp, rh).resolve_scale(y="independent")
                        .properties(height=280), width="stretch")
        st.caption("Solid = temperature (left axis) · dashed = humidity (right axis).")

    with t_rain:
        rain = alt.Chart(window).mark_bar(color="#3e7cb1", opacity=0.7).encode(
            x=_hour_axis(),
            y=alt.Y("precipitation_probability:Q", title="Rain probability (%)",
                    scale=alt.Scale(domain=[0, 100])),
            tooltip=[alt.Tooltip("time:T", title="Time", format="%d %b %H:%M"),
                     alt.Tooltip("precipitation_probability:Q", title="Rain %",
                                 format=".0f")],
        )
        wind = alt.Chart(window).mark_line(strokeWidth=2, color="#2f8f5b").encode(
            x=_hour_axis(),
            y=alt.Y("wind_speed_10m:Q", title="Wind speed at 10 m (km/h)"),
            tooltip=[alt.Tooltip("time:T", title="Time", format="%d %b %H:%M"),
                     alt.Tooltip("wind_speed_10m:Q", title="km/h", format=".1f")],
        )
        st.altair_chart(alt.layer(rain, wind).resolve_scale(y="independent")
                        .properties(height=280), width="stretch")
        st.caption("Bars = rain probability (left axis) · line = wind speed (right axis).")

    # --- Table + download (feeds the forecasting models) ---------------------------
    table = window.rename(columns={
        "time": "Time (IST)", "temperature_2m": "Temp (°C)",
        "relative_humidity_2m": "RH (%)", "cloud_cover": "Cloud (%)",
        "precipitation_probability": "Rain prob (%)", "wind_speed_10m": "Wind (km/h)",
        "shortwave_radiation": "GHI (W/m²)", "direct_radiation": "Direct (W/m²)",
        "diffuse_radiation": "Diffuse (W/m²)"})
    with st.expander("Hourly forecast values"):
        st.dataframe(table, width="stretch", hide_index=True,
                     column_config={"Time (IST)": st.column_config.DatetimeColumn(
                         format="DD MMM YYYY, HH:mm")})
    st.download_button("⬇️ Download forecast (CSV)", table.to_csv(index=False).encode(),
                       f"openmeteo_forecast_{now:%Y%m%d_%H%M}.csv", "text/csv",
                       key="dl_forecast")

    st.caption("Weather data by [Open-Meteo.com](https://open-meteo.com) (CC BY 4.0).")

    today_row = daily[daily["time"].dt.date == today]
    if today_row.empty:
        return None, None
    return _hhmm(today_row.iloc[0]["sunrise"]), _hhmm(today_row.iloc[0]["sunset"])

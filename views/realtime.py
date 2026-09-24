"""
Real-Time Operational Telemetry — Campus Digital Twin.

All figures on this page derive from ONE source of truth (FEEDERS below), so the
KPI row, the network table, the status grid and the per-feeder detail can never
disagree with each other. Replace `load_feeder_data()` with the PME query when
the SQL connection is ready — nothing else needs to change.
"""

import altair as alt
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from datetime import datetime, timedelta

from weather import render_weather_panel, IST

st.title("📡 Real-Time Operational Telemetry")

# --- TARIFFS & LIMITS (single place to edit) --------------------------------
GRID_TARIFF = 8.00        # ₹ per kWh drawn from the grid
SOLAR_TARIFF = 3.14       # ₹ per kWh generated on site (levelised)
NOMINAL_VOLTAGE = 415.0   # L-L, three phase
VOLTAGE_TOLERANCE = 0.10  # ±10% per IS 12360
PF_FLOOR = 0.85           # below this (absolute) the feeder is flagged

# --- FEEDER DEFINITIONS -----------------------------------------------------
# role: "solar" = generation, "incomer" = grid supply, "load" = downstream feeder.
# Only incomers count toward campus consumption; load feeders sit BELOW the
# incomers and would otherwise be double-counted.
FEEDERS = [
    {"key": "rw_solar",   "name": "EED Research Wing Solar",     "source": "Gr1.EED_Research_Wing_Solar",     "role": "solar",
     "voltage": 421.51, "current": 53.47, "kw": 38.87, "pf": 1.00,  "kwh_total": 78165.03,  "peak": 33},
    {"key": "rw_inc1",    "name": "EED Research Wing Incomer 1", "source": "Gr1.EED_Research_Wing_Incomer_1", "role": "incomer",
     "voltage": 421.79, "current": 38.95, "kw": 27.36, "pf": -0.96, "kwh_total": 88867.56,  "peak": 27},
    {"key": "rw_inc2",    "name": "EED Research Wing Incomer 2", "source": "Gr1.EED_Research_Wing_Incomer_2", "role": "incomer",
     "voltage": 419.85, "current": 3.89,  "kw": 2.49,  "pf": 0.89,  "kwh_total": 11904.58,  "peak": 3},
    {"key": "eed_solar",  "name": "EED Solar",                   "source": "Gr1.EED_Solar",                   "role": "solar",
     "voltage": 416.07, "current": 47.68, "kw": 34.26, "pf": -1.00, "kwh_total": 74001.94,  "peak": 34},
    {"key": "eed_inc1",   "name": "EED Incomer 1",               "source": "Gr1.EED_Incomer_1",               "role": "incomer",
     "voltage": 415.81, "current": 41.13, "kw": 30.00, "pf": -0.99, "kwh_total": 239076.54, "peak": 30},
    {"key": "eed_inc2",   "name": "EED Incomer 2",               "source": "Gr1.EED_Incomer_2",               "role": "incomer",
     "voltage": 419.54, "current": 4.61,  "kw": 2.93,  "pf": 0.88,  "kwh_total": 11502.40,  "peak": 5},
    {"key": "eed_load",   "name": "EED Load Feeder",             "source": "Gr1.EED_Load_Feeder",             "role": "load",
     "voltage": 416.38, "current": 15.47, "kw": 10.96, "pf": 0.98,  "kwh_total": 31711.39,  "peak": 11},
    {"key": "civil_load", "name": "Civil Load Feeder",           "source": "Gr1.Civil_Load_Feeder",           "role": "load",
     "voltage": 296.61, "current": 32.29, "kw": 12.88, "pf": -0.96, "kwh_total": 66131.13,  "peak": 14},
]

# Normalised 24-hour shapes; multiplied by each feeder's peak kW.
SOLAR_SHAPE = [0, 0, 0, 0, 0, 0.05, 0.20, 0.45, 0.68, 0.85, 1.00, 0.97,
               0.88, 0.72, 0.52, 0.30, 0.10, 0.02, 0, 0, 0, 0, 0, 0]
LOAD_SHAPE = [0.30, 0.26, 0.24, 0.22, 0.26, 0.38, 0.55, 0.72, 0.86, 0.94, 1.00, 0.96,
              0.88, 0.92, 0.98, 0.94, 0.84, 0.70, 0.58, 0.48, 0.42, 0.38, 0.34, 0.31]
# Deterministic day-to-day variation, so reruns don't reshuffle the chart.
DAY_JITTER = [0.98, 1.03, 0.95, 1.01, 0.97, 1.04, 0.99, 1.02, 0.96, 1.00, 1.03, 0.98,
              1.01, 0.97, 0.99, 1.02, 0.96, 1.00, 1.04, 0.95, 0.98, 1.01, 0.97, 1.00]


def hourly_curve(peak, role, factor=1.0, cutoff=None):
    """24 hourly kW values. Hours after `cutoff` return None (not yet measured)."""
    shape = SOLAR_SHAPE if role == "solar" else LOAD_SHAPE
    out = []
    for h in range(24):
        if cutoff is not None and h > cutoff:
            out.append(None)
        else:
            out.append(round(peak * shape[h] * DAY_JITTER[h] * factor, 2))
    return out


@st.cache_data(ttl=60, show_spinner=False)
def load_feeder_data(as_of_hour):
    """
    Build the feeder dataset.

    >>> REPLACE THIS with the PME query once the SQL connection is available. <<<
    Return the same columns and every downstream section keeps working.
    """
    rows = []
    for f in FEEDERS:
        today = hourly_curve(f["peak"], f["role"], 1.00, cutoff=as_of_hour)
        yday = hourly_curve(f["peak"], f["role"], 1.06)
        kwh_today = round(sum(v for v in today if v is not None), 2)
        tariff = SOLAR_TARIFF if f["role"] == "solar" else GRID_TARIFF
        rows.append({**f,
                     "today": today,
                     "yesterday": yday,
                     "kwh_today": kwh_today,
                     "kwh_yesterday": round(sum(yday), 2),
                     "cost_today": round(kwh_today * tariff, 2)})
    return rows


def feeder_status(f):
    """('ok'|'warn'|'alert', reason)."""
    lo = NOMINAL_VOLTAGE * (1 - VOLTAGE_TOLERANCE)
    hi = NOMINAL_VOLTAGE * (1 + VOLTAGE_TOLERANCE)
    if not lo <= f["voltage"] <= hi:
        return "alert", f"Voltage {f['voltage']:.0f} V outside {lo:.0f}–{hi:.0f} V"
    if abs(f["pf"]) < PF_FLOOR:
        return "warn", f"Power factor {abs(f['pf']):.2f} below {PF_FLOOR}"
    return "ok", "Within limits"


# --- SIDEBAR ----------------------------------------------------------------
with st.sidebar:
    st.header("📆 Campus Calendar")
    st.caption("Embedded Campus Maintenance & Load Schedule")
    components.iframe(
        "https://calendar.google.com/calendar/embed?"
        "height=320&wkst=1&ctz=Asia%2FKolkata&showTitle=0&showNav=1&showDate=1"
        "&showPrint=0&showTabs=0&showCalendars=0&showTz=0&mode=AGENDA",
        height=350, scrolling=True,
    )
    st.divider()
    st.header("⚙️ View Settings")
    view_date = st.date_input("Date", value=datetime.now(IST).date(),
                              max_value=datetime.now(IST).date(),
                              help="Historical dates become available once PME is connected.")
    if view_date != datetime.now(IST).date():
        st.info("Showing today's data — historical queries need the PME connection.")


# --- LIVE CLOCK -------------------------------------------------------------
@st.fragment(run_every="1s")
def render_live_clock():
    now = datetime.now(IST)
    c1, c2 = st.columns(2)
    c1.markdown(f"📅 **System Date:** `{now.strftime('%A, %d %B %Y')}`")
    c2.markdown(f"🕒 **Live System Time:** `{now.strftime('%H:%M:%S IST')}`")


render_live_clock()
st.divider()

# --- WEATHER ----------------------------------------------------------------
sunrise, sunset = render_weather_panel()
st.divider()

# --- DATA -------------------------------------------------------------------
now = datetime.now(IST)
data = load_feeder_data(now.hour)
window = f"{now:%d-%m-%Y} 00:00 – {now:%H:%M} IST"

solar = [f for f in data if f["role"] == "solar"]
incomers = [f for f in data if f["role"] == "incomer"]

gen_kw = sum(f["kw"] for f in solar)
gen_kwh = sum(f["kwh_today"] for f in solar)
grid_kw = sum(f["kw"] for f in incomers)
grid_kwh = sum(f["kwh_today"] for f in incomers)
demand_kw = grid_kw + gen_kw
demand_kwh = grid_kwh + gen_kwh
solar_share = (gen_kwh / demand_kwh * 100) if demand_kwh else 0
savings = gen_kwh * (GRID_TARIFF - SOLAR_TARIFF)

# --- CAMPUS KPI ROW ---------------------------------------------------------
st.subheader("🏛️ Campus Energy Summary")
st.caption(f"{window}  ·  Grid draw = incomers only; load feeders sit downstream "
           f"and are excluded to avoid double counting.")

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Total Demand", f"{demand_kwh:,.0f} kWh", f"{demand_kw:,.1f} kW now",
          delta_color="off", border=True)
k2.metric("Grid Draw", f"{grid_kwh:,.0f} kWh", f"{grid_kw:,.1f} kW now",
          delta_color="off", border=True)
k3.metric("Solar Generation", f"{gen_kwh:,.0f} kWh", f"{gen_kw:,.1f} kW now",
          delta_color="off", border=True)
k4.metric("Solar Share", f"{solar_share:.1f} %",
          help="Solar generation as a share of total campus demand today.", border=True)
k5.metric("Tariff Saving", f"₹ {savings:,.0f}",
          help=f"Solar kWh × (₹{GRID_TARIFF} grid − ₹{SOLAR_TARIFF} solar).", border=True)

st.divider()

# --- FEEDER STATUS GRID -----------------------------------------------------
st.subheader("🩺 Feeder Health at a Glance")

alerts = [(f, *feeder_status(f)) for f in data]
bad = [(f, s, r) for f, s, r in alerts if s != "ok"]
if bad:
    for f, s, reason in bad:
        (st.error if s == "alert" else st.warning)(f"**{f['name']}** — {reason}")
else:
    st.success("All feeders within voltage and power-factor limits.")

ICONS = {"ok": "🟢", "warn": "🟡", "alert": "🔴"}
grid_cols = st.columns(4)
for i, (f, status, reason) in enumerate(alerts):
    with grid_cols[i % 4]:
        delta = None
        if f["kwh_yesterday"]:
            change = (f["kwh_today"] - f["kwh_yesterday"]) / f["kwh_yesterday"] * 100
            delta = f"{change:+.0f}% vs yesterday"
        st.metric(f"{ICONS[status]} {f['name']}", f"{f['kw']:.2f} kW", delta,
                  delta_color="off", help=reason, border=True)
        if st.button("View detail", key=f"btn_{f['key']}", use_container_width=True):
            st.session_state.selected_feeders = [f["name"]]

st.divider()

# --- NETWORK TABLE ----------------------------------------------------------
st.subheader("📊 Real Time Data — All Feeder Network")

table = pd.DataFrame([{
    "Source": f["source"],
    "Role": f["role"].title(),
    "Voltage L-L Avg (V)": f["voltage"],
    "Current Avg (A)": f["current"],
    "Real Power (kW)": f["kw"],
    "Power Factor": abs(f["pf"]),
    "PF Type": "Leading" if f["pf"] < 0 else "Lagging",
    "Energy Today (kWh)": f["kwh_today"],
    "Cumulative Energy (kWh)": f["kwh_total"],
} for f in data])

lo = NOMINAL_VOLTAGE * (1 - VOLTAGE_TOLERANCE)
hi = NOMINAL_VOLTAGE * (1 + VOLTAGE_TOLERANCE)
styled = (table.style
          .map(lambda v: "background-color:#ffe3e3;color:#9b1c1c;font-weight:600"
               if not lo <= v <= hi else "", subset=["Voltage L-L Avg (V)"])
          .map(lambda v: "background-color:#fff4e0" if v < PF_FLOOR else "",
               subset=["Power Factor"])
          .format({"Voltage L-L Avg (V)": "{:.2f}", "Current Avg (A)": "{:.2f}",
                   "Real Power (kW)": "{:.2f}", "Power Factor": "{:.2f}",
                   "Energy Today (kWh)": "{:,.2f}", "Cumulative Energy (kWh)": "{:,.2f}"}))
st.dataframe(styled, use_container_width=True, hide_index=True)
st.caption("Power factor shown as magnitude; sign convention reported separately as "
           "leading/lagging. Red = voltage outside ±10% of 415 V.")
st.download_button("⬇️ Download network snapshot (CSV)",
                   table.to_csv(index=False).encode(),
                   f"feeder_snapshot_{now:%Y%m%d_%H%M}.csv", "text/csv")

st.divider()

# --- CHART HELPERS ----------------------------------------------------------
def _hhmm_to_float(text):
    try:
        h, m = str(text).split(":")[:2]
        return int(h) + int(m) / 60
    except (ValueError, AttributeError):
        return None


def night_bands():
    """Shaded rectangles before sunrise and after sunset, if IMD gave us the times."""
    sr, ss = _hhmm_to_float(sunrise), _hhmm_to_float(sunset)
    if sr is None or ss is None:
        return None
    bands = pd.DataFrame({"start": [0, ss], "end": [sr, 24]})
    return (alt.Chart(bands)
            .mark_rect(opacity=0.07, color="#1f2933")
            .encode(x="start:Q", x2="end:Q"))


def kw_chart(frame, colour_field=None, height=260):
    base = alt.Chart(frame).mark_line(point=False, strokeWidth=2).encode(
        x=alt.X("hour:Q", title="Hour (IST)",
                scale=alt.Scale(domain=[0, 23]),
                axis=alt.Axis(values=list(range(0, 24, 2)), format="d")),
        y=alt.Y("kw:Q", title="Real Power (kW)"),
        tooltip=[alt.Tooltip("hour:Q", title="Hour"),
                 alt.Tooltip("kw:Q", title="kW", format=".2f")] +
                ([alt.Tooltip(f"{colour_field}:N", title="Feeder")] if colour_field else []),
    )
    if colour_field:
        base = base.encode(color=alt.Color(f"{colour_field}:N", title=None))
    bands = night_bands()
    chart = (bands + base) if bands is not None else base
    return chart.properties(height=height).interactive(bind_y=False)


def long_form(feeder, which="today"):
    return pd.DataFrame({"hour": range(24), "kw": feeder[which]}).dropna()


# --- FEEDER DETAIL / COMPARISON --------------------------------------------
st.subheader("⚡ Feeder Analytics")

names = [f["name"] for f in data]
st.session_state.setdefault("selected_feeders", [names[3]])
selected = st.multiselect("Select one feeder for detail, or several to compare",
                          names, key="selected_feeders")

by_name = {f["name"]: f for f in data}

if not selected:
    st.info("Select at least one feeder above.")

elif len(selected) == 1:
    f = by_name[selected[0]]
    is_solar = f["role"] == "solar"
    label = "Generation" if is_solar else "Consumption"

    d1, d2, d3 = st.columns([1, 1, 2])
    d1.metric(f"{label} Today", f"{f['kwh_today']:,.2f} kWh",
              f"{(f['kwh_today'] - f['kwh_yesterday']) / f['kwh_yesterday'] * 100:+.1f}% vs yesterday"
              if f["kwh_yesterday"] else None,
              delta_color="normal" if is_solar else "inverse", border=True)
    d2.metric("Cost" if not is_solar else "Value at Solar Tariff",
              f"₹ {f['cost_today']:,.2f}",
              help=f"₹{SOLAR_TARIFF if is_solar else GRID_TARIFF}/kWh", border=True)
    with d3:
        st.caption(f"Real power today · {window}")
        st.altair_chart(kw_chart(long_form(f)), use_container_width=True)

    st.markdown(f"##### {label} Comparison — Today vs Yesterday")
    comp = pd.concat([
        pd.DataFrame({"hour": range(24), "kWh": f["yesterday"], "Day": "Yesterday"}),
        pd.DataFrame({"hour": range(24), "kWh": f["today"], "Day": "Today"}),
    ]).dropna()

    bars = alt.Chart(comp).mark_bar().encode(
        x=alt.X("hour:O", title="Hour (IST)"),
        xOffset="Day:N",                       # side by side, NOT stacked
        y=alt.Y("kWh:Q", title="Energy (kWh)"),
        color=alt.Color("Day:N", title=None,
                        scale=alt.Scale(domain=["Yesterday", "Today"],
                                        range=["#9ec5fe", "#1c5dd7"])),
        tooltip=["Day:N", alt.Tooltip("hour:O", title="Hour"),
                 alt.Tooltip("kWh:Q", format=".2f")],
    ).properties(height=300)
    st.altair_chart(bars, use_container_width=True)

    detail = pd.DataFrame({"Hour": [f"{h:02d}:00" for h in range(24)],
                           "Today (kW)": f["today"], "Yesterday (kW)": f["yesterday"]})
    with st.expander("Hourly values"):
        st.dataframe(detail, use_container_width=True, hide_index=True)
    st.download_button("⬇️ Download hourly data (CSV)", detail.to_csv(index=False).encode(),
                       f"{f['key']}_{now:%Y%m%d}.csv", "text/csv", key="dl_detail")

else:
    st.caption(f"Real power overlay · {window}")
    frames = []
    for name in selected:
        f = by_name[name]
        part = long_form(f)
        part["Feeder"] = name
        frames.append(part)
    st.altair_chart(kw_chart(pd.concat(frames), colour_field="Feeder", height=340),
                    use_container_width=True)

    summary = pd.DataFrame([{
        "Feeder": by_name[n]["name"],
        "Now (kW)": by_name[n]["kw"],
        "Today (kWh)": by_name[n]["kwh_today"],
        "Yesterday (kWh)": by_name[n]["kwh_yesterday"],
        "Change": f"{(by_name[n]['kwh_today'] - by_name[n]['kwh_yesterday']) / by_name[n]['kwh_yesterday'] * 100:+.1f}%"
                  if by_name[n]["kwh_yesterday"] else "—",
        "Cost (₹)": by_name[n]["cost_today"],
    } for n in selected])
    st.dataframe(summary, use_container_width=True, hide_index=True)
    st.download_button("⬇️ Download comparison (CSV)", summary.to_csv(index=False).encode(),
                       f"feeder_comparison_{now:%Y%m%d}.csv", "text/csv", key="dl_compare")

st.caption("Shaded areas on the line charts mark hours before sunrise and after sunset "
           "(IMD sun/moon times for the campus location).")

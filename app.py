import streamlit as st

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Campus Digital Twin",
    page_icon="🏛️",
    layout="wide"
)

# --- NATIVE MULTI-PAGE ROUTING ---
realtime_page = st.Page(
    "views/realtime.py", 
    title="Real-Time Operations", 
    icon="📡", 
    default=True
)

forecasting_page = st.Page(
    "views/forecasting.py", 
    title="Forecasting Environment", 
    icon="🔮"
)

pg = st.navigation({
    "Digital Twin Modules": [realtime_page, forecasting_page]
})

pg.run()

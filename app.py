import streamlit as st
import requests

st.subheader("🔍 IMD API Diagnostic Tool")

api_key = st.secrets.get("IMD_API_KEY", "")
email = st.secrets.get("IMD_EMAIL", "")
password = st.secrets.get("IMD_PASSWORD", "")

# 1. Test JWT Authentication Endpoint
st.write("--- **Testing Token Generation** ---")
auth_url = "https://api.imd.gov.in/api/oauth/token.php"
try:
    auth_res = requests.post(
        auth_url, 
        json={"email": email, "password": password}, 
        headers={"Content-Type": "application/json"},
        timeout=10
    )
    st.write(f"**Token Response Code:** `{auth_res.status_code}`")
    st.json(auth_res.json())
    jwt_token = auth_res.json().get("access_token")
except Exception as e:
    st.error(f"Token Generation Failed: {e}")
    jwt_token = None

# 2. Test Weather Endpoint with Token & API Key
if jwt_token and api_key:
    st.write("--- **Testing Weather Data Endpoint** ---")
    weather_url = "https://api.imd.gov.in/api/v1/cityforecast"
    headers = {
        "X-API-KEY": api_key,
        "Authorization": f"Bearer {jwt_token}"
    }
    try:
        w_res = requests.get(weather_url, headers=headers, timeout=10)
        st.write(f"**Weather Response Code:** `{w_res.status_code}`")
        if w_res.status_code == 200:
            st.json(w_res.json())
        else:
            st.error(f"Error {w_res.status_code}: {w_res.text}")
    except Exception as e:
        st.error(f"Weather Fetch Failed: {e}")

import streamlit as st
import requests
from supabase import create_client, Client
from datetime import datetime
import os
from dotenv import load_dotenv
import json

# Load environment variables
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

st.set_page_config(page_title="SandGrains - Auth Demo", page_icon="⏳")

# -------------------------------------------
# Auth Functions
# -------------------------------------------

def signup(email, password):
    result = supabase.auth.sign_up({"email": email, "password": password})
    return result

def login(email, password):
    result = supabase.auth.sign_in_with_password({"email": email, "password": password})
    return result

# -------------------------------------------
# UI: Auth
# -------------------------------------------

st.title("⏳ SandGrains - Life Expectancy with Login")

if "user" not in st.session_state:
    st.session_state.user = None

if st.session_state.user is None:
    auth_mode = st.radio("Choose action", ["Login", "Sign Up"], horizontal=True)

    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if st.button("Submit"):
        if not email or not password:
            st.warning("Email and password required.")
        else:
            try:
                if auth_mode == "Sign Up":
                    signup(email, password)
                    st.success("Signup successful. You can now login.")
                else:
                    res = login(email, password)
                    st.session_state.user = res.user
                    st.success(f"Welcome {res.user.email}")
            except Exception as e:
                st.error(str(e))
    st.stop()

# -------------------------------------------
# Authenticated Zone
# -------------------------------------------

st.success(f"Logged in as: {st.session_state.user.email}")
st.write("---")

# User inputs
age = st.number_input("Your Current Age", min_value=1, max_value=120, value=30)
country_code = st.text_input("Country Code (e.g., US, TR, DE)", value="US").upper()
smoking = st.selectbox("Smoking habits", ["never", "former", "current"])
exercise = st.selectbox("Exercise frequency", ["regular", "occasional", "none"])

# Life expectancy fetch
def get_life_expectancy(code):
    url = f"http://api.worldbank.org/v2/country/{code}/indicator/SP.DYN.LE00.IN?format=json&per_page=100"
    try:
        r = requests.get(url)
        data = r.json()
        if data and len(data) > 1 and isinstance(data[1], list):
            for item in data[1]:
                if item["value"]:
                    return item["value"]
        return 75
    except:
        return 75

if st.button("Calculate & Save"):
    email = st.session_state.user.email
    base_expectancy = get_life_expectancy(country_code)

    factor_score = 0
    if smoking == "never":
        factor_score += 2
    elif smoking == "current":
        factor_score -= 5

    if exercise == "regular":
        factor_score += 3
    elif exercise == "none":
        factor_score -= 3

    final_expectancy = base_expectancy + factor_score
    remaining_years = final_expectancy - age
    remaining_seconds = int(remaining_years * 31536000)

    st.success(f"Your estimated remaining life: {remaining_years:.2f} years ({remaining_seconds:,} seconds)")

    data = {
        "user_email": email,
        "age": int(age),
        "country_code": country_code,
        "locations": json.dumps([]),
        "lifestyle": json.dumps({"smoking": smoking, "exercise": exercise}),
        "genetic_factors": json.dumps({}),
        "expectancy_years": float(final_expectancy),
        "remaining_seconds": int(remaining_seconds),
        "updated_at": datetime.utcnow().isoformat()
    }

    existing = supabase.table("user_life_expectancy").select("*").eq("user_email", email).execute()

    if existing.data:
        supabase.table("user_life_expectancy").update(data).eq("user_email", email).execute()
        st.info("Your information has been updated.")
    else:
        supabase.table("user_life_expectancy").insert(data).execute()
        st.info("Your information has been saved.")

# Show existing data
user_data = supabase.table("user_life_expectancy").select("*").eq("user_email", st.session_state.user.email).execute()
if user_data.data:
    st.subheader("Your Last Recorded Data:")
    st.json(user_data.data[0])

# Logout
st.write("---")
if st.button("Log out"):
    st.session_state.user = None
    st.rerun()

import streamlit as st
import requests
from supabase import create_client, Client
from datetime import datetime
import os
import json
from dotenv import load_dotenv

# Load env
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

st.set_page_config(page_title="SandGrains", layout="wide", page_icon="⏳")

# -------------------------------------------
# Auth helpers
# -------------------------------------------
def login_or_signup(email, password):
    try:
        # Try login
        return supabase.auth.sign_in_with_password({"email": email, "password": password})
    except:
        # If fails, signup
        supabase.auth.sign_up({"email": email, "password": password})
        return supabase.auth.sign_in_with_password({"email": email, "password": password})

# -------------------------------------------
# UI: Landing + Auth
# -------------------------------------------
if "user" not in st.session_state:
    st.session_state.user = None

if st.session_state.user is None:
    # Landing screen
    st.markdown(
        """
        <div style='text-align: center; padding: 2rem 1rem;'>
            <img src='https://media.giphy.com/media/3oEjI6SIIHBdRxXI40/giphy.gif'
                 style='width:100px; height:auto; margin-bottom: 1rem;' />
            <h1 style='font-size: 2.5rem; margin-bottom: 0.5rem;'>Welcome to <span style="color:#E94E77;">SandGrains</span></h1>
            <p style='font-size: 1.1rem; max-width: 700px; margin: auto; color: #CCCCCC;'>
                Discover how much time you may have left — in seconds.<br>
                Build healthier habits and learn to live with intention.<br><br>
                This app is <strong>completely free</strong>. Just enter your email and password to continue.
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.write("")
    col1, col2 = st.columns([3, 3])
    with col1:
        email = st.text_input("Email address")
    with col2:
        password = st.text_input(
            "Password",
            type="password",
            help="Must be at least 9 characters and include lowercase, uppercase, number, and symbol."
        )

    if st.button("Continue"):
        if not email or not password:
            st.warning("Email and password required.")
        elif len(password) < 9:
            st.error("Password must be at least 9 characters.")
        else:
            try:
                res = login_or_signup(email, password)
                st.session_state.user = res.user
                st.rerun()
            except Exception as e:
                st.error("Login or signup failed.")
    st.stop()

# -------------------------------------------
# First-time user info
# -------------------------------------------
user_email = st.session_state.user.email

existing = supabase.table("user_life_expectancy").select("*").eq("user_email", user_email).execute()

if not existing.data:
    st.info("Welcome! Please tell us your name.")
    first_name = st.text_input("First name")
    last_name = st.text_input("Last name")
    if st.button("Save name"):
        supabase.table("user_life_expectancy").insert({
            "user_email": user_email,
            "first_name": first_name,
            "last_name": last_name,
            "updated_at": datetime.utcnow().isoformat()
        }).execute()
        st.success("Name saved.")
        st.rerun()
    st.stop()

# -------------------------------------------
# Logged in zone
# -------------------------------------------
st.success(f"Welcome back, {existing.data[0].get('first_name', 'friend')}!")

age = st.number_input("Your Current Age", min_value=1, max_value=120, value=30)
country_code = st.text_input("Country Code (e.g., US, TR, DE)", value="US").upper()
smoking = st.selectbox("Smoking habits", ["never", "former", "current"])
exercise = st.selectbox("Exercise frequency", ["regular", "occasional", "none"])

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
        "age": int(age),
        "country_code": country_code,
        "lifestyle": json.dumps({"smoking": smoking, "exercise": exercise}),
        "locations": json.dumps([]),
        "genetic_factors": json.dumps({}),
        "expectancy_years": float(final_expectancy),
        "remaining_seconds": int(remaining_seconds),
        "updated_at": datetime.utcnow().isoformat()
    }

    supabase.table("user_life_expectancy").update(data).eq("user_email", user_email).execute()
    st.info("Your information has been saved.")

# Show last record
record = supabase.table("user_life_expectancy").select("*").eq("user_email", user_email).execute()
if record.data:
    st.subheader("Your Last Recorded Data:")
    st.json(record.data[0])

# Logout
st.write("---")
if st.button("Log out"):
    st.session_state.user = None
    st.rerun()

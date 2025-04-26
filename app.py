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

# Page config
st.set_page_config(page_title="SandGrains", layout="wide", page_icon="⏳")

# -------------------------------------------
# Auth helper: login or signup in one step
# -------------------------------------------
def login_or_signup(email, password):
    try:
        return supabase.auth.sign_in_with_password({"email": email, "password": password})
    except:
        # user not found → signup then login
        supabase.auth.sign_up({"email": email, "password": password})
        return supabase.auth.sign_in_with_password({"email": email, "password": password})

# -------------------------------------------
# Landing + Auth
# -------------------------------------------
if "user" not in st.session_state:
    st.session_state.user = None

if st.session_state.user is None:
    # Landing: two columns
    col_img, col_txt = st.columns([1,2])
    with col_img:
        st.markdown(
            "<img src='https://i.imgur.com/YVx6qZp.gif' style='width:120px; height:auto; margin-top:1rem;'/>",
            unsafe_allow_html=True
        )
    with col_txt:
        st.markdown(
            """
            <h1 style='color:white; margin-bottom:0.2rem;'>Welcome to <span style="color:#E94E77;">SandGrains</span></h1>
            <p style='color:#CCCCCC; font-size:1.1rem; margin-top:0;'>
                See your remaining life in seconds and get inspired to live healthier.<br>
                Track your habits, take control of your time.
            </p>
            """,
            unsafe_allow_html=True
        )

    st.write("")  # spacing

    # Compact input fields
    col1, col2, col3 = st.columns([2,2,1])
    with col1:
        email = st.text_input("Email address")
    with col2:
        password = st.text_input(
            "Password",
            type="password",
            help="Must be ≥9 chars and include lowercase, uppercase, number & symbol."
        )
    with col3:
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
                except Exception:
                    st.error("Login/Signup failed. Check your credentials.")
    # Free note at bottom
    st.markdown(
        "<div style='text-align:center; color:#777777; font-size:0.9rem; margin-top:2rem;'>"
        "This app is completely free. No hidden fees, ever."
        "</div>",
        unsafe_allow_html=True
    )
    st.stop()

# -------------------------------------------
# First-time user info (name)
# -------------------------------------------
user_email = st.session_state.user.email
existing = supabase.table("user_life_expectancy").select("*").eq("user_email", user_email).execute()

if not existing.data:
    st.info("Hi there! Let's get to know you better.")
    first_name = st.text_input("First name")
    last_name = st.text_input("Last name")
    if st.button("Save name"):
        supabase.table("user_life_expectancy").insert({
            "user_email": user_email,
            "first_name": first_name,
            "last_name": last_name,
            "updated_at": datetime.utcnow().isoformat()
        }).execute()
        st.success("Thanks! Your name has been saved.")
        st.rerun()
    st.stop()

# -------------------------------------------
# Authenticated zone
# -------------------------------------------
st.success(f"Welcome back, {existing.data[0].get('first_name','Friend')}!")
st.write("---")

# Habit inputs
age = st.number_input("Your Current Age", 1, 120, 30, key="age")
country_code = st.text_input("Country Code (e.g., US, TR, DE)", value="US").upper()
smoking = st.selectbox("Smoking habits", ["never","former","current"], key="smoke")
exercise = st.selectbox("Exercise frequency", ["regular","occasional","none"], key="exer")

# Fetch life expectancy
def get_life_expectancy(code):
    url = f"http://api.worldbank.org/v2/country/{code}/indicator/SP.DYN.LE00.IN?format=json&per_page=100"
    try:
        r = requests.get(url)
        data = r.json()
        if data and len(data)>1 and isinstance(data[1], list):
            for item in data[1]:
                if item["value"] is not None:
                    return item["value"]
        return 75
    except:
        return 75

if st.button("Calculate & Save"):
    base = get_life_expectancy(country_code)
    score = 0
    score += 2 if smoking=="never" else (-5 if smoking=="current" else 0)
    score += 3 if exercise=="regular" else (-3 if exercise=="none" else 0)
    final = base + score
    rem_years = final - age
    rem_secs = int(rem_years * 31536000)
    st.success(f"Remaining life: {rem_years:.2f} years ({rem_secs:,} seconds)")

    data = {
        "age": age,
        "country_code": country_code,
        "lifestyle": json.dumps({"smoking": smoking, "exercise": exercise}),
        "locations": json.dumps([]),
        "genetic_factors": json.dumps({}),
        "expectancy_years": float(final),
        "remaining_seconds": rem_secs,
        "updated_at": datetime.utcnow().isoformat()
    }
    supabase.table("user_life_expectancy").update(data).eq("user_email", user_email).execute()
    st.info("Your data has been saved.")

# Show last record
rec = supabase.table("user_life_expectancy").select("*").eq("user_email", user_email).execute()
if rec.data:
    st.subheader("Your Last Recorded Data")
    st.json(rec.data[0])

# Logout
st.write("---")
if st.button("Log out"):
    st.session_state.user = None
    st.rerun()

import streamlit as st
import requests
from supabase import create_client, Client
from datetime import datetime
import os
import json
from dotenv import load_dotenv

# — ENVIRONMENT —
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# — PAGE CONFIG —
st.set_page_config(
    page_title="SandGrains",
    page_icon="⏳",
    layout="wide"
)

# — AUTH HELPER: TRY LOGIN, OTHERWISE SIGNUP —
def login_or_signup(email, password):
    try:
        return supabase.auth.sign_in_with_password({"email": email, "password": password})
    except:
        supabase.auth.sign_up({"email": email, "password": password})
        return supabase.auth.sign_in_with_password({"email": email, "password": password})

# — LANDING + AUTH FLOW —
if "user" not in st.session_state:
    st.session_state.user = None

if st.session_state.user is None:
    # — Card Container —
    with st.container():
        st.markdown("<div style='max-width:800px; margin:auto; padding:2rem; background-color:#1e1e1e; border-radius:12px;'>", unsafe_allow_html=True)
        col1, col2 = st.columns([1,2], gap="small")
        with col1:
            st.image(
                "https://upload.wikimedia.org/wikipedia/commons/3/3e/Hourglass_icon.svg",
                width=100,
                caption=None
            )
        with col2:
            st.markdown(
                """
                <h1 style='color:white; margin-bottom:0.2rem;'>Welcome to <span style="color:#E94E77;">SandGrains</span></h1>
                <p style='color:#BBBBBB; font-size:1rem; margin-top:0;'>
                  See your remaining time—in seconds—and get inspired to live healthier.<br>
                  Track your habits, take control of your days.
                </p>
                """,
                unsafe_allow_html=True
            )
        st.markdown("</div>", unsafe_allow_html=True)

        # — Compact Inputs & Continue —
        with st.container():
            c1, c2, c3 = st.columns([2,2,1], gap="small")
            with c1:
                email = st.text_input("Email address", key="email")
            with c2:
                password = st.text_input(
                    "Password",
                    type="password",
                    help="Must be ≥9 chars & include lowercase, uppercase, number & symbol.",
                    key="password"
                )
            with c3:
                if st.button("Continue", key="cont"):
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
        # — Free note —
        st.markdown(
            "<div style='text-align:center; color:#777777; font-size:0.85rem; margin-top:1rem;'>"
            "This app is completely free. No hidden fees, ever."
            "</div>",
            unsafe_allow_html=True
        )
    st.stop()

# — FIRST-TIME USER: GET NAME —
user_email = st.session_state.user.email
qry = supabase.table("user_life_expectancy").select("*").eq("user_email", user_email).execute()

if not qry.data:
    st.info("Hi there! To get started, tell us your name.")
    fn = st.text_input("First name", key="fn")
    ln = st.text_input("Last name", key="ln")
    if st.button("Save name", key="save_name"):
        supabase.table("user_life_expectancy").insert({
            "user_email": user_email,
            "first_name": fn,
            "last_name": ln,
            "updated_at": datetime.utcnow().isoformat()
        }).execute()
        st.success("Thanks! Your name has been saved.")
        st.rerun()
    st.stop()

# — AUTHENTICATED ZONE —
user_rec = qry.data[0]
st.success(f"Welcome back, {user_rec.get('first_name','Friend')}!")
st.write("---")

# — HABIT INPUTS —
age = st.number_input("Your Current Age", 1, 120, 30, key="age")
cc = st.text_input("Country Code (e.g., US, TR, DE)", "US", key="cc").upper()
sm = st.selectbox("Smoking habits", ["never","former","current"], key="sm")
ex = st.selectbox("Exercise frequency", ["regular","occasional","none"], key="ex")

# — FETCH LIFE EXPECTANCY —
def get_life_expectancy(country):
    url = f"http://api.worldbank.org/v2/country/{country}/indicator/SP.DYN.LE00.IN?format=json&per_page=100"
    try:
        r = requests.get(url)
        data = r.json()
        if data and len(data)>1:
            for it in data[1]:
                if it.get("value") is not None:
                    return it["value"]
        return 75
    except:
        return 75

if st.button("Calculate & Save", key="calc"):
    base = get_life_expectancy(cc)
    score = (2 if sm=="never" else -5 if sm=="current" else 0) \
          + (3 if ex=="regular" else -3 if ex=="none" else 0)
    final = base + score
    rem_y = final - age
    rem_s = int(rem_y * 31536000)
    st.success(f"Remaining life: {rem_y:.2f} years ({rem_s:,} seconds)")

    updated = {
        "age": age,
        "country_code": cc,
        "lifestyle": json.dumps({"smoking": sm, "exercise": ex}),
        "locations": json.dumps([]),
        "genetic_factors": json.dumps({}),
        "expectancy_years": float(final),
        "remaining_seconds": rem_s,
        "updated_at": datetime.utcnow().isoformat()
    }
    supabase.table("user_life_expectancy").update(updated).eq("user_email", user_email).execute()
    st.info("Your data has been saved.")

# — SHOW LAST RECORD —
rec = supabase.table("user_life_expectancy").select("*").eq("user_email", user_email).execute()
if rec.data:
    st.subheader("Your Last Recorded Data:")
    st.json(rec.data[0])

# — LOGOUT BUTTON —
st.write("---")
if st.button("Log out", key="logout"):
    st.session_state.user = None
    st.rerun()

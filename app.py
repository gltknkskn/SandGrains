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
st.set_page_config(page_title="SandGrains", page_icon="⏳", layout="wide")

# — AUTH HELPER —
def login_or_signup(email, password):
    try:
        return supabase.auth.sign_in_with_password({"email": email, "password": password})
    except:
        supabase.auth.sign_up({"email": email, "password": password})
        return supabase.auth.sign_in_with_password({"email": email, "password": password})

# — STYLES & LANDING CARD —
st.markdown("""
<style>
  .card {max-width:600px; margin:3rem auto; background:#1e1e1e; padding:2rem; border-radius:12px;}
  .card img {display:block; margin:0 auto 1rem;}
  .card h1 {color:#fff; text-align:center; font-size:2.5rem; margin:0 0 0.5rem;}
  .card p {color:#ccc; text-align:center; font-size:1rem; margin:0 0 1.5rem;}
  .card .stTextInput>div>div>input {background:#2a2a2a !important; color:#fff !important; border:none !important; border-radius:6px; padding:0.75rem !important;}
  .card .stTextInput>div>label {display:none;}
  .card .stButton>button {width:100%; background:#E94E77; color:#fff; padding:0.75rem; border:none; border-radius:6px; font-size:1rem;}
  .card small {display:block; text-align:center; color:#777; margin-top:1rem; font-size:0.8rem;}
</style>
<div class="card">
  <img src="https://upload.wikimedia.org/wikipedia/commons/3/34/Hourglass_animation.gif" width="80"/>
  <h1>SandGrains</h1>
  <p>Know your remaining time in seconds and live purposefully.</p>
</div>
""", unsafe_allow_html=True)

# — AUTHENTICATION FORM —
if "user" not in st.session_state:
    st.session_state.user = None

if st.session_state.user is None:
    with st.container():
        email = st.text_input("", placeholder="Email address", key="e1")
        password = st.text_input(
            "", placeholder="Password (≥9 chars, lowercase, uppercase, number & symbol)",
            type="password", key="p1"
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
                except Exception:
                    st.error("Login/Signup failed.")
    st.markdown("<small>This app is completely free. No hidden fees.</small>", unsafe_allow_html=True)
    st.stop()

# — FIRST TIME: NAME PROMPT —
user_email = st.session_state.user.email
resp = supabase.table("user_life_expectancy").select("*").eq("user_email", user_email).execute()

if not resp.data:
    st.info("To get started, please tell us your name:")
    fn = st.text_input("First name", key="fn2")
    ln = st.text_input("Last name", key="ln2")
    if st.button("Save name"):
        supabase.table("user_life_expectancy").insert({
            "user_email": user_email,
            "first_name": fn,
            "last_name": ln,
            "updated_at": datetime.utcnow().isoformat()
        }).execute()
        st.success("Name saved.")
        st.rerun()
    st.stop()

# — AUTHENTICATED ZONE —
user_rec = resp.data[0]
st.success(f"Hello, {user_rec.get('first_name','Friend')}! Let's calculate your time.")
st.write("---")

# — HABIT INPUTS —
age = st.number_input("Current Age", 1, 120, 30, key="age2")
cc = st.text_input("Country Code (US, TR, DE...)", "US", key="cc2").upper()
sm = st.selectbox("Smoking habits", ["never","former","current"], key="sm2")
ex = st.selectbox("Exercise freq.", ["regular","occasional","none"], key="ex2")

# — LIFE EXPECTANCY API —
def get_life_expectancy(code):
    try:
        r = requests.get(
            f"http://api.worldbank.org/v2/country/{code}/indicator/SP.DYN.LE00.IN?format=json&per_page=100"
        )
        data = r.json()
        if data and isinstance(data[1], list):
            for it in data[1]:
                if it["value"] is not None:
                    return it["value"]
        return 75
    except:
        return 75

if st.button("Calculate & Save"):
    base = get_life_expectancy(cc)
    score = (2 if sm=="never" else -5 if sm=="current" else 0) \
          + (3 if ex=="regular" else -3 if ex=="none" else 0)
    final = base + score
    rem_y = final - age
    rem_s = int(rem_y * 31536000)
    st.success(f"Remaining: {rem_y:.2f} years ({rem_s:,} seconds)")

    supabase.table("user_life_expectancy").update({
        "age": age,
        "country_code": cc,
        "lifestyle": json.dumps({"smoking":sm, "exercise":ex}),
        "locations": json.dumps([]),
        "genetic_factors": json.dumps({}),
        "expectancy_years": float(final),
        "remaining_seconds": rem_s,
        "updated_at": datetime.utcnow().isoformat()
    }).eq("user_email", user_email).execute()
    st.info("Your data has been saved.")

# — SHOW LAST RECORD —
rec = supabase.table("user_life_expectancy").select("*").eq("user_email", user_email).execute()
if rec.data:
    st.subheader("Last Recorded Data")
    st.json(rec.data[0])

# — LOGOUT —
st.write("---")
if st.button("Log out"):
    st.session_state.user = None
    st.rerun()

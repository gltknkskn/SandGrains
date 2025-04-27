import streamlit as st
import requests, json, os
from supabase import create_client, Client
from datetime import datetime
from dotenv import load_dotenv
import pandas as pd

# — ENVIRONMENT —
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# — PAGE CONFIG —
st.set_page_config(
    page_title="SandGrains",
    page_icon="⏳",
    layout="wide",
    initial_sidebar_state="expanded"
)

# — AUTH (login ≡ signup) —
def login_or_signup(email, password):
    """Try login, otherwise sign up and then login."""
    try:
        return supabase.auth.sign_in_with_password({"email": email, "password": password})
    except:
        supabase.auth.sign_up({"email": email, "password": password})
        return supabase.auth.sign_in_with_password({"email": email, "password": password})

# — LANDING / LOGIN FLOW —
if "user" not in st.session_state:
    st.session_state.user = None

if st.session_state.user is None:
    st.markdown("# SandGrains ⏳")
    st.write("**Free life-expectancy calculator.** Enter your email + password to continue.")
    email = st.text_input("Email address")
    password = st.text_input("Password (≥9 chars)", type="password")
    if st.button("Continue"):
        if not email or not password:
            st.error("Email and password required.")
        elif len(password) < 9:
            st.error("Password must be at least 9 characters.")
        else:
            res = login_or_signup(email, password)
            if res.user:
                st.session_state.user = res.user
                st.experimental_rerun()
            else:
                st.error("Login/Signup failed.")
    st.stop()

# — fetch or create profile record —
user_email = st.session_state.user.email
profile = supabase.table("user_life_expectancy") \
    .select("first_name,last_name") \
    .eq("user_email", user_email) \
    .maybe_single().execute().data

if not profile:
    # first‐time: ask name
    st.header("Welcome! Tell us your name:")
    fn = st.text_input("First name")
    ln = st.text_input("Last name")
    if st.button("Save"):
        supabase.table("user_life_expectancy").insert({
            "user_email": user_email,
            "first_name": fn,
            "last_name": ln,
            "updated_at": datetime.utcnow().isoformat()
        }).execute()
        st.success("Name saved!")
        st.experimental_rerun()
    st.stop()

first_name = profile["first_name"]
last_name  = profile["last_name"]

# — SIDEBAR MENU —
st.sidebar.image("hourglass_logo.png", width=80)
menu = st.sidebar.radio("Menu", ["Home", "Profile", "History", "Settings", "Logout"])

# — LOGOUT HANDLER —
if menu == "Logout":
    st.session_state.clear()
    st.experimental_rerun()

# — HOME PAGE —  
if menu == "Home":
    st.header(f"Hi {first_name}, estimate your time left ⏳")
    col1, col2 = st.columns([2,3])
    with col1:
        age = st.number_input("Current Age", 1, 120, 30)
        country = st.text_input("Country Code (e.g. US)", "US").upper()
        smoking = st.selectbox("Smoking habits", ["never","former","current"])
        exercise = st.selectbox("Exercise frequency", ["regular","occasional","none"])
        if st.button("Calculate & Save"):
            # fetch WB expectancy
            url = (
                f"http://api.worldbank.org/v2/country/{country}"
                "/indicator/SP.DYN.LE00.IN?format=json&per_page=100"
            )
            try:
                resp = requests.get(url).json()
                base = next((item["value"] for item in resp[1] if item["value"]), 75)
            except:
                base = 75
            score = (2 if smoking=="never" else -5 if smoking=="current" else 0) \
                  + (3 if exercise=="regular" else -3 if exercise=="none" else 0)
            final = base + score
            rem_y = final - age
            rem_s = int(rem_y * 31536000)
            st.success(f"Remaining: **{rem_y:.2f} years** ({rem_s:,} seconds)")
            # upsert record
            supabase.table("user_life_expectancy").upsert({
                "user_email": user_email,
                "first_name": first_name,
                "last_name": last_name,
                "age": age,
                "country_code": country,
                "lifestyle": json.dumps({"smoking":smoking,"exercise":exercise}),
                "locations": json.dumps([]),
                "genetic_factors": json.dumps({}),
                "expectancy_years": float(final),
                "remaining_seconds": rem_s,
                "updated_at": datetime.utcnow().isoformat()
            }, on_conflict="user_email").execute()
    with col2:
        st.image(
            "https://upload.wikimedia.org/wikipedia/commons/e/e1/Hourglass_animation.gif",
            caption="Time keeps flowing…",
            use_column_width=True
        )

# — PROFILE PAGE —  
elif menu == "Profile":
    st.header("Your Profile")
    col1, col2 = st.columns(2)
    with col1:
        fn2 = st.text_input("First name", first_name)
        ln2 = st.text_input("Last name",  last_name)
    with col2:
        st.write(f"**Email:** {user_email}")
        if st.button("Save profile"):
            supabase.table("user_life_expectancy") \
                .update({"first_name":fn2,"last_name":ln2}) \
                .eq("user_email",user_email).execute()
            st.success("Profile updated")
            st.experimental_rerun()

# — HISTORY PAGE —  
elif menu == "History":
    st.header("Your History")
    rows = supabase.table("user_life_expectancy") \
        .select("*") \
        .eq("user_email",user_email) \
        .order("updated_at", desc=False).execute().data
    if rows:
        df = pd.DataFrame(rows)
        st.dataframe(df[["updated_at","expectancy_years","remaining_seconds"]])
        # simple time series chart
        df["updated_at"] = pd.to_datetime(df["updated_at"])
        st.line_chart(df.set_index("updated_at")["remaining_seconds"])
    else:
        st.info("No history yet. Do a calculation on Home!")

# — SETTINGS PAGE —  
elif menu == "Settings":
    st.header("Settings")
    theme = st.radio("Theme", ["Dark","Light"], index=0)
    if theme == "Light":
        st.write("⚠️ You will need to manually switch your browser to light mode.")
    st.write("No further settings yet.")


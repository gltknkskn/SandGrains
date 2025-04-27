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

# — PAGE CONFIGURATION —
st.set_page_config(
    page_title="SandGrains",
    page_icon="⏳",
    layout="wide",
    initial_sidebar_state="expanded"
)

# — AUTHENTICATION HELPER —
def login_or_signup(email, password):
    try:
        return supabase.auth.sign_in_with_password({"email": email, "password": password})
    except:
        supabase.auth.sign_up({"email": email, "password": password})
        return supabase.auth.sign_in_with_password({"email": email, "password": password})

# — INITIAL LOGIN FLOW —
if "user" not in st.session_state:
    st.session_state.user = None

if st.session_state.user is None:
    st.markdown("# SandGrains ⏳")
    st.write("Free life-expectancy calculator. Enter your email & password.")
    email = st.text_input("Email address")
    password = st.text_input("Password (≥9 chars)", type="password")
    if st.button("Continue"):
        if not email or not password:
            st.error("Both fields are required.")
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

# — ENSURE PROFILE RECORD EXISTS —
user_email = st.session_state.user.email
profile = (
    supabase.table("user_life_expectancy")
    .select("first_name,last_name")
    .eq("user_email", user_email)
    .maybe_single()
    .execute()
    .data
)

if not profile:
    st.header("Welcome! What’s your name?")
    fn = st.text_input("First name")
    ln = st.text_input("Last name")
    if st.button("Save"):
        supabase.table("user_life_expectancy").insert({
            "user_email": user_email,
            "first_name": fn,
            "last_name": ln,
            "updated_at": datetime.utcnow().isoformat()
        }).execute()
        st.success("Thanks! Name saved.")
        st.experimental_rerun()
    st.stop()

first_name = profile["first_name"]
last_name  = profile["last_name"]

# — SIDEBAR MENU —
st.sidebar.image("hourglass_logo.png", width=80)
page = st.sidebar.radio("Menu", ["Home", "Profile", "History", "Settings", "Logout"])

# — LOGOUT HANDLER —
if page == "Logout":
    st.session_state.clear()
    st.experimental_rerun()

# — PAGE: HOME —  
if page == "Home":
    st.header(f"Hi {first_name}, estimate your time left ⏳")
    left, right = st.columns([2,3])
    with left:
        age = st.number_input("Your Age", 1, 120, 30)
        country = st.text_input("Country Code (US, TR, DE…)", "US").upper()
        smoking = st.selectbox("Smoking habits", ["never", "former", "current"])
        exercise = st.selectbox("Exercise frequency", ["regular", "occasional", "none"])
        if st.button("Calculate & Save"):
            # fetch base expectancy
            try:
                r = requests.get(
                    f"http://api.worldbank.org/v2/country/{country}"
                    "/indicator/SP.DYN.LE00.IN?format=json&per_page=100"
                ).json()
                base = next((it["value"] for it in r[1] if it["value"]), 75)
            except:
                base = 75
            score = (2 if smoking=="never" else -5 if smoking=="current" else 0) \
                  + (3 if exercise=="regular" else -3 if exercise=="none" else 0)
            final = base + score
            rem_y = final - age
            rem_s = int(rem_y * 31536000)
            st.success(f"Remaining life: {rem_y:.2f} years ({rem_s:,} sec)")
            # upsert record
            supabase.table("user_life_expectancy").upsert({
                "user_email": user_email,
                "first_name": first_name,
                "last_name": last_name,
                "age": age,
                "country_code": country,
                "lifestyle": json.dumps({"smoking": smoking, "exercise": exercise}),
                "locations": json.dumps([]),
                "genetic_factors": json.dumps({}),
                "expectancy_years": float(final),
                "remaining_seconds": rem_s,
                "updated_at": datetime.utcnow().isoformat()
            }, on_conflict="user_email").execute()
    with right:
        st.image(
            "https://upload.wikimedia.org/wikipedia/commons/e/e1/Hourglass_animation.gif",
            caption="Time flows on…",
            use_column_width=True
        )

# — PAGE: PROFILE —  
elif page == "Profile":
    st.header("Your Profile")
    c1, c2 = st.columns(2)
    with c1:
        fn2 = st.text_input("First name", first_name)
        ln2 = st.text_input("Last name",  last_name)
    with c2:
        st.write(f"**Email:** {user_email}")
        if st.button("Save Changes"):
            supabase.table("user_life_expectancy").update({
                "first_name": fn2,
                "last_name": ln2
            }).eq("user_email", user_email).execute()
            st.success("Profile updated.")
            st.experimental_rerun()

# — PAGE: HISTORY —  
elif page == "History":
    st.header("Your Calculation History")
    rows = (
        supabase.table("user_life_expectancy")
        .select("*")
        .eq("user_email", user_email)
        .order("updated_at", asc=True)
        .execute()
        .data
    )
    if rows:
        df = pd.DataFrame(rows)
        df["updated_at"] = pd.to_datetime(df["updated_at"])
        st.dataframe(df[["updated_at","expectancy_years","remaining_seconds"]])
        st.line_chart(df.set_index("updated_at")["remaining_seconds"])
    else:
        st.info("No history found. Try a calculation on Home.")

# — PAGE: SETTINGS —  
elif page == "Settings":
    st.header("Settings")
    theme = st.radio("Theme", ["Dark","Light"], index=0)
    st.write("To switch theme, use your browser/OS setting.")


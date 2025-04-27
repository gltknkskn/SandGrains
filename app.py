import streamlit as st
import requests
import json
import os
from datetime import datetime
from supabase import create_client
from dotenv import load_dotenv
import pandas as pd

# — ENVIRONMENT —
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# — PAGE CONFIG —
st.set_page_config(
    page_title="SandGrains",
    page_icon="⏳",
    layout="wide",
    initial_sidebar_state="expanded"
)

# — GLOBAL CSS —
st.markdown("""
<style>
/* Sidebar gradient & fixed width */
[data-testid="stSidebar"] {
  background: linear-gradient(180deg,#1a1a2e 0%,#26273a 100%);
  padding-top: 1rem;
  width: 220px !important;
}
/* Sidebar logo full width */
[data-testid="stSidebar"] img {
  width: 100% !important;
  height: auto;
  margin-bottom: 0.5rem;
}
/* Sidebar title under logo */
.sidebar-title {
  color: #ffffff;
  font-size: 1.25rem;
  font-weight: bold;
  text-align: center;
  margin-bottom: 1rem;
}
/* Main area background */
[data-testid="stAppViewContainer"] {
  background: #0f0f13;
}
/* Card style */
.card {
  background: #1e1e2d;
  padding: 1.5rem;
  border-radius: 12px;
  margin-bottom: 1.5rem;
  box-shadow: 0 4px 12px rgba(0,0,0,0.3);
}
/* Button style */
.stButton>button {
  background-color: #e94e77;
  color: white;
  border: none;
  padding: 0.6rem 1.2rem;
  border-radius: 8px;
}
/* Hide default menu/footer */
#MainMenu, footer { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# — SIDEBAR: logo and title —
st.sidebar.image("hourglass_logo.png")
st.sidebar.markdown("<div class='sidebar-title'>SandGrains</div>", unsafe_allow_html=True)
page = st.sidebar.radio(
    "Navigation",
    ["Login", "Calculator", "Chat Helper", "History", "Settings", "Logout"],
    index=0
)

# — LOGOUT —
if page == "Logout":
    st.session_state.clear()
    st.experimental_rerun()

# — AUTH HELPERS —
def login_with_signup(email, pwd):
    # attempt sign in first
    try:
        res = supabase.auth.sign_in_with_password({"email": email, "password": pwd})
        return res
    except Exception:
        # if sign in fails, try sign up
        try:
            supabase.auth.sign_up({"email": email, "password": pwd})
        except Exception:
            # likely weak password
            st.error("Password too weak or policy violation. Please choose a stronger password.")
            return None
        # after signup, sign in
        try:
            res2 = supabase.auth.sign_in_with_password({"email": email, "password": pwd})
            return res2
        except Exception:
            st.error("Signup succeeded but login failed.")
            return None

# — AUTH FLOW —
if "user" not in st.session_state or not st.session_state.user:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.header("Login")
    st.write("Free life-expectancy calculator. Please sign in or sign up.")
    email = st.text_input("Email")
    pwd = st.text_input("Password (≥9 chars)", type="password")
    if st.button("Sign In / Up"):
        if email and len(pwd) >= 9:
            result = login_with_signup(email, pwd)
            if result and getattr(result, "user", None):
                st.session_state.user = result.user
                st.success("Authenticated! Redirecting…")
                st.experimental_rerun()
            elif result is None:
                # error already shown
                pass
            else:
                st.error("Authentication failed. Please verify your credentials.")
        else:
            st.error("Enter a valid email and a password of at least 9 characters.")
    st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

# user must be authenticated at this point
user_email = st.session_state.user.email

# — ENSURE PROFILE EXISTS —
profiling = supabase.table("user_life_expectancy").select("first_name").eq("user_email", user_email).maybe_single().execute().data
if not profiling:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.header("Welcome! What’s your name?")
    fn = st.text_input("First name")
    if st.button("Save"):
        supabase.table("user_life_expectancy").insert({
            "user_email": user_email,
            "first_name": fn,
            "updated_at": datetime.utcnow().isoformat()
        }).execute()
        st.success("Name saved! Redirecting…")
        st.experimental_rerun()
    st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

first_name = profiling["first_name"]

# — CARD WRAPPER —
def card(title, content_fn):
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.subheader(title)
    content_fn()
    st.markdown("</div>", unsafe_allow_html=True)

# — CALCULATOR —
if page == "Calculator":
    def calc_box():
        age = st.number_input("Age", 1, 120, 30)
        country = st.text_input("Country Code (US,TR,DE…)", "US").upper()
        smoke = st.selectbox("Smoking", ["never", "former", "current"])
        exer = st.selectbox("Exercise", ["regular", "occasional", "none"])
        if st.button("Compute"):
            try:
                w = requests.get(
                    f"http://api.worldbank.org/v2/country/{country}/indicator/SP.DYN.LE00.IN?format=json&per_page=100"
                ).json()
                base = next((i["value"] for i in w[1] if i["value"]), 75)
            except:
                base = 75
            score = (2 if smoke == "never" else -5 if smoke == "current" else 0) + (3 if exer == "regular" else -3 if exer == "none" else 0)
            final = base + score
            rem_y = final - age
            rem_s = int(rem_y * 31536000)
            st.success(f"⏳ {rem_y:.2f} years — {rem_s:,} seconds")
            supabase.table("user_life_expectancy").upsert({
                "user_email": user_email,
                "first_name": first_name,
                "age": age,
                "country_code": country,
                "lifestyle": json.dumps({"smoke": smoke, "exercise": exer}),
                "expectancy_years": float(final),
                "remaining_seconds": rem_s,
                "updated_at": datetime.utcnow().isoformat()
            }, on_conflict="user_email").execute()
    card(f"Hello {first_name}, estimate your time left", calc_box)

# — CHAT HELPER —
elif page == "Chat Helper":
    def chat_box():
        prompt = st.text_input("Ask for a quick tip (e.g. best exercise tip?)")
        if st.button("Send"):
            if "exercise" in prompt.lower():
                st.info("Try brisk walking 30 min/day — adds ~3 years!")
            else:
                st.info("Eat more fruits, veggies & whole grains daily.")
    card("💬 Quick Health Tips", chat_box)

# — HISTORY —
elif page == "History":
    def history_box():
        rows = supabase.table("user_life_expectancy").select("updated_at,remaining_seconds").eq("user_email", user_email).order("updated_at", asc=True).execute().data
        if rows:
            df = pd.DataFrame(rows)
            df["updated_at"] = pd.to_datetime(df["updated_at"])
            st.line_chart(df.set_index("updated_at")["remaining_seconds"])
        else:
            st.info("No history yet.")
    card("⏳ Your History", history_box)

# — SETTINGS —
elif page == "Settings":
    def settings_box():
        if st.button("Clear History"):
            supabase.table("user_life_expectancy").delete().eq("user_email", user_email).execute()
            st.success("History cleared.")
    card("⚙️ Settings", settings_box)

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

# — GLOBAL STYLES —
st.markdown("""
<style>
/* Sidebar gradient background */
[data-testid="stSidebar"] {
  background: linear-gradient(180deg, #1a1a2e 0%, #26273a 100%);
  padding-top: 1rem;
}
/* Sidebar logo spacing */
[data-testid="stSidebar"] img {
  margin-bottom: 2rem;
}
/* Main area background */
[data-testid="stAppViewContainer"] {
  background: #0f0f13;
}
/* Card style */
.card {
  background:#1e1e2d; padding:1.5rem; border-radius:12px; margin-bottom:1.5rem;
  box-shadow: 0 4px 12px rgba(0,0,0,0.3);
}
/* Button style */
.stButton>button {
  background-color: #e94e77;
  color: white;
  border: none;
  padding: .6rem 1.2rem;
  border-radius: 8px;
}
/* Hide default Streamlit menu & footer */
#MainMenu, footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# — SIDEBAR: LOGO + MENU —
st.sidebar.image("hourglass_logo.png", width=200)
page = st.sidebar.radio(
    "Navigation",
    ["Login", "Home", "Profile", "History", "Settings", "Logout"]
)

# — AUTH HELPER —
def login_or_signup(email, password):
    try:
        return supabase.auth.sign_in_with_password({"email": email, "password": password})
    except:
        supabase.auth.sign_up({"email": email, "password": password})
        return supabase.auth.sign_in_with_password({"email": email, "password": password})

# — LOGOUT —
if page == "Logout":
    st.session_state.clear()
    st.experimental_rerun()

# — LOGIN PAGE —
if page == "Login":
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.header("SandGrains ⏳")
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
            if getattr(res, "user", None):
                st.session_state.user = res.user
                st.success("Logged in! Redirecting…")
                st.experimental_rerun()
            else:
                st.error("Login/Signup failed.")
    st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

# — AUTH GUARD —
if "user" not in st.session_state or not st.session_state.user:
    st.sidebar.error("Please log in first")
    st.experimental_rerun()

user_email = st.session_state.user.email

# — ENSURE PROFILE EXISTS —
prof_resp = (
    supabase.table("user_life_expectancy")
    .select("first_name,last_name")
    .eq("user_email", user_email)
    .maybe_single()
    .execute()
)
prof = prof_resp.data
if not prof:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
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
        st.success("Name saved.")
        st.experimental_rerun()
    st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

first_name = prof["first_name"]
last_name  = prof["last_name"]

# — CARD UTIL —
def card(title, fn):
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.subheader(title)
    fn()
    st.markdown("</div>", unsafe_allow_html=True)

# — HOME PAGE —
if page == "Home":
    card(f"Hi {first_name}, estimate your time left ⏳", lambda: None)
    def home_ui():
        age = st.number_input("Your Age", 1, 120, 30)
        country = st.text_input("Country Code (US, TR, DE…)", "US").upper()
        smoking = st.selectbox("Smoking habits", ["never","former","current"])
        exercise = st.selectbox("Exercise frequency", ["regular","occasional","none"])
        if st.button("Calculate & Save"):
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
    left, right = st.columns([1,2], gap="large")
    with left:
        home_ui()
    with right:
        st.image(
            "https://upload.wikimedia.org/wikipedia/commons/e/e1/Hourglass_animation.gif",
            caption="Time flows on…",
            use_column_width=True
        )

# — PROFILE PAGE —
elif page == "Profile":
    def profile_ui():
        fn2 = st.text_input("First name", first_name)
        ln2 = st.text_input("Last name",  last_name)
        if st.button("Save Changes"):
            supabase.table("user_life_expectancy").update({
                "first_name": fn2,
                "last_name": ln2
            }).eq("user_email", user_email).execute()
            st.success("Profile updated.")
            st.experimental_rerun()
    card("Your Profile", profile_ui)

# — HISTORY PAGE —
elif page == "History":
    def history_ui():
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
            st.info("No history yet. Try a calculation on Home.")
    card("Your Calculation History", history_ui)

# — SETTINGS PAGE —
elif page == "Settings":
    def settings_ui():
        theme = st.radio("Theme", ["Dark","Light"], index=0)
        st.write("To switch theme, use your browser/OS setting.")
    card("Settings", settings_ui)

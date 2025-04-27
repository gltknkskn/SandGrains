import streamlit as st
import requests, json, os
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

# — CSS STYLES —
st.markdown("""
<style>
[data-testid="stSidebar"] {background: #1a1a2e; width:220px !important; padding-top:1rem;}
[data-testid="stSidebar"] img {width:100%!important;margin-bottom:1rem;}
.sidebar-title {color:#fff; text-align:center; font-weight:bold; margin-bottom:1rem;}
[data-testid="stAppViewContainer"] {background:#0f0f13;}
.card {background:#1e1e2d; padding:1.5rem; border-radius:12px; margin:1rem 0; box-shadow:0 4px 12px rgba(0,0,0,0.3);}
.stButton>button {background:#e94e77; color:#fff; border:none; padding:.6rem 1.2rem; border-radius:8px;}
#MainMenu, footer {visibility:hidden;}
</style>
""", unsafe_allow_html=True)

# — NAVIGATION STATE init —
if "page" not in st.session_state:
    st.session_state.page = "Login"
if "user" not in st.session_state:
    st.session_state.user = None

# — SIDEBAR —
st.sidebar.image("hourglass_logo.png")
st.sidebar.markdown("<div class='sidebar-title'>SandGrains</div>", unsafe_allow_html=True)
choice = st.sidebar.radio("Navigation",
                          ["Login","Calculator","Chat Helper","History","Settings","Logout"],
                          index=["Login","Calculator","Chat Helper","History","Settings","Logout"].index(st.session_state.page))
# Update state
st.session_state.page = choice

# — LOGOUT —
if st.session_state.page == "Logout":
    st.session_state.user = None
    st.stop()

# — AUTH HELPERS —
def auth_flow(email, pwd):
    try:
        return supabase.auth.sign_in_with_password({"email":email,"password":pwd})
    except:
        try:
            supabase.auth.sign_up({"email":email,"password":pwd})
        except:
            return None
        return supabase.auth.sign_in_with_password({"email":email,"password":pwd})

# — LOGIN SCREEN —
if st.session_state.page == "Login":
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.header("Login")
    st.write("Free life-expectancy calculator. Sign in or sign up.")
    email = st.text_input("Email")
    pwd   = st.text_input("Password (≥9 chars)", type="password")
    if st.button("Sign In / Up"):
        if email and len(pwd)>=9:
            res = auth_flow(email,pwd)
            if res and getattr(res,"user",None):
                st.session_state.user = res.user
                st.session_state.page = "Calculator"
            else:
                st.error("Authentication failed or weak password.")
        else:
            st.error("Enter valid email & ≥9-char password.")
    st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

# — ENSURE AUTH —
if st.session_state.page != "Login" and not st.session_state.user:
    st.warning("Please log in first.")
    st.stop()

# — PROFILE SETUP —
if st.session_state.user:
    email = st.session_state.user.email
    prof = supabase.table("user_life_expectancy")\
        .select("first_name")\
        .eq("user_email",email)\
        .maybe_single()\
        .execute().data
    if not prof and st.session_state.page!="Login":
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.header("Welcome! What’s your name?")
        fn = st.text_input("First name")
        if st.button("Save Name"):
            supabase.table("user_life_expectancy").insert({
                "user_email":email,
                "first_name":fn,
                "updated_at":datetime.utcnow().isoformat()
            }).execute()
            st.session_state.page = "Calculator"
        st.markdown("</div>", unsafe_allow_html=True)
        st.stop()
    first_name = prof["first_name"]

# — CARD UTILITY —
def card(title, fn):
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.subheader(title)
    fn()
    st.markdown("</div>", unsafe_allow_html=True)

# — CALCULATOR —
if st.session_state.page == "Calculator":
    def run_calc():
        age = st.number_input("Age",1,120,30)
        country = st.text_input("Country Code (US,TR,DE…)", "US").upper()
        smoke = st.selectbox("Smoking", ["never","former","current"])
        exer  = st.selectbox("Exercise",["regular","occasional","none"])
        if st.button("Compute"):
            try:
                data = requests.get(
                    f"http://api.worldbank.org/v2/country/{country}"
                    "/indicator/SP.DYN.LE00.IN?format=json&per_page=100"
                ).json()
                base = next((i["value"] for i in data[1] if i["value"]),75)
            except:
                base=75
            score=(2 if smoke=="never" else -5 if smoke=="current" else 0)+\
                  (3 if exer=="regular" else -3 if exer=="none" else 0)
            final=base+score
            rem_y=final-age
            rem_s=int(rem_y*31536000)
            st.success(f"⏳ {rem_y:.2f} years — {rem_s:,} seconds")
            supabase.table("user_life_expectancy").upsert({
                "user_email":email,
                "first_name":first_name,
                "age":age,
                "country_code":country,
                "lifestyle":json.dumps({"smoke":smoke,"exercise":exer}),
                "expectancy_years":float(final),
                "remaining_seconds":rem_s,
                "updated_at":datetime.utcnow().isoformat()
            },on_conflict="user_email").execute()
    card(f"Hello {first_name}, estimate your time left", run_calc)

# — CHAT HELPER —
elif st.session_state.page == "Chat Helper":
    def run_chat():
        q = st.text_input("Ask a quick tip...")
        if st.button("Send"):
            if "exercise" in q.lower():
                st.info("Brisk walking 30 min/day adds ~3 years!")
            else:
                st.info("Eat more fruits, veggies & whole grains.")
    card("💬 Quick Health Tips", run_chat)

# — HISTORY —
elif st.session_state.page == "History":
    def run_hist():
        rows = supabase.table("user_life_expectancy")\
            .select("updated_at,remaining_seconds")\
            .eq("user_email",email)\
            .order("updated_at",asc=True).execute().data
        if rows:
            df = pd.DataFrame(rows)
            df["updated_at"] = pd.to_datetime(df["updated_at"])
            st.line_chart(df.set_index("updated_at")["remaining_seconds"])
        else:
            st.info("No history yet.")
    card("⏳ Your History", run_hist)

# — SETTINGS —
elif st.session_state.page == "Settings":
    def run_set():
        if st.button("Clear History"):
            supabase.table("user_life_expectancy")\
                .delete().eq("user_email",email).execute()
            st.success("History cleared.")
    card("⚙️ Settings", run_set)

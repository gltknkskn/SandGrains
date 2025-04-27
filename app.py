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
    initial_sidebar_state="expanded",
    menu_items={
        "Get help": "https://github.com/your-repo",
        "Report a bug": "https://github.com/your-repo/issues"
    }
)

# — STYLES —  
st.markdown("""
<style>
/* -- Sidebar Gradient -- */
[data-testid="stSidebar"] {
  background: linear-gradient(180deg,#1a1a2e 0%,#26273a 100%);
}
/* -- Card Style -- */
.card {
  background:#1e1e2d; padding:1.5rem; border-radius:12px; margin-bottom:1.5rem;
  box-shadow:0 4px 12px rgba(0,0,0,0.3);
}
/* -- Button Style -- */
.stButton>button {
  background-color:#e94e77; color:white; border:none; padding:0.6rem 1.2rem; border-radius:8px;
}
/* -- Hide Default Menu/Footer -- */
#MainMenu, footer {visibility:hidden;}
</style>
""", unsafe_allow_html=True)

# — SIDEBAR with Option Menu —  
from streamlit_option_menu import option_menu

with st.sidebar:
    st.image("hourglass_logo.png", width=150)
    menu_choice = option_menu(
        menu_title=None,
        options=["Calculator","Chat Helper","History","Settings","Logout"],
        icons=["calculator","chat","clock-history","gear","box-arrow-right"],
        menu_icon="hourglass-top",
        default_index=0,
        styles={
            "container": {"padding":"0!important","background-color":"#1a1a2e"},
            "nav-link": {"font-size":"16px","text-align":"left","margin":"0px","--hover-color":"#3a3a5e"},
            "nav-link-selected": {"background-color":"#e94e77"},
        }
    )
    st.markdown("---")
    show_tips = st.checkbox("Show Tips", value=True)
    if show_tips:
        st.markdown("""
        - **Calculator**: Estimate your remaining life in seconds.  
        - **Chat Helper**: Ask quick tips on healthy habits.  
        - **History**: Review previous calculations.  
        """)
  
# — LOGOUT —  
if menu_choice=="Logout":
    st.session_state.clear()
    st.experimental_rerun()

# — AUTH (optional) —  
# (Eğer kullanıcı auth istemiyorsan bu kısmı bypass edebilirsin.)

if "user" not in st.session_state:
    st.session_state.user = None

# Simple email/password auth
def auth_flow():
    st.markdown("<div class='card'>",unsafe_allow_html=True)
    st.header("SandGrains ⏳ Login")
    email = st.text_input("Email")
    pwd = st.text_input("Password (≥9 chars)", type="password")
    if st.button("Sign In / Up"):
        if email and len(pwd)>=9:
            try:
                res = supabase.auth.sign_in_with_password({"email":email,"password":pwd})
            except:
                supabase.auth.sign_up({"email":email,"password":pwd})
                res = supabase.auth.sign_in_with_password({"email":email,"password":pwd})
            if res.user:
                st.session_state.user = res.user
                st.success("Authenticated!")
                st.experimental_rerun()
            else:
                st.error("Auth failed")
        else:
            st.error("Provide valid creds")
    st.markdown("</div>",unsafe_allow_html=True)
    st.stop()

if not st.session_state.user:
    auth_flow()

user_email = st.session_state.user.email

# Ensure profile row
profile = supabase.table("user_life_expectancy")\
    .select("first_name")\
    .eq("user_email",user_email).maybe_single().execute().data
if not profile:
    st.markdown("<div class='card'>",unsafe_allow_html=True)
    st.header("Welcome! Enter your name")
    fn = st.text_input("First name")
    if st.button("Save"):
        supabase.table("user_life_expectancy")\
            .insert({"user_email":user_email,"first_name":fn,"updated_at":datetime.utcnow().isoformat()}).execute()
        st.success("Saved!")
        st.experimental_rerun()
    st.markdown("</div>",unsafe_allow_html=True)
    st.stop()
first_name = profile["first_name"]

# — Helper to show cards —  
def show_card(title, content_fn):
    st.markdown("<div class='card'>",unsafe_allow_html=True)
    st.subheader(title)
    content_fn()
    st.markdown("</div>",unsafe_allow_html=True)

# — CALCULATOR —  
if menu_choice=="Calculator":
    def calc_ui():
        age = st.number_input("Age",1,120,30)
        country = st.text_input("Country (US,TR,DE…)", "US").upper()
        smoke = st.selectbox("Smoking",["never","former","current"])
        exercise = st.selectbox("Exercise",["regular","occasional","none"])
        if st.button("Compute"):
            # WorldBank fetch
            try:
                data = requests.get(f"http://api.worldbank.org/v2/country/{country}/indicator/SP.DYN.LE00.IN?format=json&per_page=100").json()
                base = next((i["value"] for i in data[1] if i["value"]),75)
            except:
                base = 75
            score = (2 if smoke=="never" else -5 if smoke=="current" else 0) + \
                    (3 if exercise=="regular" else -3 if exercise=="none" else 0)
            final = base+score
            rem_y = final-age; rem_s = int(rem_y*31536000)
            st.success(f"⏳ {rem_y:.2f} yrs ({rem_s:,} sec)")
            # upsert
            supabase.table("user_life_expectancy").upsert({
                "user_email":user_email,
                "first_name":first_name,
                "age":age,
                "country_code":country,
                "lifestyle":json.dumps({"smoke":smoke,"ex":exercise}),
                "expectancy_years":float(final),
                "remaining_seconds":rem_s,
                "updated_at":datetime.utcnow().isoformat()
            }, on_conflict="user_email").execute()
    show_card(f"Hello {first_name}, calculate your time left", calc_ui)

# — CHAT HELPER —  
elif menu_choice=="Chat Helper":
    st.subheader("💬 Quick Health Tips")
    chat = st.chat_input("Ask me something like, ‘best exercise tip?’")
    if chat:
        reply = ""
        if "exercise" in chat.lower():
            reply = "Try 30 mins brisk walk daily — it adds ~3 years to your expectancy!"
        else:
            reply = "Maintain a balanced diet rich in fruits, vegs, and whole grains."
        st.session_state.setdefault("history", []).append((chat, reply))
    for q,a in st.session_state.get("history",[])[-10:]:
        with st.chat_message("user"):
            st.write(q)
        with st.chat_message("assistant"):
            st.write(a)

# — HISTORY —  
elif menu_choice=="History":
    rows = supabase.table("user_life_expectancy")\
        .select("updated_at,remaining_seconds")\
        .eq("user_email",user_email)\
        .order("updated_at",asc=True).execute().data
    if rows:
        df = pd.DataFrame(rows)
        df["updated_at"]=pd.to_datetime(df["updated_at"])
        st.line_chart(df.set_index("updated_at")["remaining_seconds"])
    else:
        st.info("No history yet.")

# — SETTINGS —  
elif menu_choice=="Settings":
    st.subheader("⚙️ Settings")
    if st.button("Clear History"):
        supabase.table("user_life_expectancy")\
            .delete().eq("user_email",user_email).execute()
        st.success("History cleared!")  

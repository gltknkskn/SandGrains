import streamlit as st
import requests
from supabase import create_client
import uuid
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Supabase connection
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Updated and more stable World Bank API handler
def get_life_expectancy(country_code):
    url = f"http://api.worldbank.org/v2/country/{country_code}/indicator/SP.DYN.LE00.IN?format=json&per_page=100"
    try:
        response = requests.get(url)
        data = response.json()
        if data and len(data) > 1 and isinstance(data[1], list):
            for item in data[1]:
                if item["value"] is not None:
                    return item["value"]
        return 75
    except Exception:
        return 75

# Streamlit app
st.set_page_config(page_title="SandGrains - Life Expectancy", page_icon="⏳")
st.title("⏳ SandGrains - Life Expectancy Calculator")

st.write("Estimate your remaining lifetime based on your current habits and environment.")

user_identifier = st.text_input("Enter your unique username or email")
age = st.number_input("Your Current Age", min_value=1, max_value=120, value=30)
country_code = st.text_input("Country Code (e.g., US, TR, DE)", value="US").upper()
smoking = st.selectbox("Smoking habits", ["never", "former", "current"])
exercise = st.selectbox("Exercise frequency", ["regular", "occasional", "none"])

if st.button("Calculate & Save"):

    if not user_identifier:
        st.error("Please enter your username or email.")
        st.stop()

    base_expectancy = get_life_expectancy(country_code)

    if base_expectancy is None:
        st.error("Unable to retrieve life expectancy data. Please check the country code.")
        st.stop()

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
        "user_id": str(uuid.uuid5(uuid.NAMESPACE_DNS, user_identifier)),
        "age": age,
        "country_code": country_code,
        "locations": [],
        "lifestyle": {"smoking": smoking, "exercise": exercise},
        "genetic_factors": {},
        "expectancy_years": final_expectancy,
        "remaining_seconds": remaining_seconds,
        "updated_at": datetime.utcnow().isoformat()
    }

    existing = supabase.table("user_life_expectancy").select("*").eq("user_id", data["user_id"]).execute()

    if existing.data:
        supabase.table("user_life_expectancy").update(data).eq("user_id", data["user_id"]).execute()
        st.info("Your information has been updated.")
    else:
        data["id"] = str(uuid.uuid4())
        supabase.table("user_life_expectancy").insert(data).execute()
        st.info("Your information has been saved.")

# Show previous data
if user_identifier:
    user_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, user_identifier))
    user_data = supabase.table("user_life_expectancy").select("*").eq("user_id", user_uuid).execute()

    if user_data.data:
        st.subheader("Your Last Recorded Data:")
        st.json(user_data.data[0])

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

# Function to get dynamic life expectancy data from World Bank API
def get_life_expectancy(country_code):
    url = f"http://api.worldbank.org/v2/country/{country_code}/indicator/SP.DYN.LE00.IN?format=json"
    try:
        response = requests.get(url)
        data = response.json()
        return data[1][0]["value"]
    except Exception:
        return 75  # Default value if API call fails

# Streamlit page
st.set_page_config(page_title="SandGrains - Life Expectancy", page_icon="⏳")
st.title("⏳ SandGrains - Life Expectancy Calculator")

st.write("Estimate your remaining lifetime based on your current habits and environment.")

# User inputs
user_identifier = st.text_input("Enter your unique username or email")

age = st.number_input("Your Current Age", min_value=1, max_value=120, value=30)
country_code = st.text_input("Country Code (e.g., US, TR, DE)", value="US").upper()

smoking = st.selectbox("Smoking habits", ["never", "former", "current"])
exercise = st.selectbox("Exercise frequency", ["regular", "occasional", "none"])

if st.button("Calculate & Save"):

    if not user_identifier:
        st.error("Please enter your username or email.")
        st.stop()

    # Fetch base life expectancy
    base_expectancy = get_life_expectancy(country_code)

    # Lifestyle factor scoring
    factor_score = 0
    if smoking == "never":
        factor_score += 2
    elif smoking == "current":
        factor_score -= 5

    if exercise == "regular":
        factor_score += 3
    elif exercise == "none":
        factor_score -= 3

    # Final life expectancy calculation
    final_expectancy = base_expectancy + factor_score
    remaining_years = final_expectancy - age
    remaining_seconds = int(remaining_years * 31536000)

    st.success(f"Your estimated remaining life: {remaining_years:.2f} years ({remaining_seconds:,} seconds)")

    # Prepare user data
    data = {
        "user_id": str(uuid.uuid5(uuid.NAMESPACE_DNS, user_identifier)),
        "age": age,
        "country_code": country_code,
        "locations": [],  # Reserved for future expansion
        "lifestyle": {"smoking": smoking, "exercise": exercise},
        "genetic_factors": {},  # Reserved for future expansion
        "expectancy_years": final_expectancy,
        "remaining_seconds": remaining_seconds,
        "updated_at": datetime.utcnow().isoformat()
    }

    # Check if the user already exists
    existing = supabase.table("user_life_expectancy").select("*").eq("user_id", data["user_id"]).execute()

    if existing.data:
        # Update existing record
        supabase.table("user_life_expectancy").update(data).eq("user_id", data["user_id"]).execute()
        st.info("Your information has been updated.")
    else:
        # Insert new record
        data["id"] = str(uuid.uuid4())
        supabase.table("user_life_expectancy").insert(data).execute()
        st.info("Your information has been saved.")

# Optionally: Show last saved user data
if user_identifier:
    user_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, user_identifier))
    user_data = supabase.table("user_life_expectancy").select("*").eq("user_id", user_uuid).execute()

    if user_data.data:
        st.subheader("Your Last Recorded Data:")
        st.json(user_data.data[0])

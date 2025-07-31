# app.py

import os
import requests
import pandas as pd
import streamlit as st
import folium
from streamlit_folium import st_folium
from src.fetch_aqi import fetch_daily_aqi

# --- Page Config ---
st.set_page_config(
    page_title="AQI Explorer",
    layout="wide",
    initial_sidebar_state="expanded"
)
st.title("🌬️ AQI Explorer")

# --- Sidebar: Settings ---
st.sidebar.header("Settings")

# Available cities
CITIES = {
    "Atlanta, GA":      "30301",
    "Billings, MT":     "59101",
    "Boston, MA":       "02108",
    "Chicago, IL":      "60601",
    "Denver, CO":       "80202",
    "Des Moines, IA":   "50309",
    "Houston, TX":      "77001",
    "Kansas City, MO":  "64101",
    "Minneapolis, MN":  "55401",
    "New York, NY":     "10001",
    "Philadelphia, PA": "19104",
    "Phoenix, AZ":      "85001",
    "San Francisco, CA":"94103",
    "Seattle, WA":      "98101",
    "Omaha, NE":        "68102",
}

labels = list(CITIES.keys())
selected_labels = st.sidebar.multiselect(
    "Select cities",
    options=labels,
    default=["New York, NY", "Los Angeles, CA"] if "Los Angeles, CA" in labels else labels[:3]
)

# Date range picker
today = pd.Timestamp.today().normalize()
default_start = today - pd.Timedelta(days=7)
default_end   = today
start_date, end_date = st.sidebar.date_input(
    "Date range",
    value=[default_start, default_end],
    min_value=pd.Timestamp("2015-01-01"),
    max_value=today
)
start_date, end_date = sorted((pd.to_datetime(start_date), pd.to_datetime(end_date)))

# Enforce limits to prevent rate-limit
MAX_CITIES = 5
MAX_DAYS   = 7
if len(selected_labels) > MAX_CITIES:
    st.sidebar.error(f"Select at most {MAX_CITIES} cities.")
    st.stop()
if (end_date - start_date).days > MAX_DAYS:
    st.sidebar.error(f"Date range must be ≤ {MAX_DAYS} days.")
    st.stop()

# Build the list of (zip, city)
cities_to_fetch = [(CITIES[label], label) for label in selected_labels]

# --- Debug Panel ---
st.sidebar.markdown("---")
st.sidebar.subheader("🔧 Debug")
api_key = os.getenv("AIRNOW_API_KEY", "")
st.sidebar.write("API key loaded:", bool(api_key), f"(length={len(api_key)})")

if st.sidebar.button("Test NYC fetch"):
    try:
        demo = fetch_daily_aqi("10001", start_date.strftime("%Y-%m-%d"))
        st.sidebar.success(f"Fetched {len(demo)} observations for 10001 on {start_date.date()}")
        st.sidebar.json(demo)
    except Exception as e:
        st.sidebar.error(f"{type(e).__name__}: {e}")

# --- Data Loader ---
@st.cache_data
def load_aqi_data(city_list, start, end):
    dates   = pd.date_range(start, end)
    records = []

    for zip_code, city in city_list:
        rate_limited = False
        for dt in dates:
            try:
                obs_list = fetch_daily_aqi(zip_code, dt.strftime("%Y-%m-%d"))
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 429:
                    rate_limited = True
                    break
                else:
                    # log other errors but continue
                    st.sidebar.error(f"API error for {city} on {dt.date()}: {e}")
                    continue

            for obs in obs_list:
                records.append({
                    "date":     pd.to_datetime(obs["DateObserved"]),
                    "city":     city,
                    "AQI":      obs["AQI"],
                    "category": obs["Category"]["Name"],
                    "lat":      obs["Latitude"],
                    "lon":      obs["Longitude"]
                })

        if rate_limited:
            st.sidebar.warning(
                f"Rate limit reached for {city}. "
                "Skipping remaining dates for this city."
            )

    st.sidebar.write(f"Total records fetched: {len(records)}")
    return pd.DataFrame(records)

df = load_aqi_data(cities_to_fetch, start_date, end_date)

# --- Time-Series Plot ---
st.subheader("Daily Max AQI Trends")
if not df.empty:
    df_max = df.groupby(["date", "city"])["AQI"].max().reset_index()
    pivot = df_max.pivot(index="date", columns="city", values="AQI")
    st.line_chart(pivot, use_container_width=True)
else:
    st.info("No data to display. Try adjusting cities or date range.")

# --- Interactive Map ---
st.subheader("Latest AQI Map")
if not df.empty:
    latest_date = df["date"].max()
    latest     = df[df["date"] == latest_date].drop_duplicates("city")
    m = folium.Map(
        location=[latest["lat"].mean(), latest["lon"].mean()],
        zoom_start=4
    )
    cat_colors = {
        "Good": "green",
        "Moderate": "yellow",
        "Unhealthy for Sensitive Groups": "orange",
        "Unhealthy": "red",
        "Very Unhealthy": "purple",
        "Hazardous": "maroon"
    }
    for _, row in latest.iterrows():
        folium.CircleMarker(
            [row["lat"], row["lon"]],
            radius=8,
            color=cat_colors.get(row["category"], "gray"),
            fill=True,
            fill_color=cat_colors.get(row["category"], "gray"),
            fill_opacity=0.7,
            popup=f"{row['city']}: AQI {row['AQI']} ({row['category']})"
        ).add_to(m)
    st_folium(m, width=800, height=400)
else:
    st.info("No map to display. Try adjusting cities or date range.")

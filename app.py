# app.py

import os
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

# --- Sidebar Controls ---
st.sidebar.header("Settings")

# List of (ZIP, City) tuples
cities = [
    ("30301", "Atlanta, GA"),
    ("59101", "Billings, MT"),
    ("02108", "Boston, MA"),
    ("60601", "Chicago, IL"),
    ("80202", "Denver, CO"),
    ("50309", "Des Moines, IA"),
    ("77001", "Houston, TX"),
    ("64101", "Kansas City, MO"),
    ("55401", "Minneapolis, MN"),
    ("10001", "New York, NY"),
    ("19104", "Philadelphia, PA"),
    ("85001", "Phoenix, AZ"),
    ("94103", "San Francisco, CA"),
    ("98101", "Seattle, WA"),
    ("68102", "Omaha, NE"),
]
zip_codes, labels = zip(*cities)

selected = st.sidebar.multiselect(
    "Select cities",
    options=labels,
    default=list(labels)
)

start_date = st.sidebar.date_input(
    "Start date",
    pd.to_datetime("2025-07-20")
)
end_date = st.sidebar.date_input(
    "End date",
    pd.to_datetime("2025-07-29")
)

# --- Debug Panel (temporary) ---
st.sidebar.markdown("---")
st.sidebar.subheader("🔧 Debug")

key = os.getenv("AIRNOW_API_KEY", "")
st.sidebar.write("API key loaded:", bool(key), f"(length={len(key)})")

if st.sidebar.button("Test NYC fetch"):
    try:
        sample = fetch_daily_aqi("10001", start_date.strftime("%Y-%m-%d"))
        st.sidebar.success(f"Fetched {len(sample)} observations")
        st.sidebar.json(sample)
    except Exception as e:
        st.sidebar.error(f"Error: {e}")

# --- Data Loading (cached) ---
@st.cache_data
def load_aqi_data(zips, city_labels, start, end):
    dates = pd.date_range(start, end)
    records = []
    for zip_code, city in zip(zips, city_labels):
        if city in selected:
            for dt in dates:
                try:
                    obs_list = fetch_daily_aqi(zip_code, dt.strftime("%Y-%m-%d"))
                    for obs in obs_list:
                        records.append({
                            "date":      pd.to_datetime(obs["DateObserved"]),
                            "city":      city,
                            "AQI":       obs["AQI"],
                            "category":  obs["Category"]["Name"],
                            "lat":       obs["Latitude"],
                            "lon":       obs["Longitude"]
                        })
                except Exception:
                    continue
    return pd.DataFrame(records)

df = load_aqi_data(zip_codes, labels, start_date, end_date)

# --- Time‑Series Plot ---
st.subheader("Daily Max AQI Trends")
if not df.empty:
    df_max = df.groupby(["date", "city"])["AQI"].max().reset_index()
    pivot = df_max.pivot(index="date", columns="city", values="AQI")
    st.line_chart(pivot)
else:
    st.write("No data to display. Try adjusting your date range or cities.")

# --- Interactive Folium Map ---
st.subheader("Latest AQI Map")
if not df.empty:
    latest_date = df["date"].max()
    latest = df[df["date"] == latest_date].drop_duplicates("city")
    m = folium.Map(
        location=[latest["lat"].mean(), latest["lon"].mean()],
        zoom_start=4
    )
    cat_colors = {
        "Good":                            "green",
        "Moderate":                        "yellow",
        "Unhealthy for Sensitive Groups": "orange",
        "Unhealthy":                       "red",
        "Very Unhealthy":                  "purple",
        "Hazardous":                       "maroon"
    }
    for _, row in latest.iterrows():
        folium.CircleMarker(
            location=[row["lat"], row["lon"]],
            radius=8,
            color=cat_colors.get(row["category"], "gray"),
            fill=True,
            fill_color=cat_colors.get(row["category"], "gray"),
            fill_opacity=0.7,
            popup=f"{row['city']}: AQI {row['AQI']} ({row['category']})"
        ).add_to(m)
    st_folium(m, width=700, height=400)
else:
    st.write("No map to display.")

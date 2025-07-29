import pandas as pd
from src.fetch_aqi import fetch_daily_aqi

# Fetch data 
data = fetch_daily_aqi("10001", "2025-07-23")

# Normalize into a flat DataFrame
df = pd.json_normalize(data)

# Select columns to keep
""" 
DateObserved → the date of the reading

ReportingArea → the city/region name

StateCode → the state (useful later)

Latitude, Longitude → for mapping

AQI → the air‑quality index value

Category.Name → the descriptor (Good, Moderate, etc.) 
"""

df_simple = df[[
    "DateObserved",
    "ReportingArea",
    "StateCode",
    "Latitude",
    "Longitude",
    "AQI",
    "Category.Name"
]]

# Rename to simplify 
df_simple = df_simple.rename(columns={
    "DateObserved": "date",
    "ReportingArea": "city",
    "StateCode": "state",
    "Category.Name": "category"
})

# Save to CSV
df_simple.to_csv("data/raw/aqi_raw.csv", index=False)

# Check if successful
print(df_simple.head())

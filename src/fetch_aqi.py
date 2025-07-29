import os
import requests
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("AIRNOW_API_KEY")

def fetch_daily_aqi(zip_code: str, date: str) -> list:
    """
    Fetches historical AQI observations for a given zip code on a specific date.
    The AirNow API wants date in 'YYYY-MM-DDThh-0000' format, so we append 'T00-0000'.
    """
    # convert "2025-07-23" → "2025-07-23T00-0000"
    date_time = f"{date}T00-0000"

    url = "https://www.airnowapi.org/aq/observation/zipCode/historical/"
    params = {
        "format":    "application/json",
        "zipCode":   zip_code,
        "date":      date_time,
        "distance":  25,
        "API_KEY":   API_KEY
    }

    resp = requests.get(url, params=params)
    resp.raise_for_status()
    return resp.json()

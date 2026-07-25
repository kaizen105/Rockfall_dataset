"""
Module to fetch and preprocess weather data from the Open-Meteo API.

This script fetches historical weather data (temperature, precipitation,
windspeed, shortwave radiation) for a specific location and engineers
additional features like 3-day and 7-day rolling rainfall sums.
"""

import os
import requests
import pandas as pd

# --- Configuration ---
LATITUDE = 22.14
LONGITUDE = 85.47
START_DATE = "2021-01-01"
END_DATE = "2023-12-31"

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)

OUTPUT_FILE = os.path.join(DATA_DIR, "weather_dataset.csv")

def fetch_weather_data() -> None:
    """Fetches weather data, processes it, and saves it to a CSV file."""
    print("--- Starting Weather Data Download ---")
    print(f"Location: Noamundi ({LATITUDE}, {LONGITUDE})")
    print(f"Time Period: {START_DATE} to {END_DATE}\n")

    # --- Construct the API URL ---
    url = (
        f"https://archive-api.open-meteo.com/v1/archive?"
        f"latitude={LATITUDE}&longitude={LONGITUDE}&"
        f"start_date={START_DATE}&end_date={END_DATE}&"
        f"daily=temperature_2m_max,precipitation_sum,windspeed_10m_max,shortwave_radiation_sum&"
        f"timezone=auto"
    )

    # --- Fetch, Process, and Save the Data ---
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()

        df_weather = pd.DataFrame(data["daily"])
        df_weather.rename(columns={"time": "Timestamp"}, inplace=True)
        df_weather["Timestamp"] = pd.to_datetime(df_weather["Timestamp"])

        print("Engineering new features (3-day and 7-day rainfall)...")
        df_weather["3_day_rainfall"] = df_weather["precipitation_sum"].rolling(window=3).sum()
        df_weather["7_day_rainfall"] = df_weather["precipitation_sum"].rolling(window=7).sum()
        df_weather.fillna(0, inplace=True)

        df_weather.to_csv(OUTPUT_FILE, index=False)

        print(f"\n--- Success! ---")
        print(f"Rich weather data saved to '{OUTPUT_FILE}'")
        print(f"The file contains {len(df_weather)} rows.")

    except requests.exceptions.RequestException as e:
        print(f"Error: A network problem occurred. Could not fetch data from the API: {e}")
    except KeyError as e:
        print(f"Error: Could not find key '{e}' in the API response. The data format may have changed.")


if __name__ == "__main__":
    fetch_weather_data()

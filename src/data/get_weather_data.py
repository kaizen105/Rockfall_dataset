"""
Module to fetch and preprocess weather data from the Open-Meteo API.

This script clusters locations into 25 macro-regions using KMeans, fetches 
historical HOURLY weather data for those centroids, applies physics-informed
downscaling, and streams the output directly to disk.
"""

import os
import time
import requests
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans

# --- Configuration ---
START_DATE = "2021-01-01"
END_DATE = "2023-12-31"
NUM_CLUSTERS = 25

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(BASE_DIR, "data_v2")
os.makedirs(DATA_DIR, exist_ok=True)

GEOMETRY_FILE = os.path.join(DATA_DIR, "geometry_dataset_500.csv")
OUTPUT_FILE = os.path.join(DATA_DIR, "weather_dataset.csv")

def apply_physics_downscaling(df: pd.DataFrame, loc_row: pd.Series, centroid_elevation: float) -> pd.DataFrame:
    """Applies physics-informed meteorological downscaling to simulate realistic microclimates."""
    df_var = df.copy()
    
    loc_elev = loc_row['elev_1']
    loc_slope = loc_row['slope_1']
    loc_aspect = loc_row['aspect_1']
    
    # 1. Temperature Lapse Rate: ~6.5C drop per 1000m elevation gain
    elev_diff = loc_elev - centroid_elevation
    temp_adjustment = -0.0065 * elev_diff
    df_var["temperature_2m"] += temp_adjustment
    
    # 2. Orographic Rainfall (Assuming Westerly prevailing wind at 270 degrees)
    aspect_rad = np.radians(loc_aspect)
    slope_rad = np.radians(loc_slope)
    wind_effect = np.cos(aspect_rad - np.radians(270)) 
    slope_effect = np.sin(slope_rad)
    rain_multiplier = 1.0 + 0.05 * wind_effect * slope_effect
    df_var["precipitation"] = np.clip(df_var["precipitation"] * rain_multiplier, 0, None)
    
    # 3. Solar Radiation (South-facing slopes get more sun in Northern Hemisphere)
    sun_effect = np.cos(aspect_rad - np.radians(180))
    rad_multiplier = 1.0 + 0.10 * sun_effect * slope_effect
    df_var["shortwave_radiation"] = np.clip(df_var["shortwave_radiation"] * rad_multiplier, 0, None)
    
    # We do NOT precalculate 72h rain here anymore, physics engine does it
    
    return df_var

def fetch_weather_data() -> None:
    print("--- Starting Clustered HOURLY Weather Data Download ---")
    
    if not os.path.exists(GEOMETRY_FILE):
        print(f"[ERROR] Geometry file not found at {GEOMETRY_FILE}")
        return

    df_geom = pd.read_csv(GEOMETRY_FILE)
    
    print(f"Clustering {len(df_geom)} locations into {NUM_CLUSTERS} macro-regions using KMeans...")
    coords = df_geom[['Y', 'X']].values # Latitude, Longitude
    kmeans = KMeans(n_clusters=NUM_CLUSTERS, random_state=42, n_init=10)
    df_geom['cluster_id'] = kmeans.fit_predict(coords)
    centroids = kmeans.cluster_centers_
    cluster_elevations = df_geom.groupby('cluster_id')['elev_1'].mean().to_dict()

    # 1. Fetch weather for the 25 centroids
    centroid_weather = {}
    for cluster_idx, (lat, lon) in enumerate(centroids):
        print(f"[{cluster_idx+1}/{NUM_CLUSTERS}] Fetching HOURLY weather for Centroid {cluster_idx}...")
        
        url = (
            f"https://archive-api.open-meteo.com/v1/archive?"
            f"latitude={lat}&longitude={lon}&"
            f"start_date={START_DATE}&end_date={END_DATE}&"
            f"hourly=temperature_2m,precipitation,windspeed_10m,shortwave_radiation&"
            f"timezone=auto"
        )
        
        retries = 3
        for attempt in range(retries):
            try:
                response = requests.get(url)
                response.raise_for_status()
                data = response.json()
                
                df_weather = pd.DataFrame(data["hourly"])
                df_weather.rename(columns={"time": "Timestamp"}, inplace=True)
                df_weather["Timestamp"] = pd.to_datetime(df_weather["Timestamp"])
                
                centroid_weather[cluster_idx] = df_weather
                time.sleep(1.0) # Free tier sleep
                break
            except Exception as e:
                print(f"  Attempt {attempt+1}/{retries} failed: {e}")
                time.sleep(2)
        
        if cluster_idx not in centroid_weather:
            print(f"[ERROR] Critical failure: Could not fetch weather for Cluster {cluster_idx}. Exiting.")
            return
            
    # 2. Distribute centroid weather to the 500 locations and append to file
    print("\nApplying macro-region weather to all locations and streaming to disk...")
    
    # Remove old file if it exists
    if os.path.exists(OUTPUT_FILE):
        os.remove(OUTPUT_FILE)
        
    first_chunk = True
    total_rows = 0
    
    for i, row in df_geom.iterrows():
        loc_id = f"LOC_{i+1}"
        cluster_idx = row['cluster_id']
        
        # Get the base weather for this location's cluster
        df_base = centroid_weather[cluster_idx].copy()
        
        # Apply physics downscaling
        centroid_elev = cluster_elevations[cluster_idx]
        df_varied = apply_physics_downscaling(df_base, row, centroid_elev)
        df_varied["Location_ID"] = loc_id
        
        # Save directly to disk
        mode = 'w' if first_chunk else 'a'
        df_varied.to_csv(OUTPUT_FILE, mode=mode, index=False, header=first_chunk)
        
        total_rows += len(df_varied)
        first_chunk = False
        
        if (i + 1) % 50 == 0:
            print(f"  Processed {i+1} locations...")
            import gc
            gc.collect()

    print(f"--- Success! ---")
    print(f"Hourly weather data saved to '{OUTPUT_FILE}'")
    print(f"The file contains {total_rows} rows.")


if __name__ == "__main__":
    fetch_weather_data()

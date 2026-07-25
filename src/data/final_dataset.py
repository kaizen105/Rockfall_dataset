"""
Dataset Merge and Consolidation Script.

This module combines the geometry dataset, weather dataset, and synthetic
sensor data into a single master dataset. It also cleans up Location IDs
and creates a separate lookup file for dashboard coordinate mapping.
"""

import os
import numpy as np
import pandas as pd

# --- Configuration ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)

GEOMETRY_FILE = os.path.join(DATA_DIR, "geometry_dataset.csv")
WEATHER_FILE = os.path.join(DATA_DIR, "weather_dataset.csv")
SENSOR_EVENTS_FILE = os.path.join(DATA_DIR, "synthetic_sensor_and_events.csv")
OUTPUT_FILE = os.path.join(DATA_DIR, "final_master_dataset.csv")
COORDINATE_LOOKUP_FILE = os.path.join(DATA_DIR, "location_coordinates.csv") # New file for map coordinates

def merge_datasets() -> None:
    """Merges all datasets and saves the output."""
    print("--- Starting Final Merge Process (Robust ID Correction Version) ---")

    # --- Step 1: Load all datasets ---
    print("Loading all three source datasets...")
    try:
        df_geometry = pd.read_csv(GEOMETRY_FILE)
        df_weather = pd.read_csv(WEATHER_FILE, parse_dates=["Timestamp"])
        df_sensor_events = pd.read_csv(SENSOR_EVENTS_FILE, parse_dates=["Timestamp"])
    except FileNotFoundError as e:
        print(f"\n[ERROR] A required file is missing: {e}.")
        return

    # --- Step 2: Create the Master List of Correct Location_IDs ---
    print("Creating a clean master list of Location IDs...")
    num_locations = len(df_geometry)
    clean_location_ids = [f"LOC_{i+1}" for i in range(num_locations)]
    df_geometry["Location_ID"] = clean_location_ids

    # --- Step 3: Rebuild the Location_IDs in the Sensor Dataframe ---
    print("Rebuilding incorrect Location_IDs in the sensor data file...")
    if len(df_sensor_events) % num_locations != 0:
        print("[ERROR] The number of rows in the sensor data is not divisible by the number of locations.")
        return

    num_timestamps_per_location = len(df_sensor_events) // num_locations

    # This is the core fix: create a new ID column from scratch based on data order
    correct_ids = np.repeat(clean_location_ids, repeats=num_timestamps_per_location)
    df_sensor_events["Location_ID"] = correct_ids
    print("Successfully replaced all 'LOC_nan' with correct, ordered IDs.")

    # --- Step 4: Extract and Prepare Geometry Data (including Lat/Lon) ---
    print("Preparing geometry data for merge...")
    lat_col, lon_col = None, None
    for col in df_geometry.columns:
        if "x" in col.lower() or "lon" in col.lower():
            lon_col = col
        if "y" in col.lower() or "lat" in col.lower():
            lat_col = col

    if lat_col and lon_col:
        print(f"Found coordinate columns: '{lat_col}' and '{lon_col}'.")
        # Create the separate coordinate lookup file for the dashboard
        df_coords = df_geometry[["Location_ID", lat_col, lon_col]].copy()
        df_coords.rename(columns={lat_col: "latitude", lon_col: "longitude"}, inplace=True)
        df_coords.to_csv(COORDINATE_LOOKUP_FILE, index=False)
        print(f"Coordinate lookup file for dashboard saved to '{COORDINATE_LOOKUP_FILE}'")
        
        geometry_cols_to_keep = ["Location_ID", "Ruggedness", "Roughness", "Aspect", "Slope"]
        geometry_cols_to_keep = [col for col in geometry_cols_to_keep if col in df_geometry.columns]
        df_geometry_clean = df_geometry[geometry_cols_to_keep]
    else:
        print("Warning: Could not find Lat/Lon columns. A coordinate lookup file was not created.")
        df_geometry_clean = df_geometry.copy()

    # --- Step 5: Merge All Datasets Together ---
    print("Merging sensor data with geometry data...")
    df_merged = pd.merge(df_sensor_events, df_geometry_clean, on="Location_ID", how="left")

    print("Merging combined data with weather data...")
    df_merged["Date"] = df_merged["Timestamp"].dt.date
    df_weather["Date"] = df_weather["Timestamp"].dt.date
    df_final = pd.merge(df_merged, df_weather, on="Date", how="left")

    # --- Step 6: Final Cleanup and Save ---
    print("Cleaning up and saving the final dataset...")
    df_final = df_final.drop(columns=["Date", "Timestamp_y"], errors="ignore").rename(columns={"Timestamp_x": "Timestamp"})
    df_final.to_csv(OUTPUT_FILE, index=False)

    print(f"\n--- Merge Complete! ---")
    print(f"Final master dataset saved to '{OUTPUT_FILE}'")
    print(f"The file contains {len(df_final):,} rows and has been fully corrected.")

if __name__ == "__main__":
    merge_datasets()

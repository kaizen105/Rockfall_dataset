"""
Realistic Rockfall Synthetic Data Generator (Hourly Streaming Version).

This script reads the 13.1 million row HOURLY weather dataset in chunks 
(one location at a time), computes geotechnical rockfall physics (Factor of Safety), 
adds geometry columns, and streams directly into the final_master_dataset.csv.

This architecture entirely bypasses OOM issues and eliminates intermediate merges.
"""

import os
import random
import numpy as np
import pandas as pd

# --- Configuration ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(BASE_DIR, "data_v2")

GEOMETRY_FILE = os.path.join(DATA_DIR, "geometry_dataset_500.csv")
WEATHER_FILE = os.path.join(DATA_DIR, "weather_dataset.csv")
OUTPUT_FILE = os.path.join(DATA_DIR, "final_master_dataset.csv")

def generate_sensor_data() -> None:
    print("--- Starting Synthetic Data Generation (Hourly Streaming Version) ---")

    try:
        df_geometry = pd.read_csv(GEOMETRY_FILE)
        if "Location_ID" not in df_geometry.columns:
            df_geometry["Location_ID"] = [f"LOC_{i+1}" for i in range(len(df_geometry))]
            
        loc_traits = {}
        for idx, row in df_geometry.iterrows():
            loc_traits[row["Location_ID"]] = row.to_dict()

    except FileNotFoundError as e:
        print(f"\n[ERROR] A required file is missing: {e}.")
        return

    # Clean old output file
    if os.path.exists(OUTPUT_FILE):
        os.remove(OUTPUT_FILE)

    print("Streaming 13.1 million rows of weather data through physics engine...")
    
    # Each location has exactly 26257 rows (3 years of hours, 24*1095 = 26280 roughly)
    # Wait, 2021-2023 hourly is exactly 26280 rows. We read by chunks of 26280.
    # To be perfectly safe, we'll group by Location_ID as we read the file
    
    chunksize = 1_000_000
    current_loc_df = []
    current_loc_id = None
    first_chunk = True
    total_rows = 0

    for chunk in pd.read_csv(WEATHER_FILE, parse_dates=["Timestamp"], chunksize=chunksize):
        for loc_id, group in chunk.groupby("Location_ID"):
            if current_loc_id is None:
                current_loc_id = loc_id
                
            if loc_id == current_loc_id:
                current_loc_df.append(group)
            else:
                # Process the completed location
                df_loc = pd.concat(current_loc_df)
                df_processed = process_location(df_loc, current_loc_id, loc_traits[current_loc_id])
                
                # Write to disk
                mode = 'w' if first_chunk else 'a'
                df_processed.to_csv(OUTPUT_FILE, mode=mode, index=False, header=first_chunk)
                first_chunk = False
                total_rows += len(df_processed)
                
                # Reset for next location
                current_loc_id = loc_id
                current_loc_df = [group]
                
    # Process the final location
    if current_loc_df:
        df_loc = pd.concat(current_loc_df)
        df_processed = process_location(df_loc, current_loc_id, loc_traits[current_loc_id])
        mode = 'w' if first_chunk else 'a'
        df_processed.to_csv(OUTPUT_FILE, mode=mode, index=False, header=first_chunk)
        total_rows += len(df_processed)

    print(f"\n--- Process Complete ---")
    print(f"Final master dataset saved to '{OUTPUT_FILE}'")
    print(f"The file contains {total_rows:,} rows.")

def process_location(df_loc: pd.DataFrame, loc_id: str, traits: dict) -> pd.DataFrame:
    """Computes physics for a single location's dataframe (usually ~26k rows)"""
    df_loc = df_loc.copy()
    df_loc.set_index("Timestamp", inplace=True, drop=False)
    
    # Map geometry columns to the dataframe
    for key, val in traits.items():
        if key not in df_loc.columns:
            df_loc[key] = val

    # Create base rolling rainfall sum (now precipitation instead of precipitation_sum)
    df_loc["rain_72h_sum"] = df_loc["precipitation"].rolling(window=72, min_periods=1).sum().fillna(0)

    # Geotechnical Constants
    loc_lag_hours = random.randint(8, 16)
    
    raw_slope = traits["slope_1"]
    slope_val = np.clip(raw_slope, 1.0, 85.0)
    beta = np.radians(slope_val)
    
    gamma = np.random.uniform(20, 25) 
    z = np.random.uniform(1.0, 2.0) 
    phi = np.radians(np.random.uniform(30, 40)) 
    c = np.random.uniform(4, 10) 

    df_loc["pore_pressure_proxy"] = df_loc["rain_72h_sum"].shift(loc_lag_hours).fillna(0)

    # Factor of Safety (FS) Calculation
    gamma_w = 9.81
    saturation_threshold = 100.0 
    h_w = np.minimum(1.0, df_loc["pore_pressure_proxy"] / saturation_threshold) * z
    u = gamma_w * h_w
    
    fs_numerator = c + (gamma * z * np.cos(beta)**2 - u) * np.tan(phi)
    fs_denominator = gamma * z * np.sin(beta) * np.cos(beta)
    df_loc["FS"] = fs_numerator / fs_denominator

    # 1. Base Displacement 
    hour_of_day = df_loc.index.hour.values
    thermal_cycle = 0.005 * np.sin((hour_of_day - 9) * (2 * np.pi / 24))
    base_noise = np.random.normal(0, 0.002, size=len(df_loc))

    k = 0.15 
    rain_creep = np.where(df_loc["FS"] <= 1.3, k / (np.maximum(df_loc["FS"], 1.01) - 1.0), 0)
    df_loc["Displacement_Rate_mm_h"] = (0.01 + thermal_cycle + base_noise + rain_creep).clip(min=0)

    # 2. Base Vibration 
    base_vib = np.random.uniform(0.1, 0.5, size=len(df_loc))
    is_blasting_hour = (hour_of_day >= 14) & (hour_of_day <= 16)
    blast_spikes = np.where(
        is_blasting_hour & (np.random.random(len(df_loc)) < 0.05),
        np.random.uniform(5, 12, size=len(df_loc)),
        0,
    )
    df_loc["Vibration_mm_s"] = base_vib + blast_spikes

    # 3. Events
    df_loc["Rockfall_Event"] = 0
    high_risk_times = df_loc.index[df_loc["FS"] <= 1.3].tolist()
    all_times = df_loc.index.tolist()

    num_events = max(1, np.random.poisson(5))
    event_times = []

    if high_risk_times:
        fs_values = df_loc.loc[high_risk_times, "FS"].values
        hp_probs = np.exp(5 * (1.3 - fs_values))
        hp_probs = hp_probs / hp_probs.sum()

    for _ in range(num_events):
        if random.random() < 0.8 and high_risk_times:
            event_times.append(np.random.choice(high_risk_times, p=hp_probs))
        else:
            event_times.append(random.choice(all_times))

    # Apply Event Physics
    for ev_time in event_times:
        if ev_time not in df_loc.index:
            continue
        idx_ev = df_loc.index.get_loc(ev_time)
        df_loc.loc[ev_time, "Rockfall_Event"] = 1

        post_window = 72
        end_idx = min(len(df_loc), idx_ev + post_window)
        time_since_event = (df_loc.index[idx_ev:end_idx] - df_loc.index[idx_ev]).total_seconds() / 3600
        decay_disp = 5 * np.exp(-0.1 * time_since_event)
        df_loc.iloc[idx_ev:end_idx, df_loc.columns.get_loc("Displacement_Rate_mm_h")] += decay_disp

        base_spike = gamma * z * np.sin(beta)
        aftershock_vib = (base_spike * np.random.uniform(0.4, 0.6)) * np.exp(-0.05 * time_since_event)
        df_loc.iloc[idx_ev:end_idx, df_loc.columns.get_loc("Vibration_mm_s")] += aftershock_vib

    # Final Noise & Dropouts
    df_loc["Displacement_Rate_mm_h"] += np.random.normal(0, 0.005, size=len(df_loc))
    df_loc["Displacement_Rate_mm_h"] = df_loc["Displacement_Rate_mm_h"].clip(lower=0) 
    df_loc["Vibration_mm_s"] += np.random.normal(0, 0.2, size=len(df_loc))
    df_loc["Vibration_mm_s"] = df_loc["Vibration_mm_s"].clip(lower=0)

    num_dropouts = int(len(df_loc) * 0.010)
    dropout_indices = np.random.choice(df_loc.index, num_dropouts, replace=False)
    df_loc.loc[dropout_indices, "Displacement_Rate_mm_h"] = np.nan
    df_loc.loc[dropout_indices, "Vibration_mm_s"] = np.nan

    # Drop intermediate and junk columns
    cols_to_drop = ["rain_72h_sum", "pore_pressure_proxy", "geometry", "rand_point", "fid", "DN", "X", "Y"]
    df_loc.drop(columns=cols_to_drop, inplace=True, errors="ignore")
    
    return df_loc

if __name__ == "__main__":
    generate_sensor_data()

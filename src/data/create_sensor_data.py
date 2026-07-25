"""
Realistic Rockfall Synthetic Data Generator.

This script generates synthetic sensor data by modeling physical behaviors 
like thermal cycles, rain-induced creep, and vibration. 

Noise & Variability Parameters Injected:
1. Variable Lag: The lag between rainfall and slope response is randomized per 
   location (drawn from Uniform[8, 16] hours) instead of a fixed 12 hours.
2. Variable Coupling Strength: The slope_factor multiplier for rain-induced 
   creep is multiplied by a random factor drawn from Uniform[0.5, 1.5] per location.
3. Final Measurement Noise: Gaussian noise is added to the final readings.
   - Displacement noise: Normal(0, 0.005)
   - Vibration noise: Normal(0, 0.2)
4. Sensor Dropouts: 1.0% of all readings are randomly nulled out (NaN) to 
   simulate real-world hardware failures.
"""

import os
import random
import numpy as np
import pandas as pd

# --- Configuration ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)

GEOMETRY_FILE = os.path.join(DATA_DIR, "geometry_dataset.csv")
WEATHER_FILE = os.path.join(DATA_DIR, "weather_dataset.csv")
OUTPUT_FILE = os.path.join(DATA_DIR, "synthetic_sensor_and_events.csv")

START_DATE = "2021-01-01"
END_DATE = "2023-12-31"

def generate_sensor_data() -> None:
    """Generates the synthetic sensor data and saves it to a CSV."""
    print("--- Starting Synthetic Data Generation (Realistic Physics Version) ---")

    try:
        df_geometry = pd.read_csv(GEOMETRY_FILE)
        df_weather = pd.read_csv(WEATHER_FILE, parse_dates=["Timestamp"])
        df_weather.set_index("Timestamp", inplace=True)

        if "Location_ID" in df_geometry.columns and not df_geometry["Location_ID"].isnull().all():
             location_ids = df_geometry["Location_ID"].unique().tolist()
        else:
             if "id" in df_geometry.columns:
                 location_ids = [f"LOC_{i}" for i in df_geometry["id"]]
             else:
                 location_ids = [f"LOC_{i+1}" for i in range(len(df_geometry))]

        # Store geometry traits for each location
        loc_traits = {}
        for idx, row in df_geometry.iterrows():
            loc_id = location_ids[idx]
            slope = row.get("Slope", 45)
            ruggedness = row.get("Ruggedness", 10)
            loc_traits[loc_id] = {"slope": slope, "ruggedness": ruggedness}

    except FileNotFoundError as e:
        print(f"\n[ERROR] A required file is missing: {e}.")
        return

    print("Creating hourly timeline and weather features...")
    all_location_dfs = []
    hourly_timestamps = pd.date_range(start=START_DATE, end=END_DATE, freq="h")

    # Interpolate weather data to hourly
    df_weather_hourly = df_weather.reindex(hourly_timestamps, method="ffill")
    df_weather_hourly["Timestamp"] = df_weather_hourly.index

    # Create base rolling rainfall sum (no lag yet)
    df_weather_hourly["rain_72h_sum"] = (
        df_weather_hourly["precipitation_sum"]
        .rolling(window=72, min_periods=1)
        .sum()
        .fillna(0)
    )

    for loc_id in location_ids:
        df_loc = df_weather_hourly.copy()
        df_loc["Location_ID"] = loc_id

        traits = loc_traits.get(loc_id, {"slope": 45, "ruggedness": 10})

        # [NEW] Variable Lag & Coupling Strength
        loc_lag_hours = random.randint(8, 16)
        loc_coupling_variation = random.uniform(0.5, 1.5)
        slope_factor = (traits["slope"] / 45.0) * loc_coupling_variation

        df_loc["pore_pressure_proxy"] = df_loc["rain_72h_sum"].shift(loc_lag_hours).fillna(0)

        # 1. Base Displacement (Thermal cycles + Noise)
        hour_of_day = df_loc.index.hour
        thermal_cycle = 0.005 * np.sin((hour_of_day - 9) * (2 * np.pi / 24))
        base_noise = np.random.normal(0, 0.002, size=len(df_loc))

        # Rainfall induced creep
        rain_creep = df_loc["pore_pressure_proxy"] * 0.001 * slope_factor

        df_loc["Displacement_Rate_mm_h"] = 0.01 + thermal_cycle + base_noise + rain_creep
        df_loc["Displacement_Rate_mm_h"] = df_loc["Displacement_Rate_mm_h"].clip(lower=0)

        # 2. Base Vibration (Noise + Machinery/Blasting)
        base_vib = np.random.uniform(0.1, 0.5, size=len(df_loc))
        is_blasting_hour = (hour_of_day >= 14) & (hour_of_day <= 16)
        blast_spikes = np.where(
            is_blasting_hour & (np.random.random(len(df_loc)) < 0.05),
            np.random.uniform(5, 12, size=len(df_loc)),
            0,
        )
        df_loc["Vibration_mm_s"] = base_vib + blast_spikes

        # 3. Events and Near Misses
        df_loc["Rockfall_Event"] = 0

        # Target only the most severe rain windows (top 5% or > 20mm)
        threshold = max(20.0, np.percentile(df_loc["pore_pressure_proxy"], 95))
        high_pressure_times = df_loc.index[df_loc["pore_pressure_proxy"] > threshold].tolist()
        all_times = df_loc.index.tolist()

        # Randomize event counts to remove the 'too clean' uniform distribution
        num_events = max(1, np.random.poisson(5))
        num_near_misses = np.random.poisson(3)
        event_times = []
        near_miss_times = []

        # Bias sampling aggressively toward the absolute highest pore pressure peaks
        if high_pressure_times:
            hp_probs = df_loc.loc[high_pressure_times, "pore_pressure_proxy"].values
            # Exponentiate to heavily penalize moderate rain and exclusively favor the peaks
            hp_probs = hp_probs**4
            hp_probs = hp_probs / hp_probs.sum()

        for _ in range(num_events):
            if random.random() < 0.8 and high_pressure_times:
                event_times.append(np.random.choice(high_pressure_times, p=hp_probs))
            else:
                event_times.append(random.choice(all_times))

        for _ in range(num_near_misses):
            if random.random() < 0.8 and high_pressure_times:
                near_miss_times.append(np.random.choice(high_pressure_times, p=hp_probs))
            else:
                near_miss_times.append(random.choice(all_times))

        # Apply Event Physics
        for ev_time in event_times:
            if ev_time not in df_loc.index:
                continue
            idx_ev = df_loc.index.get_loc(ev_time)
            df_loc.loc[ev_time, "Rockfall_Event"] = 1

            # Pre-failure (Exponential creep)
            window = random.choice([24, 48, 72])
            start_idx = max(0, idx_ev - window)
            time_to_event = (df_loc.index[idx_ev] - df_loc.index[start_idx:idx_ev]).total_seconds() / 3600
            rain_intensity = df_loc["pore_pressure_proxy"].iloc[idx_ev]
            peak_multiplier = np.clip(rain_intensity / 25.0, 0.5, 2.5)
            creep = (15 * peak_multiplier) * np.exp(-0.15 * time_to_event)
            df_loc.iloc[start_idx:idx_ev, df_loc.columns.get_loc("Displacement_Rate_mm_h")] += creep[::-1]

            # Post-failure (Aftershocks and stabilization)
            post_window = 72
            end_idx = min(len(df_loc), idx_ev + post_window)
            time_since_event = (df_loc.index[idx_ev:end_idx] - df_loc.index[idx_ev]).total_seconds() / 3600
            decay_disp = 5 * np.exp(-0.1 * time_since_event)
            df_loc.iloc[idx_ev:end_idx, df_loc.columns.get_loc("Displacement_Rate_mm_h")] += decay_disp

            aftershock_vib = np.random.uniform(12, 25, size=end_idx - idx_ev) * np.exp(-0.05 * time_since_event)
            df_loc.iloc[idx_ev:end_idx, df_loc.columns.get_loc("Vibration_mm_s")] += aftershock_vib

        # Apply Near-Miss Physics
        for nm_time in near_miss_times:
            if nm_time not in df_loc.index:
                continue
            idx_nm = df_loc.index.get_loc(nm_time)

            window = 48
            start_idx = max(0, idx_nm - window)
            time_to_nm = (df_loc.index[idx_nm] - df_loc.index[start_idx:idx_nm]).total_seconds() / 3600
            rain_intensity = df_loc["pore_pressure_proxy"].iloc[idx_nm]
            peak_multiplier = np.clip(rain_intensity / 25.0, 0.5, 2.5)
            creep = (5 * peak_multiplier) * np.exp(-0.2 * time_to_nm)
            df_loc.iloc[start_idx:idx_nm, df_loc.columns.get_loc("Displacement_Rate_mm_h")] += creep[::-1]

            post_window = 48
            end_idx = min(len(df_loc), idx_nm + post_window)
            time_since_nm = (df_loc.index[idx_nm:end_idx] - df_loc.index[idx_nm]).total_seconds() / 3600
            decay_disp = 5 * np.exp(-0.05 * time_since_nm)
            df_loc.iloc[idx_nm:end_idx, df_loc.columns.get_loc("Displacement_Rate_mm_h")] += decay_disp

        # [NEW] Final Measurement Noise
        df_loc["Displacement_Rate_mm_h"] += np.random.normal(0, 0.005, size=len(df_loc))
        df_loc["Displacement_Rate_mm_h"] = df_loc["Displacement_Rate_mm_h"].clip(lower=0) # maintain physical bounds
        df_loc["Vibration_mm_s"] += np.random.normal(0, 0.2, size=len(df_loc))
        df_loc["Vibration_mm_s"] = df_loc["Vibration_mm_s"].clip(lower=0)

        # [NEW] Sensor dropouts (1.0%)
        num_dropouts = int(len(df_loc) * 0.010)
        dropout_indices = np.random.choice(df_loc.index, num_dropouts, replace=False)
        df_loc.loc[dropout_indices, "Displacement_Rate_mm_h"] = np.nan
        df_loc.loc[dropout_indices, "Vibration_mm_s"] = np.nan

        all_location_dfs.append(df_loc)

    df_main = pd.concat(all_location_dfs)
    df_main.drop(columns=["rain_72h_sum", "pore_pressure_proxy"], inplace=True, errors="ignore")
    cols_to_keep = ["Timestamp", "Location_ID", "Displacement_Rate_mm_h", "Vibration_mm_s", "Rockfall_Event"]
    df_main = df_main[cols_to_keep]

    df_main.to_csv(OUTPUT_FILE, index=False)
    print(f"\n--- Process Complete ---")
    print(f"Realistic synthetic sensor data saved to '{OUTPUT_FILE}'")
    print(f"The file contains {len(df_main):,} rows.")

if __name__ == "__main__":
    generate_sensor_data()

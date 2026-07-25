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

        # Geotechnical Constants (Infinite Slope Model)
        loc_lag_hours = random.randint(8, 16)
        
        # QGIS artifact fix: infinite slope formula diverges near 90 degrees.
        # We cap slope to realistic failing soil bounds (26-32 degrees) for shallow failures.
        raw_slope = traits["slope"]
        slope_val = np.random.uniform(26, 32) if raw_slope > 60 else max(raw_slope, 25.0)
        beta = np.radians(slope_val)
        
        gamma = np.random.uniform(20, 25) # Unit weight (kN/m³)
        z = np.random.uniform(1.0, 2.0) # Depth to failure (m) (shallower prevents overpowering resisting term)
        phi = np.radians(np.random.uniform(30, 40)) # Friction angle (slightly higher than beta for baseline stability)
        c = np.random.uniform(4, 10) # Cohesion (kPa) - tuned to ensure baseline FS is ~1.5-2.0

        df_loc["pore_pressure_proxy"] = df_loc["rain_72h_sum"].shift(loc_lag_hours).fillna(0)

        # Factor of Safety (FS) Calculation
        gamma_w = 9.81
        saturation_threshold = 100.0 # mm
        h_w = np.minimum(1.0, df_loc["pore_pressure_proxy"] / saturation_threshold) * z
        u = gamma_w * h_w
        
        fs_numerator = c + (gamma * z * np.cos(beta)**2 - u) * np.tan(phi)
        fs_denominator = gamma * z * np.sin(beta) * np.cos(beta)
        df_loc["FS"] = fs_numerator / fs_denominator

        # 1. Base Displacement (Thermal cycles + Noise + Tertiary Creep)
        hour_of_day = df_loc.index.hour
        thermal_cycle = 0.005 * np.sin((hour_of_day - 9) * (2 * np.pi / 24))
        base_noise = np.random.normal(0, 0.002, size=len(df_loc))

        # FS-driven Creep (Injection Point 1)
        # Add creep proportional to closeness to failure when FS < 1.3
        k = 0.15 # Scaling constant for mm/h realism
        rain_creep = np.where(df_loc["FS"] <= 1.3, k / (np.maximum(df_loc["FS"], 1.01) - 1.0), 0)

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

        # Target periods where FS drops indicating instability
        high_risk_times = df_loc.index[df_loc["FS"] <= 1.3].tolist()
        all_times = df_loc.index.tolist()

        # Randomize event counts to remove the 'too clean' uniform distribution
        num_events = max(1, np.random.poisson(5))
        num_near_misses = np.random.poisson(3)
        event_times = []
        near_miss_times = []

        # Bias sampling heavily toward lowest FS (Injection Point 2)
        if high_risk_times:
            fs_values = df_loc.loc[high_risk_times, "FS"].values
            # Exponential multiplier: e^(5 * (1.3 - FS)), peaking as FS -> 1.0
            hp_probs = np.exp(5 * (1.3 - fs_values))
            hp_probs = hp_probs / hp_probs.sum()

        for _ in range(num_events):
            if random.random() < 0.8 and high_risk_times:
                event_times.append(np.random.choice(high_risk_times, p=hp_probs))
            else:
                event_times.append(random.choice(all_times))

        for _ in range(num_near_misses):
            if random.random() < 0.8 and high_risk_times:
                near_miss_times.append(np.random.choice(high_risk_times, p=hp_probs))
            else:
                near_miss_times.append(random.choice(all_times))

        # Apply Event Physics
        for ev_time in event_times:
            if ev_time not in df_loc.index:
                continue
            idx_ev = df_loc.index.get_loc(ev_time)
            df_loc.loc[ev_time, "Rockfall_Event"] = 1

            # Pre-failure ramp naturally emerges from FS tertiary creep (Injection Point 3)
            # No hardcoded exponential curve injected here.

            # Post-failure (Aftershocks and stabilization)
            post_window = 72
            end_idx = min(len(df_loc), idx_ev + post_window)
            time_since_event = (df_loc.index[idx_ev:end_idx] - df_loc.index[idx_ev]).total_seconds() / 3600
            decay_disp = 5 * np.exp(-0.1 * time_since_event)
            df_loc.iloc[idx_ev:end_idx, df_loc.columns.get_loc("Displacement_Rate_mm_h")] += decay_disp

            # Physical Vibration Spike (Injection Point 4)
            # Scales by failure mass (gamma * z) and slope energy (sin(beta))
            base_spike = gamma * z * np.sin(beta)
            vibration_spike = base_spike * np.random.uniform(0.4, 0.6)
            aftershock_vib = vibration_spike * np.exp(-0.05 * time_since_event)
            df_loc.iloc[idx_ev:end_idx, df_loc.columns.get_loc("Vibration_mm_s")] += aftershock_vib

        # Apply Near-Miss Physics
        for nm_time in near_miss_times:
            if nm_time not in df_loc.index:
                continue
            idx_nm = df_loc.index.get_loc(nm_time)

            # Pre-failure ramp emerges from FS tertiary creep. No hardcoded curve.
            
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
    cols_to_keep = ["Timestamp", "Location_ID", "Displacement_Rate_mm_h", "Vibration_mm_s", "Rockfall_Event", "FS"]
    df_main = df_main[cols_to_keep]

    df_main.to_csv(OUTPUT_FILE, index=False)
    print(f"\n--- Process Complete ---")
    print(f"Realistic synthetic sensor data saved to '{OUTPUT_FILE}'")
    print(f"The file contains {len(df_main):,} rows.")

if __name__ == "__main__":
    generate_sensor_data()

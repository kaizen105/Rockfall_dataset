"""
Realistic Rockfall Synthetic Data Generator (Hourly Streaming Version) - Release V1d.

This script reads the 13.1 million row HOURLY weather dataset in chunks 
(one location at a time), computes geotechnical rockfall physics (Factor of Safety), 
adds geometry columns, and streams directly into final_master_dataset.csv.

Updates in V1d:
- Timing within a location: restored V1b high-risk rule exactly (R >= 0.5 from lagged rain72/100, weight exp(5R);
  80% rain-driven, 20% uniform random; event-type-first; 120h spacing resampling; attempt cap 500).
- Creep: restored V1b bounded rain creep: 0.04 * R^2.
- Geotechnical Event Count Coupling: lambda_loc = min(15, 5 * w_loc / mean(w)) where w_loc = exp(-a * (FS_dry_loc - 1)).
- Pre-generation Calibration of 'a': smallest 'a' on a 0.05 grid where p90/p10 of lambda_loc is in [3, 6].
- Metadata tracking: records a, HAZARD_A, FS_dry, w_loc, lambda_loc in location_metadata.csv.
- Elimination of event-row target leak: post-event effects start strictly at idx_ev + 1.
- Precursor displacement ramp for ALL events ending at idx_ev inclusive.
- Full reproducibility: configurable seed recorded in per-location metadata.
- Row contiguity preserved: post_event_window column added (int8).
- Robust chunked part writing with atomic replace, retry loops, and resumability.
"""

import os
import sys
import argparse
import random
import time
import shutil
import pickle
import glob
import numpy as np
import pandas as pd

# --- Configuration Constants V1d ---
SATURATION_THRESHOLD = 100.0   # mm: pore pressure proxy saturation threshold
RISK_THRESHOLD = 0.5          # pore pressure fraction R >= 0.5 defines high risk hours
CREEP_MAX = 0.04              # mm/h: V1b rain creep cap: creep = 0.04 * R^2
RAIN_DRIVEN_RATIO = 0.8       # target 80% rain-driven, 20% random dry events
LAMBDA_LOC_SCALE = 5.0        # scale factor: lambda_loc = min(15, 5 * w_loc / mean(w))
LAMBDA_LOC_MAX = 15.0         # cap on lambda_loc

MIN_EVENT_SPACING_H = 120     # hours: minimum spacing between event times at same location
MAX_SPACING_ATTEMPTS = 500    # max resampling attempts to place event before counting unplaced

PRECURSOR_LEAD_MIN = 6        # hours: min precursor lead time U(6, 48)
PRECURSOR_LEAD_MAX = 48       # hours: max precursor lead time
PRECURSOR_AMPLITUDE = 0.02    # mm/h: ~3 sigma of displacement noise
POST_EVENT_HOURS = 72         # post-event window duration

NOISE_DISP_BASE = 0.002       # mm/h: base displacement Gaussian noise sigma
NOISE_DISP_FINAL = 0.005      # mm/h: final sensor displacement noise sigma
DROPOUT_RATE = 0.010          # 1.0% simultaneous sensor dropout rate

# I/O Robustness Configuration
LOCATIONS_PER_PART = 25       # locations per part file in parts/ directory
WRITE_MAX_ATTEMPTS = 3        # retry attempts for file writes
WRITE_RETRY_SLEEP_S = 1.0     # sleep between retries in seconds

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_DATA_DIR = os.path.join(BASE_DIR, "data", "inputs")
GEOMETRY_FILE = os.path.join(DEFAULT_DATA_DIR, "geometry_dataset_500.csv")
WEATHER_FILE = os.path.join(DEFAULT_DATA_DIR, "weather_dataset.csv")

def write_csv_with_retry(df: pd.DataFrame, path: str, max_attempts: int = WRITE_MAX_ATTEMPTS, delay_sec: float = WRITE_RETRY_SLEEP_S, **kwargs) -> None:
    """Writes a DataFrame to CSV with atomic replacement and retry logic."""
    temp_path = path + ".tmp"
    for attempt in range(1, max_attempts + 1):
        try:
            df.to_csv(temp_path, index=False, **kwargs)
            if os.path.exists(path):
                os.remove(path)
            os.replace(temp_path, path)
            return
        except Exception as e:
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except OSError:
                    pass
            if attempt == max_attempts:
                print(f"[ERROR] Failed to write {path} after {max_attempts} attempts: {e}")
                raise
            print(f"[RETRY] Write to {path} failed (attempt {attempt}/{max_attempts}): {e}. Retrying in {delay_sec}s...")
            time.sleep(delay_sec)

def append_metadata_with_retry(meta_records: list, meta_file: str, max_attempts: int = WRITE_MAX_ATTEMPTS, delay_sec: float = WRITE_RETRY_SLEEP_S) -> None:
    """Appends metadata records incrementally to metadata table with retry."""
    if not meta_records:
        return
    df_new = pd.DataFrame(meta_records)
    for attempt in range(1, max_attempts + 1):
        try:
            file_exists = os.path.exists(meta_file) and os.path.getsize(meta_file) > 0
            df_new.to_csv(meta_file, mode='a', header=not file_exists, index=False)
            return
        except Exception as e:
            if attempt == max_attempts:
                print(f"[ERROR] Failed to append metadata to {meta_file} after {max_attempts} attempts: {e}")
                raise
            print(f"[RETRY] Append metadata to {meta_file} failed (attempt {attempt}/{max_attempts}): {e}. Retrying in {delay_sec}s...")
            time.sleep(delay_sec)

def concatenate_parts(part_files: list, output_file: str) -> None:
    """Streams and concatenates multiple part CSV files into a single final master dataset."""
    print(f"Concatenating {len(part_files)} part files into '{output_file}'...")
    temp_output = output_file + ".tmp"
    with open(temp_output, "wb") as outfile:
        for i, part_file in enumerate(part_files):
            with open(part_file, "rb") as infile:
                if i == 0:
                    shutil.copyfileobj(infile, outfile, length=16 * 1024 * 1024)
                else:
                    # Skip the first header line of subsequent parts
                    infile.readline()
                    shutil.copyfileobj(infile, outfile, length=16 * 1024 * 1024)
    if os.path.exists(output_file):
        os.remove(output_file)
    os.replace(temp_output, output_file)

def downcast_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Downcasts DataFrame dtypes for memory and disk efficiency."""
    for col in df.select_dtypes(include=["float64"]).columns:
        df[col] = df[col].astype("float32")
    for col in ["Rockfall_Event", "post_event_window"]:
        if col in df.columns:
            df[col] = df[col].astype("int8")
    if "Location_ID" in df.columns:
        df["Location_ID"] = df["Location_ID"].astype("category")
    return df

def calibrate_hazard_a(loc_traits_all: dict, loc_params_all: dict) -> tuple:
    """Calibrates 'a' on a 0.05 grid from FS_dry only, ensuring p90/p10 of lambda_loc is in [3, 6]."""
    fs_dry_list = []
    for lid, tr in loc_traits_all.items():
        lp = loc_params_all[lid]
        raw_slope = tr["slope_1"]
        slope_val = np.clip(raw_slope, 1.0, 85.0)
        beta = np.radians(slope_val)
        gamma = lp["gamma"]
        z = lp["z"]
        phi = np.radians(lp["phi_deg"])
        c = lp["c"]
        den = gamma * z * np.sin(beta) * np.cos(beta)
        fs_dry = (c + gamma * z * (np.cos(beta) ** 2) * np.tan(phi)) / den
        fs_dry_list.append(float(fs_dry))

    fs_dry_arr = np.array(fs_dry_list)

    chosen_a = None
    chosen_stats = None
    for a_val in np.arange(0.05, 3.05, 0.05):
        a_val = round(float(a_val), 2)
        w = np.exp(-a_val * (fs_dry_arr - 1.0))
        mean_w = np.mean(w)
        lam = np.minimum(LAMBDA_LOC_MAX, LAMBDA_LOC_SCALE * w / mean_w)
        p10 = np.percentile(lam, 10)
        p90 = np.percentile(lam, 90)
        ratio = p90 / p10
        if 3.0 <= ratio <= 6.0:
            chosen_a = a_val
            chosen_stats = (p10, float(np.median(lam)), p90, ratio)
            break

    if chosen_a is None:
        raise ValueError("Could not find 'a' on 0.05 grid satisfying p90/p10 in [3, 6]")

    p10, med, p90, ratio = chosen_stats
    print(f"Calibration successful: a={chosen_a:.2f}, p10={p10:.3f}, median={med:.3f}, p90={p90:.3f}, ratio={ratio:.3f}")
    return chosen_a, fs_dry_arr

def process_location(df_loc: pd.DataFrame, loc_id: str, traits: dict, loc_params: dict,
                     lambda_loc: float, w_loc: float, fs_dry_val: float, hazard_a: float, seed: int):
    """Computes physics, V1b creep, pore-pressure weighted events and precursors for a single location."""
    df_loc = df_loc.copy()
    df_loc.set_index("Timestamp", inplace=True, drop=False)
    
    # Map geometry columns to dataframe
    for key, val in traits.items():
        if key not in df_loc.columns:
            df_loc[key] = val

    # Base rolling rainfall sum (72h)
    df_loc["rain_72h_sum"] = df_loc["precipitation"].rolling(window=72, min_periods=1).sum().fillna(0)

    # Geotechnical parameters from loc_params
    loc_lag_hours = loc_params["lag_hours"]
    gamma = loc_params["gamma"]
    z = loc_params["z"]
    phi_deg = loc_params["phi_deg"]
    phi = np.radians(phi_deg)
    c = loc_params["c"]

    raw_slope = traits["slope_1"]
    slope_val = np.clip(raw_slope, 1.0, 85.0)
    beta = np.radians(slope_val)

    df_loc["pore_pressure_proxy"] = df_loc["rain_72h_sum"].shift(loc_lag_hours).fillna(0)

    # Factor of Safety (FS) Calculation - Unmodified equation
    gamma_w = 9.81
    h_w = np.minimum(1.0, df_loc["pore_pressure_proxy"] / SATURATION_THRESHOLD) * z
    u = gamma_w * h_w
    
    fs_numerator = c + (gamma * z * np.cos(beta)**2 - u) * np.tan(phi)
    fs_denominator = gamma * z * np.sin(beta) * np.cos(beta)
    df_loc["FS"] = fs_numerator / fs_denominator

    # Dry FS (zero pore pressure)
    fs_baseline = (c + gamma * z * np.cos(beta)**2 * np.tan(phi)) / fs_denominator
    fs_dry = fs_baseline

    # 1. Base Displacement & V1b Creep: creep = 0.04 * R^2
    pore_pressure_fraction = np.minimum(1.0, df_loc["pore_pressure_proxy"].values / SATURATION_THRESHOLD)
    rain_creep = CREEP_MAX * (pore_pressure_fraction ** 2)

    hour_of_day = df_loc.index.hour.values
    thermal_cycle = 0.005 * np.sin((hour_of_day - 9) * (2 * np.pi / 24))
    base_noise = np.random.normal(0, NOISE_DISP_BASE, size=len(df_loc))
    df_loc["Displacement_Rate_mm_h"] = np.maximum(0.0, 0.01 + thermal_cycle + base_noise + rain_creep)

    # 2. Base Vibration
    base_vib = np.random.uniform(0.1, 0.5, size=len(df_loc))
    is_blasting_hour = (hour_of_day >= 14) & (hour_of_day <= 16)
    blast_spikes = np.where(
        is_blasting_hour & (np.random.random(len(df_loc)) < 0.05),
        np.random.uniform(5.0, 12.0, size=len(df_loc)),
        0.0,
    )
    df_loc["Vibration_mm_s"] = base_vib + blast_spikes

    # 3. High Risk Hours & V1b Event Sampling
    high_risk_mask = pore_pressure_fraction >= RISK_THRESHOLD
    high_risk_indices = np.where(high_risk_mask)[0]
    high_risk_hours_count = len(high_risk_indices)

    if high_risk_hours_count > 0:
        hr_weights = np.exp(5.0 * pore_pressure_fraction[high_risk_mask])
        hr_probs = hr_weights / np.sum(hr_weights)
    else:
        hr_probs = np.ones(len(df_loc)) / len(df_loc)
        high_risk_indices = np.arange(len(df_loc))

    num_events = max(1, np.random.poisson(lambda_loc))
    num_rain = int(round(num_events * RAIN_DRIVEN_RATIO))
    num_rain = min(num_events, max(0, num_rain))
    num_random = num_events - num_rain

    event_type_list = ["rain_driven"] * num_rain + ["random"] * num_random
    random.shuffle(event_type_list)

    event_records = []
    placed_indices = []
    unplaced_count = 0

    for ev_type in event_type_list:
        placed = False
        if ev_type == "rain_driven":
            for _ in range(MAX_SPACING_ATTEMPTS):
                cand_idx = np.random.choice(high_risk_indices, p=hr_probs)
                if all(abs(cand_idx - p_idx) >= MIN_EVENT_SPACING_H for p_idx in placed_indices):
                    placed_indices.append(cand_idx)
                    cand_time = df_loc.index[cand_idx]
                    event_records.append((cand_time, "rain_driven"))
                    placed = True
                    break
        else:
            for _ in range(MAX_SPACING_ATTEMPTS):
                cand_idx = random.randint(0, len(df_loc) - 1)
                if all(abs(cand_idx - p_idx) >= MIN_EVENT_SPACING_H for p_idx in placed_indices):
                    placed_indices.append(cand_idx)
                    cand_time = df_loc.index[cand_idx]
                    event_records.append((cand_time, "random"))
                    placed = True
                    break

        if not placed:
            unplaced_count += 1
            print(f"[WARNING] Location {loc_id}: could not place {ev_type} event with {MIN_EVENT_SPACING_H}h spacing after {MAX_SPACING_ATTEMPTS} attempts.")

    # Spacing stats
    if len(placed_indices) >= 2:
        sorted_indices = sorted(placed_indices)
        spacings = [sorted_indices[i] - sorted_indices[i - 1] for i in range(1, len(sorted_indices))]
        min_spacing = int(min(spacings))
        median_spacing = float(np.median(spacings))
        max_spacing = int(max(spacings))
    else:
        min_spacing = -1
        median_spacing = -1.0
        max_spacing = -1

    # 4. Apply Event Physics, Precursor Ramp, and Post-Event Decay
    df_loc["Rockfall_Event"] = np.int8(0)
    df_loc["post_event_window"] = np.int8(0)

    disp_col_idx = df_loc.columns.get_loc("Displacement_Rate_mm_h")
    vib_col_idx = df_loc.columns.get_loc("Vibration_mm_s")
    event_col_idx = df_loc.columns.get_loc("Rockfall_Event")
    post_col_idx = df_loc.columns.get_loc("post_event_window")

    event_lead_times = []
    for ev_time, ev_type in event_records:
        if ev_time not in df_loc.index:
            continue
        idx_ev = df_loc.index.get_loc(ev_time)
        df_loc.iloc[idx_ev, event_col_idx] = np.int8(1)

        # Precursor ramp on ALL events running through idx_ev INCLUSIVE
        lead_time = random.randint(PRECURSOR_LEAD_MIN, PRECURSOR_LEAD_MAX)
        event_lead_times.append(lead_time)
        start_pre = max(0, idx_ev - lead_time)
        end_pre = idx_ev + 1

        t_pre = np.arange(end_pre - start_pre)
        t_tot = end_pre - start_pre
        ramp = PRECURSOR_AMPLITUDE * (t_pre / max(1, t_tot)) ** 2
        df_loc.iloc[start_pre:end_pre, disp_col_idx] += ramp

        # Post-event effects start strictly at idx_ev + 1
        start_post = idx_ev + 1
        end_post = min(len(df_loc), idx_ev + 1 + POST_EVENT_HOURS)
        if start_post < end_post:
            df_loc.iloc[start_post:end_post, post_col_idx] = np.int8(1)
            t_decay = np.arange(end_post - start_post)
            decay_curve = 5.0 * np.exp(-t_decay / 12.0)
            df_loc.iloc[start_post:end_post, disp_col_idx] += decay_curve

            aftershock_vib = np.random.uniform(1.0, 4.0, size=len(t_decay)) * np.exp(-t_decay / 24.0)
            df_loc.iloc[start_post:end_post, vib_col_idx] += aftershock_vib

    # 5. Sensor Noise & Simultaneous Dropouts
    df_loc["Displacement_Rate_mm_h"] += np.random.normal(0, NOISE_DISP_FINAL, size=len(df_loc))
    df_loc["Displacement_Rate_mm_h"] = np.maximum(0.0, df_loc["Displacement_Rate_mm_h"].values)

    num_dropouts = int(round(len(df_loc) * DROPOUT_RATE))
    dropout_indices = np.random.choice(df_loc.index, num_dropouts, replace=False)
    df_loc.loc[dropout_indices, "Displacement_Rate_mm_h"] = np.nan
    df_loc.loc[dropout_indices, "Vibration_mm_s"] = np.nan

    # Clean up intermediate calculation columns
    cols_to_drop = ["pore_pressure_proxy", "rain_72h_sum", "X", "Y", "rand_point", "fid", "DN"]
    df_loc.drop(columns=[c for c in cols_to_drop if c in df_loc.columns], inplace=True)
    df_loc = downcast_dataframe(df_loc)

    meta_record = {
        "Location_ID": loc_id,
        "seed": seed,
        "gamma": gamma,
        "z": z,
        "phi_deg": phi_deg,
        "c": c,
        "lag_hours": loc_lag_hours,
        "baseline_FS": round(float(fs_baseline), 4),
        "HAZARD_A": round(float(hazard_a), 4),
        "a": round(float(hazard_a), 4),
        "FS_dry": round(float(fs_dry), 4),
        "w_loc": round(float(w_loc), 4),
        "lambda_loc": round(float(lambda_loc), 4),
        "high_risk_hours_count": high_risk_hours_count,
        "target_num_events": num_events,
        "num_events": len(event_records),
        "num_rain_driven": len([e for e in event_records if e[1] == "rain_driven"]),
        "num_random": len([e for e in event_records if e[1] == "random"]),
        "unplaced_events": unplaced_count,
        "min_spacing_hours": min_spacing,
        "median_spacing_hours": median_spacing,
        "max_spacing_hours": max_spacing,
        "event_timestamps": ";".join([str(t) for t, _ in event_records]),
        "event_types": ";".join([tp for _, tp in event_records]),
        "event_lead_times": ";".join([str(lt) for lt in event_lead_times]),
        "zero_high_risk_flag": 1 if high_risk_hours_count == 0 else 0,
    }

    return df_loc, meta_record

def generate_sensor_data(output_dir: str = "data/current/v1d_s1",
                         seed: int = None,
                         max_locations: int = None) -> str:
    os.makedirs(output_dir, exist_ok=True)
    parts_dir = os.path.join(output_dir, "parts")
    os.makedirs(parts_dir, exist_ok=True)

    seed_file = os.path.join(output_dir, "run_seed.txt")
    output_master_file = os.path.join(output_dir, "final_master_dataset.csv")
    output_meta_file = os.path.join(output_dir, "location_metadata.csv")

    if os.path.exists(seed_file):
        with open(seed_file, "r") as f:
            saved_seed = int(f.read().strip())
        if seed is not None and seed != saved_seed:
            raise ValueError(f"Cannot resume run: specified seed ({seed}) differs from existing saved seed ({saved_seed}) in '{output_dir}'.")
        seed = saved_seed
        print(f"Resuming run in '{output_dir}' with saved seed: {seed}")
    else:
        if seed is None:
            seed = random.randint(0, 1_000_000_000)
        with open(seed_file, "w") as f:
            f.write(str(seed) + "\n")

    print(f"=== Synthetic Rockfall Generator V1d ===")
    print(f"Run Seed: {seed}")
    print(f"Output Directory: {output_dir}")
    print(f"CREEP_MAX: {CREEP_MAX}")
    if max_locations:
        print(f"Subset Run: max {max_locations} locations")

    # Seed both random and numpy.random
    random.seed(seed)
    np.random.seed(seed)

    try:
        df_geometry = pd.read_csv(GEOMETRY_FILE)
        if "Location_ID" not in df_geometry.columns:
            df_geometry["Location_ID"] = [f"LOC_{i+1}" for i in range(len(df_geometry))]
        loc_traits_all = {row["Location_ID"]: row.to_dict() for _, row in df_geometry.iterrows()}
    except FileNotFoundError as e:
        print(f"[ERROR] Required geometry file is missing: {e}")
        sys.exit(1)

    all_loc_ids = list(loc_traits_all.keys())

    # Generate geotechnical parameters for all 500 locations deterministically
    loc_params_all = {}
    for lid in all_loc_ids:
        loc_params_all[lid] = {
            "lag_hours": random.randint(8, 16),
            "gamma": np.random.uniform(20.0, 25.0),
            "z": np.random.uniform(1.0, 2.0),
            "phi_deg": np.random.uniform(30.0, 40.0),
            "c": np.random.uniform(4.0, 10.0),
        }

    # Calibrate 'a' from FS_dry only (before generating)
    print("Calibrating 'a' from FS_dry distribution...")
    chosen_a, fs_dry_arr = calibrate_hazard_a(loc_traits_all, loc_params_all)

    # Compute w_loc and lambda_loc for all locations
    fs_dry_dict = {}
    w_dict = {}
    for i, lid in enumerate(all_loc_ids):
        fs_dry_dict[lid] = fs_dry_arr[i]
        w_dict[lid] = np.exp(-chosen_a * (fs_dry_arr[i] - 1.0))

    mean_w = np.mean(list(w_dict.values()))
    lambda_dict = {lid: min(LAMBDA_LOC_MAX, LAMBDA_LOC_SCALE * w_dict[lid] / mean_w) for lid in all_loc_ids}

    print(f"Calibration Complete: mean(w) = {mean_w:.4f}, lambda_loc range: [{min(lambda_dict.values()):.2f}, {max(lambda_dict.values()):.2f}]")

    # Filter to max_locations if specified
    active_loc_ids = all_loc_ids[:max_locations] if max_locations else all_loc_ids
    active_loc_set = set(active_loc_ids)

    # Check existing part files for resumability
    existing_part_files = sorted(glob.glob(os.path.join(parts_dir, "part_*.csv")))
    completed_loc_ids = set()
    last_completed_part_idx = -1

    for pf in existing_part_files:
        rng_file = pf.replace(".csv", "_rng.pkl")
        if os.path.exists(rng_file):
            try:
                with open(rng_file, "rb") as f:
                    part_info = pickle.load(f)
                completed_loc_ids.update(part_info["loc_ids"])
                base_name = os.path.basename(pf)
                p_idx = int(base_name.replace("part_", "").replace(".csv", ""))
                if p_idx > last_completed_part_idx:
                    last_completed_part_idx = p_idx
            except Exception as e:
                print(f"[WARNING] Corrupt part info {rng_file}: {e}")

    if last_completed_part_idx >= 0:
        last_rng_file = os.path.join(parts_dir, f"part_{last_completed_part_idx:04d}_rng.pkl")
        with open(last_rng_file, "rb") as f:
            last_info = pickle.load(f)
        random.setstate(last_info["random_state"])
        np.random.set_state(last_info["np_random_state"])
        print(f"Resuming from part {last_completed_part_idx:04d} ({len(completed_loc_ids)} locations already completed).")
    else:
        if os.path.exists(output_meta_file):
            os.remove(output_meta_file)

    chunksize = 1_000_000
    current_loc_df = []
    current_loc_id = None
    locations_processed = len(completed_loc_ids)
    next_part_idx = last_completed_part_idx + 1

    current_part_dfs = []
    current_part_loc_ids = []
    current_part_meta = []

    start_time = time.time()
    total_expected = len(active_loc_ids)

    def flush_current_part():
        nonlocal next_part_idx, current_part_dfs, current_part_loc_ids, current_part_meta
        if not current_part_dfs:
            return
        df_part = pd.concat(current_part_dfs, ignore_index=True)
        part_path = os.path.join(parts_dir, f"part_{next_part_idx:04d}.csv")
        rng_path = os.path.join(parts_dir, f"part_{next_part_idx:04d}_rng.pkl")

        rng_payload = {
            "loc_ids": list(current_part_loc_ids),
            "random_state": random.getstate(),
            "np_random_state": np.random.get_state()
        }
        with open(rng_path + ".tmp", "wb") as f:
            pickle.dump(rng_payload, f)
        if os.path.exists(rng_path):
            os.remove(rng_path)
        os.replace(rng_path + ".tmp", rng_path)

        write_csv_with_retry(df_part, part_path)
        append_metadata_with_retry(current_part_meta, output_meta_file)

        current_part_dfs = []
        current_part_loc_ids = []
        current_part_meta = []
        next_part_idx += 1

    print("Streaming weather dataset through physics engine...")
    for chunk in pd.read_csv(WEATHER_FILE, parse_dates=["Timestamp"], chunksize=chunksize):
        for loc_id, group in chunk.groupby("Location_ID", sort=False):
            if current_loc_id is None:
                current_loc_id = loc_id
                
            if loc_id == current_loc_id:
                current_loc_df.append(group)
            else:
                if current_loc_id in active_loc_set and current_loc_id not in completed_loc_ids:
                    df_loc = pd.concat(current_loc_df)
                    df_processed, meta_record = process_location(
                        df_loc, current_loc_id, loc_traits_all[current_loc_id],
                        loc_params_all[current_loc_id], lambda_dict[current_loc_id],
                        w_dict[current_loc_id], fs_dry_dict[current_loc_id], chosen_a, seed
                    )
                    current_part_dfs.append(df_processed)
                    current_part_loc_ids.append(current_loc_id)
                    current_part_meta.append(meta_record)
                    locations_processed += 1

                    if len(current_part_loc_ids) >= LOCATIONS_PER_PART:
                        flush_current_part()

                    if locations_processed % 25 == 0:
                        elapsed = time.time() - start_time
                        loc_per_sec = locations_processed / elapsed if elapsed > 0 else 1.0
                        rem_locs = max(0, total_expected - locations_processed)
                        est_rem_sec = rem_locs / loc_per_sec if loc_per_sec > 0 else 0
                        print(f"[{time.strftime('%H:%M:%S')}] Processed {locations_processed}/{total_expected} locations "
                              f"({locations_processed/total_expected*100:.1f}%) | "
                              f"Elapsed: {elapsed:.1f}s | Est. remaining: {est_rem_sec/60:.1f} min | Rate: {loc_per_sec:.2f} loc/s", flush=True)

                if max_locations and locations_processed >= max_locations:
                    current_loc_df = []
                    break

                current_loc_id = loc_id
                current_loc_df = [group]

        if max_locations and locations_processed >= max_locations:
            break

    if current_loc_df and (not max_locations or locations_processed < max_locations):
        if current_loc_id in active_loc_set and current_loc_id not in completed_loc_ids:
            df_loc = pd.concat(current_loc_df)
            df_processed, meta_record = process_location(
                df_loc, current_loc_id, loc_traits_all[current_loc_id],
                loc_params_all[current_loc_id], lambda_dict[current_loc_id],
                w_dict[current_loc_id], fs_dry_dict[current_loc_id], chosen_a, seed
            )
            current_part_dfs.append(df_processed)
            current_part_loc_ids.append(current_loc_id)
            current_part_meta.append(meta_record)
            locations_processed += 1

    flush_current_part()

    all_parts = sorted(glob.glob(os.path.join(parts_dir, "part_*.csv")))
    concatenate_parts(all_parts, output_master_file)

    if os.path.exists(output_meta_file):
        df_meta = pd.read_csv(output_meta_file).drop_duplicates(subset=["Location_ID"])
        df_meta.to_csv(output_meta_file, index=False)
    else:
        df_meta = pd.DataFrame()

    print(f"\n--- Generator Complete ---")
    print(f"Processed {locations_processed} locations across {len(all_parts)} part files.")
    print(f"Master dataset: {output_master_file} (size: {os.path.getsize(output_master_file)/1e6:.1f} MB)")
    print(f"Metadata table: {output_meta_file} ({len(df_meta)} rows)")
    return output_master_file

def main():
    parser = argparse.ArgumentParser(description="Realistic Rockfall Synthetic Sensor Data Generator V1d")
    parser.add_argument("--output-dir", type=str, default="data/current/v1d_s1", help="Output directory")
    parser.add_argument("--seed", type=int, default=None, help="Random seed (defaults to random draw)")
    parser.add_argument("--max-locations", type=int, default=None, help="Max locations to process")
    args = parser.parse_args()

    generate_sensor_data(output_dir=args.output_dir, seed=args.seed, max_locations=args.max_locations)

if __name__ == "__main__":
    main()

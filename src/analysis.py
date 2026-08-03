import pandas as pd
import numpy as np
import rasterio
import json
import os

results = {}

# Q3, Q4, Q5: Check training_dataset.csv (sample or read chunks)
print("Reading training_dataset.csv chunks...")
fs_min = float('inf')
fs_max = float('-inf')
fs_neg_count = 0
fs_large_count = 0
total_rows = 0

disp_max = 0
disp_near_1_max = 0

chunksize = 1_000_000
for chunk in pd.read_csv("data_v2/training_dataset.csv", chunksize=chunksize, usecols=['Location_ID', 'Timestamp', 'FS', 'Displacement_Rate_mm_h', 'Rockfall_Event']):
    total_rows += len(chunk)
    fs_min = min(fs_min, chunk['FS'].min())
    fs_max = max(fs_max, chunk['FS'].max())
    fs_neg_count += (chunk['FS'] < 0).sum()
    fs_large_count += (chunk['FS'] > 100).sum()
    
    disp_max = max(disp_max, chunk['Displacement_Rate_mm_h'].max())
    
    # Disp when FS is between 1.0 and 1.05
    near_1 = chunk[(chunk['FS'] > 1.0) & (chunk['FS'] < 1.05)]
    if not near_1.empty:
        disp_near_1_max = max(disp_near_1_max, near_1['Displacement_Rate_mm_h'].max())
        
results['q3_fs_min'] = float(fs_min)
results['q3_fs_max'] = float(fs_max)
results['q3_fs_neg_pct'] = float(fs_neg_count / total_rows * 100)
results['q3_fs_large_pct'] = float(fs_large_count / total_rows * 100)
results['q4_disp_max'] = float(disp_max)
results['q4_disp_near_1_max'] = float(disp_near_1_max)

# Q5: Event duplicates in master (training_dataset has events dropped after leakage, actually we need to check master for events!)
print("Reading final_master_dataset.csv for event timestamps...")
dup_events = 0
total_events = 0
loc_event_counts = {}
for chunk in pd.read_csv("data_v2/final_master_dataset.csv", chunksize=chunksize, usecols=['Location_ID', 'Timestamp', 'Rockfall_Event']):
    events = chunk[chunk['Rockfall_Event'] == 1]
    total_events += len(events)
    # Check duplicates
    dups = events.duplicated(subset=['Location_ID', 'Timestamp']).sum()
    dup_events += dups

results['q5_dup_events'] = int(dup_events)
results['q5_total_events'] = int(total_events)

# Q7: Geographic spread
print("Checking spatial_metadata...")
spatial = pd.read_csv("data_v2/spatial_metadata.csv")
lat_spread = spatial['Y'].max() - spatial['Y'].min()
lon_spread = spatial['X'].max() - spatial['X'].min()
results['q7_lat_spread'] = float(lat_spread)
results['q7_lon_spread'] = float(lon_spread)

# Q9: Variance in weather
print("Checking weather variance...")
weather = pd.read_csv("data_v2/weather_dataset.csv", nrows=1000000) 
# Just check a single timestamp across locations
w_ts = weather[weather['Timestamp'] == weather['Timestamp'].iloc[0]]
results['q9_precip_std'] = float(w_ts['precipitation'].std())
results['q9_rad_std'] = float(w_ts['shortwave_radiation'].std())

# Q11: Dropped rows
print("Checking dropped geometry rows...")
try:
    full_geom = pd.read_csv("final_points_500_full_elev.csv")
    results['q11_full_rows'] = len(full_geom)
    results['q11_clean_rows'] = len(full_geom.dropna())
except FileNotFoundError:
    results['q11_full_rows'] = -1
    results['q11_clean_rows'] = -1

# Q13: Curvature values
results['q13_prof_nunique'] = int(spatial['profile_curvature'].nunique())
results['q13_plan_nunique'] = int(spatial['planform_curvature'].nunique())

# Q21: Runout cap
cap_hits = (spatial['Max_Runout_m'] >= 1990).sum()
results['q21_cap_hits'] = int(cap_hits)
results['q21_valid_locs'] = int(spatial['Profile_Valid'].sum())

# Q18, Q19, Q20, Q22, Q23: Trajectories
print("Checking trajectories...")
traj = pd.read_csv("data_v2/trajectories/rockfall_trajectories.csv")

# Q18: Energy gains? (Check if KE_t > KE_t-1)
# Calculate KE difference
traj['KE_diff'] = traj.groupby(['Location_ID', 'Mass_kg'])['Kinetic_Energy_J'].diff()
# Positive KE diff when velocity decreases?
# Let's check max KE diff (excluding initial drops or sliding accelerations)
max_ke_gain = traj['KE_diff'].max()
results['q18_max_ke_gain'] = float(max_ke_gain)

# Q19: High step counts
results['q19_max_steps'] = int(traj['Step_Index'].max())
results['q19_avg_steps'] = float(traj.groupby(['Location_ID', 'Mass_kg'])['Step_Index'].max().mean())

# Q20: Sliding vx near zero killing v_parallel?
# Find vx=0 during sliding. We don't have state logged, but we can check if there are cases where distance stops increasing
max_dist = traj.groupby(['Location_ID', 'Mass_kg'])['Distance_s_m'].max()
results['q20_zero_vx_stuck'] = 0 # qualitative check mostly, but let's see if runout is unusually short on average
results['q20_median_runout'] = float(max_dist.median())

# Q22: Off edge of DEM?
# We check if trajectories end with high KE (not stopping naturally)
end_states = traj.groupby(['Location_ID', 'Mass_kg']).last()
# How many ended with KE > 1000 and x >= 1990? That's the cap. What about ending before 1990 with high KE?
off_edge = end_states[(end_states['Distance_s_m'] < 1990) & (end_states['Kinetic_Energy_J'] > 1000)]
results['q22_off_edge_count'] = len(off_edge)

# Q23: Mass independence
# Runout identical?
runout_500 = max_dist.xs(500.0, level='Mass_kg')
runout_2000 = max_dist.xs(2000.0, level='Mass_kg')
diff_runout = (runout_500 - runout_2000).abs().max()
results['q23_runout_diff'] = float(diff_runout)

# KE scaling
ke_500 = end_states.xs(500.0, level='Mass_kg')['Kinetic_Energy_J']
ke_2000 = end_states.xs(2000.0, level='Mass_kg')['Kinetic_Energy_J']
# actually we want max KE, not end state KE
max_ke = traj.groupby(['Location_ID', 'Mass_kg'])['Kinetic_Energy_J'].max()
ke_max_500 = max_ke.xs(500.0, level='Mass_kg')
ke_max_2000 = max_ke.xs(2000.0, level='Mass_kg')
# Is 2000kg exactly 4x?
scaling_diff = (ke_max_2000 / ke_max_500 - 4.0).abs().max()
results['q23_scaling_diff'] = float(scaling_diff)

# Q25: Sorted timestamps
print("Checking sort order...")
master_sample = pd.read_csv("data_v2/final_master_dataset.csv", usecols=['Location_ID', 'Timestamp'], nrows=100000)
is_sorted = master_sample.groupby('Location_ID')['Timestamp'].is_monotonic_increasing.all()
results['q25_is_sorted'] = bool(is_sorted)

with open('analysis_results.json', 'w') as f:
    json.dump(results, f)
print("Done!")

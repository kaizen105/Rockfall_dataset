"""
2D ROCKFALL KINEMATIC SIMULATION ENGINE
=======================================
This module implements rigid-body point-mass kinematics along a 2D topographic profile 
to determine maximum rockfall runout, bounce height, and kinetic energy.

1. Freefall / Projectile Motion:
   v_{z,t} = v_{z,t-1} - g \Delta t
   x_t = x_{t-1} + v_x \Delta t
   z_t = z_{t-1} + v_{z,t} \Delta t

2. Impact & Restitution (CRSP Model):
   Velocity is decomposed into slope-normal (v_n) and slope-tangential (v_t) vectors.
   v_{out,n} = -R_n * v_{in,n}
   v_{out,t} = R_t * v_{in,t}
   Where R_n and R_t are Normal and Tangential coefficients of restitution.

3. Sliding / Rolling Friction:
   When v_{out,n} < MIN_BOUNCE_VELOCITY, the rock transitions to continuous ground contact.
   a_{parallel} = g_{parallel} + a_{friction}
   a_{parallel} = -g \sin(\theta) - \text{sign}(v_x) \mu (g \cos(\theta))
   Where \theta is the local slope angle and \mu is the rolling friction coefficient.

4. Kinetic Energy:
   E_k = \frac{1}{2} m (v_x^2 + v_z^2)

ASSUMPTIONS & LIMITATIONS:
- Constant Azimuth Profile: The 2D elevation profile is extracted as a straight line 
  following the initial steepest-descent azimuth at the starting coordinate. It does 
  not dynamically recalculate descent direction as it moves. On heavily curved terrain, 
  this may diverge from a true 3D particle trace. This is an accepted limitation of 
  standard 2D profile-based rockfall analysis (which assumes the fall line is linear 
  or laterally constrained).
- Point Mass Kinematics: Ignores block shape, angular momentum, and air drag.
"""
import os
import rasterio
import pandas as pd
import numpy as np
import pyproj
from scipy.interpolate import RegularGridInterpolator
import warnings

warnings.filterwarnings("ignore")

# --- CRSP Kinematic Parameters ---
GRAVITY = 9.81
DT = 0.05  # time step (seconds)
RN = 0.35  # Normal Restitution (CRSP talus/soil)
RT = 0.85  # Tangential Restitution
MU = 0.15  # Rolling friction coefficient

# Numerical Failsafes
MIN_BOUNCE_VELOCITY = 0.5  # m/s (approx 1.2cm bounce height cutoff)
MAX_TIME = 120.0  # seconds
PROFILE_STEP = 2.0  # meters
PROFILE_MAX_STEPS = 1000  # 2000m max runout

MASSES = [500.0, 2000.0, 10000.0]

def extract_profile(dem_asc, y_coords_asc, x_coords, start_easting, start_northing):
    interp_z = RegularGridInterpolator((y_coords_asc, x_coords), dem_asc, bounds_error=False, fill_value=np.nan)
    
    grad_y, grad_x = np.gradient(dem_asc, y_coords_asc, x_coords)
    interp_gy = RegularGridInterpolator((y_coords_asc, x_coords), grad_y, bounds_error=False, fill_value=0.0)
    interp_gx = RegularGridInterpolator((y_coords_asc, x_coords), grad_x, bounds_error=False, fill_value=0.0)
    
    E, N = start_easting, start_northing
    
    # Calculate fixed azimuth based on initial steepest descent
    gy = interp_gy((N, E))
    gx = interp_gx((N, E))
    mag = np.hypot(gx, gy)
    if mag < 1e-4:
        return [], []
        
    dE = -gx / mag
    dN = -gy / mag
    
    profile_s = []
    profile_z = []
    cumulative_s = 0.0
    
    for _ in range(PROFILE_MAX_STEPS):
        z = interp_z((N, E))
        if np.isnan(z):
            break
            
        profile_s.append(cumulative_s)
        profile_z.append(float(z))
        
        E += dE * PROFILE_STEP
        N += dN * PROFILE_STEP
        cumulative_s += PROFILE_STEP
        
    return np.array(profile_s), np.array(profile_z)

def simulate_rockfall(s_arr, z_arr, mass):
    if len(s_arr) < 2:
        return [], 0.0, 0.0, 0.0
        
    # Initial State
    x = s_arr[0]
    z = z_arr[0] + 1.0  # initial 1m drop
    vx = 0.5
    vz = 0.0
    
    time = 0.0
    state = "BOUNCING"
    
    max_x = x
    max_h = 0.0
    max_ke = 0.0
    max_s = s_arr[-1]
    
    trajectory_log = []
    step_idx = 0
    
    while time < MAX_TIME:
        if x >= max_s:
            break
            
        ground_z = np.interp(x, s_arr, z_arr)
        
        if state == "BOUNCING":
            vz_new = vz - GRAVITY * DT
            x_new = x + vx * DT
            z_new = z + vz_new * DT
            
            ground_z_new = np.interp(x_new, s_arr, z_arr)
            
            if z_new <= ground_z_new:
                idx = min(int(x / PROFILE_STEP), len(s_arr)-2)
                dx = s_arr[idx+1] - s_arr[idx]
                dz = z_arr[idx+1] - z_arr[idx]
                
                length = np.hypot(dx, dz)
                if length == 0:
                    break
                    
                tangent = np.array([dx, dz]) / length
                normal = np.array([-tangent[1], tangent[0]])
                if normal[1] < 0: normal = -normal
                    
                vi = np.array([vx, vz])
                v_in_n = np.dot(vi, normal)
                v_in_t = np.dot(vi, tangent)
                
                v_out_n = -RN * v_in_n
                v_out_t = RT * v_in_t
                
                if abs(v_out_n) < MIN_BOUNCE_VELOCITY:
                    state = "SLIDING"
                    z = ground_z_new
                    x = x_new
                    vx = tangent[0] * v_out_t
                    vz = tangent[1] * v_out_t
                else:
                    v_out = v_out_n * normal + v_out_t * tangent
                    vx, vz = v_out[0], v_out[1]
                    z = ground_z_new + 0.01
                    x = x_new
            else:
                x, z, vz = x_new, z_new, vz_new
                
        elif state == "SLIDING":
            idx = min(int(x / PROFILE_STEP), len(s_arr)-2)
            dx = s_arr[idx+1] - s_arr[idx]
            dz = z_arr[idx+1] - z_arr[idx]
            
            tangent = np.array([dx, dz]) / np.hypot(dx, dz)
            theta = np.arctan2(tangent[1], tangent[0])
            
            g_parallel = -GRAVITY * np.sin(theta)
            g_perp = GRAVITY * np.cos(theta)
            friction = -np.sign(vx) * MU * g_perp
            
            a_parallel = g_parallel + friction
            v_parallel = np.linalg.norm([vx, vz]) * np.sign(vx)
            
            if v_parallel == 0:
                if a_parallel > 0:
                    v_parallel_new = a_parallel * DT
                else:
                    break
            else:
                v_parallel_new = v_parallel + a_parallel * DT
                if v_parallel * v_parallel_new <= 0:
                    break
                    
            vx = tangent[0] * v_parallel_new
            vz = tangent[1] * v_parallel_new
            
            x += vx * DT
            z = np.interp(x, s_arr, z_arr)
            
        # Logging
        ke = 0.5 * mass * (vx**2 + vz**2)
        h = z - ground_z
        
        trajectory_log.append({
            'Mass_kg': mass,
            'Step_Index': step_idx,
            'Time_s': round(time, 2),
            'Distance_s_m': round(x, 2),
            'Elevation_z_m': round(z, 2),
            'Velocity_x_mps': round(vx, 3),
            'Velocity_z_mps': round(vz, 3),
            'Kinetic_Energy_J': round(ke, 2)
        })
        
        max_x = max(max_x, x)
        max_h = max(max_h, h)
        max_ke = max(max_ke, ke)
        
        time += DT
        step_idx += 1
        
    return trajectory_log, max_x, max_h, max_ke

def main():
    print("Loading DEM...")
    dem_path = 'data_v2/rasters/dem_reprojected_utm45n.tif'
    
    # Create directories if they don't exist
    os.makedirs('data_v2/trajectories', exist_ok=True)
    
    with rasterio.open(dem_path) as src:
        dem = src.read(1)
        transform = src.transform
        bounds = src.bounds
        nodata = src.nodata

    if nodata is not None:
        dem = np.where(dem == nodata, np.nan, dem)

    rows = np.arange(dem.shape[0])
    cols = np.arange(dem.shape[1])
    y_coords = bounds.top + (rows + 0.5) * transform[4]
    x_coords = bounds.left + (cols + 0.5) * transform[0]
    y_coords_asc = y_coords[::-1]
    dem_asc = dem[::-1, :]

    print("Loading spatial metadata...")
    df = pd.read_csv('data_v2/spatial_metadata.csv')
    transformer = pyproj.Transformer.from_crs("EPSG:4326", "EPSG:32645", always_xy=True)

    summary_results = []
    all_trajectories = []
    
    print(f"Simulating rockfall trajectories for {len(df)} locations...")
    for idx, row in df.iterrows():
        loc_id = row['Location_ID']
        lon, lat = row['X'], row['Y']
        E, N = transformer.transform(lon, lat)
        
        s_arr, z_arr = extract_profile(dem_asc, y_coords_asc, x_coords, E, N)
        
        loc_summary = {'Location_ID': loc_id}
        max_run = 0
        max_bounce = 0
        
        is_valid = len(s_arr) >= 2
        loc_summary['Profile_Valid'] = is_valid
        
        if not is_valid:
            print(f"WARNING: Invalid DEM profile for {loc_id}. Logging zeroes.")
            for mass in MASSES:
                loc_summary[f'Max_Kinetic_Energy_{int(mass)}kg_J'] = 0.0
            loc_summary['Max_Runout_m'] = 0.0
            loc_summary['Max_Bounce_Height_m'] = 0.0
            summary_results.append(loc_summary)
            continue
        
        for mass in MASSES:
            traj_log, runout, bounce, ke = simulate_rockfall(s_arr, z_arr, mass)
            
            # Attach location ID to trajectory rows
            for t in traj_log:
                t['Location_ID'] = loc_id
            all_trajectories.extend(traj_log)
            
            # Update overall geometric maxes (mass-independent)
            max_run = max(max_run, runout)
            max_bounce = max(max_bounce, bounce)
            loc_summary[f'Max_Kinetic_Energy_{int(mass)}kg_J'] = round(ke, 2)
            
        loc_summary['Max_Runout_m'] = round(max_run, 2)
        loc_summary['Max_Bounce_Height_m'] = round(max_bounce, 2)
        
        summary_results.append(loc_summary)
        
        if (idx + 1) % 50 == 0:
            print(f"  Processed {idx + 1}/{len(df)} locations.")

    # Save full trajectories
    traj_df = pd.DataFrame(all_trajectories)
    # Reorder columns
    traj_cols = ['Location_ID', 'Mass_kg', 'Step_Index', 'Time_s', 'Distance_s_m', 'Elevation_z_m', 'Velocity_x_mps', 'Velocity_z_mps', 'Kinetic_Energy_J']
    traj_df = traj_df[traj_cols]
    traj_df.to_csv('data_v2/trajectories/rockfall_trajectories.csv', index=False)
    print(f"\nSaved full trajectories to data_v2/trajectories/rockfall_trajectories.csv")

    # Update spatial metadata
    out_df = pd.DataFrame(summary_results)
    
    # Drop existing trajectory columns if rerunning
    cols_to_drop = [c for c in df.columns if c in out_df.columns and c != 'Location_ID']
    df = df.drop(columns=cols_to_drop, errors='ignore')
    
    df = df.merge(out_df, on='Location_ID', how='left')
    df.to_csv('data_v2/spatial_metadata.csv', index=False)
    print("Appended summary trajectory features to spatial_metadata.csv")

if __name__ == "__main__":
    main()

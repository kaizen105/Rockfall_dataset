---
dataset_info:
  features:
  - name: Timestamp
    dtype: string
  - name: Location_ID
    dtype: string
  - name: Displacement_Rate_mm_h
    dtype: float64
  - name: Vibration_mm_s
    dtype: float64
  - name: Rockfall_Event
    dtype: int64
  - name: FS
    dtype: float64
  - name: elev_1
    dtype: float64
  - name: slope_1
    dtype: float64
  - name: aspect_1
    dtype: float64
  - name: rough_1
    dtype: float64
  - name: tri_1
    dtype: float64
  - name: profile_curvature
    dtype: float64
  - name: planform_curvature
    dtype: float64
  - name: temperature_2m
    dtype: float64
  - name: precipitation
    dtype: float64
  - name: windspeed_10m
    dtype: float64
  - name: shortwave_radiation
    dtype: float64
  splits:
  - name: train
    num_bytes: 2646045818
    num_examples: 12966776
  download_size: 2646045818
  dataset_size: 2646045818
configs:
- config_name: default
  data_files:
  - split: train
    path: training_dataset.csv
---

# 🪨 Noamundi Rockfall Simulation Dataset

![Dataset Size](https://img.shields.io/badge/Dataset_Size-12.96M_Rows-blue)
![Locations](https://img.shields.io/badge/Monitoring_Locations-500-green)
![Events](https://img.shields.io/badge/Rockfall_Events-2,436-red)

## 📌 1. Dataset Overview
This dataset provides a physics-informed simulation of rockfall precursor conditions and trajectory runouts for 500 monitoring locations in the Noamundi mining region in Jharkhand, India. It is designed specifically for training and benchmarking Machine Learning models on **early-warning systems, anomaly detection, rare-event classification, and spatio-temporal (ST-GNN) trajectory modeling** in geotechnical environments.

> [!WARNING]
> It is a simulated dataset mapping real-world terrain and weather variables to simulated physics sensors and trajectories. It is *not* a record of real historical rockfalls.

---

## 📊 2. Dataset Structure & Features
- **Total Rows (Timeseries):** ~12,966,700 (Cleaned Training Dataset)
- **Total Locations:** 500
- **Rockfall Events (Positive Class):** 2,436
- **Sensor Dropout Rate:** 1.0% (~130,000 rows randomly set to NaN for realism)
- **Trajectory Steps:** Dense spatio-temporal step sequences available in `rockfall_trajectories.csv`

### 2.1 Dataset Files
- **`training_dataset.csv`**: The hourly predictive timeseries containing weather, terrain metadata, and simulated IoT sensor readings. Target leakage windows (72h post-event) have been explicitly removed to make it ML-ready.
- **`spatial_metadata.csv`**: Static geographical, geomorphological, and geomechanical metadata for all 500 locations, including the final trajectory maximums (runout, bounce height, energy).
- **`data_v2/trajectories/rockfall_trajectories.csv`**: Full spatio-temporal pathing (dt=0.05s) for simulated rockfall drops across three hazard mass classes (500kg, 2000kg, 10000kg).

### 2.2 Feature Provenance (Real vs Simulated)
| Column | Status | Source |
| :--- | :--- | :--- |
| `elev_1`, `slope_1`, `aspect_1`, `rough_1`, `tri_1`, `profile_curvature`, `planform_curvature` | **Real** | DEM via OpenTopography (30m SRTM) |
| `temperature_2m`, `precipitation`, `windspeed_10m`, `shortwave_radiation` | **Real** | Historical HOURLY weather via Open-Meteo API |
| `FS` (Factor of Safety) | **Physics** | Computed hourly via Infinite Slope Stability model |
| `Displacement_Rate_mm_h`, `Vibration_mm_s` | **Simulated** | Displacement driven by FS; Vibration driven by event spikes |
| `Rockfall_Event` | **Simulated** | 80% rainfall-driven (FS threshold), 20% random triggers |
| `Max_Runout_m`, `Max_Bounce_Height_m`, `Max_Kinetic_Energy_*` | **Physics** | 2D rigid-body kinematics (CRSP parameters) |

*(Note: Geographic artifacts `X`, `Y`, `rand_point`, `fid` were intentionally dropped from the hourly training set to prevent neural networks from geographically memorizing locations. They remain available in the spatial metadata).*

### 2.3 Data Dictionaries

#### `spatial_metadata.csv` (Key Columns)
- **`Location_ID`**: Unique identifier for the monitoring point.
- **`Profile_Valid`** *(Boolean)*: Flag indicating if the DEM raycast successfully generated a valid slope profile. Exists to handle edge-case DEM nodata boundaries (flagged 1/500 locations as invalid).
- **`Profile_Clipped`** *(Boolean)*: Flag indicating if the trajectory simulation prematurely exited due to reaching the physical bounds of the extracted DEM raster before coming to a natural rest.
- **`Max_Runout_m`** *(Float)*: The absolute maximum horizontal distance a boulder traveled from the source.
- **`Max_Bounce_Height_m`** *(Float)*: The maximum vertical height achieved above the terrain during a bounce.
- **`Max_Kinetic_Energy_500kg_J` / `2000kg` / `10000kg`** *(Float)*: The peak kinetic energy achieved during the runout for the respective boulder mass.

#### `rockfall_trajectories.csv`
- **`Location_ID`**: Identifier linking back to the source location.
- **`Mass_kg`**: The mass of the simulated boulder (500.0, 2000.0, or 10000.0).
- **`Step_Index`**: Sequential integer index of the simulation step.
- **`Time_s`**: Elapsed time in seconds (dt=0.05s).
- **`Distance_s_m`**: Cumulative distance along the 2D topographic profile.
- **`Elevation_z_m`**: Absolute elevation of the boulder at the current timestep.
- **`Velocity_x_mps` / `Velocity_z_mps`**: Horizontal and vertical velocity components.
- **`Kinetic_Energy_J`**: Instantaneous kinetic energy.
- **`State`** *(String)*: Kinematic state of the boulder at this step (`BOUNCING` encompasses both freefall and bouncing physics, `SLIDING` indicates sliding friction).

---

## 🧮 3. Simulation Constraints & Assumptions
The underlying simulation is divided into two physics engines:

### 3.1 Precursor Engine (Infinite Slope Stability)
The 1D slope stability model computes Factor of Safety (FS):

![FS formula](https://latex.codecogs.com/svg.image?%5Cdpi%7B120%7D%5Cbg%7Btransparent%7D%5Ccolor%7Bwhite%7DFS%3D%5Cfrac%7Bc%2B%28%5Cgamma%20%5Ccdot%20z%20%5Ccdot%20%5Ccos%5E2%5Cbeta-u%29%5Ctan%5Cphi%7D%7B%5Cgamma%20%5Ccdot%20z%20%5Ccdot%20%5Csin%5Cbeta%20%5Ccdot%20%5Ccos%5Cbeta%7D)

**Key Modeling Decisions:**
- Geotechnical parameters (γ: 20-25 kN/m³, φ: 30°-40°, c: 4-10 kPa) are typical ranges for open-pit mining contexts per Hoek & Bray, not field-verified Noamundi measurements.
- Pore pressure:

  ![pore pressure formula](https://latex.codecogs.com/svg.image?%5Cdpi%7B120%7D%5Cbg%7Btransparent%7D%5Ccolor%7Bwhite%7Du%3D%5Cgamma_w%5Ccdot%5Cmin%5Cleft%281.0%2C%5Cfrac%7Brain_%7B72h%7D%7D%7B100.0%7D%5Cright%29%5Ccdot%20z)

  The 100.0 mm threshold for full saturation is a heuristic engineering assumption.
- 80% of events occur when FS ≤ 1.3, with the probability of failure exponentially weighted by the severity of the instability:

  ![probability formula](https://latex.codecogs.com/svg.image?%5Cdpi%7B120%7D%5Cbg%7Btransparent%7D%5Ccolor%7Bwhite%7DP%5Cpropto%20%5Cexp%285%281.3-FS%29%29)

  The remaining 20% are random triggers representing 'dry rockfalls'.
- **Stochastic Generation:** The final precursor simulation runs unseeded by design, encouraging variations across regenerations.

### 3.2 Trajectory Engine (2D Kinematics)
To simulate downstream hazard, a custom 2D kinematics engine drops boulder masses from each location and traces their downhill paths.

**Initial Conditions:** Boulders are released with a 1.0m initial vertical drop and a 0.5 m/s horizontal velocity. This mimics standard RocFall software initialization to simulate realistic dislodgement and prevent instant friction-locking on shallow start points.

**Physics Methodology & Equations:**
The model uses discrete Euler integration (dt=0.05s) mapping rigid-body impact restitution and rolling friction.

**Projectile / Freefall Motion:**

![freefall formulas](https://latex.codecogs.com/svg.image?%5Cdpi%7B120%7D%5Cbg%7Btransparent%7D%5Ccolor%7Bwhite%7D%5Cbegin%7Baligned%7Dv_%7Bz%2Ct%7D%26%3Dv_%7Bz%2Ct-1%7D-g%5CDelta%20t%5C%5Cx_t%26%3Dx_%7Bt-1%7D%2Bv_x%5CDelta%20t%5C%5Cz_t%26%3Dz_%7Bt-1%7D%2Bv_%7Bz%2Ct%7D%5CDelta%20t%5Cend%7Baligned%7D)

**Impact Velocity Decomposition:**
Velocity vectors are decomposed against the local ground slope tangent (**t̂**) and normal (**n̂**):

![impact decomposition formulas](https://latex.codecogs.com/svg.image?%5Cdpi%7B120%7D%5Cbg%7Btransparent%7D%5Ccolor%7Bwhite%7D%5Cbegin%7Baligned%7Dv_%7Bin%2Cn%7D%26%3D%5Cvec%7Bv%7D_%7Bin%7D%5Ccdot%5Cvec%7Bn%7D%5C%5Cv_%7Bin%2Ct%7D%26%3D%5Cvec%7Bv%7D_%7Bin%7D%5Ccdot%5Cvec%7Bt%7D%5Cend%7Baligned%7D)

**Restitution (CRSP Model):**
Uses Colorado Rockfall Simulation Program (CRSP) industry-standard parameters for vegetated talus slopes (R<sub>n</sub> = 0.35, R<sub>t</sub> = 0.85, μ = 0.15):

![restitution formulas](https://latex.codecogs.com/svg.image?%5Cdpi%7B120%7D%5Cbg%7Btransparent%7D%5Ccolor%7Bwhite%7D%5Cbegin%7Baligned%7Dv_%7Bout%2Cn%7D%26%3D-R_n%5Ccdot%20v_%7Bin%2Cn%7D%5C%5Cv_%7Bout%2Ct%7D%26%3DR_t%5Ccdot%20v_%7Bin%2Ct%7D%5Cend%7Baligned%7D)

**Sliding / Rolling Friction:**
Triggered when normal velocity drops below a bounce threshold (v<sub>out,n</sub> < 0.5 m/s):

![friction formula](https://latex.codecogs.com/svg.image?%5Cdpi%7B120%7D%5Cbg%7Btransparent%7D%5Ccolor%7Bwhite%7Da_%7Bparallel%7D%3D-g%5Csin%28%5Ctheta%29-%5Ctext%7Bsign%7D%28v_x%29%5Ccdot%5Cmu%5Ccdot%20g%5Ccos%28%5Ctheta%29)

**Kinetic Energy:**

![kinetic energy formula](https://latex.codecogs.com/svg.image?%5Cdpi%7B120%7D%5Cbg%7Btransparent%7D%5Ccolor%7Bwhite%7DE_k%3D%5Cfrac%7B1%7D%7B2%7Dm%28v_x%5E2%2Bv_z%5E2%29)

**Data Target Isolation:** Runout distances and kinetic energies are appended as *static topological metadata* to `spatial_metadata.csv` (and full paths in `rockfall_trajectories.csv`) to strictly prevent target leakage into the hourly predictive timeseries.

---

## 📈 4. Validation Analysis

### 4.1 Event-Window Validation (Hourly Timeseries)
The direct whole-dataset correlation between Displacement and FS is **-0.017**, which is near-zero because the hard FS ≤ 1.3 trigger acts as a step-function across millions of dry hours.

However, the **population-level learnable signal** is real: average pre-event windows show a genuine sustained climb in displacement (~0.025 to ~0.13 mm/h over 72 hours), compared to a flat ~0.015 mm/h for random non-event windows.

| Feature | FS | Displacement (mm/h) | Vibration (mm/s) | Rockfall_Event |
| :--- | :--- | :--- | :--- | :--- |
| `temperature_2m` | -0.020 | 0.011 | 0.054 | 0.000 |
| `precipitation` | -0.037 | 0.005 | 0.011 | -0.001 |
| `slope_1` | -0.782 | 0.025 | 0.004 | -0.003 |
| `FS` | 1.000 | -0.017 | -0.004 | 0.002 |
| `Displacement_Rate_mm_h` | -0.017 | 1.000 | 0.199 | **0.317** |
| `Vibration_mm_s` | -0.004 | 0.199 | 1.000 | 0.085 |

*(Note the high collinearity between `slope_1` and ruggedness `tri_1` (0.864) for feature importance interpretation).*

### 4.2 Trajectory Runout Validation
The kinematic engine was validated against the 500 sampled locations to ensure physics stability:
- **Runout Distribution:** Mean = 153.6m, Median = 113.3m, Max = 1,998.3m.
- **Invalid Profile Flagging:** The `Profile_Valid` flag successfully caught 1/500 locations (`LOC_65`) that touched a DEM NoData boundary at initialization, zeroing out its resulting metrics to prevent silent dataset contamination.
- **Truncation Check:** Of the remaining 499 valid locations, 5 (1.0%) reached the physical boundary of their extracted DEM raster array mid-flight and were cut off (explicitly flagged via `Profile_Clipped = True`). The vast majority of boulders naturally halted due to simulated physical friction rather than hitting boundary edges.
- **Energy Mass Scaling:** Verified perfectly linear scaling across masses. At identical locations, the 2000kg boulder yields exactly 4.00x the kinetic energy of the 500kg boulder, and the 10000kg boulder yields exactly 20.00x, mathematically confirming runout distance is correctly mass-independent in the kinematics loop.

---

## ⚠️ 5. Known Limitations
- **Target Leakage Validation:** In the raw dataset, sensor readings are artificially elevated for 72 hours following an event. **The `training_dataset` provided here has already had these 72-hour leakage windows strictly removed**, ensuring it is mathematically safe for ML model training.
- Simulated ground truth, not field-validated.
- **DEM Resolution limitation:** The NASA SRTM GL1 30m resolution is coarse relative to individual boulder-scale features.
- Simplified 1D slope stability physics (no 3D/groundwater/fracture modeling).
- **Constant Azimuth 2D Trajectories:** The kinematic engine extracts a straight-line downslope profile based on the initial steepest descent azimuth. It does not dynamically trace 3D topographic curvature during runout.
- **Point-Mass Trajectories:** Kinematics ignore boulder shape, fragmentation, angular momentum, and air drag.
- Static 270° wind direction assumption in the downscaling model.
- **Poisson Event Floor Bias:** Event count is governed by an artificial `max(1, poisson(5))` floor, ensuring no location is perfectly stable (0 events).

---

## 🎯 6. Suggested ML Tasks
- **Classification & Anomaly Detection:** Benchmarking rare-event logic under physically grounded class imbalance.
- **Precursor / Early-Warning Research:** Studying lead-time detection (mind the 80/20 rainfall vs random trigger split).
- **Cross-Location Generalization:** Testing models across different geographic baselines.
- **Spatio-Temporal Graph Neural Networks (ST-GNN):** Utilizing `rockfall_trajectories.csv` to graph spatial trajectory overlap, simulating downstream impact propagation and modeling hazard networks.

---

## 💻 7. Source Code
The data generation pipeline and physics engine source code is hosted on GitHub: [https://github.com/kaizen105/Rockfall_dataset](https://github.com/kaizen105/Rockfall_dataset).

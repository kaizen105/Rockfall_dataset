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

![Dataset Size](https://img.shields.io/badge/Dataset_Size-13.14M_Rows-blue)
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

### 2.1 Feature Provenance (Real vs Simulated)
| Column | Status | Source |
| :--- | :--- | :--- |
| `elev_1`, `slope_1`, `aspect_1`, `rough_1`, `tri_1`, `profile_curvature`, `planform_curvature` | **Real** | DEM via OpenTopography (30m SRTM) |
| `temperature_2m`, `precipitation`, `windspeed_10m`, `shortwave_radiation` | **Real** | Historical HOURLY weather via Open-Meteo API |
| `FS` (Factor of Safety) | **Physics** | Computed hourly via Infinite Slope Stability model |
| `Displacement_Rate_mm_h`, `Vibration_mm_s` | **Simulated** | Displacement driven by FS; Vibration driven by event spikes |
| `Rockfall_Event` | **Simulated** | 80% rainfall-driven (FS threshold), 20% random triggers |
| `Max_Runout_m`, `Max_Bounce_Height_m`, `Max_Kinetic_Energy_*` | **Physics** | 2D rigid-body kinematics (CRSP parameters) |

*(Note: Geographic artifacts `X`, `Y`, `rand_point`, `fid` were intentionally dropped from the hourly training set to prevent neural networks from geographically memorizing locations. They remain available in the spatial metadata).*

---

## 🧮 3. Simulation Constraints & Assumptions
The underlying simulation is divided into two physics engines:

### 3.1 Precursor Engine (Infinite Slope Stability)
The 1D slope stability model computes Factor of Safety (FS):
`FS = [ c + (γ · z · cos²β - u) · tanφ ] / [ γ · z · sinβ · cosβ ]`

**Key Modeling Decisions:**
- Geotechnical parameters (`γ`: 20-25 kN/m³, `φ`: 30°-40°, `c`: 4-10 kPa) are typical ranges for open-pit mining contexts per Hoek & Bray, not field-verified Noamundi measurements.
- Pore pressure `u = γ_w * min(1.0, rain_72h / 100.0) * z`. The `100.0` mm threshold for full saturation is a heuristic engineering assumption.
- 80% of events occur when `FS ≤ 1.3`, with the probability of failure exponentially weighted by the severity of the instability (`P ∝ exp(5 * (1.3 - FS))`). The remaining 20% are random triggers representing 'dry rockfalls'.
- **Stochastic Generation:** The final precursor simulation runs unseeded by design, encouraging variations across regenerations.

### 3.2 Trajectory Engine (2D Kinematics)
To simulate downstream hazard, a custom 2D kinematics engine drops boulder masses (500kg, 2,000kg, 10,000kg) from each location and traces their downhill paths.
- **Physics Math:** Uses discrete Euler integration with rigid-body impact restitution and rolling friction.
- **CRSP Sourced Parameters:** Employs the Colorado Rockfall Simulation Program (CRSP) industry-standard parameters for vegetated talus slopes (Normal Restitution `Rn = 0.35`, Tangential Restitution `Rt = 0.85`, Rolling Friction `μ = 0.15`).
- **Data Target Isolation:** Runout distances and kinetic energies are appended as *static topological metadata* to `spatial_metadata.csv` (and full paths in `rockfall_trajectories.csv`) to strictly prevent target leakage into the hourly predictive timeseries.

---

## 📈 4. Event-Window Validation Analysis
The dataset is engineered to contain a genuine predictive precursor signal, though it is obfuscated by extreme class imbalance. The direct whole-dataset correlation between Displacement and FS is **-0.017**, which is near-zero because the hard `FS ≤ 1.3` trigger acts as a step-function across millions of dry hours.

However, the **population-level learnable signal** is real: average pre-event windows show a genuine sustained climb in displacement (~0.025 to ~0.13 mm/h over 72 hours), compared to a flat ~0.015 mm/h for random non-event windows. 

### Key Feature Correlations
| Feature | FS | Displacement (mm/h) | Vibration (mm/s) | Rockfall_Event |
| :--- | :--- | :--- | :--- | :--- |
| `temperature_2m` | -0.020 | 0.011 | 0.054 | 0.000 |
| `precipitation` | -0.037 | 0.005 | 0.011 | -0.001 |
| `windspeed_10m` | -0.042 | 0.014 | 0.026 | 0.001 |
| `shortwave_radiation` | 0.011 | 0.006 | 0.049 | -0.000 |
| `elev_1` | 0.008 | -0.006 | -0.003 | -0.000 |
| `slope_1` | -0.782 | 0.025 | 0.004 | -0.003 |
| `aspect_1` | -0.001 | -0.003 | 0.003 | -0.003 |
| `rough_1` | 0.094 | 0.019 | 0.000 | 0.000 |
| `tri_1` | -0.588 | 0.032 | 0.004 | -0.003 |
| `profile_curvature` | -0.019 | -0.002 | 0.000 | 0.000 |
| `planform_curvature` | -0.001 | 0.001 | -0.001 | -0.000 |
| **Target Variables** | | | | |
| `FS` | 1.000 | -0.017 | -0.004 | 0.002 |
| `Displacement_Rate_mm_h` | -0.017 | 1.000 | 0.199 | **0.317** |
| `Vibration_mm_s` | -0.004 | 0.199 | 1.000 | 0.085 |

*(Note the high collinearity between `slope_1` and ruggedness `tri_1` (0.864) for feature importance interpretation).*

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

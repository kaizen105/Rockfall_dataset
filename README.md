# 🪨 Noamundi Rockfall Simulation Pipeline

![Dataset Size](https://img.shields.io/badge/Dataset_Size-13.14M_Rows-blue)
![Locations](https://img.shields.io/badge/Monitoring_Locations-500-green)
![Events](https://img.shields.io/badge/Rockfall_Events-2,436-red)

## 📌 1. Project Overview
This repository contains a physics-informed data generation pipeline simulating rockfall precursor conditions for the Noamundi mining region in Jharkhand, India. By fusing real-world terrain (DEM) and historical weather data with geotechnical stability modeling, the pipeline synthesizes IoT sensor readings and rockfall event labels.

> [!WARNING]
> This dataset is designed strictly for research into rockfall early-warning systems, anomaly detection, and hazard classification. **It is a physics simulation, not a record of real historical rockfall incidents.**

---

## 🏗️ 2. Repository Architecture
- 🗺️ `qgis_raw_data/`: Contains raw OpenTopography DEM exports (NASA SRTM GL1 30m resolution) and intermediate GIS shapefiles.
- ⚙️ `src/data/`: Core python scripts for the data generation pipeline.
- 📊 `data_v2/`: Output directory for the final generated datasets (`spatial_metadata.csv`, `final_master_dataset.csv`, `training_dataset.csv`).

---

## 🚀 3. Pipeline Execution (Setup & Reproducibility)
To regenerate the dataset from scratch on your local machine:

**Environment Setup:**
```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

**Execution Order:**
1. **`python src/data/prepare_geometry_500.py`**
   - Extracts real elevations and samples 500 monitoring locations constrained to a steep-slope mask.
2. **`python src/data/get_weather_data.py`**
   - Fetches historical hourly Open-Meteo data (2021-2023) and applies KMeans clustering and orographic scaling.
3. **`python src/data/create_sensor_data.py`**
   - Streams the geometries and weather through the physics engine to generate 13.14M rows of raw sensor data (`final_master_dataset.csv`).
4. **`python src/data/create_training_dataset.py`**
   - Cleans the raw dataset by removing geographic artifact columns and explicitly masking out the 72-hour post-event target leakage windows, outputting the ML-ready `training_dataset.csv`.

---

## 🔬 4. Under the Hood (Simulation Methodology)

### ⛰️ 4.1 Terrain Extraction
DEM data was obtained via OpenTopography (30m resolution). 500 monitoring locations were selected by uniform random sampling (`random_state=42`) constrained within a steep-zone polygon mask (slope ≥ 15°). 
*(Note: Applying the ≥15° mask was empirically necessary to raise the mean slope from 5.85° to 16.15°, ensuring the Factor of Safety drops low enough to enable realistic failure dynamics).*

### 🌦️ 4.2 Weather & Microclimate Downscaling
Historical hourly weather (Jan 1, 2021 – Dec 31, 2023) was pulled from the Open-Meteo API. To avoid API limits, the 500 locations were clustered into 25 KMeans centroids, then mathematically downscaled to the individual points:
- **Temperature Lapse Rate:** `-0.0065 * elev_diff`
- **Orographic Rain:** `precipitation * (1.0 + 0.05 * cos(aspect - 270°) * sin(slope))` *(assumes static Westerly wind).*
- **Solar Radiation:** `shortwave_radiation * (1.0 + 0.10 * cos(aspect - 180°) * sin(slope))`

### 🧮 4.3 Physics (Factor of Safety)
FS is computed hourly using the Infinite Slope Stability model (Skempton and DeLory):
`FS = [ c + (γ · z · cos²β - u) · tanφ ] / [ γ · z · sinβ · cosβ ]`
- `β` (slope angle): 15° to 34°
- `γ` (unit weight): 20 to 25 kN/m³ (per Hoek & Bray)
- `z` (depth): 1.0 to 2.0 m
- `φ` (friction angle): 30° to 40°
- `c` (cohesion): 4 to 10 kPa
- `γ_w` (unit weight of water): 9.81 kN/m³
- `u` (pore pressure): `γ_w * min(1.0, rain_72h / 100.0) * z` *(heuristic assumption for monsoon saturation).*

### 📡 4.4 Sensor & Event Simulation
- **Events (Poisson λ=5):** 
  - 80% triggered during critical instability (`FS ≤ 1.3`). **The probability of failure is exponentially weighted by the severity of instability** (`P ∝ exp(5 * (1.3 - FS))`).
  - 20% random triggers (modeling dry rockfalls like root wedging or mining blasts).
- **Infiltration Lag:** A random lag of 8-16 hours between rainfall and pore pressure effect.
- **Displacement Creep:** `0.15 / (max(FS, 1.01) - 1.0)` during `FS ≤ 1.3`. Includes a 24-hour thermal cycle sine-wave.
- **Post-Event Decay:** Displacement decays exponentially (`5 * exp(-0.1 * t)`) over 72 hours.
- **Vibration:** Event spikes `γ * z * sin(β) * U(0.4, 0.6) * exp(-0.05*t)`. Includes daily mining blast spikes (14:00-16:00).
- **Stochastic Generation:** While location sampling is deterministic, the final physics generation is intentionally unseeded. This ensures variance across regenerations, encouraging models to learn underlying physical relationships rather than memorizing exact noise profiles.

---

## 📈 5. Event-Window Validation Analysis
The direct whole-dataset correlation between Displacement and FS is **-0.017**, and the 72h pre-event windowed correlation is **-0.028**. 
Both are near-zero despite a real physical signal existing because the hard `FS ≤ 1.3` gate creates a step-function rather than a gradual ramp, averaging out to zero across millions of dry hours. 

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

---

## ⚠️ 6. Known Limitations
- **Target Leakage Warning:** In the raw dataset, sensor readings are artificially elevated for 72 hours following an event. Any time-series windowing for model training must explicitly mask these post-event rows to prevent target leakage (Note: `create_training_dataset.py` handles this automatically).
- Simulated ground truth, not field-validated.
- **DEM Resolution limitation:** The NASA SRTM GL1 30m resolution is coarse relative to individual boulder-scale features.
- Simplified 1D physics (Infinite Slope only, no 3D/groundwater/fracture modeling).
- **Noamundi-specific field measurements missing:** Geomechanical data relies on typical ranges from literature (Hoek & Bray).
- Static 270° wind direction assumption in the downscaling model.
- **Poisson Event Floor Bias:** Event count is governed by an artificial `max(1, poisson(5))` floor, ensuring no location is perfectly stable (0 events).
- **Undifferentiated Triggers:** Rainfall-driven events and random 'dry' rockfall events are logged identically as `Rockfall_Event = 1`.

---

## 🛠️ 7. Development History / Changelog
1. **90° QGIS Slope Bug:** Fixed raster boundary artifacts by clipping the raster.
2. **Flat-Terrain Bug:** Fixed by applying a steep-polygon mask (16.15° mean slope).
3. **Weather API Limits:** Fixed via 25-cluster KMeans and physics-based downscaling.
4. **Fabricated Elevation Bug:** Extracted real DEM elevations to fix a constant 500.0 artifact.
5. **Hourly Upgrade:** Rescaled rolling-window logic (3/7-day to 72/168-hour).
6. **Target Leakage & Junk Columns:** Discovered QGIS artifacts and post-event settling decay leakage. Fixed via a dedicated post-processing script (`create_training_dataset.py`).

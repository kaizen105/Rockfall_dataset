# Noamundi Rockfall Simulation Pipeline

## 1. Project Overview
This repository contains a physics-informed data generation pipeline simulating rockfall precursor conditions for the Noamundi mining region in Jharkhand, India. It combines real-world terrain (DEM) and weather data with geotechnical stability modeling to synthesize IoT sensor readings and rockfall event labels.

It is designed to generate synthetic datasets for research into rockfall early-warning systems, anomaly detection, and hazard classification. **It is not a record of real rockfall incidents.**

## 2. Repository Architecture
- `qgis_raw_data/`: Contains raw OpenTopography DEM exports (NASA SRTM GL1 30m resolution) and intermediate GIS shapefiles.
- `src/data/`: Core python scripts for the generation pipeline (`prepare_geometry_500.py`, `get_weather_data.py`, `create_sensor_data.py`, `fix_curvature_crs.py`).
- `data_v2/`: The output directory for the final generated datasets, including `spatial_metadata.csv` and the main `final_master_dataset.csv`.

## 3. Pipeline Execution
To regenerate the dataset from scratch on your local machine:

**Environment Setup:**
```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

**Execution Order:**
1. **Geometry Extraction:** `python src/data/prepare_geometry_500.py`
   - Samples 500 monitoring locations constrained to a steep-slope mask.
2. **Weather Downscaling:** `python src/data/get_weather_data.py`
   - Fetches historical hourly Open-Meteo data (2021-2023) and applies KMeans clustering and orographic scaling.
3. **Sensor Simulation:** `python src/data/create_sensor_data.py`
   - Streams the geometries and weather through the physics engine to generate the 13.14M rows of sensor data.

## 4. Under the Hood (Simulation Methodology)
The pipeline generates data by layering real-world geography and weather with physical simulation formulas.

### 4.1 Real vs Simulated Data
- **Real (DEM):** `elev_1`, `slope_1`, `aspect_1`, `rough_1`, `tri_1`, `profile_curvature`, `planform_curvature`
- **Real (Weather):** `temperature_2m`, `precipitation`, `windspeed_10m`, `shortwave_radiation` (Open-Meteo API)
- **Physics-derived:** Microclimate Downscaling, Factor of Safety (`FS`)
- **Simulated (Sensors):** `Displacement_Rate_mm_h`, `Vibration_mm_s`, `Rockfall_Event`

### 4.2 Terrain Extraction
DEM data was obtained via OpenTopography (30m resolution). 500 monitoring locations were selected by uniform random sampling (`random_state=42`) constrained within a steep-zone polygon mask (slope ≥ 15°). 
*(Note: Applying the ≥15° mask was empirically necessary to raise the mean slope from 5.85° to 16.15°, ensuring the Factor of Safety drops low enough to enable realistic failure dynamics).*

### 4.3 Weather & Microclimate Downscaling
Historical hourly weather (Jan 1, 2021 – Dec 31, 2023) was pulled from the Open-Meteo API. To avoid API limits and redundancies, the 500 locations were clustered into 25 KMeans centroids for the API fetch, then mathematically downscaled to the individual points:
- **Temperature Lapse Rate:** `-0.0065 * elev_diff`
- **Orographic Rain:** `precipitation * (1.0 + 0.05 * cos(aspect - 270°) * sin(slope))` *(assumes static Westerly wind).*
- **Solar Radiation:** `shortwave_radiation * (1.0 + 0.10 * cos(aspect - 180°) * sin(slope))`

### 4.4 Physics (Factor of Safety)
FS is computed hourly using the Infinite Slope Stability model (Skempton and DeLory):
`FS = [ c + (γ · z · cos²β - u) · tanφ ] / [ γ · z · sinβ · cosβ ]`
- `β` (slope angle): 15° to 34°
- `γ` (unit weight): 20 to 25 kN/m³ (per Hoek & Bray)
- `z` (depth): 1.0 to 2.0 m
- `φ` (friction angle): 30° to 40°
- `c` (cohesion): 4 to 10 kPa
- `γ_w` (unit weight of water): 9.81 kN/m³
- `u` (pore pressure): `γ_w * min(1.0, rain_72h / 100.0) * z` *(heuristic assumption for monsoon saturation).*

### 4.5 Sensor & Event Simulation
- **Events (Poisson λ=5):** 
  - 80% triggered during critical instability (`FS ≤ 1.3`). **The probability of failure is exponentially weighted by the severity of instability** (`P ∝ exp(5 * (1.3 - FS))`).
  - 20% random triggers (modeling dry rockfalls like root wedging or mining blasts).
- **Infiltration Lag:** A random lag of 8-16 hours between rainfall and pore pressure effect.
- **Displacement Creep:** `0.15 / (max(FS, 1.01) - 1.0)` during `FS ≤ 1.3`. Includes a 24-hour thermal cycle sine-wave.
- **Post-Event Decay:** Displacement decays exponentially (`5 * exp(-0.1 * t)`) over 72 hours.
- **Vibration:** Event spikes `γ * z * sin(β) * U(0.4, 0.6) * exp(-0.05*t)`. Includes daily mining blast spikes (14:00-16:00).

## 5. Deliberate Stochastic Generation
While point locations and KMeans clustering are deterministic (`random_state=42`), the final physics/sensor generation step (`create_sensor_data.py`) is intentionally **NOT seeded**. This is a deliberate design choice to ensure that anyone regenerating the data receives statistically identical but individually variant data (rather than perfectly identical "blessed" data). This forces models to learn the underlying physics rather than overfitting to specific generated numbers.

## 6. Development History / Changelog
1. **90° QGIS Slope Bug:** Fixed raster boundary artifacts.
2. **Flat-Terrain Bug:** Fixed by applying a steep-polygon mask (16.15° mean slope).
3. **Weather API Limits:** Fixed via 25-cluster KMeans downscaling.
4. **Fabricated Elevation Bug:** Extracted real DEM elevations to fix a constant 500.0 artifact.
5. **Hourly Upgrade:** Rescaled rolling-window logic (72/168-hour).
6. **Junk Columns:** Dropped QGIS artifacts (`rand_point`, `fid`, `X`, `Y`) from the training set.

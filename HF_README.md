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
    num_bytes: 1534000000
    num_examples: 13140000
  download_size: 1534000000
  dataset_size: 1534000000
configs:
- config_name: default
  data_files:
  - split: train
    path: data/train-*
---

# Noamundi Rockfall Simulation Dataset

## 1. Overview
This dataset is a physics-informed simulation of rockfall precursor conditions for the Noamundi mining region in Jharkhand, India. It combines real-world terrain (DEM) and weather data with geotechnical stability modeling to synthesize IoT sensor readings and rockfall event labels.

It is designed for research into rockfall early-warning systems, anomaly detection, and hazard classification. **It is not a record of real rockfall incidents.** No real rockfall event ever recorded at Noamundi is represented here.

## 2. What Is Real vs Simulated
| Column | Status | Source |
| :--- | :--- | :--- |
| `elev_1`, `slope_1`, `aspect_1`, `rough_1`, `tri_1` | **Real** | DEM via OpenTopography, processed in QGIS |
| `temperature_2m`, `precipitation`, `windspeed_10m`, `shortwave_radiation` | **Real** | Historical HOURLY weather via Open-Meteo API |
| Weather Downscaling | **Physics-derived** | Math-based adjustments (lapse rates, orographic formulas) |
| `FS` (Factor of Safety) | **Physics-derived** | Computed hourly via Infinite Slope Stability model |
| `Displacement_Rate_mm_h`, `Vibration_mm_s` | **Simulated** | Displacement driven by FS; Vibration from event spikes |
| `Rockfall_Event` | **Simulated** | 80% rainfall-driven (FS threshold), 20% random |

*(Note: Geographic artifacts `X`, `Y`, `rand_point`, `fid`, `DN` were dropped from the training set to prevent geographic memorization, but are retained in `spatial_metadata.csv` for GNN edge construction).*

## 3. Full Methodology

### Terrain Extraction
DEM data for the Noamundi region was obtained via OpenTopography and processed in QGIS to extract Elevation, Slope, Aspect, Roughness, and Ruggedness (TRI). 500 monitoring locations were selected by generating random points constrained within a steep-zone polygon mask (slope ≥ 15°). 
*(Note: Unconstrained random sampling was originally attempted but failed, yielding a mean slope of ~5.85°, which made the physics engine inert. Masking forced the mean slope up to 16.15°, enabling realistic failure dynamics).*

### Weather & Microclimate Downscaling
Historical hourly weather was pulled from the Open-Meteo API. Due to API rate limits across 500 locations—and because Open-Meteo's native grid resolution (~9-11km) makes per-point fetches largely redundant—the 500 locations were clustered into 25 KMeans macro-regions. The API fetched true hourly data for the 25 centroids, which was then mathematically downscaled to the 500 individual locations:
- **Temperature Lapse Rate:** `-0.0065 * elev_diff` (-6.5°C per 1000m elevation difference).
- **Orographic Rain:** `precipitation * (1.0 + 0.05 * cos(aspect - 270°) * sin(slope))`. *(Note: 270° assumes a static Westerly prevailing wind, which is a simplification that does not reflect actual seasonal monsoon shifts in this region).*
- **Solar Radiation:** `shortwave_radiation * (1.0 + 0.10 * cos(aspect - 180°) * sin(slope))`.

### Physics (Factor of Safety)
The Factor of Safety (FS) is computed hourly using the Infinite Slope Stability model (Skempton and DeLory), the identical single-point foundation used in tools like SHALSTAB and TRIGRS:
`FS = [ c + (γ · z · cos²β - u) · tanφ ] / [ γ · z · sinβ · cosβ ]`
- `β` (slope angle): 15° to 34° (real DEM)
- `γ` (unit weight): 20 to 25 kN/m³ (literature)
- `z` (depth): 1.0 to 2.0 m (literature)
- `φ` (friction angle): 30° to 40° (literature)
- `c` (cohesion): 4 to 10 kPa (literature)
- `u` (pore pressure): `9.81 * min(1.0, rain_72h / 100.0) * z`
*(Note: The `100.0` cumulative rainfall threshold for full soil saturation is a heuristically tuned value designed to simulate severe monsoonal conditions, rather than a field-measured geohydrological property. Furthermore, this 1D model does NOT account for 3D stress, groundwater routing, or joint/fracture mechanics).*

### Sensor & Event Simulation
- **Events:** Event count follows a Poisson process (λ = 5). 80% of events are weighted toward hours of critical instability (FS ≤ 1.3). 20% are placed at completely random hours (representing non-rainfall triggers).
- **Displacement Creep:** `0.15 / (max(FS, 1.01) - 1.0)` gated strictly on hours where `FS ≤ 1.3`. 
- **Vibration:** Event spikes are modeled as `γ * z * sin(β) * U(0.4, 0.6) * exp(-0.05*t)`.

## 4. Development History / Changelog
1. **90° QGIS Slope Bug:** QGIS raster processing initially produced 90° slope artifacts at boundaries; fixed by clipping the raster.
2. **Flat-Terrain Bug:** Unconstrained sampling yielded flat terrain (5.85° mean slope). Fixed by applying a steep-polygon mask (16.15° mean slope).
3. **Weather API Limits:** Fixed via 25-cluster KMeans and physics-based downscaling.
4. **Fabricated Elevation Bug:** An early script injected `elev_1 = 500.0` constant due to a missing DEM band; fixed by extracting real DEM elevations.
5. **Hourly Upgrade:** Upgraded from daily to hourly weather, requiring a rescale of the rolling-window logic (3/7-day to 72/168-hour).
6. **Junk Columns:** Discovered QGIS artifacts (`rand_point`, `fid`, `X`, `Y`) were contaminating the dataset as proxies for latitude. Dropped from the training set, retained only in `spatial_metadata.csv`.

## 5. Event-Window Validation Analysis
The direct whole-dataset correlation between Displacement and FS is **-0.017**, and the 72h pre-event windowed correlation is **-0.028**. 
Both are near-zero despite a real physical signal existing because the hard `FS ≤ 1.3` gate creates a step-function rather than a gradual ramp, averaging out to zero across the millions of dry hours. 

However, the **population-level learnable signal** is real: average pre-event windows show a genuine sustained climb in displacement (~0.025 to ~0.13 mm/h over 72 hours), compared to a flat ~0.015 mm/h for random non-event windows. 

The strongest single predictive correlation in the dataset is `Displacement_Rate_mm_h` vs `Rockfall_Event` (**0.317**). 
*(Note: Individual events vary by design. 80% show clean FS-driven displacement ramps, while 20% show flat FS with no precursors, intentionally simulating unpredictable failure modes).*

## 6. Key Feature Correlations
| Feature | FS | Displacement_Rate (mm/h) | Vibration (mm/s) | Rockfall_Event |
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
| **Target Cross-Correlations** | | | | |
| `FS` | 1.000 | -0.017 | -0.004 | 0.002 |
| `Displacement_Rate_mm_h` | -0.017 | 1.000 | 0.199 | 0.317 |
| `Vibration_mm_s` | -0.004 | 0.199 | 1.000 | 0.085 |
| `Rockfall_Event` | 0.002 | 0.317 | 0.085 | 1.000 |

*(For the full 13x13 matrix including junk columns, please refer to `dataset_summary.json`).*
*(Note the high collinearity between `slope_1` and ruggedness `tri_1` (0.864) for feature importance interpretation).*

## 7. Known Limitations
- Simulated ground truth, not field-validated.
- Simplified 1D physics (Infinite Slope only, no 3D/groundwater/fracture modeling).
- No geomechanical data (UCS, cohesion, friction angle from real site testing) because open geotechnical data is lacking for Indian mining regions.
- Static 270° wind direction assumption in the rainfall downscaling model (does not reflect actual seasonal monsoon direction shifts).
- Event count governed by Poisson process rather than purely FS-emergent.
- Weak whole-dataset correlation numbers requiring event-windowed temporal analysis to see the real signal.
- Class imbalance (2,436 positive events across 13.14M rows).
- Weather is downscaled from 25 real fetches, not independently measured at all 500 locations.

## 8. Suggested Uses
- **Classification & Anomaly Detection:** Benchmarking rare-event logic under physically grounded class imbalance.
- **Precursor / Early-Warning Research:** Studying lead-time detection (mind the 80/20 rainfall vs random trigger split).
- **Cross-Location Generalization:** Testing models across different geographic baselines.
- **Feature Ablation Studies:** Comparing relative value of terrain-only vs weather-only vs sensor-only inputs.

## 9. Dataset Structure Stats
- **Total Rows:** 13,140,000
- **Total Locations:** 500
- **Rockfall Events:** 2,436
- **Missing Data (Dropout):** 1.0% (~131,000 rows on sensor columns)

## 10. Code and Reproducibility
The full streaming pipeline is hosted at [https://github.com/kaizen105/Rockfall_dataset](https://github.com/kaizen105/Rockfall_dataset). 
To regenerate the data from scratch, run the scripts in this exact order:
1. `src/data/prepare_geometry_500.py`
2. `src/data/get_weather_data.py`
3. `src/data/create_sensor_data.py`

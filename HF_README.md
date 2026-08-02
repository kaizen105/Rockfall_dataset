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

## Overview
This dataset is a physics-informed simulation of rockfall precursor conditions, built by combining real-world terrain and weather data from the Noamundi mining region with synthetic IoT sensor readings and rockfall event labels.

It is designed for research into rockfall early-warning systems, precursor detection, anomaly detection, and hazard classification. **It is not a record of real rockfall incidents.** No real rockfall event ever recorded at Noamundi is represented here. 

## What Is Real vs. Simulated
| Component | Status | Source |
| :--- | :--- | :--- |
| **Terrain features** (Slope, Aspect, Ruggedness, Roughness, Elevation) | **Real** | Digital Elevation Model (DEM) via OpenTopography, processed in QGIS for the Noamundi region. |
| **Weather features** (temperature, precipitation, wind, radiation) | **Real** | Historical HOURLY weather via the Open-Meteo API for 25 macro-regions. |
| **Microclimate Downscaling** | **Physics-derived** | Weather is downscaled per location using lapse rates and orographic/solar logic, *not* Gaussian noise. |
| **Factor of Safety (FS)** | **Physics-derived** | Computed hourly per location using the Infinite Slope Stability model, driven by real slope angles and rainfall pore pressure. |
| **Sensor readings** (Displacement_Rate_mm_h, Vibration_mm_s) | **Simulated** | Displacement is driven by FS. Vibration includes physics-scaled event spikes plus background sensor noise. |
| **Rockfall events** | **Simulated** | 80% of events are driven by critical FS thresholds; 20% are random (non-rainfall). |

## Dataset Structure
- **13,140,000 rows:** True hourly readings across **500 unique locations**, spanning January 2021 to December 2023.
- **2,436 labeled rockfall events.**

### Columns
| Column | Description |
| :--- | :--- |
| `Timestamp` | Hourly timestamp |
| `Location_ID` | Simulated monitoring station identifier (LOC_1 to LOC_500) |
| `Displacement_Rate_mm_h` | Simulated ground displacement rate, driven by FS-based creep |
| `Vibration_mm_s` | Simulated ground vibration reading |
| `Rockfall_Event` | Binary label, 1 if a rockfall event occurs |
| `FS` | Factor of Safety, computed hourly |
| `elev_1`, `slope_1`, `aspect_1`, `rough_1`, `tri_1` | Static, **real** terrain features per location derived from DEM |
| `temperature_2m`, `precipitation`, `windspeed_10m`, `shortwave_radiation` | **Real** hourly weather features, downscaled to the specific location |

*(Note: Geographic artifacts `X`, `Y`, `rand_point`, `fid`, `DN` have been dropped from the training set to prevent geographic memorization, but are retained in `spatial_metadata.csv` for GNN edge construction).*

## Known Issues & Fixes (Changelog)
1. **The 90° QGIS Slope Bug:** Earlier QGIS raster processing produced 90-degree slope artifacts at DEM boundaries. This was fixed by correctly clipping the raster before slope generation.
2. **The Flat-Terrain Bug:** The original random point sampling favored flat terrain (avg 6° slope), causing the physics engine to fail. The sampling was rewritten to strictly target steep geographic slopes (15°–34°).
3. **The Fake Elevation Bug:** A previous generation script accidentally fabricated elevations (`elev_1 = 500 + noise`) due to a missing DEM band. This was corrected, and the dataset now uses actual DEM elevations.
4. **Weather Clustering & Downscaling:** Fetching 3 years of hourly data for 500 locations exceeds free Open-Meteo API limits. To solve this, the 500 locations were clustered into 25 KMeans macro-regions. The API fetches true hourly data for those 25 centroids, which is then physically downscaled to the 500 locations.

## Physics-Based Weather Downscaling
To bridge the 25 centroid fetches to the 500 unique locations, weather is downscaled using strict physical rules (not random Gaussian noise):
- **Temperature Lapse Rate:** Adjusted by elevation difference from the centroid using a ~6.5°C drop per 1,000m.
- **Orographic Rain:** Precipitation is scaled based on slope and aspect relative to a simplified hardcoded 270° Westerly prevailing wind direction.
- **Solar Radiation:** Shortwave radiation is scaled based on deviation from South-facing aspects.

## The Physics Engine & Event Triggers
The Factor of Safety (FS) is calculated using the Infinite Slope model. During sustained rainfall, pore pressure rises, dropping the FS. 
Rockfall events are placed using two distinct triggers:
1. **Rainfall-Driven (80%):** Placed at hours heavily weighted toward critical instability (`FS ≤ 1.3`). These events display a distinct precursor signal (displacement creep) in the final hours before failure.
2. **Random/Non-Rainfall (20%):** Placed randomly to simulate thermal cycling, blasting, or wildlife. These exhibit **zero** precursor displacement signals.

Because 20% of events are random and displacement only accelerates at the very end of the rainfall window, the overall dataset correlation between Displacement and FS is intentionally weak, requiring advanced temporal models (LSTMs, Transformers) to detect the true precursor windows.

## Code and Reproducibility
The full streaming architecture is open-sourced in this repository. It natively handles the 13.1 million rows with a minimal memory footprint.

## License
Released under CC-BY-4.0. You are free to share and adapt this dataset with attribution.

# Noamundi Rockfall Simulation Dataset

## Overview
This dataset is a physics-informed simulation of rockfall precursor conditions, built by combining real-world terrain and weather data from the Noamundi mining region with synthetic IoT sensor readings and rockfall event labels.

It is designed for research into rockfall early-warning systems, precursor detection, anomaly detection, and hazard classification. **It is not a record of real rockfall incidents.** No real rockfall event ever recorded at Noamundi is represented here. The terrain and weather layers are real; the sensor readings and event occurrences are simulated, now driven in part by a geotechnical stability model rather than arbitrary noise.

## What Is Real vs. Simulated
| Component | Status | Source |
| :--- | :--- | :--- |
| **Terrain features** (Slope, Aspect, Ruggedness, Roughness, Elevation) | **Real** | Digital Elevation Model (DEM) via OpenTopography, processed in QGIS for the Noamundi region. |
| **Weather features** (temperature, precipitation, wind, radiation) | **Real** | Historical HOURLY weather via the Open-Meteo API for 25 macro-regions. |
| **Microclimate Downscaling** | **Physics-derived** | Weather is downscaled per location using lapse rates and orographic/solar logic, *not* Gaussian noise. |
| **Factor of Safety (FS)** | **Physics-derived** | Computed hourly per location using the Infinite Slope Stability model, driven by real slope angles and rainfall pore pressure. |
| **Sensor readings** (Displacement_Rate_mm_h, Vibration_mm_s) | **Simulated** | Displacement is driven by FS. Vibration includes physics-scaled event spikes plus background sensor noise. |
| **Rockfall events** | **Simulated** | 80% of events are driven by critical FS thresholds; 20% are random (non-rainfall). |

The full generation pipeline, including the QGIS terrain extraction steps, the weather fetch script, the FS-based sensor simulation script, and the merge/validation scripts, is open sourced here: https://github.com/kaizen105/Rockfall_dataset

## Dataset Structure
- **13,140,000 rows**, true hourly readings across **500 simulated monitoring locations**, spanning January 2021 to December 2023.
- **2,436 labeled rockfall events**, reflecting the extreme rarity of real rockfall occurrence.

### Columns
| Column | Description |
| :--- | :--- |
| `Timestamp` | Hourly timestamp |
| `Location_ID` | Simulated monitoring station identifier (LOC_1 to LOC_500) |
| `Displacement_Rate_mm_h` | Simulated ground displacement rate, driven by FS-based creep |
| `Vibration_mm_s` | Simulated ground vibration reading |
| `Rockfall_Event` | Binary label, 1 if a rockfall event occurs |
| `FS` | Factor of Safety, computed hourly per location from the Infinite Slope Stability model |
| `elev_1`, `slope_1`, `aspect_1`, `rough_1`, `tri_1` | Static, **real** terrain features per location derived from DEM |
| `temperature_2m`, `precipitation`, `windspeed_10m`, `shortwave_radiation` | **Real** hourly weather features, downscaled to the specific location |

*(Note: Geographic artifacts `X`, `Y`, `rand_point`, `fid`, `DN` have been dropped from the training set to prevent geographic memorization, but are retained in `spatial_metadata.csv` for GNN edge construction).*

## How the Simulation Was Built

- **Terrain layer:** DEM data for the Noamundi region was obtained via OpenTopography and processed in QGIS to extract Elevation, Slope, Aspect, Ruggedness, and Roughness at each simulated monitoring location. These values are static per location.
- **Weather layer & Microclimate:** Historical weather data for the same region was pulled from the Open-Meteo API. To avoid API rate limits across 500 locations, locations were clustered into 25 macro-regions (KMeans). The 25 centroid fetches were then mathematically downscaled to the 500 locations using true lapse rates (~6.5°C per 1km elevation), orographic rain (factoring slope and aspect against a 270° Westerly prevailing wind), and solar radiation aspect adjustments.
- **Physics layer (FS):** A Factor of Safety is computed for every location at every hour using the Infinite Slope Stability model (Skempton and DeLory), the same core equation used as a simplified single-point foundation in regional tools such as SHALSTAB and TRIGRS:

  `FS = [ c + (γ · z · cos²β - u) · tanφ ] / [ γ · z · sinβ · cosβ ]`

  Variable ranges used, drawn from literature values for weathered rock and soil:
  - **β (slope angle):** 15° to 34°, explicitly sampled from the real DEM to ensure steep terrain dynamics.
  - **γ (unit weight):** 20 to 25 kN/m³
  - **z (depth to failure plane):** 1.0 to 2.0 m
  - **φ (friction angle):** 30° to 40°
  - **c (cohesion):** 4 to 10 kPa
  - **u (pore water pressure):** dynamically derived each hour from a 72-hour rolling rainfall proxy (h_w), 0 when dry and rising toward saturation during heavy rain.

  Under dry conditions (u = 0), the constants keep baseline FS in a stable range of roughly 1.5 to 2.5. During sustained rainfall, u rises, frictional resistance is stripped away, and FS is driven down toward and below the 1.0 failure threshold.

- **Sensor layer:** Displacement is generated as background noise plus an FS-driven creep term that accelerates as FS drops toward 1.0. Vibration includes background sensor noise plus event-triggered spikes scaled by slope angle and assumed failure mass.
- **Event layer:** The number of events per location follows a Poisson process (λ = 5). Within that budget, 80% of events are placed at hours weighted exponentially toward low FS (favoring FS ≤ 1.3, exhibiting clear displacement precursors), and 20% are placed at fully random hours to represent non-rainfall-triggered failure modes such as thermal cycling or blasting (exhibiting zero precursor signal).

## Known Issues & Fixes (Changelog)
1. **The 90° QGIS Slope Bug (Fixed):** Earlier QGIS raster processing produced 90-degree slope artifacts at DEM boundaries. This was fixed by correctly clipping the raster before slope generation.
2. **The Flat-Terrain Bug (Fixed):** The original random point sampling favored flat terrain (avg 6° slope), causing the physics engine to fail. The sampling was rewritten to strictly target steep geographic slopes (15°–34°).
3. **The Fake Elevation Bug (Fixed):** A previous generation script accidentally fabricated elevations (`elev_1 = 500 + noise`) due to a missing DEM band. This was corrected, and the dataset now uses actual DEM elevations.

## Known Limitations
- **Simulated ground truth:** Event labels and sensor readings do not correspond to any real, observed rockfall. Models trained on this dataset should not be assumed to transfer directly to real-world deployment without validation against real sensor and incident data.
- **Simplified physics:** The FS calculation uses a single-point Infinite Slope model with literature-range constants rather than site-measured geotechnical properties. It ignores 3D stress effects, spatial groundwater flow, and joint/fracture mechanics.
- **Event count remains partially arbitrary:** Total event count per location is still governed by a Poisson process rather than emerging entirely from FS crossing a failure threshold. 
- **Weak direct FS-to-event correlation:** Because event count is Poisson-controlled and 20% of events are randomly placed, the direct correlation between FS and the `Rockfall_Event` label across all 13M rows is weak, even though FS perfectly drives displacement (correlation around -0.78) during critical windows.
- **Class imbalance:** With 2,436 positive events across 13.1 million rows, statistics computed per-location or per-season carry wide uncertainty and should be interpreted cautiously.
- **Sensor dropout:** A small fraction of sensor readings (~1.0%) are missing, simulating realistic hardware downtime.

## Suggested Uses
- Binary classification of rockfall risk from combined terrain, weather, sensor, and FS features.
- Anomaly detection given the strong class imbalance, which better reflects real-world deployment conditions than balanced classification.
- Precursor / early-warning research, using the FS-driven displacement creep to study lead-time detection ahead of events.
- Cross-location generalization testing, since terrain and FS baselines vary meaningfully across the 500 simulated locations.
- Feature ablation studies comparing the relative value of terrain-only, weather-only, sensor-only, and FS-only inputs.
- Methodology benchmarking for imbalanced, rare-event classification under semi-synthetic but physically grounded conditions.

## Code and Reproducibility
The full streaming architecture is open-sourced in this repository. It natively handles the 13.1 million rows with a minimal memory footprint. Anyone wanting to inspect the exact constants used, regenerate the dataset with different assumptions, or extend the physics model can start from that repository.

## Citation
If you use this dataset, please credit the author and note its synthetic nature in any derived work or publication.

## License
Released under CC-BY-4.0. You are free to share and adapt this dataset with attribution.

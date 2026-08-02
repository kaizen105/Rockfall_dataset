# Noamundi Rockfall Simulation Dataset

## 1. Overview
This dataset is a physics-informed simulation of rockfall precursor conditions for the Noamundi mining region in Jharkhand, India. It combines real-world terrain (DEM) and weather data with geotechnical stability modeling to synthesize IoT sensor readings and rockfall event labels.

It is designed for research into rockfall early-warning systems, anomaly detection, and hazard classification. **It is not a record of real rockfall incidents.** No real rockfall event ever recorded at Noamundi is represented here.

## 2. What Is Real vs Simulated
| Column | Status | Source |
| :--- | :--- | :--- |
| `elev_1`, `slope_1`, `aspect_1`, `rough_1`, `tri_1`, `profile_curvature`, `planform_curvature` | **Real** | DEM via OpenTopography, processed in QGIS / Python |
| `temperature_2m`, `precipitation`, `windspeed_10m`, `shortwave_radiation` | **Real** | Historical HOURLY weather via Open-Meteo API |
| Weather Downscaling | **Physics-derived** | Math-based adjustments (lapse rates, orographic formulas) |
| `FS` (Factor of Safety) | **Physics-derived** | Computed hourly via Infinite Slope Stability model |
| `Displacement_Rate_mm_h`, `Vibration_mm_s` | **Simulated** | Displacement driven by FS; Vibration from event spikes |
| `Rockfall_Event` | **Simulated** | 80% rainfall-driven (FS threshold), 20% random |

*(Note: Geographic artifacts `X`, `Y`, `rand_point`, `fid`, `DN` were dropped from the training set to prevent geographic memorization, but are retained in `spatial_metadata.csv` for GNN edge construction).*

## 3. Full Methodology

### Terrain Extraction
DEM data for the Noamundi region was obtained via OpenTopography (NASA SRTM GL1 30m resolution) and processed in QGIS to extract Elevation, Slope, Aspect, Roughness, and Ruggedness (TRI). 500 monitoring locations were selected by pure uniform random sampling (using `random_state=42`) constrained within a steep-zone polygon mask (slope ≥ 15°). 
*(Note: Unconstrained random sampling was originally attempted but yielded a mean slope of ~5.85°, causing the Factor of Safety to always exceed 2.0. This made the physics engine inert with zero possible failures. Applying the ≥15° mask was empirically necessary—not an arbitrary choice—raising the mean slope to 16.15° and enabling realistic failure dynamics).*

### Weather & Microclimate Downscaling
Historical hourly weather (exact date range: **Jan 1, 2021 – Dec 31, 2023**) was pulled from the Open-Meteo API for four precise variables: `temperature_2m`, `precipitation`, `windspeed_10m`, and `shortwave_radiation`. Due to API rate limits across 500 locations, and because Open-Meteo's native grid resolution (~9-11km) makes per-point fetches largely redundant, the 500 locations were clustered into 25 KMeans macro-regions. The API fetched true hourly data for the 25 centroids. This was then mathematically downscaled to the 500 individual locations step-by-step:
- **Temperature Lapse Rate:** `-0.0065 * elev_diff` (-6.5°C per 1000m elevation difference).
- **Orographic Rain:** `precipitation * (1.0 + 0.05 * cos(aspect - 270°) * sin(slope))`. *(Note: 270° assumes a static Westerly prevailing wind, which is a simplification that does not reflect actual seasonal monsoon shifts in this region).*
- **Solar Radiation:** `shortwave_radiation * (1.0 + 0.10 * cos(aspect - 180°) * sin(slope))`.

### Physics (Factor of Safety)
The Factor of Safety (FS) is computed hourly using the Infinite Slope Stability model (Skempton and DeLory), the identical single-point foundation used in tools like SHALSTAB and TRIGRS:
`FS = [ c + (γ · z · cos²β - u) · tanφ ] / [ γ · z · sinβ · cosβ ]`
- `β` (slope angle): 15° to 34° (real DEM)
- `γ` (unit weight): 20 to 25 kN/m³ (Typical ranges for weathered lateritic/iron-ore soils in open-pit mining contexts, per Hoek, E. & Bray, J.W., *Rock Slope Engineering*)
- `z` (depth): 1.0 to 2.0 m (literature)
- `φ` (friction angle): 30° to 40° (Typical ranges, per Hoek & Bray)
- `c` (cohesion): 4 to 10 kPa (Typical ranges, per Hoek & Bray)
- `γ_w` (unit weight of water): 9.81 kN/m³ (Standard constant)
- `u` (pore pressure): `γ_w * min(1.0, rain_72h / 100.0) * z`
*(Note: The `100.0` mm cumulative rainfall threshold for full soil saturation is a heuristic engineering assumption, not field-calibrated. It is logically designed to bring pore pressure to its physical maximum under sustained monsoon-intensity rainfall over a 72-hour window. Furthermore, this 1D model does NOT account for 3D stress, groundwater routing, or joint/fracture mechanics).*

### Sensor & Event Simulation
- **Events:** Event count follows a Poisson process (λ = 5). *(Note: Poisson λ=5 is an arbitrary modeling choice to ensure a realistic sparse class imbalance; it is not derived from a measured regional event-rate).* 
  - 80% of events are triggered during hours of critical instability (FS ≤ 1.3). **Crucially, the probability of failure at any specific hour is exponentially weighted by the severity of the instability** (`P ∝ exp(5 * (1.3 - FS))`). This means a severe hour with FS=0.9 is mathematically much more likely to trigger the rockfall than a borderline hour with FS=1.29.
  - 20% are placed at completely random hours. **This 20% random trigger explicitly represents real, literature-recognized non-rainfall rockfall triggers** (e.g., root wedging, thermal expansion, mining-blast-induced fracture), ensuring the dataset models unpredictable failure modes alongside rainfall-driven failures.
- **Infiltration Lag:** A random lag of 8 to 16 hours is applied between the 72-hour rainfall accumulation and its effect on pore pressure to simulate realistic soil infiltration delays.
- **Displacement Creep:** `0.15 / (max(FS, 1.01) - 1.0)` gated strictly on hours where `FS ≤ 1.3`. Base displacement also includes a 24-hour sine-wave thermal cycle (amplitude 0.005 mm/h peaking at 15:00) to model daily rock expansion.
- **Post-Event Decay:** When an event occurs, displacement follows an exponential decay curve (`5 * exp(-0.1 * t)`) over the following 72-hour window, simulating the physical settling of a detached rock mass.
- **Vibration:** Event spikes are modeled as `γ * z * sin(β) * U(0.4, 0.6) * exp(-0.05*t)`. Base vibration also incorporates daily mining blast spikes (5-12 mm/s) occurring randomly between 14:00 and 16:00, characteristic of active open-pit mining operations.

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
| `profile_curvature` | -0.019 | -0.002 | 0.000 | 0.000 |
| `planform_curvature` | -0.001 | 0.001 | -0.001 | -0.000 |
| **Target Cross-Correlations** | | | | |
| `FS` | 1.000 | -0.017 | -0.004 | 0.002 |
| `Displacement_Rate_mm_h` | -0.017 | 1.000 | 0.199 | 0.317 |
| `Vibration_mm_s` | -0.004 | 0.199 | 1.000 | 0.085 |
| `Rockfall_Event` | 0.002 | 0.317 | 0.085 | 1.000 |

*(For the full 13x13 matrix including junk columns, please refer to `dataset_summary.json`).*
*(Note the high collinearity between `slope_1` and ruggedness `tri_1` (0.864) for feature importance interpretation).*

## 7. Known Limitations
- **Target Leakage Warning:** Sensor readings (`Displacement_Rate_mm_h`, `Vibration_mm_s`) are artificially elevated for 72 hours following any event timestamp; any time-series windowing for model training must strictly exclude rows at or after the event hour to avoid target leakage.
- Simulated ground truth, not field-validated.
- **DEM Resolution limitation:** The NASA SRTM GL1 30m resolution is coarse relative to individual rockfall/boulder-scale features. Higher-resolution LiDAR was not openly available for this region.
- Simplified 1D physics (Infinite Slope only, no 3D/groundwater/fracture modeling).
- **Noamundi-specific field measurements missing:** No geomechanical data (UCS, cohesion, friction angle from real site testing) is available. This is a known constraint for Indian mining regions generally, requiring the use of typical ranges from literature (Hoek & Bray).
- Static 270° wind direction assumption in the rainfall downscaling model (does not reflect actual seasonal monsoon direction shifts).
- **Poisson Event Floor Bias:** Event count is governed by an artificial `max(1, poisson(5))` floor. Every single location is mathematically forced to have at least 1 event. No location is perfectly stable (0 events). This is a statistical bias designed for dataset richness but deviates from real-world regional hazard distributions.
- **Undifferentiated Triggers:** Both rainfall-driven events (80%) and random 'dry' rockfall events (20%) are logged identically as `Rockfall_Event = 1`. The lack of a specific `Trigger_Type` column prevents easily isolating the 20% random-trigger subset for cleaner, non-circular validation.
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

## 10. Setup and Reproducibility
To regenerate this dataset from scratch on your local machine:

1. **Environment Setup:**
   ```bash
   python -m venv venv
   venv\Scripts\activate
   pip install -r requirements.txt
   ```
2. **Execution Order:**
   - Run `python src/data/prepare_geometry_500.py` to extract real elevation from QGIS files.
   - Run `python src/data/get_weather_data.py` to fetch clustered hourly Open-Meteo data.
   - Run `python src/data/create_sensor_data.py` to stream 13M rows through the physics engine.

**Deliberate Stochastic Generation:** While point locations and KMeans clustering are deterministic (using `random_state=42`), the final physics/sensor/event generation step (`create_sensor_data.py`) is intentionally **NOT seeded**. This is a deliberate design choice to ensure that anyone regenerating the data receives statistically identical but individually variant data (rather than perfectly identical "blessed" data). This forces models to learn the underlying physics rather than overfitting to specific generated numbers. Users requiring strict reproducibility for published results should securely archive their specifically generated `.csv` files.

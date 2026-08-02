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

## 1. Dataset Overview
This dataset provides a physics-informed simulation of rockfall precursor conditions for 500 monitoring locations in the Noamundi mining region in Jharkhand, India. It is designed specifically for training and benchmarking Machine Learning models on **early-warning systems, anomaly detection, and rare-event classification** in geotechnical environments.

**⚠️ Important:** It is a simulated dataset mapping real-world terrain and weather variables to simulated physics sensors. It is *not* a record of real historical rockfalls.

## 2. Dataset Structure & Features
- **Total Rows:** 13,140,000 (Hourly data from 2021-01-01 to 2023-12-31)
- **Total Locations:** 500
- **Rockfall Events (Positive Class):** 2,436
- **Sensor Dropout Rate:** 1.0% (~131,000 rows randomly set to NaN for realism)

### Feature Origins
| Column | Origin | Description |
| :--- | :--- | :--- |
| `elev_1`, `slope_1`, `aspect_1`, `rough_1`, `tri_1`, `profile_curvature`, `planform_curvature` | **Real** | DEM via OpenTopography (30m SRTM) |
| `temperature_2m`, `precipitation`, `windspeed_10m`, `shortwave_radiation` | **Real** | Historical HOURLY weather via Open-Meteo API |
| `FS` (Factor of Safety) | **Physics** | Computed hourly via Infinite Slope Stability model |
| `Displacement_Rate_mm_h`, `Vibration_mm_s` | **Simulated** | Displacement driven by FS; Vibration driven by event spikes |
| `Rockfall_Event` | **Simulated** | 80% rainfall-driven (FS threshold), 20% random triggers |

*(Note: Geographic artifacts `X`, `Y`, `rand_point`, `fid` were intentionally dropped from this training set to prevent neural networks from geographically memorizing locations).*

## 3. Data Provenance & Physics Constraints
The simulation relies on the Infinite Slope Stability model (Skempton and DeLory):
`FS = [ c + (γ · z · cos²β - u) · tanφ ] / [ γ · z · sinβ · cosβ ]`

**Key Physics Constraints & Assumptions:**
- `β` (slope angle) is constrained to 15°–34°.
- Geotechnical parameters (`γ`: 20-25 kN/m³, `φ`: 30°-40°, `c`: 4-10 kPa) are typical ranges for open-pit mining contexts per Hoek & Bray, not field-verified Noamundi measurements.
- Pore pressure `u = γ_w * min(1.0, rain_72h / 100.0) * z`. The `100.0` mm threshold for full saturation is a heuristic engineering assumption.
- 80% of events occur when `FS ≤ 1.3`, with the probability of failure exponentially weighted by the severity of the instability (`P ∝ exp(5 * (1.3 - FS))`).
- 20% of events are random triggers, explicitly representing 'dry rockfalls' (e.g., thermal expansion, mining blasts).

## 4. Learnable Signals & Correlations
The dataset is engineered to contain a genuine predictive precursor signal, though it is obfuscated by extreme class imbalance. The direct whole-dataset correlation between Displacement and FS is **-0.017**, which is near-zero because the hard `FS ≤ 1.3` trigger acts as a step-function.

However, the **population-level learnable signal** is real: average 72-hour pre-event windows show a sustained climb in displacement (~0.025 to ~0.13 mm/h), compared to a flat ~0.015 mm/h for non-event windows. 

### Pearson Cross-Correlations
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
| `Displacement_Rate_mm_h` | -0.017 | 1.000 | 0.199 | **0.317** |
| `Vibration_mm_s` | -0.004 | 0.199 | 1.000 | 0.085 |

*(Note the high collinearity between `slope_1` and ruggedness `tri_1` (0.864) for feature importance interpretation).*

## 5. Known Dataset Limitations
- **Target Leakage Warning:** Sensor readings (`Displacement_Rate_mm_h`, `Vibration_mm_s`) are artificially elevated for 72 hours following any event timestamp to simulate settling. **Any time-series windowing for model training must strictly exclude rows at or after the event hour to avoid target leakage.**
- **Poisson Event Floor Bias:** Event count is governed by an artificial `max(1, poisson(5))` floor. Every single location is mathematically forced to have at least 1 event. No location is perfectly stable (0 events). This is a statistical bias designed for dataset richness but deviates from real-world regional hazard distributions.
- **Undifferentiated Triggers:** Both rainfall-driven events (80%) and random 'dry' rockfall events (20%) are logged identically as `Rockfall_Event = 1`. 
- **DEM Resolution limitation:** The 30m resolution is coarse relative to individual boulder-scale features.
- **Unseeded Generation:** The dataset is generated unseeded by design to force robustness against noise; users needing perfect byte-for-byte reproducibility should archive their downloaded `.csv`.

## 6. Suggested ML Tasks
- **Classification & Anomaly Detection:** Benchmarking rare-event logic under physically grounded class imbalance.
- **Precursor / Early-Warning Research:** Studying lead-time detection (mind the 80/20 rainfall vs random trigger split).
- **Cross-Location Generalization:** Testing models across different geographic baselines.
- **Feature Ablation Studies:** Comparing relative value of terrain-only vs weather-only vs sensor-only inputs.

## 7. Source Code
The data generation pipeline and physics engine source code is hosted on GitHub: [https://github.com/kaizen105/Rockfall_dataset](https://github.com/kaizen105/Rockfall_dataset).

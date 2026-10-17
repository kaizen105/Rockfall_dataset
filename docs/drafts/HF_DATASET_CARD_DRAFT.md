---
dataset_info:
  features:
  - name: Timestamp
    dtype: string
  - name: temperature_2m
    dtype: float32
  - name: precipitation
    dtype: float32
  - name: windspeed_10m
    dtype: float32
  - name: shortwave_radiation
    dtype: float32
  - name: Location_ID
    dtype: string
  - name: elev_1
    dtype: float32
  - name: slope_1
    dtype: float32
  - name: aspect_1
    dtype: float32
  - name: rough_1
    dtype: float32
  - name: tri_1
    dtype: float32
  - name: profile_curvature
    dtype: float32
  - name: planform_curvature
    dtype: float32
  - name: FS
    dtype: float32
  - name: Displacement_Rate_mm_h
    dtype: float32
  - name: Vibration_mm_s
    dtype: float32
  - name: Rockfall_Event
    dtype: int8
  - name: post_event_window
    dtype: int8
  splits:
  - name: train
    num_bytes: 2113671785
    num_examples: 13140000
  download_size: 2113671785
  dataset_size: 2113671785
configs:
- config_name: default
  data_files:
  - split: train
    path: training_dataset.csv
---

# 🪨 Noamundi Rockfall Simulation Dataset (Release V1d)

![Dataset Size](https://img.shields.io/badge/Dataset_Size-13.14M_Rows-blue)
![Locations](https://img.shields.io/badge/Monitoring_Locations-500-green)
![Events](https://img.shields.io/badge/Rockfall_Events-2,484-red)
![Contiguity](https://img.shields.io/badge/Row_Contiguity-100%25-brightgreen)
![Leak Free](https://img.shields.io/badge/Target_Leakage-Zero_Step_Leak-success)

## 📌 1. Dataset Overview

This dataset provides a physics-informed synthetic benchmark of rockfall precursor conditions and downstream trajectory kinematics across **500 monitored locations** in the Noamundi mining region of Jharkhand, India, spanning **3 continuous years of hourly observations** (2021–2023).

It is specifically constructed for training, validating, and evaluating Machine Learning algorithms on:
- **Rare-Event Early-Warning Systems**: Detecting micro-velocity acceleration prior to slope failure.
- **Physics-Informed Anomaly Detection**: Benchmarking whether geotechnical physics (Factor of Safety, $FS$) yields learnable value beyond surface weather observations.
- **Spatio-Temporal Generalization**: Cross-validation across clustered, geographically distinct slope profiles without spatial leakage.

> [!WARNING]
> This is a simulated dataset coupling real-world digital elevation models (DEM) and historical weather records with deterministic geotechnical stability equations and kinematic runout engines. It is **not** a registry of actual historical mining accidents.

---

## 📊 2. Dataset Structure & Features

- **Total Rows (Hourly Timeseries):** Exactly **13,140,000 rows** (500 locations $\times$ 26,280 hours; 100% contiguous, zero time gaps).
- **Monitoring Locations:** 500 locations (`LOC_1` to `LOC_500`).
- **Main Release (Seed 42):** **2,484 rockfall events** (1,992 rain-driven [80.19%], 492 stochastic random [19.81%], 0 unplaced).
- **Replication Releases:** Seed 1337 (**2,567 events**) and Seed 2024 (**2,529 events**).
- **Flagged Post-Event Windows:** 178,789 rows flagged with `post_event_window = 1` in Seed 42 (184,723 in Seed 1337; 182,088 in Seed 2024) for exclusion during training/evaluation.
- **Simultaneous Sensor Dropouts:** Exactly 1.00076% (263 hours per location, 131,500 rows total) simultaneously set to `NaN` in `Displacement_Rate_mm_h` and `Vibration_mm_s`.

### 2.1 Dataset Files

1. **`training_dataset.csv`** (2,113,671,785 bytes):
   The primary ML-ready hourly timeseries (18 columns, downcasted to `float32` and `int8`). All 13,140,000 rows and continuous timestamps are preserved. Rows within the 72-hour window following an event are flagged (`post_event_window = 1`) to allow masking during model training and evaluation without breaking time-series contiguity.
2. **`location_metadata.csv`**:
   Per-location simulation records across all 500 locations, recording the run seed, geotechnical properties ($\gamma, z, \phi, c$), pore-pressure lag hours, dry Factor of Safety ($FS_{\text{dry}}$), calibrated sensitivity $a=0.50$, location hazard weight $w_{\text{loc}}$, event rate $\lambda_{\text{loc}}$, actual event counts (rain-driven vs. random), inter-event spacings, and individual event timestamps.
3. **`spatial_metadata.csv`**:
   Static topographical, geomorphological, and geomechanical metadata for all 500 locations, including DEM-derived features (`elev_1`, `slope_1`, `aspect_1`, `rough_1`, `tri_1`, curvatures) and trajectory runout maximums (`Max_Runout_m`, `Max_Bounce_Height_m`, `Max_Kinetic_Energy_*`).
4. **`trajectories/`**:
   *(TODO: Trajectory kinematic fixes and updated trajectory rollouts will be released in an upcoming update).*

### 2.2 Feature Provenance (Real vs. Simulated)

| Column | Type | Provenance | Source / Description |
| :--- | :---: | :---: | :--- |
| `Timestamp` | String | Real | Hourly UTC timestamp spanning 2021-01-01 00:00:00 to 2023-12-31 23:00:00 |
| `Location_ID` | String | Design | Unique identifier (`LOC_1` through `LOC_500`) |
| `elev_1`, `slope_1`, `aspect_1`, `rough_1`, `tri_1` | Float32 | **Real** | NASA SRTM GL1 30m DEM via OpenTopography |
| `profile_curvature`, `planform_curvature` | Float32 | **Real** | Curvatures computed on UTM Zone 45N reprojected grid (m$^{-1}$) |
| `temperature_2m`, `precipitation`, `windspeed_10m`, `shortwave_radiation` | Float32 | **Real** | Historical hourly ERA5/Open-Meteo weather records for Noamundi |
| `FS` | Float32 | **Physics** | Hourly 1D Infinite Slope Stability Factor of Safety |
| `Displacement_Rate_mm_h` | Float32 | **Simulated** | Thermal cycle + tertiary pore-pressure creep + precursor ramp + noise |
| `Vibration_mm_s` | Float32 | **Simulated** | Ambient seismic background + afternoon blasting spikes + aftershocks |
| `Rockfall_Event` | Int8 | **Simulated** | Discrete label (`1` at failure hour, `0` otherwise) |
| `post_event_window` | Int8 | **Design** | Exclusion mask (`1` for 72h post-event window; `0` otherwise) |

*(Note: Geographic coordinate artifacts `X`, `Y`, `rand_point`, `fid`, `DN` have been intentionally excluded from `training_dataset.csv` to prevent models from memorizing spatial locations).*

---

## 🧮 3. Simulation Methodology & Physics Engines

### 3.1 Precursor Engine (Infinite Slope Stability & Dual-Role Decoupling)

Slope stability is governed by the 1D Infinite Slope equation:

$$FS_t = \frac{c + (\gamma \cdot z \cdot \cos^2\beta - u_t) \tan\phi}{\gamma \cdot z \cdot \sin\beta \cdot \cos\beta}$$

Where:
- $\beta$ is slope angle (`slope_1` in radians),
- $\gamma \sim U(20, 25)$ kN/m³ is soil unit weight,
- $z \sim U(2.0, 5.0)$ m is failure slab thickness,
- $\phi \sim U(30^\circ, 40^\circ)$ is friction angle,
- $c \sim U(4.0, 10.0)$ kPa is cohesion,
- $u_t = \gamma_w \cdot R_t \cdot z$ is transient pore-water pressure, with pore-pressure fraction $R_t = \min(1.0, \text{rain\_72h\_lagged}_t / 100.0)$.

#### Decoupled Timing vs. Frequency (The V1d Architecture)
Release V1d resolves the hazard trade-off by strictly decoupling failure timing within a location from failure frequency across locations:

1. **Within-Location Failure Timing (Rainfall Gating)**:
   - For a given location, 80% of events are rain-driven, sampled strictly during elevated pore-pressure hours ($R_t \ge 0.50$) with exponential probability weights $w_t \propto \exp(5.0 \cdot R_t)$.
   - The remaining 20% of events are drawn uniformly at random across all 26,280 hours to simulate stochastic dry rockfalls.
   - This achieves an empirical **Rain Lift of 11.67x** in the $[50, 100)$ mm `rain72` bin and **30.45x** in the $[100, \infty)$ mm bin (Seed 42).
2. **Cross-Location Failure Frequency (Geotechnical Stability)**:
   - Location event counts are governed by static geotechnical dry slope stability $FS_{\text{dry}}$:
     $$\lambda_{\text{loc}} = \min\left(15, 5.0 \cdot \frac{w_{\text{loc}}}{\text{mean}(w)}\right), \quad w_{\text{loc}} = \exp(-a \cdot (FS_{\text{dry}} - 1.0))$$
   - The sensitivity parameter $a$ was calibrated prior to generation on a 0.05 grid: $a = 0.50$ was selected as the minimal sensitivity yielding a 90th-to-10th percentile hazard spread ratio within $[3.0, 6.0]$ ($p_{10} = 2.42$, median $= 4.97$, $p_{90} = 7.50$, spread ratio $= 3.10$).
   - Total events per location follow $N_{\text{loc}} = \max(1, \text{Poisson}(\lambda_{\text{loc}}))$.
   - This produces a strong negative rank correlation between slope stability and event count: **Spearman $r_s = -0.6454$** ($p = 3.01 \times 10^{-60}$).

#### Precursor Ramp & Zero-Step Leakage
- **Displacement Ramp**: Every rockfall event is preceded by an emergent tertiary creep ramp starting $U(6, 48)$ hours prior to failure and extending through the failure hour (`idx_ev`) inclusive:
  $$\Delta_{\text{disp}}(t) = 0.02 \cdot \left(\frac{t}{T_{\text{lead}}}\right)^2 \quad \text{mm/h}$$
- **Post-Event Decay**: Physical stress-relaxation displacement ($5.0 \cdot \exp(-t/12.0)$ mm/h) and aftershock vibrations ($U(1, 4) \cdot \exp(-t/24.0)$ mm/s) start strictly at `idx_ev + 1`, eliminating event-row target leakage.
- **Minimum Event Spacing**: A strict $120.0$-hour minimum inter-event spacing is enforced via resampling ($72\text{h post-event window} + 48\text{h maximum precursor lead time}$). In Seed 42, **100% of the 2,484 events are completely isolated** (0 overlapping events).

### 3.2 Trajectory Kinematics Engine
*(TODO: Full kinematics update and parameter re-calibration in progress).*

---

## 📈 4. Measured Empirical Properties & Validation

All metrics below are strictly measured from `data_release_v1d_s1/` (Seed 42) with multi-seed replication confirmed:

### 4.1 Event Counts & Stability Coupling

| Metric | Seed 42 (`s1`) | Seed 1337 (`s2`) | Seed 2024 (`s3`) | Assertion Standard |
| :--- | :---: | :---: | :---: | :---: |
| **Total Events** | 2,484 | 2,567 | 2,529 | ~2,500 target |
| **Rain-Driven Share** | 1,992 (80.19%) | 2,057 (80.13%) | 2,030 (80.27%) | $80\% \pm 10\%$ (Passed) |
| **Random Dry Share** | 492 (19.81%) | 510 (19.87%) | 499 (19.73%) | ~20% (Passed) |
| **Unplaced Events** | 0 (0.00%) | 0 (0.00%) | 0 (0.00%) | 0 unplaced under 120h rule |
| **Events/Loc Mean** | 4.968 | 5.134 | 5.058 | $5.0 \pm 0.5$ (Passed) |
| **Events/Loc Variance** | **7.891** | **8.297** | **8.343** | **$> \text{Mean}$ (Overdispersed, Passed)** |
| **Spearman $r_s$ ($FS_{\text{dry}}$ vs Count)** | **-0.6454** | **-0.6309** | **-0.6369** | $\le -0.40$ (Passed) |

### 4.2 Rain Lift Across `rain72` Accumulation Bins (Seed 42)

| `rain72` Accumulation Bin | Total Location-Hours | Share of Hours | Event Count | Event Rate / 1,000h | Rain Lift |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **[0, 5) mm** | 7,772,671 | 59.15% | 299 | 0.0385 | 0.20x |
| **[5, 20) mm** | 2,783,689 | 21.18% | 141 | 0.0507 | 0.27x |
| **[20, 50) mm** | 2,014,488 | 15.33% | 243 | 0.1206 | 0.64x |
| **[50, 100) mm** | 415,573 | 3.16% | 917 | 2.2066 | **11.67x** |
| **[100, inf) mm** | 153,579 | 1.17% | 884 | 5.7560 | **30.45x** |

### 4.3 Pre-Event Displacement Acceleration Profile (Seed 42)

| Relative Hour | Rain-Driven Events (mm/h) | Stochastic Random Events (mm/h) | Non-Event Background Baseline |
| :---: | :---: | :---: | :---: |
| **-48h** | 0.02667 | 0.01149 | ~0.0117 |
| **-24h** | 0.03711 | 0.01284 | ~0.0117 |
| **-12h** | 0.04534 | 0.01680 | ~0.0117 |
| **-6h** | 0.05163 | 0.02180 | ~0.0117 |
| **-1h** | 0.05904 | 0.02768 | ~0.0117 |
| **0h (Failure)** | **0.06090** | **0.02933** | **~0.0117** |

### 4.4 Two-Sided Step Leakage Checks Across All Events

Evaluated on step differences $|\text{val}[\text{idx\_ev}] - \text{val}[\text{idx\_ev}-1]|$ across all 2,422 evaluated events in Seed 42:
- **Displacement Step**: Mean = 0.006428 mm/h $\le 3\sigma$ bound (0.016155 mm/h).
- **Vibration Step**: Mean = 0.254060 mm/s $\le 3\sigma$ bound (2.016809 mm/s).
- **Conclusion**: Event rows show zero artificial step discontinuities.

---

## 🔄 5. Changes from V1 (Audit & Architecture Evolution)

1. **Elimination of Target Leakage Windows**:
   - In V1, 72-hour post-event rows were dropped from disk, breaking time contiguity. In V1d, all 13,140,000 continuous hours are preserved, and post-event windows are cleanly flagged via `post_event_window = 1`.
2. **Resolution of Event-Row Discontinuity**:
   - In V1, precursor ramps ended at `idx_ev - 1`, causing an artificial drop at the event label. In V1d, ramps extend through `idx_ev` inclusive.
3. **Enforcement of 120h Minimum Spacing**:
   - In V1, 15.7% of events overlapped with previous decay windows, corrupting precursor baselines. In V1d, an attempt-capped resampling loop enforces $\ge 120$h spacing (100% of events are isolated).
4. **Decoupled Physical Stability (V1c $\rightarrow$ V1d)**:
   - In V1c, continuous hazard weighting collapsed rain lift from 11.6x to 1.25x. V1d restored heavy rainfall gating within locations while tying cross-location event frequency to geotechnical stability ($r_s = -0.6454$).
5. **Deterministic Seeding & Resumability**:
   - Full pipeline generates chunked 25-location parts with saved RNG states and records all parameters in `location_metadata.csv`.

---

## 🧪 6. FS With vs. Without: Benchmark Results

*(Placeholder: Formal model evaluation results across 5-fold StratifiedGroupKFold comparing Rain-Only vs. Rain-Only + FS will be inserted here following the benchmark ladder execution).*

---

## ⚠️ 7. Known Limitations

1. **FS Absolute Calibration**: The 1D Infinite Slope Factor of Safety is a relative stability index (median $FS \approx 3.0$), not an absolute real-world failure predictor.
2. **Simulated Ground Truth**: Labels and sensor channels emerge from a known mathematical generating process, not in-situ field telemetry.
3. **Subtle Precursor Amplitude**: Displacement precursors are deliberately calibrated to weak, realistic magnitudes (+0.02 mm/h ramp above background noise) rather than obvious artificial spikes.
4. **Vibration Noise Modeling in V1d**: In V1d, sensor measurement noise $\mathcal{N}(0, 0.2)$ and subsequent zero-clipping were omitted on `Vibration_mm_s`, leaving values strictly positive ($\ge 0.10$ mm/s) without zero-inflation.
5. **Hazard Calibration Choices**: The hazard exponent $a = 0.50$ and the $[3.0, 6.0]$ inter-decile spread target are engineering design choices.
6. **Geotechnical Parameter Sources**: Cohesion ($c$) and friction angle ($\phi$) ranges reflect typical literature values for open-pit slopes (Hoek & Bray), not laboratory core tests from Noamundi.
7. **Trajectory Kinematics Engine**: Kinematics use mass-independent point-mass Euler integration; the resulting 4.00x and 20.00x kinetic energy scaling across boulder masses is mathematically guaranteed by construction and should not be cited as empirical validation.

---

## 🎯 8. Suggested ML Tasks

- **Rare-Event Imbalanced Classification**: Predicting rockfall failure ($2,484$ positives across $13.14\text{M}$ hours, positive rate $\approx 0.0189\%$).
- **Early-Warning Lead-Time Forecasting**: Detecting precursor ramp initiation 6 to 48 hours prior to failure.
- **Physics-Informed Ablation**: Evaluating whether adding geotechnical physics ($FS$) provides statistically significant out-of-fold PR-AUC lift over weather-only features.
- **Spatial Group Generalization**: Benchmarking models under `StratifiedGroupKFold` grouped by `Location_ID`.

---

## 💻 9. Source Code & References

- **Pipeline Repository**: [https://github.com/kaizen105/Rockfall_dataset](https://github.com/kaizen105/Rockfall_dataset)
- **Terrain Data**: NASA SRTM GL1 30m via OpenTopography
- **Weather Data**: Historical hourly records via Open-Meteo Historical Archive API

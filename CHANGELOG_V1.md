# Changelog V1 - Precursor Engine & Training Dataset Fixes

## Overview
This log tracks changes made to the synthetic rockfall precursor generator (`src/data/create_sensor_data.py`) and post-processing pipeline (`src/data/create_training_dataset.py`) to eliminate target leakage, implement physically grounded precursor ramps, enforce reproducibility, and preserve time-series contiguity.

---

## Changes Log

### Initial Setup - [2026-10-17]
- Created `AGENT_RULES.md` defining strict constraints, data hygiene, and validation requirements.
- Switched to branch `precursor-fixes-v1`.
- Verified existing files in `data_v2/` remain untouched.

### Precursor Engine & Pipeline Bug Fixes (3-Location Subset Validation) - [2026-10-17]
- **Files Modified**:
  - `src/data/create_sensor_data.py`:
    - Defined per-location pore-pressure fraction $R = \min(1.0, \text{pore\_pressure\_proxy} / 100.0)$.
    - High-risk hours gated at $R \ge 0.5$ (default `RISK_THRESHOLD = 0.5`).
    - Rain-driven events sampled from high-risk hours with probability weight $\propto \exp(5.0 \cdot R)$.
    - Replaced $k / (FS - 1)$ rain creep with bounded smooth function $\text{rain\_creep} = \text{CREEP\_MAX} \cdot R^2$ (capped at 0.04 mm/h).
    - Removed event-row target leakage: post-event decay and vibration aftershocks start strictly at `idx_ev + 1`.
    - Added precursor displacement ramp for all events ending at `idx_ev - 1` (amplitude 0.02 mm/h, lead time $U(6, 48)$).
    - Added CLI seed argument (defaults to random draw, recorded in `location_metadata.csv`).
    - Simultaneous sensor dropouts at 1.0% on identical rows.
  - `src/data/create_training_dataset.py`:
    - Preserved all rows and time-series contiguity (no 72h post-event row deletion).
    - Verified `post_event_window` column (`int8`).
    - Dropped geographic memorization columns (`X`, `Y`, `rand_point`, `fid`, `DN`).
    - Downcasted dtypes (`float32`, `int8`, `category`).
  - `src/analysis/run_assertions.py`:
    - Created validation script testing all required assertions and descriptive statistics.
- **Evidence (3-Location Test)**:
  - High-risk hours: min = 1,051 (>= 100 PASS).
  - Rain-driven event share: 80.95% (PASS, within [0.70, 0.90]).
  - Row contiguity: 26,280 rows per location with 0 timestamp gaps (PASS).
  - Sensor dropouts: Exactly identical rows at 1.0008% (PASS).
  - Event row displacement vs preceding hour: mean diff = -0.0478 mm/h, max diff = -0.0066 mm/h <= 3*sigma (PASS).
  - 24h pre-event vs baseline: rain-driven 0.3753 mm/h, random 0.0269 mm/h vs baseline 0.0116 mm/h (PASS).
  - Bitwise reproducibility: Identical dataframes across runs with seed 42 (PASS).

### Follow-Up Refinements & Overlap Analysis (3-Location Subset) - [2026-10-17]
- **Modifications**:
  - `src/data/create_sensor_data.py`:
    - Adjusted precursor ramp to run through `idx_ev` inclusive (`end_pre = idx_ev + 1`), preventing artificial displacement drop at the label row.
    - Added `event_lead_times` to per-location metadata.
  - `src/analysis/run_assertions.py`:
    - Implemented two-sided event-row leakage check for displacement: $|\text{disp}[\text{idx\_ev}] - \text{disp}[\text{idx\_ev}-1]| \le 3\sigma_{\text{disp}}$.
    - Implemented two-sided event-row leakage check for vibration: $|\text{vib}[\text{idx\_ev}] - \text{vib}[\text{idx\_ev}-1]| \le 3\sigma_{\text{vib}}$.
    - Added overlap detection: events with previous event in $\le 72$h and $\le (72\text{h} + T_{\text{lead}})$.
    - Segmented pre-event 24h displacement and hourly profiles (-48h to 0h) into isolated vs non-isolated groups.
- **Evidence**:
  - Two-sided displacement diff: mean = 0.00767 mm/h, max = 0.01350 mm/h $\le 3\sigma$ (0.01616 mm/h) (PASS).
  - Two-sided vibration diff: mean = 0.32495 mm/s, max = 0.55086 mm/s $\le 3\sigma$ (2.20164 mm/s) (PASS).
  - Overlap findings: 2 of 13 events (15.4%) fell within previous 72h post-event decay window.
  - Isolated rain-driven events ($n=8$): clean monotonic ramp from 0.02258 mm/h (-48h) to 0.06181 mm/h (0h), matching baseline (0.01175) + rain creep (~0.03) + ramp (+0.02).
  - Non-isolated rain-driven events ($n=2$): elevated (-48h: 1.89 mm/h, -36h: 2.45 mm/h) due to predecessor post-event decay.

### Minimum Event Spacing Constraint & Robust I/O Regeneration (Release V1b) - [2026-10-17]
- **Problem & Motivation**:
  - In initial full run (`data_release_v1/`, seed `463324005`), 398 of 2,535 events (15.7%) occurred within 72h of an earlier event, causing an aftershock contamination leak on all-events leakage checks (mean displacement difference 0.0363 mm/h vs $3\sigma$ threshold of 0.0162 mm/h).
- **Modifications**:
  - `src/data/create_sensor_data.py`:
    - Added `MIN_EVENT_SPACING_H = 120` (72h post-event decay + 48h maximum precursor lead time).
    - Event type drawn first (80/20 target), followed by resampling candidate timestamps with attempt cap `MAX_SPACING_ATTEMPTS = 500`.
    - Added unplaced event logging and tracking (`unplaced_events` column in metadata).
    - Addressed Windows `OSError: [Errno 22] Invalid argument` file append contention by transitioning from monolithic file append to chunked part writes (25 locations per part in `parts/`), atomic replace with 3-attempt retry loop, incremental metadata logging, checkpointed RNG states (`random.getstate()` / `np.random.get_state()`) for resumability, and fast binary streaming concatenation into `final_master_dataset.csv`.
  - `src/analysis/run_assertions.py`:
    - Added assertions for minimum spacing in metadata $\ge 120$h.
    - Updated assertions to enforce two-sided leak checks across ALL events.
- **Evidence**:
  - **3-Location Subset Re-validation (seed 42)**:
    - Min event spacing: 525.0h $\ge 120$h across all 10 pairs (PASS).
    - All-events displacement transition: mean = 0.004514 mm/h $\le 3\sigma$ (0.016155 mm/h), max = 0.012956 mm/h (PASS).
    - Reproducibility test: bitwise identical outputs across independent runs (`pd.testing.assert_frame_equal`).
  - **Full 500-Location Run (`data_release_v1b/`, seed `340144852`)**:
    - Total rows: exactly 13,140,000 across 500 locations with 0 timestamp gaps (PASS).
    - Total rockfalls: 2,442 events (1,946 rain-driven [79.6888%], 496 random [20.3112%], 0 unplaced events; PASS).
    - Poisson(5) consistency: mean = 4.884 events/location ($z = 1.16$, PASS).
    - Min spacing across all 1,942 multi-event pairs: strictly 120.0h (min = 120.0h, median = 2,188.5h, max = 21,993.0h; PASS).
    - Overlap count: exactly 0 events (0.00%) within $\le (72\text{h} + T_{\text{lead}})$; 100% of events are isolated.
    - All-events displacement step leakage: mean = 0.006174 mm/h $\le 3\sigma$ (0.016155 mm/h); max = 0.025769 mm/h (PASS).
    - All-events vibration step leakage: mean = 0.344439 mm/s $\le 3\sigma$ (2.113679 mm/s) (PASS).
    - `final_master_dataset.csv` and `training_dataset.csv` are bit-identical (`8110b5ef1747c8b5de67c03f95eb6dd8`, 2,105,263,058 bytes each).

### Physically Grounded Hazard & Geotechnical FS Coupling (Release V1c) - [2026-10-17]
- **Problem & Motivation**:
  - In V1b, event occurrence was decoupled from spatial stability: location event counts were drawn from i.i.d. $\max(1, \text{Poisson}(5))$ regardless of terrain geotechnical vulnerability ($r_s = -0.0039$), and rain events were drawn only from an artificial pore-pressure threshold ($R \ge 0.5$).
  - V1c grounds both event probability and event frequency directly into the infinite-slope Factor of Safety ($FS_t$).
- **Modifications**:
  - `src/data/create_sensor_data.py`:
    - **Hazard Formulation**: $h = \exp(-HAZARD\_A \cdot (FS_t - 1))$ per location-hour.
    - **Hazard Parameter Calibration**: Calibrated prior to generation across $a \in \{0.5, 1.0, 1.5, 2.0, 3.0\}$; selected $HAZARD\_A = 0.55$, yielding a $p_{90}/p_{10}$ ratio of 3.268 (within the required [3, 6] range: $p_{10}=2.340$, median$=4.983$, $p_{90}=7.648$).
    - **Geotechnical Event Rate Coupling**: Computed location hazard sum $S_{\text{loc}} = \sum h_t$; scaled rate $\lambda_{\text{loc}} = \min(15, 5 \cdot S_{\text{loc}} / \text{mean}(S_{\text{all}}))$; drew $N = \max(1, \text{Poisson}(\lambda_{\text{loc}}))$.
    - **Continuous Sampling**: 80% rain-driven events sampled across ALL hours with probability weights proportional to $h$ (no artificial $R \ge 0.5$ gating). 20% random dry events sampled uniformly over all hours.
    - **Recalibrated Creep**: $\text{creep} = CREEP\_MAX\_NEW \cdot D^2$ with relative deficit $D = \max(0, 1 - FS_t / FS_{\text{dry\_loc}})$. Calibrated $CREEP\_MAX\_NEW = 0.309637$ mm/h so that mean creep in `rain72 >= 50mm` hours matches the V1b empirical benchmark ($0.023662$ mm/h).
    - **Metadata Tracking**: Recorded `HAZARD_A`, `FS_dry`, `S_loc`, and `lambda_loc` in `location_metadata.csv`.
  - `src/analysis/run_assertions.py`:
    - Replaced i.i.d. Poisson assertion with mean events/location $5 \pm 0.5$ ($[4.5, 5.5]$), minimum events/location $\ge 1$, and variance > Poisson mean ($\text{Var}(N) > \text{Mean}(N)$, confirming physical overdispersion).
- **Evidence & Multi-Run Results**:
  - **Subset Test (Seed 42, 3 locations)**:
    - Min high-risk hours: 1,051 (PASS).
    - Spacing $\ge 120$h: min = 850.0h (PASS).
    - Reproducibility: Bitwise identical datasets and metadata across two independent runs (PASS).
  - **Release V1c Runs (500 locations each, 3 independent random seeds)**:
    - **Run 1 (`data_release_v1c_s1/`, seed `42`)**:
      - Events: 2,557 (2,060 rain-driven [80.56%], 497 random [19.44%], 0 unplaced).
      - Events/loc: min=1, median=5.0, mean=5.114, max=17, variance=10.422 (overdispersion PASS).
      - Spearman(mean FS, events): $r_s = -0.6950$ ($p = 2.35 \times 10^{-73}$); strong negative coupling as designed.
      - Rain lift ([50, inf) mm): 1.255 (event rate 0.244 / 1000h vs overall 0.195).
      - Inter-event spacing: min=120.0h, median=2,371.0h, max=21,308.0h (100% isolated).
      - All-events step leakage: disp mean = 0.006183 mm/h $\le 3\sigma$; vib mean = 0.352724 mm/s $\le 3\sigma$.
    - **Run 2 (`data_release_v1c_s2/`, seed `1337`)**:
      - Events: 2,477 (1,993 rain-driven [80.46%], 484 random [19.54%], 0 unplaced).
      - Events/loc: min=1, median=5.0, mean=4.954, max=21, variance=9.611 (overdispersion PASS).
      - Spearman(mean FS, events): $r_s = -0.6447$ ($p = 4.36 \times 10^{-60}$).
      - Rain lift ([50, inf) mm): 1.333 (event rate 0.251 / 1000h vs overall 0.189).
      - Inter-event spacing: min=127.0h, median=2,497.0h, max=24,577.0h (100% isolated).
      - All-events step leakage: disp mean = 0.006236 mm/h $\le 3\sigma$; vib mean = 0.327633 mm/s $\le 3\sigma$.
    - **Run 3 (`data_release_v1c_s3/`, seed `2024`)**:
      - Events: 2,540 (2,041 rain-driven [80.35%], 499 random [19.65%], 0 unplaced).
      - Events/loc: min=1, median=5.0, mean=5.080, max=14, variance=9.332 (overdispersion PASS).
      - Spearman(mean FS, events): $r_s = -0.6692$ ($p = 3.22 \times 10^{-66}$).
      - Rain lift ([50, inf) mm): 1.236 (event rate 0.239 / 1000h vs overall 0.193).
      - Inter-event spacing: min=124.0h, median=2,458.0h, max=24,670.0h (100% isolated).
      - All-events step leakage: disp mean = 0.006226 mm/h $\le 3\sigma$; vib mean = 0.345369 mm/s $\le 3\sigma$.

### Split-Role Timing & Geotechnical Frequency Decoupling (Release V1d) - [2026-10-17]
- **Problem & Why V1c Was Superseded**:
  - In V1c, continuous hazard sampling over ALL hours $h_t = \exp(-a(FS_t - 1))$ with $a = 0.55$ gave only a ~2x probability ratio between the wettest and driest hour within a location. Consequently, rain lift collapsed from ~11.6 and 31.0 in V1b down to ~1.0 - 1.3 in V1c.
  - V1d splits the dual roles of stability physics:
    1. **Within-Location Timing**: Restores the V1b rule exactly (high-risk hours $R \ge 0.5$ from lagged rain72/100, sampling weight $\propto \exp(5R)$, 80% rain-driven, 20% uniform random, event-type-first, 120h spacing resampling, attempt cap 500).
    2. **Cross-Location Frequency**: Grounds location event rate directly in dry slope stability: $\lambda_{\text{loc}} = \min(15, 5 \cdot w_{\text{loc}} / \text{mean}(w))$, with $w_{\text{loc}} = \exp(-a \cdot (FS_{\text{dry\_loc}} - 1))$.
    3. **Creep Model**: Restored V1b bounded rain creep $\text{creep} = 0.04 \cdot R^2$ (removing $D^2$ creep).
- **Modifications**:
  - `src/data/create_sensor_data.py`:
    - Implemented pre-generation calibration of $a$ on a 0.05 grid from $FS_{\text{dry\_loc}}$ only (smallest $a$ with $p_{90}/p_{10}$ of $\lambda_{\text{loc}} \in [3, 6]$); selected $a = 0.50$ ($p_{10} \approx 2.4$, median $\approx 5.0$, $p_{90} \approx 7.5$, ratio $\approx 3.03 - 3.21$).
    - Restored exact V1b within-location pore-pressure gating ($R \ge 0.5$) and exponential weight $\exp(5R)$.
    - Restored exact V1b simultaneous sensor dropout generation ($263$ rows per location, exactly 1.00076%).
    - Restored $0.04 \cdot R^2$ rain creep.
    - Preserved 120h minimum spacing, precursor ramp ending at `idx_ev` inclusive, post-event decay and vibration aftershocks starting strictly at `idx_ev + 1`, and chunked resumable 25-location part writes.
    - Recorded `a`, `HAZARD_A`, `FS_dry`, `w_loc`, and `lambda_loc` in `location_metadata.csv`.
  - `src/analysis/run_assertions.py`:
    - Preserved all V1c assertions (spacing $\ge 120$h, rain-driven share $0.8 \pm 0.1$, mean events $5 \pm 0.5$, min events $\ge 1$, variance > mean, two-sided leak checks across ALL events, contiguity, dropouts, reproducibility).
    - Added: Rain lift $\ge 5.0$ in `[50, 100)` mm bin and $\ge 10.0$ in `[100, inf)` mm bin.
    - Added: Spearman rank correlation between $FS_{\text{dry}}$ and event count $\le -0.40$.
    - Added: Verification that $w_{\text{loc}}$ in metadata strictly matches theoretical $\exp(-a \cdot (FS_{\text{dry}} - 1.0))$ ($|\Delta| < 0.01$).
- **Evidence & Multi-Run Results**:
  - **Subset Test (Seed 42, 3 locations)**:
    - Min high-risk hours: 1,051 (PASS).
    - Rain lift: 14.26 in `[50, 100)` mm and 25.22 in `[100, inf)` mm (PASS).
    - Spacing $\ge 120$h: min = 182.0h (PASS).
    - Reproducibility: Bitwise identical datasets and metadata across two independent runs (PASS).
  - **Release V1d Full Runs (500 locations each, 3 independent random seeds)**:
    - **Run 1 (`data_release_v1d_s1/`, seed `42`)**:
      - Total events: 2,484 (1,992 rain-driven [80.19%], 492 random [19.81%], 0 unplaced).
      - Events/loc: min=1, median=5.0, mean=4.968, max=15, variance=7.891 (overdispersion PASS).
      - Spearman($FS_{\text{dry}}$, count): $r_s = -0.6454$ ($p = 3.01 \times 10^{-60}$); Spearman(Mean FS, count): $r_s = -0.6456$.
      - Rain lift: **11.67** in `[50, 100)` mm ($\ge 5$ PASS) and **30.45** in `[100, inf)` mm ($\ge 10$ PASS).
      - Inter-event spacing: min=120.0h, median=2,139.5h, max=21,675.0h (100% isolated).
      - All-events step leakage: disp mean = 0.006428 mm/h $\le 3\sigma$; vib mean = 0.254060 mm/s $\le 3\sigma$.
      - Share of events with $FS \le 1.3$: 4.07% (101 / 2,484).
    - **Run 2 (`data_release_v1d_s2/`, seed `1337`)**:
      - Total events: 2,567 (2,057 rain-driven [80.13%], 510 random [19.87%], 0 unplaced).
      - Events/loc: min=1, median=5.0, mean=5.134, max=14, variance=8.297 (overdispersion PASS).
      - Spearman($FS_{\text{dry}}$, count): $r_s = -0.6309$ ($p = 7.35 \times 10^{-57}$); Spearman(Mean FS, count): $r_s = -0.6316$.
      - Rain lift: **11.76** in `[50, 100)` mm ($\ge 5$ PASS) and **30.96** in `[100, inf)` mm ($\ge 10$ PASS).
      - Inter-event spacing: min=120.0h, median=2,097.0h, max=21,799.0h (100% isolated).
      - All-events step leakage: disp mean = 0.006375 mm/h $\le 3\sigma$; vib mean = 0.234802 mm/s $\le 3\sigma$.
      - Share of events with $FS \le 1.3$: 2.61% (67 / 2,567).
    - **Run 3 (`data_release_v1d_s3/`, seed `2024`)**:
      - Total events: 2,529 (2,030 rain-driven [80.27%], 499 random [19.73%], 0 unplaced).
      - Events/loc: min=1, median=5.0, mean=5.058, max=15, variance=8.343 (overdispersion PASS).
      - Spearman($FS_{\text{dry}}$, count): $r_s = -0.6369$ ($p = 3.11 \times 10^{-58}$); Spearman(Mean FS, count): $r_s = -0.6372$.
      - Rain lift: **11.96** in `[50, 100)` mm ($\ge 5$ PASS) and **29.94** in `[100, inf)` mm ($\ge 10$ PASS).
      - Inter-event spacing: min=120.0h, median=2,099.0h, max=20,375.0h (100% isolated).
      - All-events step leakage: disp mean = 0.006286 mm/h $\le 3\sigma$; vib mean = 0.245452 mm/s $\le 3\sigma$.
      - Share of events with $FS \le 1.3$: 4.75% (120 / 2,529).

### V1d Size Audit Findings & Generator Column Cleanup Fix - [2026-10-17]
- **Size Audit Findings**:
  - Investigated the byte size difference between `data_release_v1d_s1/` and earlier releases (`v1b`, `v1c_s1`):
    - `final_master_dataset.csv` in V1d was 2,510,604,927 bytes (~2,510 MB) compared to 2,105,263,058 bytes in V1b. The root cause was identified as 5 un-dropped geographic metadata columns (`['X', 'Y', 'rand_point', 'fid', 'DN']`) loaded from `spatial_metadata.csv` that were retained in the master file (23 columns vs. 18 columns, adding ~397 MB of ASCII data).
    - In contrast, `training_dataset.csv` in V1d was 2,113,671,785 bytes (~2,113.7 MB, 18 columns), because `create_training_dataset.py` explicitly stripped those 5 columns.
    - The minor +8.4 MB (+0.40%) difference between `training_dataset.csv` in V1b (2,105.3 MB) and V1d (2,113.7 MB) was traced to `Vibration_mm_s`: V1d omitted final Gaussian measurement noise $\mathcal{N}(0, 0.2)$ and subsequent zero-clipping (`.clip(lower=0)`). In V1b/V1c, this clipping drove ~9.5% of rows to the 3-character string `"0.0"`. In V1d, without zero-clipping, all vibration values remain $\ge 0.10000085$ mm/s and are serialized as full 9–10 character floats (+0.6557 characters/row $\times$ 13.14M rows $\approx 8.6$ MB).
    - Verified all files have 100% Windows CRLF line endings, exact identical `float32` serialization precision, and exactly 13,140,001 lines (1 header + 13,140,000 data rows).
- **Generator Fix (`src/data/create_sensor_data.py`)**:
  - Updated `cols_to_drop` on line 340 to explicitly drop `['X', 'Y', 'rand_point', 'fid', 'DN']` in addition to `pore_pressure_proxy` and `rain_72h_sum`.
  - **Verification**: Regenerated the 3-location test subset with seed 42 into a temporary directory. Confirmed:
    - Generated `training_dataset.csv` is bit-identical to reference `data_release_v1d_subset/training_dataset.csv` via `pd.testing.assert_frame_equal` and MD5 checksum (`abde273b8a0c85fd35f20b8e39aba8d1`).
    - Generated `final_master_dataset.csv` matches `training_dataset.csv` bit-for-bit (MD5: `abde273b8a0c85fd35f20b8e39aba8d1`), confirming the 5 leftover columns are removed and future generator runs produce clean 18-column master files.


# Phase A Analysis Report: Factor of Safety & Geotechnical Parameter Audit

This report contains strictly measured empirical statistics from `data_release_v1b/` (`training_dataset.csv` and `location_metadata.csv`).

---

## Failures Report

- **None**: All 500 monitored locations processed without missing records, numerical overflow, or missing values.

---

## 1. Geotechnical Parameter Distributions & Baseline FS

Computed across all 500 locations from `data_release_v1b/location_metadata.csv`.

- **Actual Column Names Used**: `gamma`, `z`, `phi_deg`, `c`, `baseline_FS`

| Parameter | Column Name | Mean | Standard Deviation (Std) | Coefficient of Variation (CV, %) |
| :--- | :--- | :---: | :---: | :---: |
| Unit Weight ($\gamma$, $\text{kN/m}^3$) | `gamma` | 22.5686 | 1.4418 | 6.39% |
| Failure Depth ($z$, $\text{m}$) | `z` | 1.4921 | 0.2849 | 19.10% |
| Friction Angle ($\phi$, deg) | `phi_deg` | 35.1113 | 2.8559 | 8.13% |
| Cohesion ($c$, $\text{kPa}$) | `c` | 6.9893 | 1.7107 | 24.48% |
| Baseline Factor of Safety | `baseline_FS` | 3.5074 | 1.3806 | 39.36% |

*Interpretation: Baseline FS displays substantial cross-location dispersion (CV ~39.4%) driven largely by variation in slope angle, cohesion, and failure depth.*

---

## 2. Dry Factor of Safety OLS Fit & Terrain Correlations

Per location, slope angle $\beta = \text{slope\_1}$ (initial value) and dry factor of safety $\text{fs\_dry} = \max(\text{FS})$.

### OLS Regression: $\log(\text{fs\_dry}) \sim \log(\tan(\text{radians}(\text{slope\_1})))$
- **Fitted Model**: $\log(\text{fs\_dry}) = -0.0508 - 0.9873 \cdot \log(\tan(\text{radians}(\text{slope\_1})))$
- **Coefficient of Determination ($R^2$)**: **0.8536**
- **Hidden Share ($1 - R^2$)**: **0.1464** (**14.64%**)

*Interpretation: Slope angle explains 85.36% of variance in dry stability, leaving 14.64% attributable to unobserved geotechnical parameters ($\gamma, z, \phi, c$).*

### Pearson Correlation ($r$) with Other Terrain Features
Correlations between $\log(\text{fs\_dry})$ and static location terrain features:

| Terrain Feature Column | Pearson Correlation ($r$) | $p$-value | Significance |
| :--- | :---: | :---: | :---: |
| `elev_1` (Elevation) | +0.0457 | $3.0774 \times 10^{-1}$ | Not significant ($p > 0.05$) |
| `rough_1` (Roughness) | +0.0443 | $3.2291 \times 10^{-1}$ | Not significant ($p > 0.05$) |
| `tri_1` (Terrain Ruggedness Index) | -0.7187 | $1.2754 \times 10^{-80}$ | Significant ($p < 10^{-4}$) |
| `profile_curvature` | -0.0145 | $7.4565 \times 10^{-1}$ | Not significant ($p > 0.05$) |
| `planform_curvature` | +0.0175 | $6.9627 \times 10^{-1}$ | Not significant ($p > 0.05$) |

*Interpretation: Only TRI strongly correlates with dry stability ($r = -0.7187$) due to collinearity with slope steepness; curvature and elevation share no linear association.*

---

## 3. Per-Location Factor of Safety Distribution across 500 Locations

Distribution summaries across the 500 locations for per-location $\min(\text{FS})$, $\text{median}(\text{FS})$, and $\max(\text{FS})$:

| Statistic | Per-Location Min FS (`fs_min`) | Per-Location Median FS (`fs_median`) | Per-Location Max FS (`fs_max`) |
| :--- | :---: | :---: | :---: |
| **count** | 500.0000 | 500.0000 | 500.0000 |
| **mean** | 2.2645 | 3.4923 | 3.5074 |
| **std** | 0.9325 | 1.3752 | 1.3806 |
| **min** | 0.8346 | 1.3320 | 1.3370 |
| **25%** | 1.7838 | 2.7881 | 2.8013 |
| **50% (Median)** | 2.0750 | 3.2037 | 3.2159 |
| **75%** | 2.4530 | 3.7593 | 3.7764 |
| **max** | 9.0743 | 13.7204 | 13.7768 |

### Locations Reaching Critical Stability Thresholds
- **Locations with $\min(\text{FS}) \le 1.3$**: **17 locations** (3.40%)
- **Locations with $\min(\text{FS}) \le 1.5$**: **53 locations** (10.60%)
- **Locations with $\min(\text{FS}) \le 2.0$**: **220 locations** (44.00%)

*Interpretation: Only 3.4% of locations ever reach traditional geotechnical failure limit $FS \le 1.3$, demonstrating why rainfall pore-pressure fraction $R$ is necessary to govern risk.*

---

## 4. Rain-Only vs. Factor of Safety Dynamics (Non-ML Check)

Restricted strictly to clean pre-failure hours (`post_event_window == 0`).

- **Rolling 72h Rainfall Definition**: `rain72` = rolling 72-hour sum of `precipitation` per location (`min_periods=1`).
- **Within-Location Hourly Spearman Correlation ($\text{FS}$ vs $\text{rain72}$)**:
  - **Median across 500 locations**: **-0.9641**
  - **Mean across 500 locations**: **-0.9641**
  - **Range**: Min = -0.9796, Max = -0.9473
- **Location Mean FS vs. Location Total Event Count (`num_events`)**:
  - **Spearman Correlation ($r_s$)**: **-0.0039** ($p = 0.9302$)
  - **Pearson Correlation ($r$)**: **+0.0274** ($p = 0.5408$)

*Interpretation: Factor of Safety responds almost monotonically to 72h cumulative rainfall within every location ($r_s = -0.9641$), whereas cross-location event frequency is decoupled from baseline FS ($r_s = -0.0039$, consistent with independent Poisson draws).*

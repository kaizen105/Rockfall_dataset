# Card & README Number Sources Appendix

This document indexes every numerical quantity cited in [`HF_DATASET_CARD_DRAFT.md`](file:///c:/Rockfall_AI_Project/HF_DATASET_CARD_DRAFT.md) and [`README_github_DRAFT.md`](file:///c:/Rockfall_AI_Project/README_github_DRAFT.md) against its verified source line in [`DATASET_FACTS.md`](file:///c:/Rockfall_AI_Project/DATASET_FACTS.md) and repository audit logs.

---

## 1. Primary Dataset Dimensions & File Sizes

| Quantity Cited | Context in Drafts | Source File | Line in Source |
|---|---|---|---|
| **13,140,000** | Total rows in master & training dataset | `DATASET_FACTS.md` | Line 30 |
| **500** | Monitored locations (`LOC_1` through `LOC_500`) | `DATASET_FACTS.md` | Line 29 |
| **26,280** | Hours per location (3 years $\times$ 8,760 hours) | `DATASET_FACTS.md` | Line 30 |
| **100%** | Row contiguity (0 timestamp gaps) | `DATASET_FACTS.md` | Line 31 |
| **2,113,671,785 B** | Exact byte size of `training_dataset.csv` (Seed 42) | `v1d_size_audit.md` / `DATASET_FACTS.md` | Line 33 |
| **178,789** | Flagged post-event rows (`post_event_window = 1`) in Seed 42 | `DATASET_FACTS.md` | Line 35 |
| **184,723** | Flagged post-event rows in Seed 1337 | `DATASET_FACTS.md` | Line 35 |
| **182,088** | Flagged post-event rows in Seed 2024 | `DATASET_FACTS.md` | Line 35 |

---

## 2. Event Counts & Proportions Across Seeds

| Quantity Cited | Context in Drafts | Source File | Line in Source |
|---|---|---|---|
| **2,484** | Total rockfall events in Main Release (Seed 42) | `DATASET_FACTS.md` | Line 43 |
| **2,567** | Total rockfall events in Replication Run 1 (Seed 1337) | `DATASET_FACTS.md` | Line 43 |
| **2,529** | Total rockfall events in Replication Run 2 (Seed 2024) | `DATASET_FACTS.md` | Line 43 |
| **1,992 (80.1932%)** | Rain-driven events in Seed 42 | `DATASET_FACTS.md` | Line 44 |
| **2,057 (80.1325%)** | Rain-driven events in Seed 1337 | `DATASET_FACTS.md` | Line 44 |
| **2,030 (80.2689%)** | Rain-driven events in Seed 2024 | `DATASET_FACTS.md` | Line 44 |
| **492 (19.8068%)** | Stochastic random dry events in Seed 42 | `DATASET_FACTS.md` | Line 45 |
| **510 (19.8675%)** | Stochastic random dry events in Seed 1337 | `DATASET_FACTS.md` | Line 45 |
| **499 (19.7311%)** | Stochastic random dry events in Seed 2024 | `DATASET_FACTS.md` | Line 45 |
| **0 (0.00%)** | Unplaced events across all three runs under 120h spacing | `DATASET_FACTS.md` | Line 46 |

---

## 3. Spatial Distribution & Geotechnical Coupling

| Quantity Cited | Context in Drafts | Source File | Line in Source |
|---|---|---|---|
| **1 event** | Minimum events per location | `DATASET_FACTS.md` | Line 47 |
| **3.0 events** | 25th percentile of events per location | `DATASET_FACTS.md` | Line 48 |
| **5.0 events** | Median events per location | `DATASET_FACTS.md` | Line 49 |
| **4.968 events** | Mean events per location in Seed 42 | `DATASET_FACTS.md` | Line 50 |
| **5.134 events** | Mean events per location in Seed 1337 | `DATASET_FACTS.md` | Line 50 |
| **5.058 events** | Mean events per location in Seed 2024 | `DATASET_FACTS.md` | Line 50 |
| **7.0 events** | 75th percentile of events per location | `DATASET_FACTS.md` | Line 51 |
| **15 events** | Maximum events per location in Seed 42 (cap $\lambda \le 15$) | `DATASET_FACTS.md` | Line 52 |
| **7.891** | Event count variance in Seed 42 (overdispersion pass) | `DATASET_FACTS.md` | Line 53 |
| **8.297** | Event count variance in Seed 1337 | `DATASET_FACTS.md` | Line 53 |
| **8.343** | Event count variance in Seed 2024 | `DATASET_FACTS.md` | Line 53 |
| **-0.6454** | Spearman $r_s$ ($FS_{\text{dry}}$ vs count) in Seed 42 | `DATASET_FACTS.md` | Line 62 |
| **3.01 $\times$ 10$^{-60}$** | $p$-value for Spearman $r_s$ in Seed 42 | `DATASET_FACTS.md` | Line 63 |
| **-0.6309** | Spearman $r_s$ ($FS_{\text{dry}}$ vs count) in Seed 1337 | `DATASET_FACTS.md` | Line 62 |
| **-0.6369** | Spearman $r_s$ ($FS_{\text{dry}}$ vs count) in Seed 2024 | `DATASET_FACTS.md` | Line 62 |
| **101 (4.066%)** | Share of events with $FS \le 1.3$ at failure hour in Seed 42 | `DATASET_FACTS.md` | Line 66 |
| **a = 0.50** | Calibrated hazard sensitivity exponent | `DATASET_FACTS.md` | Line 17 |
| **3.10** | $p_{90}/p_{10}$ spread ratio of $\lambda_{\text{loc}}$ ($p_{10}=2.42, p_{90}=7.50$) | `DATASET_FACTS.md` | Line 17 |

---

## 4. Rain Lift & Accumulation Metrics

| Quantity Cited | Context in Drafts | Source File | Line in Source |
|---|---|---|---|
| **0.1890 / 1000h** | Overall failure rate in Seed 42 | `DATASET_FACTS.md` | Line 75 |
| **0.0385 / 1000h** | Event rate in $[0, 5)$ mm `rain72` bin (Lift: 0.20x) | `DATASET_FACTS.md` | Line 78 |
| **0.0507 / 1000h** | Event rate in $[5, 20)$ mm `rain72` bin (Lift: 0.27x) | `DATASET_FACTS.md` | Line 79 |
| **0.1206 / 1000h** | Event rate in $[20, 50)$ mm `rain72` bin (Lift: 0.64x) | `DATASET_FACTS.md` | Line 80 |
| **2.2066 / 1000h** | Event rate in $[50, 100)$ mm `rain72` bin in Seed 42 | `DATASET_FACTS.md` | Line 81 |
| **11.67x** | Rain lift in $[50, 100)$ mm bin in Seed 42 | `DATASET_FACTS.md` | Line 81 |
| **11.76x** | Rain lift in $[50, 100)$ mm bin in Seed 1337 | `DATASET_FACTS.md` | Line 90 |
| **11.96x** | Rain lift in $[50, 100)$ mm bin in Seed 2024 | `DATASET_FACTS.md` | Line 99 |
| **5.7560 / 1000h** | Event rate in $[100, \infty)$ mm `rain72` bin in Seed 42 | `DATASET_FACTS.md` | Line 82 |
| **30.45x** | Rain lift in $[100, \infty)$ mm bin in Seed 42 | `DATASET_FACTS.md` | Line 82 |
| **30.96x** | Rain lift in $[100, \infty)$ mm bin in Seed 1337 | `DATASET_FACTS.md` | Line 91 |
| **29.94x** | Rain lift in $[100, \infty)$ mm bin in Seed 2024 | `DATASET_FACTS.md` | Line 100 |

---

## 5. Event Spacing & Profile Metrics

| Quantity Cited | Context in Drafts | Source File | Line in Source |
|---|---|---|---|
| **1,984 pairs** | Consecutive event pairs in Seed 42 | `DATASET_FACTS.md` | Line 110 |
| **120.0 hours** | Minimum enforced spacing between events across all runs | `DATASET_FACTS.md` | Line 111 |
| **2,139.5 hours** | Median inter-event spacing in Seed 42 (~89.1 days) | `DATASET_FACTS.md` | Line 112 |
| **21,675.0 hours** | Maximum inter-event spacing in Seed 42 (~2.47 years) | `DATASET_FACTS.md` | Line 113 |
| **0 (0.00%)** | Overlapping events within 72h post-event decay | `DATASET_FACTS.md` | Line 114 |
| **0 (0.00%)** | Overlapping events within $72\text{h} + T_{\text{lead}}$ | `DATASET_FACTS.md` | Line 115 |
| **100.0%** | Percentage of events completely isolated | `DATASET_FACTS.md` | Line 116 |
| **0.02667 mm/h** | Hourly displacement at -48h for rain-driven events (Seed 42) | `DATASET_FACTS.md` | Line 126 |
| **0.03711 mm/h** | Hourly displacement at -24h for rain-driven events (Seed 42) | `DATASET_FACTS.md` | Line 128 |
| **0.04534 mm/h** | Hourly displacement at -12h for rain-driven events (Seed 42) | `DATASET_FACTS.md` | Line 130 |
| **0.05163 mm/h** | Hourly displacement at -6h for rain-driven events (Seed 42) | `DATASET_FACTS.md` | Line 131 |
| **0.05904 mm/h** | Hourly displacement at -1h for rain-driven events (Seed 42) | `DATASET_FACTS.md` | Line 134 |
| **0.06090 mm/h** | Hourly displacement at 0h (failure) for rain-driven events | `DATASET_FACTS.md` | Line 135 |
| **0.04601 mm/h** | Mean displacement across pre-24h window for rain-driven | `DATASET_FACTS.md` | Line 136 |
| **~0.0117 mm/h** | Non-event background displacement baseline | `DATASET_FACTS.md` | Line 136 |

---

## 6. Two-Sided Leakage Checks & Dropouts

| Quantity Cited | Context in Drafts | Source File | Line in Source |
|---|---|---|---|
| **2,422** | Evaluated events in Seed 42 (excluding series edges) | `DATASET_FACTS.md` | Line 146 |
| **0.006428 mm/h** | Mean absolute step in displacement across event rows | `DATASET_FACTS.md` | Line 146 |
| **0.016155 mm/h** | 3-sigma bound for displacement step (Passed) | `DATASET_FACTS.md` | Line 146 |
| **0.254060 mm/s** | Mean absolute step in vibration across event rows | `DATASET_FACTS.md` | Line 147 |
| **2.016809 mm/s** | 3-sigma bound for vibration step (Passed) | `DATASET_FACTS.md` | Line 147 |
| **0.006375 mm/h** | Mean displacement step in Seed 1337 | `DATASET_FACTS.md` | Line 148 |
| **0.234802 mm/s** | Mean vibration step in Seed 1337 | `DATASET_FACTS.md` | Line 149 |
| **0.006286 mm/h** | Mean displacement step in Seed 2024 | `DATASET_FACTS.md` | Line 150 |
| **0.245452 mm/s** | Mean vibration step in Seed 2024 | `DATASET_FACTS.md` | Line 151 |
| **1.00076%** | Simultaneous sensor dropout rate (263 rows per location) | `DATASET_FACTS.md` | Line 158 |
| **131,500** | Total rows with simultaneous sensor dropouts per run | `DATASET_FACTS.md` | Lines 160-161 |

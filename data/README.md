# Data Directory Overview

This directory contains the simulation inputs, active production releases, and historical audit versions for the Noamundi Rockfall Dataset.

---

## 1. Directory Structure

```text
data/
├── current/                      # Active production releases (V1d)
│   ├── v1d_s1/                   # Main Published Release (Seed 42)
│   │   ├── training_dataset.csv  (2.11 GB, ML-ready, untracked)
│   │   ├── final_master_dataset.csv (2.11 GB, untracked)
│   │   └── location_metadata.csv (162 KB, tracked in Git)
│   ├── v1d_s2/                   # Scientific Replication Seed 1337 (untracked)
│   └── v1d_s3/                   # Scientific Replication Seed 2024 (untracked)
│
├── inputs/                       # Upstream simulation inputs
│   ├── spatial_metadata.csv      (66 KB, static terrain & trajectory metrics, tracked)
│   ├── geometry_dataset_500.csv  (81 KB, 500 monitoring point traits, tracked)
│   └── weather_dataset.csv       (870 MB, Open-Meteo hourly weather, untracked)
│
└── archive/                      # Historical superseded research releases
    ├── v1/                       (Initial un-spaced run)
    ├── v1b/                      (First 120h-spaced Poisson run)
    ├── v1c/                      (Continuous FS hazard runs s1, s2, s3)
    ├── subsets/                  (Fast 3-location test subsets)
    └── data_v1/, data_v2/        (Legacy raw dumps)
```

---

## 2. Remote Download Links

Large files (>5 MB) are hosted externally and ignored by Git:
- **Hugging Face Hub**: [Kaizen696/noamundi-rockfall-simulation-dataset](https://huggingface.co/datasets/Kaizen696/noamundi-rockfall-simulation-dataset)
- **Rebuilding Weather Data**: To rebuild `data/inputs/weather_dataset.csv`, see [`docs/REBUILD_INPUTS.md`](file:///c:/Rockfall_AI_Project/docs/REBUILD_INPUTS.md).

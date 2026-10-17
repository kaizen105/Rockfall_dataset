# Repository Cleanup & Hygiene Plan

## 1. Security & Hygiene Risks (Reported First)

### 1.1 Large Blobs in Git History (>50 MB)
Searching the entire git object database (`git rev-list --objects --all | git cat-file --batch-check`) identified **three historical blobs exceeding 50 MB** and three additional blobs exceeding 25 MB still retained in `.git/objects`:

| Blob SHA | Size | Path at Commit | Commits Containing Blob |
|---|---|---|---|
| `1ca125a0686e2dc579a1c3ffc893b8f9bf06869f` | **60.08 MB** | `data/final_master_dataset.csv` | `9d6b2f5`, `f94a1c9` |
| `fd82dba3236b920b458fe607e102748765fe3c39` | **53.19 MB** | `data/final_master_dataset.csv` | `f94a1c9`, `d42cde1` |
| `3b7b0e7482a872f4ae005ba5a9a0d216a5cbe2bd` | **53.19 MB** | `data/final_master_dataset.csv` | `d42cde1`, `44edb41` |
| `7d7f0cda5b74be2e30fdca764f58bc0f5ab0464b` | 32.22 MB | `data/synthetic_sensor_and_events.csv` | `9d6b2f5`, `f94a1c9` |
| `692ca12167a7e44f636fb91bd556816316f39952` | 25.22 MB | `data/synthetic_sensor_and_events.csv` | `f94a1c9`, `d42cde1` |
| `88c29959edb65765be6d15d9e425f7fbd42d69cf` | 25.21 MB | `data/synthetic_sensor_and_events.csv` | `d42cde1`, `44edb41` |

- **Total `.git/` Directory Size**: **59.05 MB** (`61,913,944` bytes).
- **Risk Assessment**: Although these files were removed from the working tree in later commits, their historical objects remain permanently packaged in `.git/objects/pack/`. If the repository is ever pushed upstream to GitHub without filtering, these 50+ MB blobs will bloat clone times and approach GitHub's 100 MB hard limit.

### 1.2 Secrets & API Keys Scan
- Scanned all tracked files in git history and working tree using regex patterns for API keys (`hf_*`, `ghp_*`, `sk-*`, bearer tokens, private keys, Open-Meteo parameters).
- **Result**: **0 secrets found**. `src/data/get_weather_data.py` uses the open, unauthenticated public Open-Meteo historical archive API (`https://archive-api.open-meteo.com/v1/archive`). No credentials or tokens exist in the repository.

### 1.3 Machine-Specific Absolute Paths in Tracked Files
- Scanned all tracked files for absolute OS paths.
- **Critical Risk Detected**: `.vscode/settings.json` is **currently tracked in Git** and contains hardcoded Windows paths specific to the author's local workstation:
  ```json
  {
      "python.defaultInterpreterPath": "c:\\Rockfall_AI_Project\\venv\\Scripts\\python.exe",
      "python.analysis.extraPaths": [
          "c:\\Rockfall_AI_Project",
          "c:\\Rockfall_AI_Project\\src\\data"
      ]
  }
  ```
  **Remediation**: Untrack `.vscode/settings.json` (`git rm --cached .vscode/settings.json`), replace with relative workspace paths or gitignore `.vscode/`.

---

## 2. Top 40 Files in Workspace by Size

| Rank | Size (MB) | File Path | Category | Description / Role |
|---|---|---|---|---|
| 1 | 3,530.50 MB | `data_v2/final_master_dataset.csv` | Large Data (>5 MB) | Legacy full unmasked master dataset |
| 2 | 2,868.22 MB | `data_v2/training_dataset.csv` | Large Data (>5 MB) | Legacy training dataset (leakage present) |
| 3 | 2,394.40 MB | `data_release_v1d_s2/final_master_dataset.csv` | Large Data (>5 MB) | V1d Seed 1337 master dataset (23 cols) |
| 4 | 2,394.32 MB | `data_release_v1d_s3/final_master_dataset.csv` | Large Data (>5 MB) | V1d Seed 2024 master dataset (23 cols) |
| 5 | 2,394.30 MB | `data_release_v1d_s1/final_master_dataset.csv` | Large Data (>5 MB) | V1d Seed 42 master dataset (23 cols) |
| 6 | 2,015.86 MB | `data_release_v1d_s2/training_dataset.csv` | Large Data (>5 MB) | V1d Seed 1337 clean training dataset (18 cols) |
| 7 | 2,015.77 MB | `data_release_v1d_s3/training_dataset.csv` | Large Data (>5 MB) | V1d Seed 2024 clean training dataset (18 cols) |
| 8 | 2,015.75 MB | `data_release_v1d_s1/training_dataset.csv` | Large Data (>5 MB) | V1d Seed 42 clean training dataset (18 cols) |
| 9 | 2,007.74 MB | `data_release_v1b/final_master_dataset.csv` | Large Data (>5 MB) | V1b master dataset (18 cols) |
| 10 | 2,007.74 MB | `data_release_v1b/training_dataset.csv` | Large Data (>5 MB) | V1b clean training dataset (18 cols) |
| 11 | 2,007.73 MB | `data_release_v1c_s2/final_master_dataset.csv` | Large Data (>5 MB) | V1c Seed 1337 master dataset (18 cols) |
| 12 | 2,007.73 MB | `data_release_v1c_s2/training_dataset.csv` | Large Data (>5 MB) | V1c Seed 1337 clean training dataset (18 cols) |
| 13 | 2,007.65 MB | `data_release_v1/final_master_dataset.csv` | Large Data (>5 MB) | V1 initial run master dataset |
| 14 | 2,007.65 MB | `data_release_v1/training_dataset.csv` | Large Data (>5 MB) | V1 initial run training dataset |
| 15 | 2,007.65 MB | `data_release_v1c_s3/final_master_dataset.csv` | Large Data (>5 MB) | V1c Seed 2024 master dataset (18 cols) |
| 16 | 2,007.65 MB | `data_release_v1c_s3/training_dataset.csv` | Large Data (>5 MB) | V1c Seed 2024 clean training dataset (18 cols) |
| 17 | 2,007.61 MB | `data_release_v1c_s1/final_master_dataset.csv` | Large Data (>5 MB) | V1c Seed 42 master dataset (18 cols) |
| 18 | 2,007.61 MB | `data_release_v1c_s1/training_dataset.csv` | Large Data (>5 MB) | V1c Seed 42 clean training dataset (18 cols) |
| 19 | 909.31 MB | `data_v2/synthetic_sensor_and_events.csv` | Large Data (>5 MB) | Pre-downscaled sensor and event file |
| 20 | 830.06 MB | `data_v2/weather_dataset.csv` | Large Data (>5 MB) | Raw hourly weather dataset from API |
| 21 | 120.62 MB | `data_release_v1d_s2/parts/part_0009.csv` | Scratch/Temp | Checkpoint part file (locs 226-250) |
| 22 | 120.57 MB | `data_release_v1d_s3/parts/part_0009.csv` | Scratch/Temp | Checkpoint part file (locs 226-250) |
| 23 | 120.57 MB | `data_release_v1d_s1/parts/part_0009.csv` | Scratch/Temp | Checkpoint part file (locs 226-250) |
| 24 | 120.15 MB | `data_release_v1d_s2/parts/part_0018.csv` | Scratch/Temp | Checkpoint part file (locs 451-475) |
| 25 | 120.14 MB | `data_release_v1d_s1/parts/part_0012.csv` | Scratch/Temp | Checkpoint part file (locs 301-325) |
| 26 | 120.12 MB | `data_release_v1d_s1/parts/part_0018.csv` | Scratch/Temp | Checkpoint part file (locs 451-475) |
| 27 | 120.11 MB | `data_release_v1d_s2/parts/part_0016.csv` | Scratch/Temp | Checkpoint part file (locs 401-425) |
| 28 | 120.09 MB | `data_release_v1d_s3/parts/part_0012.csv` | Scratch/Temp | Checkpoint part file (locs 301-325) |
| 29 | 120.08 MB | `data_release_v1d_s3/parts/part_0016.csv` | Scratch/Temp | Checkpoint part file (locs 401-425) |
| 30 | 120.07 MB | `data_release_v1d_s3/parts/part_0018.csv` | Scratch/Temp | Checkpoint part file (locs 451-475) |
| 31 | 120.07 MB | `data_release_v1d_s2/parts/part_0012.csv` | Scratch/Temp | Checkpoint part file (locs 301-325) |
| 32 | 120.06 MB | `data_release_v1d_s1/parts/part_0016.csv` | Scratch/Temp | Checkpoint part file (locs 401-425) |
| 33 | 120.05 MB | `data_release_v1d_s2/parts/part_0011.csv` | Scratch/Temp | Checkpoint part file (locs 276-300) |
| 34 | 120.01 MB | `data_release_v1d_s3/parts/part_0011.csv` | Scratch/Temp | Checkpoint part file (locs 276-300) |
| 35 | 120.00 MB | `data_release_v1d_s1/parts/part_0011.csv` | Scratch/Temp | Checkpoint part file (locs 276-300) |
| 36 | 119.99 MB | `data_release_v1d_s3/parts/part_0014.csv` | Scratch/Temp | Checkpoint part file (locs 351-375) |
| 37 | 119.99 MB | `data_release_v1d_s1/parts/part_0014.csv` | Scratch/Temp | Checkpoint part file (locs 351-375) |
| 38 | 119.97 MB | `data_release_v1d_s3/parts/part_0015.csv` | Scratch/Temp | Checkpoint part file (locs 376-400) |
| 39 | 119.97 MB | `data_release_v1d_s2/parts/part_0014.csv` | Scratch/Temp | Checkpoint part file (locs 351-375) |
| 40 | 119.93 MB | `data_release_v1d_s2/parts/part_0015.csv` | Scratch/Temp | Checkpoint part file (locs 376-400) |

---

## 3. Git Tracked Files Audit

- Total tracked files (`git ls-files`): **35 files**.
- Tracked files $> 5$ MB: **0 files**.
- Largest tracked files currently in index:
  1. `qgis_raw_data/steep_mask.tif` (2.13 MB) - Small Data (<5 MB)
  2. `qgis_raw_data/steep_polygons.shp.gpkg` (1.05 MB) - Small Data (<5 MB)
  3. `results/event_windows.png` (0.22 MB) - Generated Output
  4. `results/correlation_heatmap.png` (0.17 MB) - Generated Output

---

## 4. Current `.gitignore` & Proposed Additions

### Current Content of `.gitignore`
```gitignore
venv/
__pycache__/
.ipynb_checkpoints/
data_v1/
data_v2/
```

### Proposed Comprehensive `.gitignore` (Do Not Apply Yet)
```gitignore
# Python environments & caches
venv/
env/
__pycache__/
*.py[cod]
*$py.class
.ipynb_checkpoints/

# IDE & Editor configurations (contain machine-specific absolute paths)
.vscode/
.idea/
*.sublime-project
*.sublime-workspace

# Large datasets & generated releases (hosted externally on Hugging Face / Kaggle)
data_v1/
data_v2/
data_release_*/
*.csv
!spatial_metadata.csv
!data/README.md

# Intermediate generation parts & checkpoints
*/parts/
*_rng.pkl
part_*.csv

# Scratch analysis files & temporary logs
scratch/
*.log
task-*.log
temp/
tmp/

# OS-specific clutter
Thumbs.db
Desktop.ini
.DS_Store
```

---

## 5. Proposed Clean Folder Layout & File Disposition Table

### Proposed Repository Layout
```text
Rockfall_AI_Project/
├── .gitignore
├── AGENT_RULES.md                  # Strict pairing & integrity rules
├── CHANGELOG_V1.md                 # Longitudinal pipeline audit log
├── DATASET_FACTS.md                # Ground-truth measured statistics across releases
├── README.md                       # Comprehensive repository documentation & pipeline guide
├── requirements.txt                # Production dependencies
│
├── data/
│   ├── README.md                   # Pointer & download instructions for HF & Kaggle
│   └── spatial_metadata.csv        # Static terrain & geotechnical metadata (500 locations)
│
├── docs/                           # Centralized audit & phase reports
│   ├── phaseA_report.md
│   ├── v1d_size_audit.md
│   ├── REPO_CLEANUP_PLAN.md
│   └── CARD_NUMBER_SOURCES.md
│
├── notebooks/                      # Exploratory notebooks
│   └── check.ipynb
│
├── qgis_raw_data/                  # Raw spatial masks (under 5 MB total)
│   ├── steep_mask.tif
│   └── steep_polygons.shp.gpkg
│
├── results/                        # Summary figures & assertion outputs
│   ├── analysis_results.json
│   ├── dataset_summary.json
│   └── *.png
│
└── src/                            # Modular pipeline codebase
    ├── analysis/                   # Validation & assertion scripts
    │   ├── check.py
    │   ├── plot_verification.py
    │   └── run_assertions.py
    └── data/                       # Core generation pipeline
        ├── prepare_geometry_500.py
        ├── fix_curvature_crs.py
        ├── get_weather_data.py
        ├── create_sensor_data.py
        ├── simulate_trajectory.py
        └── create_training_dataset.py
```

### File Action Table

| File / Folder | Action | Target Destination | Rationale |
|---|---|---|---|
| `src/data/*.py` | **Keep** | `src/data/` | Core generation engines |
| `src/analysis/*.py` | **Keep** | `src/analysis/` | Test & assertion suites |
| `spatial_metadata.csv` | **Keep** | `data/` | Ground truth 500-location terrain/geotechnical traits |
| `AGENT_RULES.md` | **Keep** | Root | Critical operational constraints |
| `CHANGELOG_V1.md` | **Keep** | Root | Audit log of all versions and fixes |
| `DATASET_FACTS.md` | **Keep** | Root | Measured empirical numbers for papers/cards |
| `README.md` | **Keep / Update** | Root | Master GitHub landing documentation |
| `requirements.txt` | **Keep** | Root | Python package dependencies |
| `phaseA_report.md` | **Move** | `docs/phaseA_report.md` | Audit report; keep root uncluttered |
| `v1d_size_audit.md` | **Move** | `docs/v1d_size_audit.md` | Audit report; keep root uncluttered |
| `REPO_CLEANUP_PLAN.md` | **Move** | `docs/REPO_CLEANUP_PLAN.md` | Planning document |
| `data_release_v1/` | **Keep / Gitignore** | Local disk | Historical release |
| `data_release_v1_subset/` | **Keep / Gitignore** | Local disk | Test subset |
| `data_release_v1b/` | **Keep / Gitignore** | Local disk | Benchmark V1b release |
| `data_release_v1c_s*/` | **Keep / Gitignore** | Local disk | Benchmark V1c releases |
| `data_release_v1d_s*/` | **Keep / Gitignore** | Local disk | Main V1d releases (s1, s2, s3) |
| `data_v1/`, `data_v2/` | **Keep / Gitignore** | Local disk | Raw upstream weather and DEM tables |
| `.vscode/settings.json` | **Untrack / Gitignore**| Local disk only | Machine-specific Windows paths must not be tracked |
| `results/all_scripts.txt`| **Delete** | N/A | Redundant dump file; clutter |
| `src/analysis.py` | **Delete** | N/A | Superseded ad-hoc script; functionality lives in `src/analysis/` |

---

## 6. Pipeline Reproduction Commands

To reproduce any release deterministically from raw weather and spatial metadata:

### Pre-processing & Terrain Geometry
```bash
python src/data/prepare_geometry_500.py
python src/data/fix_curvature_crs.py
python src/data/get_weather_data.py
python src/data/simulate_trajectory.py
```

### V1d Main Releases (Seeds 42, 1337, 2024)

#### Seed 42 (Main Release — `data_release_v1d_s1`)
```bash
# 1. Precursor Sensor Simulation
python src/data/create_sensor_data.py --output-dir data_release_v1d_s1 --seed 42

# 2. Downcasting & Post-Processing (Training Dataset)
python src/data/create_training_dataset.py --input-path data_release_v1d_s1/final_master_dataset.csv --output-path data_release_v1d_s1/training_dataset.csv

# 3. Assertions & Validation Suite
python src/analysis/run_assertions.py --release-dir data_release_v1d_s1 --seed 42
```

#### Seed 1337 (Replication Run 1 — `data_release_v1d_s2`)
```bash
python src/data/create_sensor_data.py --output-dir data_release_v1d_s2 --seed 1337
python src/data/create_training_dataset.py --input-path data_release_v1d_s2/final_master_dataset.csv --output-path data_release_v1d_s2/training_dataset.csv
python src/analysis/run_assertions.py --release-dir data_release_v1d_s2 --seed 1337
```

#### Seed 2024 (Replication Run 2 — `data_release_v1d_s3`)
```bash
python src/data/create_sensor_data.py --output-dir data_release_v1d_s3 --seed 2024
python src/data/create_training_dataset.py --input-path data_release_v1d_s3/final_master_dataset.csv --output-path data_release_v1d_s3/training_dataset.csv
python src/analysis/run_assertions.py --release-dir data_release_v1d_s3 --seed 2024
```

### Fast 3-Location Test Subset (Seed 42)
```bash
python src/data/create_sensor_data.py --output-dir data_release_v1d_subset --seed 42 --max-locations 3
python src/data/create_training_dataset.py --input-path data_release_v1d_subset/final_master_dataset.csv --output-path data_release_v1d_subset/training_dataset.csv
python src/analysis/run_assertions.py --release-dir data_release_v1d_subset --seed 42
```

---

## 7. Audit of `create_sensor_data.py` Column Dropping

### Is `cols_to_drop` Leaving Artifacts in `final_master_dataset.csv`?
**YES**. In `src/data/create_sensor_data.py` (lines 340-341):
```python
cols_to_drop = ["pore_pressure_proxy", "rain_72h_sum"]
df_loc.drop(columns=[c for c in cols_to_drop if c in df_loc.columns], inplace=True)
```
Because `df_geometry` initially loaded `['X', 'Y', 'rand_point', 'fid', 'DN']` from `spatial_metadata.csv`, those 5 columns were carried into `final_master_dataset.csv`, expanding it to 23 columns and 2,510 MB.

### Proposed One-Line Fix (Do Not Apply Yet)
Change line 340 of `src/data/create_sensor_data.py` from:
```python
cols_to_drop = ["pore_pressure_proxy", "rain_72h_sum"]
```
to:
```python
cols_to_drop = ["pore_pressure_proxy", "rain_72h_sum", "X", "Y", "rand_point", "fid", "DN"]
```

### Verification Procedure (Zero-Risk Validation)
1. Run the 3-location generator with seed 42 to a test directory:
   ```bash
   python src/data/create_sensor_data.py --output-dir data_release_v1d_test_subset --seed 42 --max-locations 3
   ```
2. Run `create_training_dataset.py`:
   ```bash
   python src/data/create_training_dataset.py --input-path data_release_v1d_test_subset/final_master_dataset.csv --output-path data_release_v1d_test_subset/training_dataset.csv
   ```
3. Execute a bitwise assertion against the baseline subset:
   ```python
   import pandas as pd
   df_test = pd.read_csv("data_release_v1d_test_subset/training_dataset.csv")
   df_ref = pd.read_csv("data_release_v1d_subset/training_dataset.csv")
   pd.testing.assert_frame_equal(df_test, df_ref)
   ```
   Because `create_training_dataset.py` was already dropping `['X', 'Y', 'rand_point', 'fid', 'DN']` down to 18 columns, dropping them earlier inside `create_sensor_data.py` will leave `training_dataset.csv` 100% bit-identical while stripping ~397 MB of unneeded columns from `final_master_dataset.csv`.

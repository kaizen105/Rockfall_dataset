# Rockfall Dataset Generation and Analysis

This repository contains a complete, physics-informed pipeline for creating, merging, and analyzing realistic synthetic rockfall event data. The core of this dataset is anchored in **real-world geospatial data**, which is then combined with historical weather conditions and simulated sensor readings.

## 🌍 The Workflow: How the Data Was Created

### Step 1: Topographical Data (OpenTopography & QGIS)
The foundational geometry dataset was derived using **OpenTopography** to obtain the initial Digital Elevation Model (DEM). **QGIS** was then used to process this elevation data and extract critical terrain features at various locations, including:
- **Slope**
- **Aspect**
- **Ruggedness**
- **Roughness**

These features were exported from QGIS into `data/geometry_dataset.csv` and form the physical basis for the simulated rockfall events.

### Step 2: Weather Data Integration (Open-Meteo API)
Using `src/data/get_weather_data.py`, historical weather data for the corresponding location (e.g., Noamundi) was fetched using the Open-Meteo API. This includes temperatures, precipitation sums, and wind speeds, while also engineering features like 3-day and 7-day rolling rainfall sums.

### Step 3: Physics-Informed Sensor Simulation
Using `src/data/create_sensor_data.py`, synthetic IoT sensor data (vibration and displacement) was generated. The script physically models:
- Thermal cycles
- Rain-induced slope creep (using the precipitation data)
- Blasting machinery noise
- Pre-failure and post-failure displacement curves for rockfall events.

### ⚠️ Data Reality & Simulation Assumptions

To ensure transparency for machine learning applications, it is critical to distinguish between real-world observations and synthetic engineering in this dataset:

**What is REAL:**
- **Terrain & Geometry:** Slope, aspect, ruggedness, and roughness are derived from real-world OpenTopography DEM data.
- **Weather:** Historical precipitation, temperature, and wind data are real meteorological records.

**What is SIMULATED (Synthetic):**
- **Sensor Readings:** Displacement and vibration values are synthetically generated using physical heuristics (e.g., sine waves for thermal cycles, lagged rainfall multipliers for creep).
- **Event Occurrence & Timing:** Rockfalls are artificially injected. 80% of events are constrained to occur during extreme rain events (top 5% of rainfall windows), with timestamps mathematically heavily weighted towards the absolute peak of the storm.
- **Event Physics:** The pre-failure displacement ramp is a mathematically scaled exponential curve, bounded by physical assumptions based on the rainfall intensity.
- **Event Distribution:** Event counts per location are randomized using a Poisson distribution (mean=5) to ensure natural variance, avoiding artificially uniform counts.

*Note: While event placement aggressively targets peak storm hours to model a "rainfall-triggered" causal chain, the event occurrences themselves are synthetically constructed, not empirical observations.*

### Step 4: Final Consolidation
Using `src/data/final_dataset.py`, the geospatial QGIS data, the historical weather data, and the synthetic sensor data are all merged into a single master dataset (`data/final_master_dataset.csv`).

## 📂 Repository Structure

```text
Rockfall_AI_Project/
├── src/
│   ├── data/
│   │   ├── get_weather_data.py       # Fetches historical weather data
│   │   ├── create_sensor_data.py     # Generates synthetic sensor data
│   │   └── final_dataset.py          # Merges all data into a master dataset
│   └── analysis/
│       ├── check.py                  # Validates the final dataset
│       └── plot_verification.py      # Plots timelines of rockfall events
├── data/                             # Generated datasets & QGIS exports
│   ├── geometry_dataset.csv          # Exported from QGIS (Slope, Ruggedness, etc.)
│   └── geometry_dataset.qmd          # QGIS metadata file
├── results/                          # Output visual plots and heatmaps
├── notebooks/                        # Exploratory Jupyter Notebooks
├── requirements.txt                  # Python dependencies
└── .gitignore
```

## 🚀 Setup & Execution

1. **Clone the repository:**
   ```bash
   git clone https://github.com/kaizen105/Rockfall_dataset.git
   cd Rockfall_dataset
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the Data Generation Pipeline (in order):**
   ```bash
   python src/data/get_weather_data.py
   python src/data/create_sensor_data.py
   python src/data/final_dataset.py
   ```

4. **Run the Analysis & Validation:**
   ```bash
   python src/analysis/check.py
   python src/analysis/plot_verification.py
   ```
   *Analysis scripts will automatically save validation metrics and plots to the `results/` folder.*

# Rockfall Dataset Generation and Analysis

[![Hugging Face Dataset](https://img.shields.io/badge/%F0%9F%A4%97%20Hugging%20Face-Dataset-blue)](https://huggingface.co/datasets/Kaizen696/noamundi-rockfall-simulation-dataset)

This repository contains a complete, physics-informed pipeline for creating, merging, and analyzing realistic synthetic rockfall event data. The core of this dataset is anchored in **real-world geospatial data**, which is then combined with historical weather conditions and simulated sensor readings. You can access the final generated dataset directly on Hugging Face using the link above.

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
- **Sensor Readings:** Synthetic sensor readings are anchored to the **Infinite Slope Stability Model** (Skempton & DeLory), a classic soil mechanics formula used as the simplified, single-point foundation for regional tools like SHALSTAB and TRIGRS.

#### The Physics Model (Infinite Slope Stability)
The simulation computes a time-series **Factor of Safety (FS)** for every location:
```math
FS = \frac{c + (\gamma \cdot z \cdot \cos^2\beta - u) \cdot \tan\phi}{\gamma \cdot z \cdot \sin\beta \cdot \cos\beta}
```
Where variables are assigned realistic geotechnical bounds for weathered rock/soil:
* $\beta$ = Slope angle ($26^\circ - 32^\circ$, mapped from DEM to prevent vertical QGIS artifacts)
* $\gamma$ = Unit weight of soil/rock ($20 - 25 \text{ kN/m}^3$)
* $z$ = Depth to failure plane ($1.0 - 2.0 \text{ m}$)
* $\phi$ = Friction angle ($30^\circ - 40^\circ$)
* $c$ = Cohesion ($4 - 10 \text{ kPa}$)
* $u$ = Pore water pressure, dynamically derived from a 72-hour rolling rainfall proxy ($h_w$).

When conditions are dry ($u=0$), the constants ensure the baseline FS hovers in a stable range of **1.5 – 2.5**. During severe rainfall, $u$ spikes, stripping away frictional resistance and driving the FS below the **1.0** failure threshold.

- **Event Occurrence & Timing:** Event probabilities dynamically scale using an exponential multiplier based on the calculated Factor of Safety. Rain-induced failures are deterministically biased towards periods where the slope physically yields ($FS \le 1.3$). The probability of a rockfall peaks exponentially as $FS \to 1.0$.
- **Event Physics:** 
  - **Pre-failure displacement** (tertiary creep) emerges naturally in the time-series as a physically modeled inverse function of the degrading FS (`creep ∝ 1 / (FS - 1.0)`). 
  - **Vibration spikes** are dynamically scaled based on a proxy for the failing mass and slope energy (`γ * z * sin(β)`), rather than arbitrary random injection. Steeper, deeper failures produce louder signatures.
- **Event Distribution:** Overall event counts per location are still probabilistically regulated via a Poisson distribution (mean=5) to maintain dataset usability and variability for classification models.

*Note: While the simulation uses the core Infinite Slope FS equation to model realistic precursor behavior, it is a simplified 1D approximation lacking rigorous 3D hydrological routing or spatial groundwater flow.*

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

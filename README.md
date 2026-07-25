# Rockfall Dataset Generation and Analysis

This repository contains a complete pipeline for generating, merging, and analyzing realistic synthetic rockfall event data. It creates a robust master dataset by combining static geographical features, historical weather conditions (via the Open-Meteo API), and realistically simulated sensor readings.

## 📂 Repository Structure

```text
Rockfall_AI_Project/
├── src/
│   ├── data/
│   │   ├── get_weather_data.py       # Fetches historical weather data
│   │   ├── create_sensor_data.py     # Generates synthetic sensor data based on physics
│   │   └── final_dataset.py          # Merges all data into a master dataset
│   └── analysis/
│       ├── check.py                  # Validates the final dataset
│       └── plot_verification.py      # Plots timelines of rockfall events
├── data/                             # Generated datasets (.csv)
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
   *Note: Analysis scripts will automatically save validation metrics and plots to the `results/` folder.*

## 📊 Features

- **Physics-Informed Simulations:** Generates thermal cycle displacements, rain-induced creep, and blasting vibrations.
- **API Integration:** Pulls accurate real-world historical daily weather.
- **Robust Consolidation:** Cleans and normalizes geographical coordinates for dashboard applications.

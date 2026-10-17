# Rebuilding Generator Inputs

This guide documents the procedures for regenerating upstream simulation inputs that are not tracked in Git due to file size constraints.

---

## 1. Rebuilding `data_v2/weather_dataset.csv`

The hourly meteorological dataset (`data_v2/weather_dataset.csv`) is **not tracked in Git** because its uncompressed size is approximately **870 MB** (870,377,944 bytes across 13,140,000 hourly rows). It is ignored by Git via the rule `data_v2/*` in `.gitignore`.

### Generation Details
- **Generating Script**: [`src/data/get_weather_data.py`](file:///c:/Rockfall_AI_Project/src/data/get_weather_data.py)
- **Data Source**: Open-Meteo Historical Archive API (`https://archive-api.open-meteo.com/v1/archive`). No API key or authentication is required.
- **Date Range**: `2021-01-01 00:00:00` to `2023-12-31 23:00:00` (3 continuous years, 26,280 hours per location).
- **Spatial Resolution & Clustering**: The 500 monitoring locations from [`data_v2/geometry_dataset_500.csv`](file:///c:/Rockfall_AI_Project/data_v2/geometry_dataset_500.csv) are clustered into 25 macro-regional centroids using $k$-means spatial clustering.
- **Microclimate Downscaling**: The script applies physics-informed downscaling to translate centroid hourly weather to each specific location:
  1. *Temperature Lapse Rate*: $-0.0065^\circ\text{C}$ per meter of elevation difference from centroid.
  2. *Orographic Precipitation*: Wind-slope aspect interaction assuming $270^\circ$ prevailing westerly winds.
  3. *Solar Radiation*: Aspect-slope trigonometric shading modulation.
- **Output Destination**: `data_v2/weather_dataset.csv` (~870 MB).

### Command to Rebuild
To rebuild `weather_dataset.csv` from scratch:
```bash
python src/data/get_weather_data.py
```
*Note: The download and downscaling process takes approximately 2–5 minutes depending on network latency to the Open-Meteo API.*

---

## 2. Tracked Upstream Geometrical Inputs

Unlike `weather_dataset.csv`, the following small generator input files **are tracked in Git** on branch `cleanup-v1d`:
- [`data_v2/geometry_dataset_500.csv`](file:///c:/Rockfall_AI_Project/data_v2/geometry_dataset_500.csv) (81 KB, 500 rows): Initial coordinates and DEM slope/elevation attributes for the 500 locations.
- [`data_v2/spatial_metadata.csv`](file:///c:/Rockfall_AI_Project/data_v2/spatial_metadata.csv) (66 KB, 500 rows): Full static topographic, curvature, and trajectory parameters.
- [`qgis_raw_data/`](file:///c:/Rockfall_AI_Project/qgis_raw_data/) (small GIS masks and shapefiles, under 5 MB total).

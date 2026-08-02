import pandas as pd
import numpy as np
import rasterio
from pyproj import Transformer
import os

def fix_curvature():
    print("--- 1. Computing curvature from DEM ---")
    dem_path = r"c:\Rockfall_AI_Project\data_v2\rasters\dem_reprojected_utm45n.tif"
    with rasterio.open(dem_path) as src:
        dem = src.read(1).astype(float)
        transform = src.transform
        nodata = src.nodata
        crs = src.crs

    if nodata is not None:
        dem[dem == nodata] = np.nan

    # Cell sizes (resolution)
    cell_x = transform[0]
    cell_y = -transform[4] 

    # Zevenbergen & Thorne (1987)
    Z5 = dem[1:-1, 1:-1]
    Z1 = dem[0:-2, 0:-2]
    Z2 = dem[0:-2, 1:-1]
    Z3 = dem[0:-2, 2:]
    Z4 = dem[1:-1, 0:-2]
    Z6 = dem[1:-1, 2:]
    Z7 = dem[2:, 0:-2]
    Z8 = dem[2:, 1:-1]
    Z9 = dem[2:, 2:]

    L = cell_x  
    D = ((Z4 + Z6) / 2 - Z5) / (L**2)
    E = ((Z2 + Z8) / 2 - Z5) / (L**2)
    F = (-Z1 + Z3 + Z7 - Z9) / (4 * L**2)
    G = (-Z4 + Z6) / (2 * L)
    H = (Z2 - Z8) / (2 * L)

    profile_curv = np.zeros_like(dem)
    planform_curv = np.zeros_like(dem)

    mask = (G**2 + H**2) > 0
    G2_H2 = G[mask]**2 + H[mask]**2

    # Profile Curvature
    profile_curv[1:-1, 1:-1][mask] = -2 * (D[mask]*G[mask]**2 + E[mask]*H[mask]**2 + F[mask]*G[mask]*H[mask]) / G2_H2

    # Planform Curvature
    planform_curv[1:-1, 1:-1][mask] = 2 * (D[mask]*H[mask]**2 + E[mask]*G[mask]**2 - F[mask]*G[mask]*H[mask]) / G2_H2

    print("--- 2. Reprojecting coordinates and sampling ---")
    spatial_path = r"c:\Rockfall_AI_Project\data_v2\spatial_metadata.csv"
    df_spatial = pd.read_csv(spatial_path)

    transformer = Transformer.from_crs("EPSG:4326", crs, always_xy=True) 
    utm_coords = [transformer.transform(x, y) for x, y in zip(df_spatial['X'], df_spatial['Y'])]

    profile_vals = []
    planform_vals = []
    for x, y in utm_coords:
        col, row = ~transform * (x, y)
        r = int(np.clip(int(row), 0, profile_curv.shape[0]-1))
        c = int(np.clip(int(col), 0, profile_curv.shape[1]-1))
        profile_vals.append(profile_curv[r, c])
        planform_vals.append(planform_curv[r, c])

    df_spatial['profile_curvature'] = profile_vals
    df_spatial['planform_curvature'] = planform_vals
    df_spatial.to_csv(spatial_path, index=False)

    print("--- 3. Updating geometry_dataset_500.csv ---")
    geom_path = r"c:\Rockfall_AI_Project\data_v2\geometry_dataset_500.csv"
    df_geom = pd.read_csv(geom_path)
    if 'Location_ID' in df_geom.columns:
        mapping_prof = dict(zip(df_spatial['Location_ID'], df_spatial['profile_curvature']))
        mapping_plan = dict(zip(df_spatial['Location_ID'], df_spatial['planform_curvature']))
        df_geom['profile_curvature'] = df_geom['Location_ID'].map(mapping_prof)
        df_geom['planform_curvature'] = df_geom['Location_ID'].map(mapping_plan)
    else:
        df_geom['profile_curvature'] = profile_vals
        df_geom['planform_curvature'] = planform_vals
    df_geom.to_csv(geom_path, index=False)

    print("--- 4. Updating final_master_dataset.csv (chunked) ---")
    master_path = r"c:\Rockfall_AI_Project\data_v2\final_master_dataset.csv"
    mapping_prof = dict(zip(df_spatial['Location_ID'], df_spatial['profile_curvature']))
    mapping_plan = dict(zip(df_spatial['Location_ID'], df_spatial['planform_curvature']))

    chunksize = 1_000_000
    temp_path = master_path + ".tmp"
    first = True
    total_rows = 0
    for chunk in pd.read_csv(master_path, chunksize=chunksize):
        chunk['profile_curvature'] = chunk['Location_ID'].map(mapping_prof)
        chunk['planform_curvature'] = chunk['Location_ID'].map(mapping_plan)
        chunk.to_csv(temp_path, mode='w' if first else 'a', index=False, header=first)
        first = False
        total_rows += len(chunk)
        print(f"Processed {total_rows} rows...")

    os.replace(temp_path, master_path)
    
    # Let's print out the required proofs!
    print("FINISHED SCRIPT. PRINTING REQUIRED PROOFS:")
    
    print("\n[ITEM 3 PROOF]")
    print(df_spatial['profile_curvature'].nunique())
    print(df_spatial['planform_curvature'].nunique())
    print(df_spatial['profile_curvature'].describe())
    print(df_spatial['planform_curvature'].describe())
    print(df_spatial[['Location_ID', 'profile_curvature', 'planform_curvature']].sample(10, random_state=42))

if __name__ == '__main__':
    fix_curvature()

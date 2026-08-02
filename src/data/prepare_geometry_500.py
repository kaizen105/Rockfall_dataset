import pandas as pd
import os

def main():
    print("Loading raw QGIS exported geometry points (with real elevations)...")
    df = pd.read_csv("final_points_500_full_elev.csv")
    print(f"Original file contains {len(df)} rows.")

    # Drop any rows with NaN values (we only want clean data)
    df_clean = df.dropna().copy()
    print(f"Found {len(df_clean)} fully populated rows.")

    # Sample exactly 500 points randomly for the pipeline run
    df_sampled = df_clean.sample(n=500, random_state=42).reset_index(drop=True)
    
    # Save the prepared geometry dataset to data_v2
    out_path = "data_v2/geometry_dataset_500.csv"
    os.makedirs("data_v2", exist_ok=True)
    df_sampled.to_csv(out_path, index=False)
    
    print(f"\nSuccessfully saved {len(df_sampled)} highly realistic steep-slope points to {out_path}.")
    print("Elevation Statistics of final 500:")
    print(df_sampled["elev_1"].describe())
    print("\nSlope Statistics of final 500:")
    print(df_sampled["slope_1"].describe())

if __name__ == "__main__":
    main()

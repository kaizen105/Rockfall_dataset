import pandas as pd
import os

def main():
    input_path = "data_v2/final_master_dataset.csv"
    output_path = "data_v2/training_dataset.csv"
    
    print(f"Loading final master dataset from {input_path}...")
    # Read the full dataset
    df = pd.read_csv(input_path)
    print(f"Loaded {len(df)} rows.")

    # 1. Drop geographic artifacts to prevent geographic memorization
    junk_cols = ['X', 'Y', 'rand_point', 'fid', 'DN']
    cols_to_drop = [c for c in junk_cols if c in df.columns]
    if cols_to_drop:
        print(f"Dropping geographic artifacts: {cols_to_drop}")
        df = df.drop(columns=cols_to_drop)

    # 2. Mask out 72-hour post-event leakage
    print("Identifying 72-hour post-event target leakage windows...")
    
    # Create a boolean series where events are True, everything else is NA
    is_event = (df['Rockfall_Event'] == 1)
    df['Leakage_Mask'] = is_event.replace(False, pd.NA)

    # Forward fill the True values up to 72 hours (rows) per location
    print("Applying 72-hour forward mask per location...")
    df['Leakage_Mask'] = df.groupby('Location_ID')['Leakage_Mask'].ffill(limit=72)
    
    # Fill remaining NaNs with False
    df['Leakage_Mask'] = df['Leakage_Mask'].fillna(False)
    
    # The event row itself should be kept for training! It's only the 72 hours *after* it that are contaminated.
    # So we remove the actual event rows from the mask.
    df['Leakage_Mask'] = df['Leakage_Mask'] & ~is_event

    num_leakage_rows = df['Leakage_Mask'].sum()
    print(f"Found {num_leakage_rows} target leakage rows to drop.")

    # 3. Filter and save
    df_clean = df[~df['Leakage_Mask']].drop(columns=['Leakage_Mask'])
    print(f"Cleaned dataset size: {len(df_clean)} rows.")

    print(f"Saving to {output_path}...")
    df_clean.to_csv(output_path, index=False)
    print("Successfully created the clean, leakage-free training dataset!")

if __name__ == "__main__":
    main()

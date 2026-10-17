"""
Training Dataset Preparation Module.

Updates in V1:
- Retains all rows and continuous timestamps (no row deletion).
- Ensures 'post_event_window' column is present (int8) for training exclusion/masking.
- Drops geographic artifacts ['X', 'Y', 'rand_point', 'fid', 'DN'].
- Downcasts dtypes (float32 / int8 / category).
- Reads and writes in chunks to maintain low memory footprint.
"""

import os
import argparse
import pandas as pd

def process_training_dataset(input_path: str = "data/current/v1d_s1/final_master_dataset.csv",
                             output_path: str = "data/current/v1d_s1/training_dataset.csv") -> None:
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input master dataset not found: {input_path}")

    print(f"Loading master dataset from '{input_path}'...")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    if os.path.exists(output_path):
        os.remove(output_path)

    chunksize = 1_000_000
    first_chunk = True
    total_rows = 0
    post_event_rows = 0

    junk_cols = ['X', 'Y', 'rand_point', 'fid', 'DN']

    for chunk in pd.read_csv(input_path, chunksize=chunksize):
        # 1. Drop geographic artifacts if present
        cols_to_drop = [c for c in junk_cols if c in chunk.columns]
        if cols_to_drop:
            chunk = chunk.drop(columns=cols_to_drop)

        # 2. Check post_event_window presence
        if "post_event_window" not in chunk.columns:
            raise ValueError("Required column 'post_event_window' is missing from master dataset!")

        post_event_rows += int(chunk["post_event_window"].sum())

        # 3. Downcast dtypes
        for col in chunk.select_dtypes(include=["float64"]).columns:
            chunk[col] = chunk[col].astype("float32")
        for col in ["Rockfall_Event", "post_event_window"]:
            if col in chunk.columns:
                chunk[col] = chunk[col].astype("int8")
        if "Location_ID" in chunk.columns:
            chunk["Location_ID"] = chunk["Location_ID"].astype("category")

        # 4. Stream to disk (preserving all rows)
        mode = 'w' if first_chunk else 'a'
        chunk.to_csv(output_path, mode=mode, index=False, header=first_chunk)
        first_chunk = False
        total_rows += len(chunk)

    print(f"Successfully created clean training dataset: '{output_path}'")
    print(f"Total rows: {total_rows:,} (all rows preserved; post-event window rows: {post_event_rows:,}).")

def main():
    parser = argparse.ArgumentParser(description="Create Training Dataset with preserved contiguity")
    parser.add_argument("--input-path", type=str, default="data/current/v1d_s1/final_master_dataset.csv", help="Input master dataset path")
    parser.add_argument("--output-path", type=str, default="data/current/v1d_s1/training_dataset.csv", help="Output training dataset path")
    args = parser.parse_args()

    process_training_dataset(input_path=args.input_path, output_path=args.output_path)

if __name__ == "__main__":
    main()

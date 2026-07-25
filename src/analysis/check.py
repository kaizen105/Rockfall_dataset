"""
Dataset Validation and Basic Analysis Script.

This module loads the final merged dataset and performs basic
integrity checks, including identifying missing values, duplicates,
and generating correlation heatmaps.
"""

import os
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

# --- Configuration ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(BASE_DIR, "data")
RESULTS_DIR = os.path.join(BASE_DIR, "results")
os.makedirs(RESULTS_DIR, exist_ok=True)
FILE_PATH = os.path.join(DATA_DIR, "final_master_dataset.csv")

def validate_dataset() -> None:
    """Validates the structure and content of the final master dataset."""
    if not os.path.exists(FILE_PATH):
        print(f"[ERROR] Dataset not found at {FILE_PATH}. Please generate it first.")
        return

    # Load dataset
    df = pd.read_csv(FILE_PATH)

    print("\n===== 1. Basic Info =====")
    print(df.info())
    print("\nFirst 5 rows:\n", df.head())
    print("\nSummary statistics:\n", df.describe())

    print("\n===== 2. Missing Values =====")
    missing = df.isnull().sum()
    print(missing)
    if missing.sum() == 0:
        print("No missing values [OK]")
    else:
        print("Missing values found [WARNING]")

    print("\n===== 3. Duplicates =====")
    dup_count = df.duplicated().sum()
    print(f"Duplicate rows: {dup_count}")
    if dup_count == 0:
        print("No duplicates [OK]")

    print("\n===== 4. Column Types =====")
    print(df.dtypes)

    # Convert likely categorical columns
    cat_cols = ["Location_ID", "Rockfall_Event"]
    for col in cat_cols:
        if col in df.columns:
            df[col] = df[col].astype("category")

    print("\nAfter conversion:")
    print(df.dtypes)

    print("\n===== 5. Categorical Value Check =====")
    for col in cat_cols:
        if col in df.columns:
            print(f"{col} unique values: {df[col].unique()}")

    print("\n===== 6. Numeric Range Checks =====")
    numeric_cols = df.select_dtypes(include=["float64", "int64"]).columns.tolist()
    for col in numeric_cols:
        print(f"{col}: min={df[col].min()}, max={df[col].max()}")

    print("\n===== 7. Correlation Heatmap =====")
    num_df = df[numeric_cols]  # select only numeric columns
    plt.figure(figsize=(12, 8))
    sns.heatmap(num_df.corr(), annot=True, cmap="coolwarm")
    plt.title("Feature Correlation")
    heatmap_path = os.path.join(RESULTS_DIR, "correlation_heatmap.png")
    plt.savefig(heatmap_path)
    print(f"Heatmap saved to {heatmap_path}")
    plt.close()

    print("\n===== 8. Optional: Distribution Plots =====")
    # Plot only first 10 numeric columns to save time on large dataset
    for col in numeric_cols[:10]:
        plt.figure()
        sns.histplot(df[col], kde=True, bins=50)
        plt.title(f"Distribution of {col}")
        dist_path = os.path.join(RESULTS_DIR, f"dist_{col}.png")
        plt.savefig(dist_path)
        plt.close()
        print(f"Distribution plot saved to {dist_path}")

    print("\n[OK] Dataset validation complete.")

if __name__ == "__main__":
    validate_dataset()

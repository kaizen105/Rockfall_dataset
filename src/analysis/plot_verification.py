"""
Plot Verification Script.

This module plots a timeline of a rockfall event for a specific location
(LOC_1). It visualizes rainfall, displacement rate, and vibration over time.
"""

import os
import pandas as pd
import matplotlib.pyplot as plt

# --- Configuration ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(BASE_DIR, "data")
RESULTS_DIR = os.path.join(BASE_DIR, "results")
os.makedirs(RESULTS_DIR, exist_ok=True)

FILE_PATH = os.path.join(DATA_DIR, "final_master_dataset.csv")
OUTPUT_PLOT = os.path.join(RESULTS_DIR, "validation_plot.png")

def create_verification_plot() -> None:
    """Creates a verification plot for a rockfall event at LOC_1."""
    if not os.path.exists(FILE_PATH):
        print(f"[ERROR] Dataset not found at {FILE_PATH}. Please generate it first.")
        return

    df = pd.read_csv(FILE_PATH, parse_dates=["Timestamp"])

    # Find LOC_1
    df_loc1 = df[df["Location_ID"] == "LOC_1"].copy()
    df_loc1.set_index("Timestamp", inplace=True)

    # Find the first rockfall event
    event_times = df_loc1[df_loc1["Rockfall_Event"] == 1].index
    if not event_times.empty:
        first_event = event_times[0]
        
        # Plot 7 days before and 3 days after
        start_time = first_event - pd.Timedelta(days=7)
        end_time = first_event + pd.Timedelta(days=3)
        
        plot_df = df_loc1.loc[start_time:end_time]
        
        fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(12, 10), sharex=True)
        
        # Plot Rainfall
        ax1.bar(plot_df.index, plot_df["precipitation_sum"], color="blue", alpha=0.5, label="Daily Rain (mm)")
        ax1.set_ylabel("Rainfall (mm)")
        ax1.legend(loc="upper left")
        
        # Plot Displacement
        ax2.plot(plot_df.index, plot_df["Displacement_Rate_mm_h"], color="red", label="Displacement (mm/h)")
        ax2.axvline(first_event, color="black", linestyle="--", label="Rockfall Event")
        ax2.set_ylabel("Displacement Rate")
        ax2.legend(loc="upper left")
        
        # Plot Vibration
        ax3.plot(plot_df.index, plot_df["Vibration_mm_s"], color="green", label="Vibration (mm/s)", alpha=0.7)
        ax3.axvline(first_event, color="black", linestyle="--")
        ax3.set_ylabel("Vibration")
        ax3.legend(loc="upper left")
        
        plt.tight_layout()
        plt.savefig(OUTPUT_PLOT)
        print(f"Plot saved to {OUTPUT_PLOT}")
    else:
        print("No events found for LOC_1")

if __name__ == "__main__":
    create_verification_plot()

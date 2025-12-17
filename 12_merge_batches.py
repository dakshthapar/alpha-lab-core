import glob
import os

import polars as pl

DATA_DIR = "data/training_batches"
OUTPUT_FILE = "data/TRAIN_FULL.parquet"


def merge_data():
    print(f"--- MERGING BATCHES FROM {DATA_DIR} (MEMORY-EFFICIENT MODE) ---")

    # 1. Find all parquet files
    files = sorted(glob.glob(f"{DATA_DIR}/*.parquet"))
    print(f"Found {len(files)} day-files.")

    if len(files) == 0:
        print("CRITICAL: No files found. Did you run mass production?")
        return
        
    # --- REGIME REPORTING ---
    regime_counts = {}
    for f in files:
        # Expected format: sim_day_ID_REGIME.parquet
        # Fallback for old files: sim_day_ID.parquet
        try:
            parts = os.path.basename(f).replace(".parquet", "").split("_")
            if len(parts) >= 4:
                regime = parts[3]  # sim, day, id, REGIME
            else:
                regime = "LEGACY"
            regime_counts[regime] = regime_counts.get(regime, 0) + 1
        except:
            pass
            
    print("\n--- REGIME DISTRIBUTION ---")
    for r, c in regime_counts.items():
        print(f"{r}: {c} days")
    print("---------------------------\n")

    # 2. Use Polars streaming engine to process without loading into RAM
    print("Merging with streaming engine (memory-efficient)...")
    
    # Polars can handle this efficiently with streaming mode
    # This processes data in chunks internally without loading everything
    lf = pl.scan_parquet(f"{DATA_DIR}/*.parquet")
    
    # Use sink_parquet for streaming write (never loads full data into RAM)
    print("Writing to output file (streaming mode)...")
    lf.sink_parquet(OUTPUT_FILE)
    
    # Get stats without loading full data
    print("\n--- FINAL DATASET STATS ---")
    final_lf = pl.scan_parquet(OUTPUT_FILE)
    row_count = final_lf.select(pl.len()).collect().item()
    
    print(f"Total Rows: {row_count:,}")
    print(f"Columns: {len(final_lf.columns)}")
    print(f"Saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    merge_data()

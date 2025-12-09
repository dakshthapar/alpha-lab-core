import glob

import polars as pl

DATA_DIR = "data/training_batches"
OUTPUT_FILE = "data/TRAIN_FULL.parquet"


def merge_data():
    print(f"--- MERGING BATCHES FROM {DATA_DIR} ---")

    # 1. Find all parquet files
    files = glob.glob(f"{DATA_DIR}/*.parquet")
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
                regime = parts[3] # sim, day, id, REGIME
            else:
                regime = "LEGACY"
            regime_counts[regime] = regime_counts.get(regime, 0) + 1
        except:
            pass
            
    print("\n--- REGIME DISTRIBUTION ---")
    for r, c in regime_counts.items():
        print(f"{r}: {c} days")
    print("---------------------------\n")

    # 2. Lazy Load & Concatenate
    # Polars scans them all instantly without loading into RAM
    lf = pl.scan_parquet(f"{DATA_DIR}/*.parquet")

    # 3. Sort by Timestamp (Optional, but good for sequential training)
    # Since simulated days are independent, sorting by day/time helps if we add a 'day_id' later.
    # For now, we just ensure data integrity.

    print("Collecting and merging...")
    df = lf.collect()

    print("--- FINAL DATASET STATS ---")
    print(f"Total Rows: {df.height}")
    print(f"Columns: {len(df.columns)}")

    # 4. Save
    df.write_parquet(OUTPUT_FILE)
    print(f"Saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    merge_data()

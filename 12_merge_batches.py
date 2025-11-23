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

import glob
import os

import polars as pl

# Configuration
DATA_DIR = "data/training_batches"
OUTPUT_FILE = "data/TEST_OOD.parquet"

# OOD data starts from seed 20000 (day IDs >= 20000)
OOD_START_ID = 20000


def merge_ood_data():
    print("=" * 80)
    print("OUT-OF-DISTRIBUTION TEST DATA MERGE")
    print("=" * 80)
    
    # 1. Find all parquet files
    all_files = sorted(glob.glob(f"{DATA_DIR}/*.parquet"))
    print(f"\n📁 Found {len(all_files)} total batch files in {DATA_DIR}/")
    
    # 2. Filter for OOD files (day_id >= 20000)
    ood_files = []
    for f in all_files:
        try:
            basename = os.path.basename(f)
            # Expected format: sim_day_ID_REGIME.parquet
            parts = basename.replace(".parquet", "").split("_")
            if len(parts) >= 3:
                day_id = int(parts[2])  # sim, day, ID
                if day_id >= OOD_START_ID:
                    ood_files.append(f)
        except Exception as e:
            # Skip files that don't match expected format
            pass
    
    print(f"🔍 Filtered to {len(ood_files)} OOD files (day_id >= {OOD_START_ID})")
    
    if len(ood_files) == 0:
        print("❌ CRITICAL: No OOD files found!")
        print(f"   Expected files with day_id >= {OOD_START_ID}")
        print(f"   Did you run: python 14_launch_parallel.py --start-seed {OOD_START_ID} ?")
        return
    
    # 3. Display regime distribution
    from collections import defaultdict
    regime_counts = defaultdict(int)
    
    for f in ood_files:
        try:
            basename = os.path.basename(f)
            parts = basename.replace(".parquet", "").split("_")
            if len(parts) >= 4:
                regime = parts[3]  # sim, day, id, REGIME
            else:
                regime = "LEGACY"
            regime_counts[regime] += 1
        except:
            pass
    
    print("\n" + "=" * 80)
    print("OOD REGIME DISTRIBUTION")
    print("=" * 80)
    for regime, count in sorted(regime_counts.items()):
        print(f"  {regime:12s}: {count:5d} days")
    print("=" * 80)
    
    # 4. Merge using streaming mode
    print(f"\n📦 Merging {len(ood_files)} OOD files...")
    print(f"   Output: {OUTPUT_FILE}")
    print("   Using streaming mode (memory-efficient)...")
    
    lf = pl.scan_parquet(ood_files)
    lf.sink_parquet(OUTPUT_FILE)
    
    # 5. Get stats without loading full data
    print("\n" + "=" * 80)
    print("FINAL OOD DATASET STATS")
    print("=" * 80)
    
    final_lf = pl.scan_parquet(OUTPUT_FILE)
    row_count = final_lf.select(pl.len()).collect().item()
    file_size_mb = os.path.getsize(OUTPUT_FILE) / (1024 * 1024)
    
    print(f"  File: {OUTPUT_FILE}")
    print(f"  Rows: {row_count:,}")
    print(f"  Columns: {len(final_lf.collect_schema().names())}")
    print(f"  Size: {file_size_mb:.2f} MB")
    print("=" * 80)
    
    print("\n✅ OOD TEST DATA MERGE COMPLETE!")
    print("\n📝 Usage:")
    print("   This is your 'robustness test' dataset with fresh market trajectories.")
    print("   Use it to verify your model didn't just memorize specific order flows.")
    print()


if __name__ == "__main__":
    merge_ood_data()

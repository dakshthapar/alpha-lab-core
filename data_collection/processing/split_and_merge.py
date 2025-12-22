import glob
import os
import random
from collections import defaultdict

import polars as pl

# Configuration
DATA_DIR = "data/training_batches"
OUTPUT_DIR = "data"

# Split ratios
TRAIN_RATIO = 0.70
VAL_RATIO = 0.15
TEST_RATIO = 0.15

# Random seed for reproducibility
RANDOM_SEED = 42


def split_and_merge():
    print("=" * 80)
    print("STRATIFIED REGIME SPLIT & MERGE")
    print("=" * 80)
    
    # 1. Find all parquet files
    files = sorted(glob.glob(f"{DATA_DIR}/*.parquet"))
    print(f"\n📁 Found {len(files)} batch files in {DATA_DIR}/")
    
    if len(files) == 0:
        print("❌ CRITICAL: No files found. Run simulation first!")
        return
    
    # 2. Group files by regime
    print("\n📊 Grouping files by regime...")
    regime_files = defaultdict(list)
    
    for f in files:
        # Expected format: sim_day_ID_REGIME.parquet
        # Fallback for old files: sim_day_ID.parquet
        try:
            basename = os.path.basename(f)
            parts = basename.replace(".parquet", "").split("_")
            if len(parts) >= 4:
                regime = parts[3]  # sim, day, id, REGIME
            else:
                regime = "LEGACY"
            regime_files[regime].append(f)
        except Exception as e:
            print(f"⚠️  Warning: Could not parse {basename}: {e}")
            regime_files["UNKNOWN"].append(f)
    
    # 3. Display regime distribution
    print("\n" + "=" * 80)
    print("REGIME DISTRIBUTION")
    print("=" * 80)
    total_files = 0
    for regime, files_list in sorted(regime_files.items()):
        print(f"  {regime:12s}: {len(files_list):5d} days")
        total_files += len(files_list)
    print(f"  {'TOTAL':12s}: {total_files:5d} days")
    print("=" * 80)
    
    # 4. Stratified split within each regime
    print("\n🎲 Performing stratified split (seed={})...".format(RANDOM_SEED))
    random.seed(RANDOM_SEED)
    
    train_files = []
    val_files = []
    test_files = []
    
    for regime, files_list in regime_files.items():
        # Shuffle files within this regime
        shuffled = files_list.copy()
        random.shuffle(shuffled)
        
        # Calculate split indices
        n = len(shuffled)
        train_end = int(n * TRAIN_RATIO)
        val_end = int(n * (TRAIN_RATIO + VAL_RATIO))
        
        # Split
        regime_train = shuffled[:train_end]
        regime_val = shuffled[train_end:val_end]
        regime_test = shuffled[val_end:]
        
        train_files.extend(regime_train)
        val_files.extend(regime_val)
        test_files.extend(regime_test)
        
        print(f"  {regime:12s}: {len(regime_train):4d} train | {len(regime_val):4d} val | {len(regime_test):4d} test")
    
    print("\n" + "=" * 80)
    print(f"  {'TOTAL':12s}: {len(train_files):4d} train | {len(val_files):4d} val | {len(test_files):4d} test")
    print("=" * 80)
    
    # 5. Validate splits
    assert len(train_files) + len(val_files) + len(test_files) == total_files, "Split doesn't add up!"
    assert len(set(train_files) & set(val_files)) == 0, "Train/Val overlap!"
    assert len(set(train_files) & set(test_files)) == 0, "Train/Test overlap!"
    assert len(set(val_files) & set(test_files)) == 0, "Val/Test overlap!"
    print("✅ Split validation passed (no overlaps)")
    
    # 6. Merge each split using streaming mode
    splits = {
        "TRAIN": train_files,
        "VAL": val_files,
        "TEST": test_files
    }
    
    print("\n" + "=" * 80)
    print("MERGING SPLITS (Streaming Mode)")
    print("=" * 80)
    
    for split_name, split_files in splits.items():
        if len(split_files) == 0:
            print(f"\n⚠️  {split_name}: No files to merge, skipping...")
            continue
        
        output_file = f"{OUTPUT_DIR}/{split_name}.parquet"
        print(f"\n📦 {split_name}: Merging {len(split_files)} files...")
        print(f"   Output: {output_file}")
        
        # Use Polars streaming engine
        lf = pl.scan_parquet(split_files)
        lf.sink_parquet(output_file)
        
        # Get stats without loading full data
        final_lf = pl.scan_parquet(output_file)
        row_count = final_lf.select(pl.len()).collect().item()
        
        print(f"   ✅ {split_name}: {row_count:,} rows | {len(final_lf.columns)} columns")
    
    # 7. Final summary
    print("\n" + "=" * 80)
    print("FINAL DATASET SUMMARY")
    print("=" * 80)
    
    for split_name in ["TRAIN", "VAL", "TEST"]:
        output_file = f"{OUTPUT_DIR}/{split_name}.parquet"
        if os.path.exists(output_file):
            size_mb = os.path.getsize(output_file) / (1024 * 1024)
            lf = pl.scan_parquet(output_file)
            rows = lf.select(pl.len()).collect().item()
            print(f"  {split_name:5s}.parquet: {rows:10,d} rows | {size_mb:8.2f} MB")
    
    print("=" * 80)
    print("✅ SPLIT AND MERGE COMPLETE!")
    print("=" * 80)
    
    print("\n📝 Next steps:")
    print("  1. Verify data quality: python 9_validate_data_quality.py")
    print("  2. Train your model on TRAIN.parquet")
    print("  3. Tune hyperparameters using VAL.parquet")
    print("  4. Final evaluation on TEST.parquet")
    print()


if __name__ == "__main__":
    split_and_merge()

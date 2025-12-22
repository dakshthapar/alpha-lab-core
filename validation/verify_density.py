import os
import sys

import polars as pl

# --- CONFIG ---
# This must match the OUTPUT of Script 6 (The Parser)
# If you changed Script 6 to save as "train.parquet", change this line.
if len(sys.argv) > 1:
    INPUT_FILE = sys.argv[1]
else:
    INPUT_FILE = "data/final_training_data.parquet"


def print_lob_snapshot(row):
    """
    Pretty prints a single row of the Limit Order Book
    """
    print(f"\n--- ORDER BOOK SNAPSHOT (Time: {row['timestamp']}) ---")
    print(f"{'BID VOL':<10} | {'BID PRICE':<10} || {'ASK PRICE':<10} | {'ASK VOL':<10}")
    print("-" * 46)

    # Print Levels 1 to 5
    for i in range(1, 6):
        bid_p = row[f"bid_px_{i}"]
        bid_v = row[f"bid_qty_{i}"]
        ask_p = row[f"ask_px_{i}"]
        ask_v = row[f"ask_qty_{i}"]

        # Highlight Level 1
        prefix = ">>" if i == 1 else "  "
        print(f"{bid_v:<10} | {bid_p:<10.2f} {prefix} {ask_p:<10.2f} | {ask_v:<10}")


def verify_density():
    if not os.path.exists(INPUT_FILE):
        print(f"CRITICAL: Could not find {INPUT_FILE}")
        print("Did you run '6_process_depth.py' first?")
        sys.exit(1)

    print(f"--- INSPECTING: {INPUT_FILE} ---")
    df = pl.read_parquet(INPUT_FILE)

    total_rows = df.height
    print(f"Total Snapshots: {total_rows}")

    # 1. CHECK FOR WARMUP (Zeros)
    # We define a "Valid" row as one where Level 1 Bids are non-zero
    valid_df = df.filter(pl.col("bid_px_1") > 0)
    warmup_rows = total_rows - valid_df.height

    print(f"Warm-up Rows (Empty): {warmup_rows}")
    print(
        f"Valid Trading Rows:   {valid_df.height}  ({(valid_df.height / total_rows) * 100:.1f}%)"
    )

    if valid_df.height == 0:
        print("\n❌ FAILURE: The order book is completely empty.")
        print("Check your simulation config. Are Value Agents added?")
        sys.exit(1)

    # 2. CHECK FOR "DENSITY" (Level 5)
    # Do we have liquidity deep in the book?
    dense_df = valid_df.filter(pl.col("bid_qty_5") > 0)
    density_pct = (dense_df.height / valid_df.height) * 100

    print("\n--- DENSITY CHECK ---")
    print(f"Rows with Level 5 Data: {dense_df.height} ({density_pct:.1f}%)")

    if density_pct < 50:
        print("⚠️  WARNING: Book is thin. Less than 50% of rows have Level 5 data.")
    else:
        print("✅  SUCCESS: Book is Dense (Value Agents are working).")

    # 3. VISUALIZE SNAPSHOT
    # Pick the middle row of the valid data to show a representative state
    mid_idx = valid_df.height // 2
    snapshot = valid_df.row(mid_idx, named=True)

    print_lob_snapshot(snapshot)

    # 4. STATS
    mid_price_std = valid_df["mid_price"].std()
    print(f"\nMid-Price Volatility (StdDev): {mid_price_std:.4f}")


if __name__ == "__main__":
    verify_density()

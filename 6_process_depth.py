import ast

import polars as pl
from tqdm import tqdm

# --- CONFIG ---
INPUT_FILE = "data/synthetic_factory_data.parquet"
OUTPUT_FILE = "data/final_training_data.parquet"
DEPTH_LEVELS = 5


def parse_depth_string(depth_str):
    """
    Converts string "[(24000, 10), (23999, 5)]" -> List of Tuples
    """
    try:
        if not depth_str or depth_str == "[]":
            return []
        return ast.literal_eval(depth_str)
    except:
        return []


def process_abides_data():
    print(f"--- LOADING RAW DATA: {INPUT_FILE} ---")
    df = pl.read_parquet(INPUT_FILE)

    # 1. Filter for Depth Events only and convert to Pandas for iteration
    # (Iterating complex strings is often cleaner in pure Python/Pandas than Polars exprs)
    mask = (pl.col("EventType") == "BID_DEPTH") | (pl.col("EventType") == "ASK_DEPTH")
    df_depth = df.filter(mask).filter(pl.col("EventTime") > 0).to_pandas()

    print(f"--- PARSING {len(df_depth)} DEPTH SNAPSHOTS ---")

    processed_rows = []

    # We maintain the "Current State" of the book
    # Because Bids and Asks update asynchronously
    current_state = {"timestamp": 0, "symbol": "NIFTY_SIM"}
    # Initialize empty columns
    for i in range(1, DEPTH_LEVELS + 1):
        current_state[f"bid_px_{i}"] = 0.0
        current_state[f"bid_qty_{i}"] = 0
        current_state[f"ask_px_{i}"] = 0.0
        current_state[f"ask_qty_{i}"] = 0

    # 2. Iterate and Update State
    for _, row in tqdm(df_depth.iterrows(), total=len(df_depth)):
        ts = row["EventTime"]
        evt_type = row["EventType"]
        raw_val = row["ScalarEventValue"]

        # Parse the list of tuples: [(Price, Vol), ...]
        levels = parse_depth_string(raw_val)

        # Update Timestamp
        current_state["timestamp"] = ts

        if evt_type == "BID_DEPTH":
            # Bids: High Price is Top (Already sorted by ABIDES usually, but safety sort)
            levels.sort(key=lambda x: x[0], reverse=True)

            for i in range(DEPTH_LEVELS):
                if i < len(levels):
                    current_state[f"bid_px_{i + 1}"] = float(levels[i][0])
                    current_state[f"bid_qty_{i + 1}"] = int(levels[i][1])
                else:
                    # Pad with 0 if not enough depth
                    current_state[f"bid_px_{i + 1}"] = 0.0
                    current_state[f"bid_qty_{i + 1}"] = 0

        elif evt_type == "ASK_DEPTH":
            # Asks: Low Price is Top
            levels.sort(key=lambda x: x[0], reverse=False)

            for i in range(DEPTH_LEVELS):
                if i < len(levels):
                    current_state[f"ask_px_{i + 1}"] = float(levels[i][0])
                    current_state[f"ask_qty_{i + 1}"] = int(levels[i][1])
                else:
                    current_state[f"ask_px_{i + 1}"] = 0.0
                    current_state[f"ask_qty_{i + 1}"] = 0

        # Save a copy of the state at this timestamp
        processed_rows.append(current_state.copy())

    # 3. Convert back to Polars
    print("--- CONSTRUCTING FINAL DATAFRAME ---")
    final_df = pl.DataFrame(processed_rows)

    # 4. Feature Engineering (Optional: Add Mid Price)
    final_df = final_df.with_columns(
        ((pl.col("bid_px_1") + pl.col("ask_px_1")) / 2).alias("mid_price")
    )

    # 5. Save
    print(f"--- SAVING TO {OUTPUT_FILE} ---")
    final_df.write_parquet(OUTPUT_FILE)
    print("SUCCESS: Data is ready for Deep Learning.")
    print(final_df.head())


if __name__ == "__main__":
    process_abides_data()

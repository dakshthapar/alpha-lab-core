import sys

import pandas as pd
import polars as pl
from tqdm import tqdm

# --- CONFIG ---
INPUT_FILE = "data/synthetic_dense_data.parquet"
OUTPUT_FILE = "data/final_training_data.parquet"  # Overwriting the old empty file
DEPTH = 5


def reconstruct_book():
    print(f"--- LOADING EVENTS: {INPUT_FILE} ---")
    df = pl.read_parquet(INPUT_FILE)

    # 1. FILTER FOR RELEVANT EVENTS
    # We need Submissions, Cancellations, and Executions to track liquidity
    mask = pl.col("EventType").is_in(
        ["ORDER_SUBMITTED", "ORDER_CANCELLED", "ORDER_EXECUTED"]
    )
    events = df.filter(mask)

    # 2. CHECK FOR ORDER_ID
    if "order_id" not in events.columns:
        print("CRITICAL: 'order_id' column missing. Cannot track cancellations!")
        print(f"Available: {events.columns}")
        sys.exit(1)

    # Convert to Pandas for faster row-wise iteration (Polars is column-major)
    # We select only what we need to minimize RAM usage
    print("Converting to iterator...")
    events_pd = (
        events.select(
            ["EventTime", "EventType", "side", "limit_price", "quantity", "order_id"]
        )
        .sort("EventTime")
        .to_pandas()
    )

    print(f"Processing {len(events_pd)} Atomic Events...")

    # --- STATE ENGINE ---
    # Global Order Map: order_id -> {price, qty, side}
    active_orders = {}

    # Price Levels: price -> total_volume
    # We use dictionaries for sparse storage
    bid_levels = {}
    ask_levels = {}

    snapshots = []

    for _, row in tqdm(events_pd.iterrows(), total=len(events_pd)):
        evt = row["EventType"]
        oid = row["order_id"]

        # --- HANDLER: SUBMISSION (Add Liquidity) ---
        if evt == "ORDER_SUBMITTED":
            try:
                price = float(row["limit_price"])
                qty = int(row["quantity"])
                side = str(row["side"])  # "Side.BID" or "Side.ASK"

                if pd.isna(price) or price <= 0:
                    continue

                # Track Order
                active_orders[oid] = {"p": price, "q": qty, "s": side}

                # Update Book
                if "BID" in side:
                    bid_levels[price] = bid_levels.get(price, 0) + qty
                else:
                    ask_levels[price] = ask_levels.get(price, 0) + qty
            except:
                continue

        # --- HANDLER: REMOVAL (Cancel/Execute) ---
        elif evt in ["ORDER_CANCELLED", "ORDER_EXECUTED"]:
            # We must know the price to remove it from the level
            if oid in active_orders:
                order_info = active_orders[oid]
                price = order_info["p"]
                side = order_info["s"]

                # In a simple sim, we assume full cancellation/execution for simplicity
                # (Or we can use the 'quantity' column if provided in cancel logs)
                # Here we check if the log has a valid quantity, else use tracked qty
                log_qty = row["quantity"]
                qty_to_remove = (
                    int(log_qty)
                    if (pd.notna(log_qty) and log_qty > 0)
                    else order_info["q"]
                )

                # Update Book
                if "BID" in side:
                    if price in bid_levels:
                        bid_levels[price] = max(0, bid_levels[price] - qty_to_remove)
                        if bid_levels[price] == 0:
                            del bid_levels[price]
                else:
                    if price in ask_levels:
                        ask_levels[price] = max(0, ask_levels[price] - qty_to_remove)
                        if ask_levels[price] == 0:
                            del ask_levels[price]

                # If fully removed, delete from tracker
                # (For partials, we should technically update active_orders, but this is approx)
                if qty_to_remove >= order_info["q"]:
                    del active_orders[oid]
                else:
                    active_orders[oid]["q"] -= qty_to_remove

        # --- SNAPSHOT GENERATION ---
        # Sort and Extract Top 5
        # Bids: Descending (Highest buy is best)
        # Asks: Ascending (Lowest sell is best)

        snapshot = {
            "timestamp": row["EventTime"],
            "symbol": "NIFTY_SIM",  # Hardcoded for training consistency
        }

        # Top 5 Bids
        sorted_bids = sorted(bid_levels.items(), key=lambda x: x[0], reverse=True)[
            :DEPTH
        ]
        for i in range(DEPTH):
            if i < len(sorted_bids):
                snapshot[f"bid_px_{i + 1}"] = sorted_bids[i][0]
                snapshot[f"bid_qty_{i + 1}"] = sorted_bids[i][1]
            else:
                snapshot[f"bid_px_{i + 1}"] = 0.0
                snapshot[f"bid_qty_{i + 1}"] = 0

        # Top 5 Asks
        sorted_asks = sorted(ask_levels.items(), key=lambda x: x[0], reverse=False)[
            :DEPTH
        ]
        for i in range(DEPTH):
            if i < len(sorted_asks):
                snapshot[f"ask_px_{i + 1}"] = sorted_asks[i][0]
                snapshot[f"ask_qty_{i + 1}"] = sorted_asks[i][1]
            else:
                snapshot[f"ask_px_{i + 1}"] = 0.0
                snapshot[f"ask_qty_{i + 1}"] = 0

        # Mid Price (Feature)
        b1 = snapshot["bid_px_1"]
        a1 = snapshot["ask_px_1"]
        if b1 > 0 and a1 > 0:
            snapshot["mid_price"] = (b1 + a1) / 2
        else:
            snapshot["mid_price"] = 0.0

        snapshots.append(snapshot)

    # --- SAVE ---
    print("Converting to Parquet...")
    final_df = pl.DataFrame(snapshots)

    # Filter out empty books (warmup)
    final_df = final_df.filter(pl.col("mid_price") > 0)

    final_df.write_parquet(OUTPUT_FILE)
    print(f"SUCCESS: Reconstructed {final_df.height} full-depth snapshots.")
    print(f"Saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    reconstruct_book()

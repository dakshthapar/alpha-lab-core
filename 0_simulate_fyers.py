import datetime
import os

import numpy as np
import polars as pl

# Output config
OUTPUT_FILE = "data/simulated_market_data.parquet"
os.makedirs("data", exist_ok=True)

print("--- GENERATING SYNTHETIC DATA ON CPU ---")

# 1. Generate Fake Time Series (100k rows)
ROWS = 100_000
rng = np.random.default_rng(seed=42)
price_walk = rng.normal(0, 0.5, ROWS).cumsum() + 24000

data = {
    "timestamp": [
        datetime.datetime.now() + datetime.timedelta(milliseconds=i * 10)
        for i in range(ROWS)
    ],
    "symbol": ["NSE:NIFTY50-INDEX"] * ROWS,
    "ltp": price_walk,
    "vol_traded": rng.integers(1, 1000, ROWS).cumsum(),
}

# 2. Generate 5 Levels of Depth
for i in range(1, 6):
    data[f"bid_px_{i}"] = price_walk - (i * 0.05) + rng.normal(0, 0.01, ROWS)
    data[f"ask_px_{i}"] = price_walk + (i * 0.05) + rng.normal(0, 0.01, ROWS)
    data[f"bid_qty_{i}"] = rng.integers(50, 500, ROWS)
    data[f"ask_qty_{i}"] = rng.integers(50, 500, ROWS)

# 3. Save to Parquet
df = pl.DataFrame(data)
df.write_parquet(OUTPUT_FILE)

print(f"SUCCESS: Saved {ROWS} rows to {OUTPUT_FILE}")

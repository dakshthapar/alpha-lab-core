import polars as pl

# Load the data
df = pl.read_parquet("data/synthetic_factory_data.parquet")

print("--- INSPECTING DEPTH LOGS ---")

# 1. Filter for Depth Events
# We cast back to proper types for viewing
depth_logs = df.filter(
    (pl.col("EventType") == "BID_DEPTH") | (pl.col("EventType") == "ASK_DEPTH")
)

if depth_logs.height > 0:
    # 2. Show us the data
    # We specifically want to see 'ScalarEventValue' which usually holds the L1/L2 data
    print(
        depth_logs.select(
            ["EventTime", "EventType", "ScalarEventValue", "limit_price", "quantity"]
        ).head(10)
    )
else:
    print(
        "WARNING: Depth events found in EventList but no rows returned. Check filtering."
    )

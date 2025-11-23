import polars as pl

# Load the raw simulation data
df = pl.read_parquet("data/synthetic_factory_data.parquet")

print(f"--- TOTAL ROWS: {df.height} ---")

# 1. Check Unique Event Types
# We are looking for "ORDER_SUBMITTED", "ORDER_EXECUTED", or "limit_order"
print("\n--- EVENT TYPES PRESENT ---")
events = df["EventType"].unique().to_list()
for e in events:
    print(f"- {e}")

# 2. Check Order Columns
# We need to see if 'limit_price' and 'quantity' have non-null values
print("\n--- DATA SAMPLE (Orders Only) ---")
try:
    # Filter for rows that actually have a price (ignore system messages)
    orders = df.filter(pl.col("limit_price") != "nan")
    if orders.height > 0:
        print(
            orders.select(
                ["EventTime", "EventType", "limit_price", "quantity", "side"]
            ).head(5)
        )
    else:
        print(
            "WARNING: No rows found with price data! The config might have 'log_orders=False'."
        )
except Exception as e:
    print(f"Error filtering data: {e}")

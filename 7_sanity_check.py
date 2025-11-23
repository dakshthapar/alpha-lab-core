import polars as pl

# 1. Load Data
df = pl.read_parquet("data/final_training_data.parquet")

print(f"Total Rows: {df.height}")

# 2. Filter out the "Warm Up" (Rows where Mid Price is 0)
clean_df = df.filter(pl.col("mid_price") > 0)

print(f"Valid Trading Rows: {clean_df.height}")
print(f"Dropped {df.height - clean_df.height} rows of warm-up data.")

if clean_df.height > 0:
    print("\n--- FIRST 5 VALID ROWS ---")
    print(clean_df.head(5))

    print("\n--- PRICE STATISTICS ---")
    print(
        clean_df.select(
            [
                pl.col("mid_price").min().alias("Low"),
                pl.col("mid_price").mean().alias("Average"),
                pl.col("mid_price").max().alias("High"),
                pl.col("mid_price").std().alias("Volatility"),
            ]
        )
    )

    # Optional: Save the clean version
    clean_df.write_parquet("data/clean_training_data.parquet")
    print("\nSaved clean data to: data/clean_training_data.parquet")
else:
    print("\nCRITICAL: The entire simulation was empty. Check config!")

# import os
# import shutil
# import sys
# from pathlib import Path

# import numpy as np
# import pandas as pd

# # --- PATH SETUP ---
# current_dir = Path(os.getcwd())
# sys.path.append(str(current_dir / "libs" / "abides" / "abides-core"))
# sys.path.append(str(current_dir / "libs" / "abides" / "abides-markets"))

# # --- IMPORTS ---
# try:
#     from abides_core import abides
#     from abides_core.kernel import Kernel
#     from abides_core.utils import parse_logs_df, str_to_ns
#     from abides_markets.agents.exchange_agent import ExchangeAgent
#     from abides_markets.agents.noise_agent import NoiseAgent
#     from abides_markets.agents.value_agent import ValueAgent
#     from abides_markets.oracles.sparse_mean_reverting_oracle import (
#         SparseMeanRevertingOracle,
#     )
# except ImportError as e:
#     print(f"CRITICAL: Import Failed. {e}")
#     sys.exit(1)

# # --- CONFIGURATION ---
# OUTPUT_FILE = "data/synthetic_dense_data.parquet"
# SEED = 1
# TICKER = "ABM"  # Must be ABM for JPMC library
# SIM_START_STR = "09:00:00"
# MKT_OPEN_STR = "09:30:00"
# MKT_CLOSE_STR = "10:00:00"


# def build_dense_config(seed=1):
#     np.random.seed(seed)
#     mkt_open_ns = str_to_ns(MKT_OPEN_STR)
#     mkt_close_ns = str_to_ns(MKT_CLOSE_STR)
#     sim_start_ns = str_to_ns(SIM_START_STR)

#     agents = []

#     # 1. ORACLE
#     r_bar = 100_000
#     symbol_config = {
#         TICKER: {
#             "r_bar": r_bar,
#             "kappa": 1.67e-13,
#             "sigma_s": 0,
#             "fund_vol": 1e-8,
#             "megashock_lambda_a": 2.77778e-18,
#             "megashock_mean": 1000,
#             "megashock_var": 50_000,
#             "random_state": np.random.RandomState(seed=np.random.randint(0, 2**32)),
#         }
#     }

#     oracle = SparseMeanRevertingOracle(mkt_open_ns, mkt_close_ns, symbol_config)

#     # 2. EXCHANGE (The Fix is Here)
#     agents.append(
#         ExchangeAgent(
#             id=0,
#             name="EXCHANGE",
#             type="ExchangeAgent",
#             mkt_open=mkt_open_ns,
#             mkt_close=mkt_close_ns,
#             symbols=[TICKER],
#             pipeline_delay=0,
#             computation_delay=0,
#             stream_history=10,
#             log_orders=True,
#             # FORCE DEPTH LOGGING
#             book_logging=True,
#             book_log_depth=10,
#         )
#     )
#     agent_count = 1

#     # 3. Value Agents
#     num_value_agents = 100
#     for i in range(num_value_agents):
#         va = ValueAgent(
#             id=agent_count,
#             name=f"VALUE_{i}",
#             type="ValueAgent",
#             symbol=TICKER,
#             starting_cash=1_000_000,
#             sigma_n=r_bar / 10,
#             r_bar=r_bar,
#             kappa=1.67e-13,
#             lambda_a=5.7e-12,
#             log_orders=True,
#         )
#         agents.append(va)
#         agent_count += 1

#     # 4. Noise Agents
#     num_noise = 50
#     wakeup_base = pd.to_datetime(MKT_OPEN_STR)
#     for i in range(num_noise):
#         delay_seconds = np.random.uniform(0, 10)
#         delay_ns = int(delay_seconds * 1_000_000_000)
#         staggered_time_ns = mkt_open_ns + delay_ns

#         na = NoiseAgent(
#             id=agent_count,
#             name=f"NOISE_{i}",
#             type="NoiseAgent",
#             symbol=TICKER,
#             starting_cash=100_000,
#             wakeup_time=staggered_time_ns,
#             log_orders=True,
#         )
#         agents.append(na)
#         agent_count += 1

#     return {
#         "agents": agents,
#         "kernel_start_time": sim_start_ns,
#         "kernel_stop_time": mkt_close_ns,
#         "oracle": oracle,
#     }


# def run_simulation():
#     print(f"--- STARTING ROBUST DENSE SIMULATION [SEED: {SEED}] ---")

#     components = build_dense_config(seed=SEED)
#     kernel_rng = np.random.RandomState(seed=SEED)

#     kernel = Kernel(
#         agents=components["agents"],
#         start_time=components["kernel_start_time"],
#         stop_time=components["kernel_stop_time"],
#         random_state=kernel_rng,
#         log_dir="log",
#     )

#     kernel.oracle = components["oracle"]

#     end_state = kernel.run()

#     print("--- SIMULATION FINISHED. PARSING LOGS... ---")
#     df = parse_logs_df(end_state)

#     print("Sanitizing dataframe...")
#     for col in df.columns:
#         if df[col].dtype == "object":
#             df[col] = df[col].astype(str)

#     os.makedirs("data", exist_ok=True)
#     df.to_parquet(OUTPUT_FILE)

#     print(f"SUCCESS: Generated {len(df)} rows.")
#     print(f"Saved to: {OUTPUT_FILE}")
#     return df


# if __name__ == "__main__":
#     if os.path.exists("log"):
#         shutil.rmtree("log")
#     run_simulation()
import polars as pl

# Load data
df = pl.read_parquet("data/synthetic_dense_data.parquet")

print("--- CHECKING ORDER COLUMNS ---")

# Filter for Order Submissions
orders = df.filter(pl.col("EventType") == "ORDER_SUBMITTED")

if orders.height > 0:
    # Check if we have the specific columns we need for reconstruction
    cols_to_check = ["EventTime", "limit_price", "quantity", "side", "agent_id"]

    # Select available columns (intersection)
    available_cols = [c for c in cols_to_check if c in df.columns]

    print(f"Displaying data from columns: {available_cols}")
    print(orders.select(available_cols).head(5))

    # Check for non-nulls
    null_count = orders.select(pl.col("limit_price").null_count()).item(0, 0)
    print(f"\nNull Prices: {null_count} / {orders.height}")

    if null_count == 0:
        print("✅ SUCCESS: Order data is in separate columns.")
    else:
        print("❌ PROBLEM: Order columns are empty.")

else:
    print("No orders found.")

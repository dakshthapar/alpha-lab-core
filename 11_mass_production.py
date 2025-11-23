import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import polars as pl
from tqdm import tqdm

# --- PATH SETUP ---
current_dir = Path(os.getcwd())
sys.path.append(str(current_dir / "libs" / "abides" / "abides-core"))
sys.path.append(str(current_dir / "libs" / "abides" / "abides-markets"))

# --- IMPORTS ---
try:
    from abides_core.kernel import Kernel
    from abides_core.utils import parse_logs_df, str_to_ns
    from abides_markets.agents.exchange_agent import ExchangeAgent
    from abides_markets.agents.noise_agent import NoiseAgent
    from abides_markets.agents.value_agent import ValueAgent
    from abides_markets.oracles.sparse_mean_reverting_oracle import (
        SparseMeanRevertingOracle,
    )
except ImportError as e:
    print(f"CRITICAL: Import Failed. {e}")
    sys.exit(1)

# --- GLOBAL CONFIG (THE UPGRADE) ---
DATA_DIR = Path("data/training_batches")
NUM_DAYS = 1000  # 1,000 Days (~3 years of data)
TICKER = "ABM"

# NSE TIMINGS (Full Day Simulation)
SIM_START_STR = "09:00:00"
MKT_OPEN_STR = "09:15:00"  # NSE Open
MKT_CLOSE_STR = "15:30:00"  # NSE Close


def run_day(seed):
    np.random.seed(seed)

    # Calculate Nanoseconds
    sim_start_ns = str_to_ns(SIM_START_STR)
    mkt_open_ns = str_to_ns(MKT_OPEN_STR)
    mkt_close_ns = str_to_ns(MKT_CLOSE_STR)

    agents = []

    # 1. Oracle
    symbol_config = {
        TICKER: {
            "r_bar": 100_000,
            "kappa": 1.67e-13,
            "sigma_s": 0,
            "fund_vol": 1e-8,
            "megashock_lambda_a": 2.77778e-18,
            "megashock_mean": 1000,
            "megashock_var": 50_000,
            "random_state": np.random.RandomState(seed=np.random.randint(0, 2**32)),
        }
    }
    oracle = SparseMeanRevertingOracle(mkt_open_ns, mkt_close_ns, symbol_config)

    # 2. Exchange
    agents.append(
        ExchangeAgent(
            id=0,
            name="EXCHANGE",
            type="ExchangeAgent",
            mkt_open=mkt_open_ns,
            mkt_close=mkt_close_ns,
            symbols=[TICKER],
            pipeline_delay=0,
            computation_delay=0,
            stream_history=10,
            log_orders=True,
            book_logging=True,
            book_log_depth=10,
        )
    )

    # 3. Value Agents (100)
    for i in range(100):
        agents.append(
            ValueAgent(
                id=len(agents),
                name=f"VALUE_{i}",
                type="ValueAgent",
                symbol=TICKER,
                starting_cash=1_000_000,
                sigma_n=10000,
                r_bar=100_000,
                kappa=1.67e-13,
                lambda_a=5.7e-12,
                log_orders=True,
            )
        )

    # 4. Noise Agents (50 - Spread over first 30 mins)
    wakeup_base = pd.to_datetime(MKT_OPEN_STR)
    for i in range(50):
        # Spread noise entry over first 30 mins to prevent "Thundering Herd" crash
        delay_ns = int(np.random.uniform(0, 1800) * 1_000_000_000)
        agents.append(
            NoiseAgent(
                id=len(agents),
                name=f"NOISE_{i}",
                type="NoiseAgent",
                symbol=TICKER,
                starting_cash=100_000,
                wakeup_time=mkt_open_ns + delay_ns,
                log_orders=True,
            )
        )

    # 5. Run Kernel
    kernel = Kernel(
        agents=agents,
        start_time=sim_start_ns,
        stop_time=mkt_close_ns,
        random_state=np.random.RandomState(seed=seed),
        skip_log=True,  # Optimization
    )
    kernel.oracle = oracle
    end_state = kernel.run()

    # 6. Parse & Reconstruct
    raw_df = parse_logs_df(end_state)
    return reconstruct_lob(raw_df)


def reconstruct_lob(raw_df):
    mask = raw_df["EventType"].isin(
        ["ORDER_SUBMITTED", "ORDER_CANCELLED", "ORDER_EXECUTED"]
    )
    events = raw_df[mask].sort_values("EventTime")

    if "order_id" not in events.columns:
        return None

    active_orders = {}
    bid_levels = {}
    ask_levels = {}
    snapshots = []

    for row in events.itertuples():
        evt = row.EventType
        oid = row.order_id

        if evt == "ORDER_SUBMITTED":
            try:
                price = float(row.limit_price)
                qty = int(row.quantity)
                side = str(row.side)
                if pd.isna(price) or price <= 0:
                    continue

                active_orders[oid] = {"p": price, "q": qty, "s": side}

                if "BID" in side:
                    bid_levels[price] = bid_levels.get(price, 0) + qty
                else:
                    ask_levels[price] = ask_levels.get(price, 0) + qty
            except:
                continue

        elif evt in ["ORDER_CANCELLED", "ORDER_EXECUTED"]:
            if oid in active_orders:
                info = active_orders[oid]
                rem_qty = (
                    row.quantity
                    if (pd.notna(row.quantity) and row.quantity > 0)
                    else info["q"]
                )
                remove = int(rem_qty)

                if "BID" in info["s"]:
                    if info["p"] in bid_levels:
                        bid_levels[info["p"]] = max(0, bid_levels[info["p"]] - remove)
                        if bid_levels[info["p"]] == 0:
                            del bid_levels[info["p"]]
                else:
                    if info["p"] in ask_levels:
                        ask_levels[info["p"]] = max(0, ask_levels[info["p"]] - remove)
                        if ask_levels[info["p"]] == 0:
                            del ask_levels[info["p"]]

                if remove >= info["q"]:
                    del active_orders[oid]
                else:
                    active_orders[oid]["q"] -= remove

        # Snapshot Top 5
        row_dict = {"timestamp": row.EventTime, "symbol": TICKER}
        bids = sorted(bid_levels.items(), key=lambda x: x[0], reverse=True)[:5]
        asks = sorted(ask_levels.items(), key=lambda x: x[0])[:5]

        for i in range(5):
            row_dict[f"bid_px_{i + 1}"] = bids[i][0] if i < len(bids) else 0.0
            row_dict[f"bid_qty_{i + 1}"] = bids[i][1] if i < len(bids) else 0
            row_dict[f"ask_px_{i + 1}"] = asks[i][0] if i < len(asks) else 0.0
            row_dict[f"ask_qty_{i + 1}"] = asks[i][1] if i < len(asks) else 0

        # Mid Price & Validity Check
        if row_dict["bid_px_1"] > 0 and row_dict["ask_px_1"] > 0:
            row_dict["mid_price"] = (row_dict["bid_px_1"] + row_dict["ask_px_1"]) / 2
            snapshots.append(row_dict)

    return pl.DataFrame(snapshots)


if __name__ == "__main__":
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    print(f"--- LAUNCHING MASS PRODUCTION ({NUM_DAYS} DAYS) ---")
    print("Timings: 09:15 - 15:30 (NSE Standard)")

    # We use a larger range to avoid reusing previous seeds
    start_seed = 101

    for i in tqdm(range(start_seed, start_seed + NUM_DAYS), desc="Simulating Days"):
        try:
            day_df = run_day(seed=i)

            if day_df is not None and day_df.height > 100:  # Ensure nontrivial data
                file_path = DATA_DIR / f"sim_day_{i}.parquet"
                day_df.write_parquet(file_path)

            del day_df

        except Exception:
            # Don't crash the whole batch for one bad day
            # print(f"Skipped Day {i}: {e}")
            continue

    print("\n--- BATCH COMPLETE ---")

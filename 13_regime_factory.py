import sys
import os
import shutil
import argparse
import pandas as pd
import numpy as np
import polars as pl
from tqdm import tqdm
from pathlib import Path

# --- PATH SETUP ---
current_dir = Path(os.getcwd())
sys.path.append(str(current_dir / "libs" / "abides" / "abides-core"))
sys.path.append(str(current_dir / "libs" / "abides" / "abides-markets"))

# --- IMPORTS ---
try:
    from abides_core.utils import parse_logs_df, str_to_ns
    from abides_core.kernel import Kernel
    from abides_markets.agents.exchange_agent import ExchangeAgent
    from abides_markets.agents.noise_agent import NoiseAgent
    from abides_markets.agents.value_agent import ValueAgent
    from abides_markets.oracles.sparse_mean_reverting_oracle import SparseMeanRevertingOracle
except ImportError as e:
    print(f"CRITICAL: Import Failed. {e}")
    sys.exit(1)

# --- GLOBAL CONFIG ---
DATA_DIR = Path("data/training_batches")
TICKER = "ABM"

# NSE TIMINGS (Full Day Simulation by default)
SIM_START_STR = "09:00:00"
MKT_OPEN_STR =  "09:15:00"
MKT_CLOSE_STR = "15:30:00"

def get_regime_params(seed):
    """
    Selects a market regime based on probabilities and adds domain randomization.
    """
    rng = np.random.default_rng(seed)
    dice = rng.random()
    
    # 1. Select Base Regime
    if dice < 0.60:
        regime = "STANDARD"
        # Standard Params
        p = {
            "fund_vol": 1e-8,
            "kappa": 1.67e-13,
            "num_value_agents": 100,
            "sigma_n": 10000,   # Standard "smartness" for Value Agents
            "num_noise": 50
        }
    elif dice < 0.80:
        regime = "VOLATILE" # Panic / Flash Crash
        p = {
            "fund_vol": 1e-7,       # 10x Volatility
            "kappa": 1.67e-13,
            "num_value_agents": 50, # Low Liquidity (Thin Book)
            "sigma_n": 100000,      # Confused Smart Money (High Error)
            "num_noise": 50
        }
    else:
        regime = "MOMENTUM" # Hype / Comparison
        p = {
            "fund_vol": 1e-8,
            "kappa": 1.67e-15,      # 100x Lower Mean Reversion -> Trends persist
            "num_value_agents": 100,
            "sigma_n": 10000,
            "num_noise": 100        # High Retail Activity
        }
        
    # 2. Domain Randomization (Perturb by +/- 20%)
    # We multiply by a factor between 0.8 and 1.2
    def random_scale(val):
        return val * rng.uniform(0.8, 1.2)

    p["fund_vol"] = random_scale(p["fund_vol"])
    p["kappa"] = random_scale(p["kappa"])
    p["sigma_n"] = random_scale(p["sigma_n"])
    
    # Integers usually shouldn't be floated
    # But we can jiggle agent counts slightly
    p["num_value_agents"] = int(p["num_value_agents"] * rng.uniform(0.9, 1.1))
    p["num_noise"] = int(p["num_noise"] * rng.uniform(0.9, 1.1))
    
    return regime, p

def run_day(seed, regime_override=None):
    """Runs a single day of simulation with specific regime parameters."""
    
    # 1. SETUP CONFIG
    # Determine Parameters
    regime, params = get_regime_params(seed)
    
    if regime_override:
        # Force a specific regime (for testing)
        # We just re-roll until we get it, or hardcode. Hardcoding for safety.
        regime = regime_override
        # ... logic to force param set ...
        # Ideally, just let the tester handle it, but for now we follow seed logic strictly
        # unless manual override implemented fully. 
        # For simplicity in this script, we'll stick to seed-based unless strictly needed.
    
    np.random.seed(seed)
    
    sim_start_ns = str_to_ns(SIM_START_STR)
    mkt_open_ns = str_to_ns(MKT_OPEN_STR)
    mkt_close_ns = str_to_ns(MKT_CLOSE_STR)
    
    agents = []
    
    # 2. ORACLE
    symbol_config = {
        TICKER: {
            "r_bar": 100_000,
            "kappa": params["kappa"],
            "sigma_s": 0,
            "fund_vol": params["fund_vol"],
            "megashock_lambda_a": 2.77778e-18,
            "megashock_mean": 1000,
            "megashock_var": 50_000,
            "random_state": np.random.RandomState(seed=np.random.randint(0, 2**32))
        }
    }
    oracle = SparseMeanRevertingOracle(mkt_open_ns, mkt_close_ns, symbol_config)
    
    # 3. EXCHANGE
    agents.append(ExchangeAgent(
        id=0, name="EXCHANGE", type="ExchangeAgent",
        mkt_open=mkt_open_ns, mkt_close=mkt_close_ns, symbols=[TICKER],
        pipeline_delay=0, computation_delay=0, stream_history=10,
        log_orders=True, book_logging=True, book_log_depth=10
    ))
    
    # 4. VALUE AGENTS (Smart Money)
    for i in range(params["num_value_agents"]):
        agents.append(ValueAgent(
            id=len(agents), name=f"VALUE_{i}", type="ValueAgent", symbol=TICKER,
            starting_cash=1_000_000, 
            sigma_n=params["sigma_n"], 
            r_bar=100_000,
            kappa=params["kappa"], 
            lambda_a=5.7e-12, 
            log_orders=True
        ))

    # 5. NOISE AGENTS (Retail)
    wakeup_base = pd.to_datetime(MKT_OPEN_STR)
    for i in range(params["num_noise"]):
        # Spread noise entry over first 30 mins
        delay_ns = int(np.random.uniform(0, 1800) * 1_000_000_000) 
        agents.append(NoiseAgent(
            id=len(agents), name=f"NOISE_{i}", type="NoiseAgent", symbol=TICKER,
            starting_cash=100_000, wakeup_time=mkt_open_ns + delay_ns, log_orders=True
        ))

    # 6. RUN KERNEL
    kernel = Kernel(
        agents=agents, start_time=sim_start_ns, stop_time=mkt_close_ns,
        random_state=np.random.RandomState(seed=seed),
        skip_log=True 
    )
    kernel.oracle = oracle
    end_state = kernel.run()
    
    # 7. RECONSTRUCT LOB
    raw_df = parse_logs_df(end_state)
    return reconstruct_lob(raw_df), regime

def reconstruct_lob(raw_df):
    mask = raw_df["EventType"].isin(["ORDER_SUBMITTED", "ORDER_CANCELLED", "ORDER_EXECUTED"])
    events = raw_df[mask].sort_values("EventTime")
    
    if "order_id" not in events.columns: return None

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
                if pd.isna(price) or price <= 0: continue
                
                active_orders[oid] = {"p": price, "q": qty, "s": side}
                
                if "BID" in side: bid_levels[price] = bid_levels.get(price, 0) + qty
                else: ask_levels[price] = ask_levels.get(price, 0) + qty
            except: continue
            
        elif evt in ["ORDER_CANCELLED", "ORDER_EXECUTED"]:
            if oid in active_orders:
                info = active_orders[oid]
                rem_qty = row.quantity if (pd.notna(row.quantity) and row.quantity > 0) else info["q"]
                remove = int(rem_qty)
                
                if "BID" in info["s"]:
                    if info["p"] in bid_levels:
                        bid_levels[info["p"]] = max(0, bid_levels[info["p"]] - remove)
                        if bid_levels[info["p"]] == 0: del bid_levels[info["p"]]
                else:
                    if info["p"] in ask_levels:
                        ask_levels[info["p"]] = max(0, ask_levels[info["p"]] - remove)
                        if ask_levels[info["p"]] == 0: del ask_levels[info["p"]]
                
                if remove >= info["q"]: del active_orders[oid]
                else: active_orders[oid]["q"] -= remove

        # Snapshot Top 5
        row_dict = {"timestamp": row.EventTime, "symbol": TICKER}
        bids = sorted(bid_levels.items(), key=lambda x: x[0], reverse=True)[:5]
        asks = sorted(ask_levels.items(), key=lambda x: x[0])[:5]
        
        for i in range(5):
            row_dict[f"bid_px_{i+1}"] = bids[i][0] if i < len(bids) else 0.0
            row_dict[f"bid_qty_{i+1}"] = bids[i][1] if i < len(bids) else 0
            row_dict[f"ask_px_{i+1}"] = asks[i][0] if i < len(asks) else 0.0
            row_dict[f"ask_qty_{i+1}"] = asks[i][1] if i < len(asks) else 0

        if row_dict["bid_px_1"] > 0 and row_dict["ask_px_1"] > 0:
            row_dict["mid_price"] = (row_dict["bid_px_1"] + row_dict["ask_px_1"]) / 2
            snapshots.append(row_dict)

    return pl.DataFrame(snapshots).filter(pl.col("mid_price") > 0)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--test-mode", action="store_true", help="Run only 3 days (one of each regime) for testing")
    parser.add_argument("--days", type=int, default=1000, help="Number of days to simulate")
    parser.add_argument("--start-seed", type=int, default=1000, help="Starting random seed")
    args = parser.parse_args()

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    num_days = 3 if args.test_mode else args.days
    start_seed = args.start_seed
    
    print(f"--- LAUNCHING REGIME FACTORY ({num_days} DAYS) ---")
    print(f"Test Mode: {args.test_mode}")
    
    for i in tqdm(range(start_seed, start_seed + num_days), desc="Simulating"):
        try:
            day_df, regime = run_day(seed=i)
            
            if day_df is not None and day_df.height > 100:
                # Filename includes REGIME for easier debugging/splitting later
                file_path = DATA_DIR / f"sim_day_{i}_{regime}.parquet"
                day_df.write_parquet(file_path)
            
            del day_df
            
        except Exception as e:
            print(f"Error Day {i}: {e}")
            continue
            
    print(f"\n--- BATCH COMPLETE ---")

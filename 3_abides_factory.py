import os
import shutil
import sys
from pathlib import Path

# --- PATH SETUP ---
current_dir = Path(os.getcwd())
sys.path.append(str(current_dir / "libs" / "abides" / "abides-core"))
sys.path.append(str(current_dir / "libs" / "abides" / "abides-markets"))

try:
    from abides_core import abides
    from abides_core.utils import parse_logs_df
    from abides_markets.configs import rmsc04
except ImportError as e:
    print(f"CRITICAL IMPORT ERROR: {e}")
    sys.exit(1)

# --- CONFIGURATION ---
OUTPUT_FILE = "data/synthetic_factory_data.parquet"
SEED = 1


def run_simulation():
    print(f"--- STARTING FACTORY SIMULATION [SEED: {SEED}] ---")

    # 1. BUILD CONFIGURATION
    config = rmsc04.build_config(seed=SEED)

    # 2. OVERRIDE TIMES (Using Dict Syntax)
    config["end_time"] = "10:00:00"

    # 3. RUN KERNEL
    end_state = abides.run(config)

    print("--- SIMULATION FINISHED. PARSING LOGS... ---")

    # 4. PARSE LOGS
    df = parse_logs_df(end_state)

    # --- FIX: SANITIZE DATA FOR PARQUET ---
    # ABIDES logs raw Python objects (Messages) which crash PyArrow.
    # We convert all 'object' type columns to strings to preserve the info safely.
    print("Sanitizing dataframe for Parquet storage...")
    for col in df.columns:
        if df[col].dtype == "object":
            df[col] = df[col].astype(str)

    # 5. SAVE
    os.makedirs("data", exist_ok=True)
    df.to_parquet(OUTPUT_FILE)

    print(f"SUCCESS: Generated {len(df)} rows.")
    print(f"Saved to: {OUTPUT_FILE}")

    return df


if __name__ == "__main__":
    if os.path.exists("log"):
        shutil.rmtree("log")

    df = run_simulation()
    print(df.head())

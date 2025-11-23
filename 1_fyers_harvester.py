import datetime
import os
import time
from collections import deque

import polars as pl
from dotenv import load_dotenv
from fyers_apiv3.FyersWebsocket import data_ws

# Load secrets from .env
load_dotenv()

# --- CONFIG ---
# Check for credentials
APP_ID = os.getenv("FYERS_APP_ID")
TOKEN = os.getenv("FYERS_ACCESS_TOKEN")

if not APP_ID or not TOKEN:
    raise ValueError("Missing Credentials! Check your .env file.")

ACCESS_TOKEN = f"{APP_ID}:{TOKEN}"
SYMBOLS = ["NSE:NIFTY50-INDEX", "NSE:NIFTYBANK-INDEX"]
BUFFER_SIZE = 5000  # Rows to buffer in RAM

data_buffer = deque()


def on_message(message):
    """Flatten Fyers JSON to Polars Row"""
    global data_buffer
    if "bids" in message and "asks" in message:
        row = {
            "timestamp": datetime.datetime.now(),
            "symbol": message.get("symbol"),
            "ltp": message.get("ltp"),
            "vol": message.get("vol_traded_today"),
        }
        # Capture Top 5 Levels
        for i, bid in enumerate(message["bids"][:5]):
            row[f"bid_px_{i + 1}"] = bid["price"]
            row[f"bid_qty_{i + 1}"] = bid["volume"]
        for i, ask in enumerate(message["asks"][:5]):
            row[f"ask_px_{i + 1}"] = ask["price"]
            row[f"ask_qty_{i + 1}"] = ask["volume"]

        data_buffer.append(row)
        if len(data_buffer) >= BUFFER_SIZE:
            flush_to_disk()


def flush_to_disk():
    global data_buffer
    if not data_buffer:
        return
    filename = f"data/fyers_{int(time.time_ns())}.parquet"
    print(f"--- SAVING {len(data_buffer)} TICKS TO {filename} ---")
    pl.DataFrame(list(data_buffer)).write_parquet(filename)
    data_buffer.clear()


def on_open():
    print(f"Connected. Subscribing to {SYMBOLS}...")
    fyers.subscribe(symbols=SYMBOLS, data_type="DepthUpdate")
    fyers.keep_running()


def on_close(msg):
    print("Closed. Flushing...")
    flush_to_disk()


if __name__ == "__main__":
    os.makedirs("data", exist_ok=True)
    fyers = data_ws.FyersDataSocket(
        access_token=ACCESS_TOKEN,
        log_path="fyers_logs",
        litemode=False,
        write_to_file=False,
        reconnect=True,
        on_connect=on_open,
        on_close=on_close,
        on_message=on_message,
    )
    fyers.connect()

import os
import sys
import time
import datetime
import pytz
import argparse
import pandas as pd
from fyers_apiv3 import fyersModel
from dotenv import load_dotenv

# --- COMMAND LINE ARGUMENT SETUP ---
parser = argparse.ArgumentParser(description="Fyers Market Depth Harvester")
parser.add_argument("--debug", action="store_true", help="Enable verbose debug logging")
args = parser.parse_args()

DEBUG_MODE = args.debug

def log(msg, level="INFO"):
    """Smart logger that filters based on mode"""
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    if level == "DEBUG" and not DEBUG_MODE:
        return
    print(f"[{timestamp}] [{level}] {msg}")

# --- SECURITY & CONFIG ---
load_dotenv()
CLIENT_ID = os.getenv("FYERS_CLIENT_ID")
DATA_DIR = "harvested_data"
SYMBOLS = [
    "NSE:HDFCBANK-EQ",
    "NSE:RELIANCE-EQ",
    "NSE:ADANIENT-EQ",
    "NSE:INFY-EQ",
    "NSE:TATAMOTORS-EQ"
]

# --- TIME CONSTANTS (IST) ---
IST = pytz.timezone('Asia/Kolkata')
MARKET_OPEN_HOUR = 9
MARKET_OPEN_MINUTE = 15
MARKET_CLOSE_HOUR = 15
MARKET_CLOSE_MINUTE = 30

def get_ist_time():
    return datetime.datetime.now(IST)

def wait_for_market_open():
    """Checks time. Returns True to proceed, False to exit."""
    now = get_ist_time()
    market_open = now.replace(hour=MARKET_OPEN_HOUR, minute=MARKET_OPEN_MINUTE, second=0, microsecond=0)
    market_close = now.replace(hour=MARKET_CLOSE_HOUR, minute=MARKET_CLOSE_MINUTE, second=0, microsecond=0)
    
    if now > market_close:
        log("Market is closed for the day. Exiting.", "INFO")
        return False

    if now < market_open:
        wait_seconds = (market_open - now).total_seconds()
        log(f"Market not open yet. Waiting {wait_seconds:.0f} seconds...", "INFO")
        time.sleep(wait_seconds)
        log("Market Open! Starting harvest.", "INFO")
    else:
        log("Market is live. Starting immediately.", "INFO")
        
    return True

def main():
    if DEBUG_MODE:
        log("--- DIAGNOSTIC MODE ENABLED ---", "DEBUG")
    
    # 1. Verification
    if not CLIENT_ID:
        log("CRITICAL ERROR: FYERS_CLIENT_ID not found in .env file.", "ERROR")
        return

    # 2. Setup Directories
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)

    # 3. Read Token
    try:
        with open("access_token.txt", "r") as f:
            access_token = f.read().strip()
        log("Token loaded successfully.", "DEBUG")
    except FileNotFoundError:
        log("CRITICAL ERROR: 'access_token.txt' not found.", "ERROR")
        return

    # 4. Initialize Fyers
    try:
        fyers = fyersModel.FyersModel(client_id=CLIENT_ID, is_async=False, token=access_token, log_path="")
        log("Fyers Object Initialized.", "DEBUG")
    except Exception as e:
        log(f"Initialization Failed: {e}", "ERROR")
        return

    # 5. Wait for Open
    if not wait_for_market_open():
        return

    log("--- HARVESTER ACTIVE ---", "INFO")
    
    # 6. Collection Loop
    try:
        while True:
            now = get_ist_time()
            
            # STOP CONDITION
            if now.hour >= MARKET_CLOSE_HOUR and now.minute >= MARKET_CLOSE_MINUTE:
                log("Market Closed. Stopping Harvester.", "INFO")
                break
            
            # --- FETCH CYCLE ---
            data_batch = []
            timestamp_str = now.isoformat()
            
            log("Starting fetch cycle...", "DEBUG")

            for sym in SYMBOLS:
                try:
                    # API Call
                    response = fyers.depth(data={"symbol": sym, "ohlcv_flag": 1})
                    
                    # Debug Raw Response
                    if DEBUG_MODE:
                        # Print condensed version to avoid spamming console too much
                        status = response.get('s', 'unknown')
                        log(f"{sym} Response Status: {status}", "DEBUG")
                        if status != "ok":
                            log(f"FULL ERROR RESPONSE: {response}", "DEBUG")

                    # Processing
                    if "d" in response and response["d"]:
                        stock_data = response["d"][sym]
                        
                        row = {
                            "timestamp": timestamp_str,
                            "symbol": stock_data["symbol"],
                            "ltp": stock_data["ltp"],
                            "total_buy_qty": stock_data["totalbuyqty"],
                            "total_sell_qty": stock_data["totalsellqty"]
                        }
                        
                        for i, bid in enumerate(stock_data["bids"][:5]):
                            row[f"bid_px_{i+1}"] = bid["price"]
                            row[f"bid_qty_{i+1}"] = bid["qty"]
                        for i, ask in enumerate(stock_data["ask"][:5]):
                            row[f"ask_px_{i+1}"] = ask["price"]
                            row[f"ask_qty_{i+1}"] = ask["qty"]
                            
                        data_batch.append(row)
                        
                    # Rate Limit Sleep
                    time.sleep(0.05) 

                except Exception as e:
                    log(f"CRASH fetching {sym}: {e}", "ERROR")

            # SAVE BATCH
            if data_batch:
                df = pd.DataFrame(data_batch)
                today_str = now.strftime("%Y-%m-%d")
                filename = f"{DATA_DIR}/market_depth_{today_str}.csv"
                
                header = not os.path.exists(filename)
                df.to_csv(filename, mode='a', header=header, index=False)
                
                log(f"Snapshot saved for {len(data_batch)} stocks.", "INFO")
            else:
                log("WARNING: No data collected this cycle.", "DEBUG")
            
            # Sleep 5 Seconds
            time.sleep(5)

    except KeyboardInterrupt:
        log("Manual Stop.", "INFO")

if __name__ == "__main__":
    main()
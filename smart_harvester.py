import os
import time
import datetime
import pytz
import pandas as pd
from fyers_apiv3 import fyersModel
from dotenv import load_dotenv

# --- SECURITY SETUP ---
# Load environment variables from .env file
load_dotenv()

# Fetch Credentials from Environment
CLIENT_ID = os.getenv("FYERS_CLIENT_ID")

# Configuration
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
    """
    Checks the time. If before 9:15 AM, sleeps until market open.
    Returns True if market is open/yet to open. Returns False if market is already closed.
    """
    now = get_ist_time()
    
    # Define Open and Close times for TODAY
    market_open = now.replace(hour=MARKET_OPEN_HOUR, minute=MARKET_OPEN_MINUTE, second=0, microsecond=0)
    market_close = now.replace(hour=MARKET_CLOSE_HOUR, minute=MARKET_CLOSE_MINUTE, second=0, microsecond=0)
    
    # Case 1: Market is already closed for the day
    if now > market_close:
        print(f"[{now}] Market is already closed. Exiting.")
        return False

    # Case 2: Before Market Open (Wait)
    if now < market_open:
        wait_seconds = (market_open - now).total_seconds()
        print(f"[{now}] Market not open yet. Waiting {wait_seconds:.0f} seconds until 9:15 AM...")
        time.sleep(wait_seconds)
        print(f"[{get_ist_time()}] Market Open! Starting harvest.")
    
    # Case 3: Market is currently open (Start immediately)
    else:
        print(f"[{now}] Market is live. Starting immediately.")
        
    return True

def main():
    # 1. Verification
    if not CLIENT_ID:
        print("CRITICAL ERROR: FYERS_CLIENT_ID not found in .env file.")
        return

    # 2. Setup Directories
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)

    # 3. Authentication (Read Daily Token from File)
    try:
        with open("access_token.txt", "r") as f:
            access_token = f.read().strip()
    except FileNotFoundError:
        print("CRITICAL ERROR: 'access_token.txt' not found. Please upload the token file.")
        return

    # 4. Initialize Fyers
    try:
        fyers = fyersModel.FyersModel(client_id=CLIENT_ID, is_async=False, token=access_token, log_path="")
    except Exception as e:
        print(f"Initialization Failed: {e}")
        return

    # 5. Wait for Open
    if not wait_for_market_open():
        return

    print("--- HARVESTER ACTIVE ---")
    
    # 6. Collection Loop
    try:
        while True:
            now = get_ist_time()
            
            # STOP CONDITION: 3:30 PM
            if now.hour >= MARKET_CLOSE_HOUR and now.minute >= MARKET_CLOSE_MINUTE:
                print(f"[{now}] Market Closed. Stopping Harvester.")
                break
            
            # FETCH DATA
            data_batch = []
            timestamp_str = now.isoformat()

            for sym in SYMBOLS:
                try:
                    # FIX: Fetch depth for one symbol at a time using 'data' parameter
                    response = fyers.depth(data={"symbol": sym, "ohlcv_flag": 1})
                    
                    if "d" in response and response["d"]:
                        # API returns a dictionary where key is the symbol
                        stock_data = response["d"][sym]
                        
                        row = {
                            "timestamp": timestamp_str,
                            "symbol": stock_data["symbol"],
                            "ltp": stock_data["ltp"],
                            "total_buy_qty": stock_data["totalbuyqty"],
                            "total_sell_qty": stock_data["totalsellqty"]
                        }
                        
                        # Capture Top 5 Bids
                        for i, bid in enumerate(stock_data["bids"][:5]):
                            row[f"bid_px_{i+1}"] = bid["price"]
                            row[f"bid_qty_{i+1}"] = bid["qty"]
                        
                        # Capture Top 5 Asks
                        for i, ask in enumerate(stock_data["ask"][:5]):
                            row[f"ask_px_{i+1}"] = ask["price"]
                            row[f"ask_qty_{i+1}"] = ask["qty"]
                            
                        data_batch.append(row)
                        
                        # Tiny sleep to be polite to the API (avoid Rate Limits)
                        time.sleep(0.05) 
                        
                except Exception as e:
                    print(f"Error fetching {sym}: {e}")

            # SAVE BATCH
            if data_batch:
                df = pd.DataFrame(data_batch)
                today_str = now.strftime("%Y-%m-%d")
                filename = f"{DATA_DIR}/market_depth_{today_str}.csv"
                
                header = not os.path.exists(filename)
                df.to_csv(filename, mode='a', header=header, index=False)
                
                print(f"[{now.time()}] Snapshot saved for {len(data_batch)} symbols.")
            
            # Sleep 5 Seconds (Total loop time will be approx 5.5s)
            time.sleep(5)

    except KeyboardInterrupt:
        print("Manual Stop.")

if __name__ == "__main__":
    main()
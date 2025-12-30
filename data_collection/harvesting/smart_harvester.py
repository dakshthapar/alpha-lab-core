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
parser.add_argument("--use-ssm", action="store_true", help="Retrieve access token from AWS SSM Parameter Store (for cloud deployment)")
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
    "NSE:SBIN-EQ"  # Swapped TATAMOTORS for SBIN to ensure stability
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

def get_access_token_from_ssm(region='ap-south-1'):
    """Retrieve access token from AWS SSM Parameter Store"""
    try:
        import boto3
        log("Retrieving access token from AWS SSM...", "DEBUG")
        ssm = boto3.client('ssm', region_name=region)
        response = ssm.get_parameter(Name='FYERS_ACCESS_TOKEN', WithDecryption=True)
        token = response['Parameter']['Value']
        log("✅ Access token retrieved from SSM", "DEBUG")
        return token
    except ImportError:
        log("❌ boto3 not installed. Install: pip install boto3", "ERROR")
        return None
    except Exception as e:
        log(f"❌ Error retrieving token from SSM: {e}", "ERROR")
        log("   Make sure FYERS_ACCESS_TOKEN is set in SSM Parameter Store", "ERROR")
        return None

def main():
    if DEBUG_MODE:
        log("--- DIAGNOSTIC MODE ENABLED ---", "DEBUG")
    
    if not CLIENT_ID:
        log("CRITICAL ERROR: FYERS_CLIENT_ID not found in .env file.", "ERROR")
        return

    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)

    # Load access token (from SSM or local file)
    if args.use_ssm:
        log("Using AWS SSM Parameter Store for token retrieval", "INFO")
        access_token = get_access_token_from_ssm()
        if not access_token:
            return
    else:
        try:
            with open("access_token.txt", "r") as f:
                access_token = f.read().strip()
            log("Token loaded from local file.", "DEBUG")
        except FileNotFoundError:
            log("CRITICAL ERROR: 'access_token.txt' not found.", "ERROR")
            log("   Run get_token.py to generate tokens, or use --use-ssm for cloud mode", "ERROR")
            return

    try:
        fyers = fyersModel.FyersModel(client_id=CLIENT_ID, is_async=False, token=access_token, log_path="")
        log("Fyers Object Initialized.", "DEBUG")
    except Exception as e:
        log(f"Initialization Failed: {e}", "ERROR")
        return

    if not wait_for_market_open():
        return

    log("--- HARVESTER ACTIVE ---", "INFO")
    
    try:
        while True:
            now = get_ist_time()
            if now.hour >= MARKET_CLOSE_HOUR and now.minute >= MARKET_CLOSE_MINUTE:
                log("Market Closed. Stopping Harvester.", "INFO")
                break
            
            data_batch = []
            timestamp_str = now.isoformat()
            
            log("Starting fetch cycle...", "DEBUG")

            for sym in SYMBOLS:
                try:
                    response = fyers.depth(data={"symbol": sym, "ohlcv_flag": 1})
                    
                    if DEBUG_MODE:
                        status = response.get('s', 'unknown')
                        log(f"{sym} Response Status: {status}", "DEBUG")
                        if status != "ok":
                            log(f"FULL ERROR RESPONSE: {response}", "DEBUG")

                    if "d" in response and response["d"]:
                        stock_data = response["d"][sym]
                        
                        row = {
                            "timestamp": timestamp_str,
                            "symbol": sym,
                            "ltp": stock_data.get("ltp", 0),
                            "total_buy_qty": stock_data.get("totalbuyqty", 0),
                            "total_sell_qty": stock_data.get("totalsellqty", 0)
                        }
                        
                        bids = stock_data.get("bids", [])
                        asks = stock_data.get("ask", [])
                        
                        # --- CRASH FIX: Use .get('volume') instead of ['qty'] ---
                        for i in range(5):
                            if i < len(bids):
                                row[f"bid_px_{i+1}"] = bids[i].get("price", 0)
                                # Fyers V3 uses 'volume' for quantity in depth
                                row[f"bid_qty_{i+1}"] = bids[i].get("volume", bids[i].get("qty", 0))
                            else:
                                row[f"bid_px_{i+1}"] = 0
                                row[f"bid_qty_{i+1}"] = 0
                                
                        for i in range(5):
                            if i < len(asks):
                                row[f"ask_px_{i+1}"] = asks[i].get("price", 0)
                                row[f"ask_qty_{i+1}"] = asks[i].get("volume", asks[i].get("qty", 0))
                            else:
                                row[f"ask_px_{i+1}"] = 0
                                row[f"ask_qty_{i+1}"] = 0
                            
                        data_batch.append(row)
                        
                    time.sleep(0.05) 

                except Exception as e:
                    log(f"CRASH fetching {sym}: {e}", "ERROR")

            if data_batch:
                df = pd.DataFrame(data_batch)
                today_str = now.strftime("%Y-%m-%d")
                filename = f"{DATA_DIR}/market_depth_{today_str}.csv"
                header = not os.path.exists(filename)
                df.to_csv(filename, mode='a', header=header, index=False)
                log(f"Snapshot saved for {len(data_batch)} stocks.", "INFO")
            else:
                log("WARNING: No data collected this cycle.", "DEBUG")
            
            time.sleep(5)

    except KeyboardInterrupt:
        log("Manual Stop.", "INFO")

if __name__ == "__main__":
    main()
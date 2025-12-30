# Fyers Data Harvesting Guide

This guide covers collecting real-time market depth data from Indian stock markets using the Fyers API.

> [!NOTE]
> **Prerequisites**: Complete [INSTALL_GUIDE.md](INSTALL_GUIDE.md) before proceeding.

---

## 📚 Table of Contents

- [Overview](#overview)
- [Quick Start (Local Development)](#quick-start-local-development)
- [Understanding Access Tokens](#understanding-access-tokens)
- [Running the Harvester](#running-the-harvester)
- [Data Format](#data-format)
- [Troubleshooting](#troubleshooting)
- [Next Steps](#next-steps)

---

## Overview

The **smart_harvester.py** script collects Level 2 Market Depth data for a basket of NSE stocks during trading hours (9:15 AM - 3:30 PM IST).

### Target Stocks ("Alpha 5")

- `NSE:HDFCBANK-EQ` - HDFC Bank
- `NSE:RELIANCE-EQ` - Reliance Industries
- `NSE:ADANIENT-EQ` - Adani Enterprises
- `NSE:INFY-EQ` - Infosys
- `NSE:SBIN-EQ` - State Bank of India

### What is Level 2 Market Depth?

Market depth shows the **order book**:
- **Best 5 bid prices** and quantities (buyers)
- **Best 5 ask prices** and quantities (sellers)
- **Last Traded Price (LTP)**
- **Total buy/sell quantities**

This data is essential for:
- Understanding market liquidity
- Analyzing order flow
- Training market-making algorithms
- Calibrating ABIDES simulations

---

## Quick Start (Local Development)

### Step 1: Set Up Fyers API Credentials

1. **Create a Fyers Account**: Sign up at [https://fyers.in](https://fyers.in)

2. **Create an API App**:
   - Go to [https://myapi.fyers.in/apps](https://myapi.fyers.in/apps)
   - Click "Create App"
   - Set **Redirect URL**: `http://127.0.0.1/`
   - Note your **App ID** and **Secret Key**

3. **Configure .env File**:
   
   Create a `.env` file in the `alpha-lab-core` folder:
   
   ```bash
   nano .env
   ```
   
   Add your credentials:
   
   ```plaintext
   FYERS_CLIENT_ID=XS12345-100
   FYERS_SECRET_KEY=ABCD1234WXYZ
   ```
   
   > [!IMPORTANT]
   > **Terminology**: Fyers calls it "App ID" but we use `FYERS_CLIENT_ID` in the code.
   
   Save and exit (`Ctrl+O`, `Enter`, `Ctrl+X`).

### Step 2: Generate Your First Access Token

Access tokens are required to call the Fyers API and expire daily at 6:00 AM.

```bash
cd ~/path/to/alpha-lab-core
python3 data_collection/harvesting/get_token.py
```

**What happens**:
1. A browser opens with Fyers login
2. Log in with your Fyers credentials
3. Authorize the app
4. You'll see a blank page with a URL like: `http://127.0.0.1/?s=ok&code=ABC123...`
5. **Copy the entire URL** and paste it into the terminal

**Output**:
```
✅ SUCCESS! TOKENS GENERATED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📌 ACCESS TOKEN (Valid for 1 day):
eyJ0eXAiOiJKV1QiLCJhbGc...
✅ Saved to: access_token.txt

🔄 REFRESH TOKEN (Valid for 15 days):
dGhpcyBpcyBhIHNhbXBsZSByZWZyZXNo...
✅ Saved to: refresh_token.txt
```

> [!TIP]
> The refresh token allows automated daily token refresh for 15 days. See [TOKEN_REFRESH_GUIDE.md](TOKEN_REFRESH_GUIDE.md) for automation setup.

### Step 3: Run the Harvester Locally

```bash
# Start harvester
python3 data_collection/harvesting/smart_harvester.py
```

**Expected Output**:
```
[09:14:55] [INFO] Market not open yet. Waiting 95 seconds...
[09:15:00] [INFO] Market Open! Starting harvest.
[09:15:00] [INFO] Reloading access token to ensure it's fresh...
[09:15:01] [INFO] --- HARVESTER ACTIVE ---
[09:15:05] [INFO] Snapshot saved for 5 stocks.
[09:15:10] [INFO] Snapshot saved for 5 stocks.
```

**Stop the harvester**: Press `Ctrl+C`

> [!NOTE]
> The harvester now **pauses** when the market closes instead of stopping, and automatically resumes the next trading day with the updated access token.

### Step 4: Verify Data Collection

```bash
# Check harvested data folder
ls -lh harvested_data/

# View today's data
head -20 harvested_data/market_depth_$(date +%Y-%m-%d).csv
```

---

## Understanding Access Tokens

### 🎫 Access Token
- **Validity**: 1 day (expires at 6:00 AM the next morning)
- **Purpose**: Used to fetch market data
- **Regeneration**: Required daily (or use automated refresh)

### 🔄 Refresh Token
- **Validity**: 15 days
- **Purpose**: Automatically generates new access tokens without manual login
- **Benefit**: Only login ONCE every 15 days!

### Token Workflow Options

**Option A: Manual Daily Tokens** (Simplest)
- Generate token daily before market opens
- Run harvester manually
- Good for: Testing, local development

**Option B: Automated 15-Day Refresh** (Recommended)
- Set up once, tokens auto-refresh for 15 days
- See: [TOKEN_REFRESH_GUIDE.md](TOKEN_REFRESH_GUIDE.md)
- Good for: Production, 24/7 cloud deployment

**Option C: 24/7 Cloud Deployment** (Advanced)
- Combines automated tokens + AWS EC2
- See: [CLOUD_HARVESTER_GUIDE.md](CLOUD_HARVESTER_GUIDE.md)
- Good for: Continuous data collection

---

## Running the Harvester

### Basic Usage

```bash
# Standard mode (uses access_token.txt)
python3 data_collection/harvesting/smart_harvester.py

# Debug mode (verbose logging)
python3 data_collection/harvesting/smart_harvester.py --debug

# AWS SSM mode (for cloud deployment)
python3 data_collection/harvesting/smart_harvester.py --use-ssm
```

### Harvester Behavior

The harvester:
1. **Waits for market open** if started before 9:15 AM
2. **Reloads token** after waiting to ensure fresh token
3. **Collects data** every 5 seconds during market hours
4. **Pauses at market close** (3:30 PM) until next trading day
5. **Resumes automatically** the next day at 9:15 AM with updated token

> [!IMPORTANT]
> The harvester will **automatically pick up the updated token** when resuming, whether it's the initial startup wait or after market close.

### Running in Background (Linux)

For continuous collection without keeping terminal open:

```bash
# Start in background with logging
nohup python3 -u data_collection/harvesting/smart_harvester.py > harvester.log 2>&1 &

# Monitor logs
tail -f harvester.log

# Check if running
ps aux | grep smart_harvester

# Stop harvester
pkill -f smart_harvester
```

---

## Data Format

### Output File

Data is saved to: `harvested_data/market_depth_YYYY-MM-DD.csv`

### CSV Schema

| Column | Type | Description |
|--------|------|-------------|
| `timestamp` | `str` | ISO 8601 timestamp with timezone |
| `symbol` | `str` | Stock symbol (e.g., `NSE:HDFCBANK-EQ`) |
| `ltp` | `float` | Last Traded Price |
| `total_buy_qty` | `int` | Total buy-side quantity |
| `total_sell_qty` | `int` | Total sell-side quantity |
| `bid_px_1` to `bid_px_5` | `float` | Best 5 bid prices |
| `bid_qty_1` to `bid_qty_5` | `int` | Best 5 bid quantities |
| `ask_px_1` to `ask_px_5` | `float` | Best 5 ask prices |
| `ask_qty_1` to `ask_qty_5` | `int` | Best 5 ask quantities |

### Example Row

```csv
timestamp,symbol,ltp,total_buy_qty,total_sell_qty,bid_px_1,bid_qty_1,...
2025-12-30T10:15:30+05:30,NSE:HDFCBANK-EQ,1750.25,125000,98000,1750.20,500,...
```

### Reading Data in Python

```python
import pandas as pd

# Read today's data
df = pd.read_csv('harvested_data/market_depth_2025-12-30.csv')

# Filter specific stock
hdfcbank = df[df['symbol'] == 'NSE:HDFCBANK-EQ']

# Calculate spread
df['spread'] = df['ask_px_1'] - df['bid_px_1']

# Analyze order book imbalance
df['imbalance'] = (df['total_buy_qty'] - df['total_sell_qty']) / (df['total_buy_qty'] + df['total_sell_qty'])
```

---

## Troubleshooting

### Issue: "Invalid Token" or "Unauthorized"

**Cause**: Token expired or incorrect

**Solution**:
1. Regenerate token: `python3 data_collection/harvesting/get_token.py`
2. Restart harvester

### Issue: "FYERS_CLIENT_ID not found"

**Cause**: Missing or incorrect `.env` file

**Solution**:
1. Verify `.env` exists in project root
2. Check it contains both `FYERS_CLIENT_ID` and `FYERS_SECRET_KEY`
3. Ensure no extra spaces or quotes

### Issue: "No data collected this cycle"

**Causes**:
- Market is closed (check time: 9:15-15:30 IST)
- API rate limiting
- Network issues

**Solution**:
1. Check current IST time
2. Test internet: `ping 8.8.8.8`
3. Check Fyers status: [https://fyers.in](https://fyers.in)
4. Run in debug mode: `--debug`

### Issue: Browser doesn't open for token generation

**Solution**:
1. Install a browser: `sudo apt install firefox` or `sudo apt install chromium`
2. If on remote server, generate token on local machine and upload:
   ```bash
   echo "YOUR_TOKEN" | ssh user@server "cat > ~/alpha-lab-core/access_token.txt"
   ```

---

## Next Steps

### For Local Development
- Continue running harvester manually with daily tokens
- Analyze collected data with Pandas/Polars
- Use for ABIDES simulation calibration

### For Automated Token Refresh
- Follow [TOKEN_REFRESH_GUIDE.md](TOKEN_REFRESH_GUIDE.md)
- Set up 15-day automated token refresh
- Manual work only once every 15 days

### For 24/7 Cloud Deployment
- Follow [CLOUD_HARVESTER_GUIDE.md](CLOUD_HARVESTER_GUIDE.md)
- Deploy to AWS EC2
- Combine with automated token refresh
- Continuous data collection without manual intervention

---

## See Also

- [INSTALL_GUIDE.md](INSTALL_GUIDE.md) - Initial setup
- [TOKEN_REFRESH_GUIDE.md](TOKEN_REFRESH_GUIDE.md) - Automated token refresh (15 days)
- [CLOUD_HARVESTER_GUIDE.md](CLOUD_HARVESTER_GUIDE.md) - AWS 24/7 deployment
- [DATASET_GENERATION_GUIDE.md](DATASET_GENERATION_GUIDE.md) - Synthetic data generation
- [README.md](README.md) - Project overview

---

**Last Updated**: 2025-12-30  
**Version**: 1.0

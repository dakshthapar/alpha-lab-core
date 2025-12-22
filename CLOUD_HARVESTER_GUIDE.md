# Alpha Lab: Cloud Harvester Operations Manual

**Purpose**: Maintain a 24/7 AWS cloud server collecting Level 2 Market Depth data for the "Alpha 5" stock basket.

**Target**: NSE stocks (HDFCBANK, RELIANCE, ADANIENT, INFY, SBIN)

---

## 📋 Table of Contents

- [Part 1: First-Time Setup (One-Off)](#part-1-first-time-setup-one-off)
- [Part 2: The Daily Ritual (08:30 AM - 09:10 AM)](#part-2-the-daily-ritual-0830-am---0910-am)
- [Part 3: Maintenance & Troubleshooting](#part-3-maintenance--troubleshooting)
- [Part 4: Weekly Data Download](#part-4-weekly-data-download-saturday)
- [File Reference](#file-reference)

---

## Part 1: First-Time Setup (One-Off)

> [!IMPORTANT]
> Perform this only when setting up a fresh AWS instance or moving to a new server.

### 1.1 Infrastructure Requirements

**AWS Instance Specifications**:
- **OS**: Ubuntu 24.04 LTS
- **Instance Type**: `t2.micro` or `t3.micro` (Free Tier eligible)
- **Storage**: 8-16 GB (depends on retention period)

**Security Groups**:
- **SSH (Port 22)**: Allow from "My IP" only
- **HTTP/HTTPS (Ports 80/443)**: BLOCK (not needed)

**Key Pair**:
- Download and save `alpha-key.pem` securely on your laptop
- Set permissions: `chmod 400 alpha-key.pem`

### 1.2 Server Initialization

SSH into your AWS instance:

```bash
ssh -i alpha-key.pem ubuntu@YOUR_AWS_IP
```

Run the setup commands:

```bash
# Update system and install dependencies
sudo apt update && sudo apt install -y python3-pip python3-venv git

# Clone the repository
git clone https://github.com/dakshthapar/alpha-lab-core.git
cd alpha-lab-core

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt
```

**Verification**:
```bash
# Check Python version
python3 --version  # Should be 3.10+

# Verify installation
python3 -c "import fyers_apiv3; print('✅ Fyers API installed')"
```

### 1.3 Security Configuration (.env)

> [!CAUTION]
> The `.env` file is NOT in GitHub for security reasons. You must create it manually.

Create the environment file:

```bash
nano .env
```

Paste your Fyers credentials:

```plaintext
FYERS_CLIENT_ID=XS12345-100
# Note: Secret key is only needed on your laptop for token generation
```

**Save and Exit**:
- Save: `Ctrl+O`, then `Enter`
- Exit: `Ctrl+X`

**Verify**:
```bash
cat .env  # Should show your client ID
```

### 1.4 Initial Test Run

Before deploying 24/7, test the harvester manually:

```bash
# Ensure virtual environment is active
source .venv/bin/activate

# Run in foreground (for testing)
python3 data_collection/harvesting/smart_harvester.py --debug
```

You should see:
```
[12:21:30] [INFO] --- HARVESTER ACTIVE ---
[12:21:35] [INFO] Snapshot saved for 5 stocks.
```

Stop with `Ctrl+C` once verified.

---

## Part 2: The Daily Ritual (08:30 AM - 09:10 AM)

> [!WARNING]
> Fyers Access Tokens expire every night at midnight. You **must** regenerate and upload a new token before market open (09:15 IST).

### 2.1 Generate Token (On Your Laptop)

**Time Required**: 2-3 minutes

Open your terminal in the `alpha-lab-core` folder on your **laptop** (not server):

```bash
cd ~/path/to/alpha-lab-core
source .venv/bin/activate  # If using venv locally
python3 data_collection/harvesting/get_token.py
```

**What happens**:
1. A browser window opens (Fyers login page)
2. Log in with your Fyers credentials
3. Authorize the app
4. You'll see a blank page with a URL like: `http://127.0.0.1/?s=ok&code=ABC123...&auth_code=XYZ...`

**Copy the entire URL** and paste it back into the terminal.

**Output**:
```
✅ Access Token Generated Successfully!
Token: eyJ0...  (save this to access_token.txt on server)
```

Copy the token string (starts with `eyJ0`).

### 2.2 Upload Token to Server

You have **two methods** to upload the token:

#### Method A: The "Speedster" ⚡ (Recommended)

Run this **single command** from your laptop terminal. It uploads the token via SSH in one shot:

```bash
# Replace YOUR_TOKEN and YOUR_AWS_IP
echo "YOUR_TOKEN_STRING" | ssh -i alpha-key.pem ubuntu@YOUR_AWS_IP "cat > /home/ubuntu/alpha-lab-core/access_token.txt"
```

**Example**:
```bash
echo "eyJ0eXAiOiJKV1QiLCJhbGc..." | ssh -i alpha-key.pem ubuntu@13.201.45.67 "cat > /home/ubuntu/alpha-lab-core/access_token.txt"
```

**Verification** (optional):
```bash
ssh -i alpha-key.pem ubuntu@YOUR_AWS_IP "cat /home/ubuntu/alpha-lab-core/access_token.txt"
```

#### Method B: The "Manual" 🛠️

If you prefer logging in step-by-step:

1. **SSH into the server**:
   ```bash
   ssh -i alpha-key.pem ubuntu@YOUR_AWS_IP
   ```

2. **Navigate to project folder**:
   ```bash
   cd alpha-lab-core
   ```

3. **Overwrite the old token**:
   ```bash
   # Note the '>' symbol - it overwrites the file
   echo "YOUR_TOKEN_STRING" > access_token.txt
   ```

4. **Verify**:
   ```bash
   cat access_token.txt  # Should show your new token
   ```

### 2.3 Start the Harvester (Background Mode)

Once the token is uploaded, start the harvester in **background mode**:

```bash
# Ensure you're in the project folder
cd ~/alpha-lab-core

# Activate virtual environment
source .venv/bin/activate

# Kill any old process (if running)
pkill -f data_collection/harvesting/smart_harvester.py

# Start in background with logging
nohup python3 -u data_collection/harvesting/smart_harvester.py > harvester.log 2>&1 &
```

**What this does**:
- `nohup`: Keeps running after you disconnect SSH
- `python3 -u`: Unbuffered output (logs appear immediately)
- `> harvester.log`: Saves all output to log file
- `2>&1`: Captures errors too
- `&`: Runs in background

**Verify it's running**:
```bash
ps aux | grep smart_harvester
```

You should see the process listed.

---

## Part 3: Maintenance & Troubleshooting

### 3.1 Monitoring the Harvester

#### Real-Time Log Monitoring

```bash
# SSH into server
ssh -i alpha-key.pem ubuntu@YOUR_AWS_IP

# View live logs
tail -f harvester.log
```

**Good output**:
```
[10:00:05] [INFO] Snapshot saved for 5 stocks.
[10:00:10] [INFO] Snapshot saved for 5 stocks.
```

**Bad output**:
```
[10:00:05] [ERROR] CRASH fetching NSE:HDFCBANK-EQ: Invalid token
[10:00:05] [ERROR] API ERROR
```

#### Check Process Status

```bash
# Is the harvester running?
ps aux | grep smart_harvester

# If no output, it crashed!
```

### 3.2 Common Issues

#### Issue 1: "Invalid Token" or "Unauthorized"

**Cause**: Token expired or incorrect

**Solution**:
1. Regenerate token using `data_collection/harvesting/get_token.py` on laptop
2. Upload new token (see Part 2.2)
3. Restart harvester:
   ```bash
   pkill -f data_collection/harvesting/smart_harvester.py
   cd ~/alpha-lab-core && source .venv/bin/activate
   nohup python3 -u data_collection/harvesting/smart_harvester.py > harvester.log 2>&1 &
   ```

#### Issue 2: "No data collected this cycle"

**Cause**: Market closed, API issues, or network problem

**Solution**:
1. Check if market is open (09:15 - 15:30 IST)
2. Test internet: `ping 8.8.8.8`
3. Check Fyers API status: https://fyers.in

#### Issue 3: Process crashed / not running

**Cause**: Unhandled exception, out of memory, or manual kill

**Solution**:
1. Check logs: `tail -100 harvester.log`
2. Look for Python traceback
3. Restart harvester (see 3.2 Issue 1 solution)

#### Issue 4: Disk full

**Cause**: Too much data accumulated

**Solution**:
```bash
# Check disk usage
df -h

# Check harvested_data size
du -sh ~/alpha-lab-core/harvested_data/

# Delete old files (example: files older than 30 days)
find ~/alpha-lab-core/harvested_data/ -type f -mtime +30 -delete
```

### 3.3 Restarting the Harvester

Whenever you need to restart (after code updates, crashes, etc.):

```bash
# 1. Kill old process
pkill -f data_collection/harvesting/smart_harvester.py

# 2. Navigate to folder
cd ~/alpha-lab-core

# 3. Activate virtual environment
source .venv/bin/activate

# 4. Pull latest code (if updated)
git pull

# 5. Start in background
nohup python3 -u data_collection/harvesting/smart_harvester.py > harvester.log 2>&1 &

# 6. Verify it's running
tail -f harvester.log
```

### 3.4 Updating Code

If you push updates to GitHub:

```bash
# SSH into server
ssh -i alpha-key.pem ubuntu@YOUR_AWS_IP

# Stop harvester
pkill -f data_collection/harvesting/smart_harvester.py

# Pull latest code
cd ~/alpha-lab-core
git pull

# Restart harvester
source .venv/bin/activate
nohup python3 -u data_collection/harvesting/smart_harvester.py > harvester.log 2>&1 &
```

---

## Part 4: Weekly Data Download (Saturday)

Download the week's collected data to your laptop for training:

### 4.1 Download All Data

From your **laptop terminal**:

```bash
# Create local destination folder
mkdir -p ~/my_training_data

# Download entire harvested_data folder
scp -i alpha-key.pem -r ubuntu@YOUR_AWS_IP:/home/ubuntu/alpha-lab-core/harvested_data/ ~/my_training_data/
```

**Example**:
```bash
scp -i alpha-key.pem -r ubuntu@13.201.45.67:/home/ubuntu/alpha-lab-core/harvested_data/ ~/my_training_data/
```

### 4.2 Download Specific Date Range

If you only want recent data:

```bash
# Download last 7 days (example)
scp -i alpha-key.pem ubuntu@YOUR_AWS_IP:/home/ubuntu/alpha-lab-core/harvested_data/market_depth_2025-12-*.csv ~/my_training_data/
```

### 4.3 Verify Downloaded Data

```bash
# Check files
ls -lh ~/my_training_data/harvested_data/

# Count rows in a file
wc -l ~/my_training_data/harvested_data/market_depth_2025-12-22.csv
```

### 4.4 Clean Up Server (Optional)

After downloading, free up space on server:

```bash
# SSH into server
ssh -i alpha-key.pem ubuntu@YOUR_AWS_IP

# Archive old data (optional - create backup)
cd ~/alpha-lab-core
tar -czf harvested_data_backup_$(date +%Y%m%d).tar.gz harvested_data/

# Move backup to safe location or download
scp harvested_data_backup_*.tar.gz ubuntu@YOUR_LAPTOP_IP:/backup/

# Delete old raw files (CAREFUL!)
rm -rf harvested_data/*.csv
```

---

## File Reference

| File | Location | Purpose |
|------|----------|---------|
| `data_collection/harvesting/smart_harvester.py` | AWS & Laptop | Main harvester script. Runs 09:15-15:30 IST. |
| `data_collection/harvesting/get_token.py` | **Laptop Only** | Generates daily Fyers access token. |
| `.env` | AWS & Laptop | Stores `FYERS_CLIENT_ID` (not in Git). |
| `access_token.txt` | **AWS Only** | Stores temporary daily token (expires nightly). |
| `harvester.log` | **AWS Only** | Log file to monitor harvester status. |
| `harvested_data/*.csv` | AWS | Collected market depth data by date. |
| `alpha-key.pem` | **Laptop Only** | AWS SSH key (NEVER upload to server or Git). |

---

## Quick Reference Commands

### Daily Workflow (08:30-09:10 AM)

```bash
# On Laptop: Generate token
python3 data_collection/harvesting/get_token.py

# Upload token (speedster method)
echo "YOUR_TOKEN" | ssh -i alpha-key.pem ubuntu@YOUR_AWS_IP "cat > /home/ubuntu/alpha-lab-core/access_token.txt"

# Verify harvester is running (on server)
ssh -i alpha-key.pem ubuntu@YOUR_AWS_IP "ps aux | grep smart_harvester"
```

### Monitor Status

```bash
# Live logs
ssh -i alpha-key.pem ubuntu@YOUR_AWS_IP "tail -f /home/ubuntu/alpha-lab-core/harvester.log"

# Check process
ssh -i alpha-key.pem ubuntu@YOUR_AWS_IP "ps aux | grep smart_harvester"
```

### Restart Harvester

```bash
# One-liner from laptop
ssh -i alpha-key.pem ubuntu@YOUR_AWS_IP "pkill -f data_collection/harvesting/smart_harvester.py && cd /home/ubuntu/alpha-lab-core && source .venv/bin/activate && nohup python3 -u data_collection/harvesting/smart_harvester.py > harvester.log 2>&1 &"
```

---

## Security Best Practices

> [!CAUTION]
> **Critical Security Rules**

1. **NEVER commit**:
   - `.env` file
   - `access_token.txt`
   - `alpha-key.pem`
   - Any credentials

2. **Restrict SSH access**:
   - Use "My IP" in AWS Security Groups
   - Rotate SSH keys quarterly
   - Disable password authentication

3. **Monitor access**:
   - Check AWS CloudTrail for unusual activity
   - Review SSH logs: `sudo tail /var/log/auth.log`

4. **Token security**:
   - Tokens expire daily (automatic security)
   - Never share tokens
   - Regenerate if compromised

---

## Cost Optimization

**Expected Costs** (AWS t2.micro):
- **Compute**: $0 (Free Tier) or ~$8.50/month
- **Storage**: ~$0.10-0.50/month (10-50 GB)
- **Data Transfer**: ~$0.10/month

**Tips**:
- Use Free Tier (12 months for new accounts)
- Delete old data weekly after download
- Stop instance on weekends if not needed

---

## Support & Troubleshooting

### Issue Escalation Path

1. **Check logs**: `tail -100 harvester.log`
2. **Search GitHub Issues**: [alpha-lab-core/issues](https://github.com/dakshthapar/alpha-lab-core/issues)
3. **Run in debug mode**: `python3 data_collection/harvesting/smart_harvester.py --debug`
4. **Create issue**: Provide logs, error messages, and steps to reproduce

### Contact

- **GitHub Issues**: For bug reports and feature requests
- **Documentation**: [README.md](README.md), [INSTALL_GUIDE.md](INSTALL_GUIDE.md)

---

**Last Updated**: 2025-12-22  
**Version**: 1.0

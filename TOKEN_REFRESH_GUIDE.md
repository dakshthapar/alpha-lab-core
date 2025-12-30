# Fyers Token Refresh Guide

**For Beginners: Understanding Automated Authentication**

This guide explains how to set up automated token refresh for the Fyers API, so you don't have to log in manually every day.

---

## 📚 Table of Contents

- [What Are Tokens?](#what-are-tokens)
- [Quick Start (3 Steps)](#quick-start-3-steps)
- [Option A: AWS Automation (Recommended for 24/7 Cloud)](#option-a-aws-automation-recommended-for-247-cloud)
- [Option B: Manual Refresh (For Local Development)](#option-b-manual-refresh-for-local-development)
- [Troubleshooting](#troubleshooting)
- [FAQ](#faq)

---

## What Are Tokens?

Think of tokens as **temporary passwords** for the Fyers API:

### 🎫 Access Token
- **Validity**: 1 day (expires at 6:00 AM the next morning)
- **Purpose**: Used to fetch market data
- **Problem**: You need to manually login every day to get a new one ❌

### 🔄 Refresh Token
- **Validity**: 15 days
- **Purpose**: Automatically generates new access tokens without manual login
- **Benefit**: Only login ONCE every 15 days! ✅

---

## Quick Start (3 Steps)

### Step 1: Generate Your First Tokens

Run the token generator on your **local machine** (not AWS server):

```bash
cd ~/path/to/alpha-lab-core
python3 data_collection/harvesting/get_token.py
```

**What happens**:
1. A browser opens → log in to Fyers
2. You'll land on a blank page with a long URL
3. Copy the entire URL and paste it into the terminal
4. You'll get **TWO tokens**: access token + refresh token

**Output**:
```
✅ SUCCESS! TOKENS GENERATED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📌 ACCESS TOKEN (Valid for 1 day):
eyJ0eXAiOiJKV1QiLCJhbGc...
✅ Saved to: daily_token.txt

🔄 REFRESH TOKEN (Valid for 15 days):
dGhpcyBpcyBhIHNhbXBsZSByZWZyZXNo...
✅ Saved to: refresh_token.txt
```

### Step 2: Add Your PIN to .env

Fyers requires a **4-digit PIN** to refresh tokens. Add it to your `.env` file:

```bash
# Open .env file
nano .env

# Add this line (replace 1234 with your actual Fyers PIN)
FYERS_PIN=1234

# Save and exit (Ctrl+O, Enter, Ctrl+X)
```

### Step 3: Choose Your Path

- **For 24/7 AWS cloud harvesting** → [Option A: AWS Automation](#option-a-aws-automation-recommended-for-247-cloud)
- **For local development/testing** → [Option B: Manual Refresh](#option-b-manual-refresh-for-local-development)

---

## Option A: AWS Automation (Recommended for 24/7 Cloud)

This setup runs a Lambda function daily at 7:00 AM to refresh your access token automatically.

### Prerequisites

> [!IMPORTANT]
> **All setup steps are done from your LOCAL LAPTOP** using AWS CLI, except where noted.

**1. Install AWS CLI on your local laptop**:

**Arch Linux**:
```bash
sudo pacman -S aws-cli
```

**Ubuntu / Debian**:
```bash
sudo apt install awscli
```

**macOS**:
```bash
brew install awscli
```

**Verify installation**:
```bash
aws --version
# Should show: aws-cli/2.x.x or higher
```

**2. AWS Account** with CLI configured **on your local laptop**:

> [!TIP]
> Before configuring, verify AWS CLI is installed: `aws --version`

   ```bash
   aws configure
   # Enter your AWS Access Key ID
   # Enter your AWS Secret Access Key
   # Default region: ap-south-1
   ```

   **Verify configuration worked**:
   ```bash
   aws sts get-caller-identity
   # Should show your AWS account ID and user info
   ```

**3. Install boto3** on your local laptop:
   ```bash
   uv pip install boto3
   ```

### Step A1: Store Your PIN Securely

**📍 Run from: LOCAL LAPTOP**

```bash
aws secretsmanager create-secret \
    --name FYERS_PIN \
    --secret-string "1234" \
    --region ap-south-1

# Replace 1234 with your actual PIN
```

### Step A2: Deploy Lambda Function (Automatic Upload)

**📍 Run from: LOCAL LAPTOP** (from your `alpha-lab-core` project folder)

> [!NOTE]
> The deployment script now **automatically** reads credentials from your `.env` file and token files, then uploads them to AWS. No manual upload needed!

**Prerequisites:**
- `.env` file must contain: `FYERS_CLIENT_ID`, `FYERS_SECRET_KEY`, `FYERS_PIN`
- Token files must exist: `refresh_token.txt`, `access_token.txt` (or `daily_token.txt`)

**Run deployment:**
```bash
python data_collection/harvesting/deploy_lambda_refresh.py
```

**What it does automatically:**
1. 📤 Uploads credentials from `.env` to AWS SSM
2. 📤 Uploads tokens from files to AWS SSM  
3. 📤 Uploads PIN to AWS Secrets Manager
4. 📦 Creates deployment package with dependencies
5. 🚀 Deploys/updates Lambda function
6. ⏰ Sets up EventBridge daily trigger

**What it does**:
- Creates a Lambda function called `FyersTokenRefresh`
- Sets up daily trigger at 7:00 AM IST
- Configures permissions to read/write SSM parameters

### Step A3: Test Lambda Manually

**📍 Run from: LOCAL LAPTOP**

```bash
aws lambda invoke \
    --function-name FyersTokenRefresh \
    --region ap-south-1 \
    output.json

# Check the result
cat output.json
```

**Expected output**:
```json
{"statusCode": 200, "body": "{\"message\": \"✅ Token refresh completed successfully!\"}"}
```

### Step A4: Update Harvester to Use AWS

**📍 Run from: AWS SERVER** (SSH into your AWS instance)

When starting the harvester on AWS, add the `--use-ssm` flag:

```bash
# SSH into AWS server
ssh -i alpha-key.pem ubuntu@YOUR_AWS_IP

# Start harvester with SSM mode
cd ~/alpha-lab-core
source .venv/bin/activate
nohup python3 -u data_collection/harvesting/smart_harvester.py --use-ssm > harvester.log 2>&1 &
```

### 🎉 Done! What Happens Now?

- **Every 7:00 AM**: Lambda runs automatically and refreshes your access token in SSM
- **Harvester behavior**: The smart harvester now **pauses** when market closes instead of exiting, and automatically **resumes the next trading day at 9:15 AM** with the freshly updated token
- **Token pickup**: After any wait period (startup or market close), the harvester reloads the token from SSM to ensure it's always using the latest version
- **Every 15 days**: You manually run `get_token.py` once to get a new refresh token

> [!NOTE]
> The harvester intelligently picks up token updates whether it's waiting for initial market open or resuming after market close.

---

## Option B: Manual Refresh (For Local Development)

If you're not using AWS, you can manually refresh tokens when needed.

### B1: Generate Initial Tokens

```bash
python3 data_collection/harvesting/get_token.py
```

### B2: Refresh Access Token (When Expired)

```bash
python3 data_collection/harvesting/refresh_token.py --local
```

**What it does**:
- Reads `refresh_token.txt` from current folder
- Calls Fyers API to get a new access token
- Saves new token to `access_token.txt`

### B3: Run Harvester

```bash
python3 data_collection/harvesting/smart_harvester.py
# Uses access_token.txt by default
```

### B4: Repeat Every 15 Days

When your refresh token expires (after 15 days), run Step B1 again.

---

## Troubleshooting

### Issue: "refresh_token not found in response"

**Cause**: Refresh tokens may not be enabled for your Fyers app.

**Solution**:
1. Check Fyers API settings at https://myapi.fyers.in/apps
2. Ensure your app has "Refresh Token" permission enabled
3. If not available, contact Fyers support

### Issue: "Invalid PIN" error

**Cause**: Wrong PIN or PIN not set

**Solution**:
1. Verify your PIN in the Fyers mobile app
2. Update `.env` file with correct PIN:
   ```bash
   FYERS_PIN=YOUR_CORRECT_PIN
   ```
3. If using AWS, update Secrets Manager:
   ```bash
   aws secretsmanager update-secret --secret-id FYERS_PIN --secret-string "YOUR_CORRECT_PIN"
   ```

### Issue: "Refresh token expired"

**Cause**: 15 days have passed

**Solution**:
1. Run `get_token.py` to get a new 15-day refresh token
2. Upload new refresh token to AWS (if using cloud):
   ```bash
   python data_collection/harvesting/aws_ssm_helper.py set \
       --name FYERS_REFRESH_TOKEN \
       --value <new_refresh_token>
   ```

### Issue: Lambda function fails

**Cause**: Missing permissions or credentials

**Solution**:
1. Check CloudWatch Logs:
   ```bash
   aws logs tail /aws/lambda/FyersTokenRefresh --follow --region ap-south-1
   ```
2. Verify all SSM parameters are set:
   ```bash
   python data_collection/harvesting/aws_ssm_helper.py list
   ```
3. Verify PIN is in Secrets Manager:
   ```bash
   aws secretsmanager get-secret-value --secret-id FYERS_PIN --region ap-south-1
   ```

### Issue: "boto3 not installed" (AWS mode)

**Solution**:
```bash
uv pip install boto3
```

---

## FAQ

### Q: Why 15 days? Can I extend it?

**A**: This is a Fyers API limitation. Refresh tokens expire after 15 days for security reasons. You cannot extend this period.

### Q: Is my PIN secure in AWS Secrets Manager?

**A**: Yes! AWS Secrets Manager encrypts your PIN at rest using AES-256 encryption. Only your Lambda function can access it via IAM permissions.

### Q: What happens if I forget to refresh after 15 days?

**A**: Your harvester will stop working after the access token expires (1 day after the last successful refresh). Simply run `get_token.py` again to restart the 15-day cycle.

### Q: Can I use this for live trading?

**A**: This guide is for **data collection only**. Live trading requires additional risk management and is outside the scope of this project.

### Q: Do I need AWS for local development?

**A**: No! You can use **Option B: Manual Refresh** for local development. AWS is only needed for 24/7 cloud deployment.

### Q: How much does AWS Lambda cost?

**A**: **FREE** for most users! AWS Free Tier includes:
- 1 million Lambda requests per month (you'll use ~30/month)
- 400,000 GB-seconds of compute time (you'll use ~1 GB-second/day)

After Free Tier: ~$0.02/month

### Q: What if my refresh fails?

**A**: The harvester will continue using the old token until it expires. Check CloudWatch Logs to debug the issue, then manually run `get_token.py` if needed.

### Q: Can I see when my tokens expire?

**A**: Yes! Fyers tokens include expiry information. Use this Python snippet:
```python
import jwt
token = "<your_access_token>"
decoded = jwt.decode(token, options={"verify_signature": False})
print("Expires:", decoded['exp'])
```

---

## Security Checklist

✅ **Never commit**:
- `.env` file
- `access_token.txt`
- `refresh_token.txt`
- `daily_token.txt`

✅ **Always verify**:
- `.gitignore` includes all sensitive files
- AWS IAM roles have minimal permissions
- PIN is stored in Secrets Manager (encrypted)

✅ **Recommended practices**:
- Rotate refresh tokens every week (instead of waiting 15 days)
- Set up CloudWatch alarms for Lambda failures
- Monitor SSM parameter access in CloudTrail

---

## Support

**Have questions**?
- 📖 Read the [CLOUD_HARVESTER_GUIDE.md](CLOUD_HARVESTER_GUIDE.md) for AWS deployment details
- 🐛 Check [GitHub Issues](https://github.com/dakshthapar/alpha-lab-core/issues)
- 💬 Start a [Discussion](https://github.com/dakshthapar/alpha-lab-core/discussions)

---

**Last Updated**: 2025-12-30  
**Version**: 1.0

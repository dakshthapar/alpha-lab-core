"""
Refresh Token Script - AWS Lambda Function
Automatically refreshes Fyers access token using a refresh token.

This script is designed to run daily on AWS Lambda (triggered at 7:00 AM IST)
to generate a new access_token without manual browser login.

Token Lifecycle:
- Access Token: Valid for 1 day (expires 6:00 AM next day)
- Refresh Token: Valid for 15 days (requires manual refresh after expiry)

AWS Requirements:
- boto3 (AWS SDK)
- SSM Parameter Store: FYERS_REFRESH_TOKEN, FYERS_CLIENT_ID, FYERS_SECRET_KEY
- Secrets Manager: FYERS_PIN (4-digit PIN)
"""

import os
import json
import hashlib
import requests

def get_ssm_parameter(parameter_name, region='ap-south-1'):
    """Retrieve parameter from AWS SSM Parameter Store"""
    try:
        import boto3
        ssm = boto3.client('ssm', region_name=region)
        response = ssm.get_parameter(Name=parameter_name, WithDecryption=True)
        return response['Parameter']['Value']
    except Exception as e:
        print(f"❌ Error retrieving {parameter_name} from SSM: {e}")
        return None

def get_secret(secret_name, region='ap-south-1'):
    """Retrieve secret from AWS Secrets Manager"""
    try:
        import boto3
        secrets = boto3.client('secretsmanager', region_name=region)
        response = secrets.get_secret_value(SecretId=secret_name)
        return response['SecretString']
    except Exception as e:
        print(f"❌ Error retrieving {secret_name} from Secrets Manager: {e}")
        return None

def put_ssm_parameter(parameter_name, value, region='ap-south-1'):
    """Store parameter in AWS SSM Parameter Store"""
    try:
        import boto3
        ssm = boto3.client('ssm', region_name=region)
        ssm.put_parameter(
            Name=parameter_name,
            Value=value,
            Type='SecureString',
            Overwrite=True
        )
        print(f"✅ Updated {parameter_name} in SSM")
        return True
    except Exception as e:
        print(f"❌ Error storing {parameter_name} in SSM: {e}")
        return False

def refresh_access_token(client_id, secret_key, refresh_token, pin):
    """
    Generate new access token using refresh token.
    
    Args:
        client_id: Fyers App ID (e.g., XS12345-100)
        secret_key: Fyers Secret Key
        refresh_token: Valid refresh token (15-day validity)
        pin: 4-digit Fyers PIN
    
    Returns:
        New access token or None on failure
    """
    # Step 1: Generate appIdHash (SHA256 of client_id:secret_key)
    hash_payload = f"{client_id}:{secret_key}"
    app_id_hash = hashlib.sha256(hash_payload.encode()).hexdigest()
    
    # Step 2: Prepare refresh request
    url = "https://api-t1.fyers.in/api/v3/validate-refresh-token"
    payload = {
        "grant_type": "refresh_token",
        "appIdHash": app_id_hash,
        "refresh_token": refresh_token,
        "pin": pin
    }
    
    print(f"🔄 Requesting new access token from Fyers API...")
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        data = response.json()
        
        if data.get("s") == "ok":
            new_access_token = data.get("access_token")
            print(f"✅ New access token generated successfully!")
            return new_access_token
        else:
            error_msg = data.get("message", "Unknown error")
            print(f"❌ Error refreshing token: {error_msg}")
            print(f"Full response: {data}")
            return None
    except Exception as e:
        print(f"❌ Exception during API call: {e}")
        return None

def lambda_handler(event, context):
    """
    AWS Lambda entry point.
    
    This function is triggered daily by EventBridge (CloudWatch Events).
    It retrieves credentials from SSM/Secrets Manager, refreshes the token,
    and stores the new access token back in SSM.
    """
    print("="*70)
    print("🚀 Fyers Token Refresh - AWS Lambda")
    print("="*70)
    
    region = os.environ.get('AWS_REGION', 'ap-south-1')
    
    # Step 1: Retrieve credentials from AWS
    print("\n📥 Retrieving credentials from AWS...")
    client_id = get_ssm_parameter('FYERS_CLIENT_ID', region)
    secret_key = get_ssm_parameter('FYERS_SECRET_KEY', region)
    refresh_token = get_ssm_parameter('FYERS_REFRESH_TOKEN', region)
    pin = get_secret('FYERS_PIN', region)
    
    if not all([client_id, secret_key, refresh_token, pin]):
        error_msg = "❌ CRITICAL: Missing credentials in AWS SSM/Secrets Manager"
        print(error_msg)
        return {
            'statusCode': 500,
            'body': json.dumps({'error': error_msg})
        }
    
    print("✅ All credentials retrieved successfully")
    
    # Step 2: Refresh access token
    print("\n🔄 Refreshing access token...")
    new_access_token = refresh_access_token(client_id, secret_key, refresh_token, pin)
    
    if not new_access_token:
        error_msg = "❌ Failed to refresh access token"
        print(error_msg)
        return {
            'statusCode': 500,
            'body': json.dumps({'error': error_msg})
        }
    
    # Step 3: Store new access token in SSM
    print("\n💾 Storing new access token in SSM...")
    if put_ssm_parameter('FYERS_ACCESS_TOKEN', new_access_token, region):
        success_msg = "✅ Token refresh completed successfully!"
        print("\n" + "="*70)
        print(success_msg)
        print("="*70)
        return {
            'statusCode': 200,
            'body': json.dumps({'message': success_msg})
        }
    else:
        error_msg = "❌ Failed to store new token in SSM"
        print(error_msg)
        return {
            'statusCode': 500,
            'body': json.dumps({'error': error_msg})
        }

def main_local():
    """
    Local testing mode (without AWS).
    Reads credentials from environment variables or .env file.
    """
    from dotenv import load_dotenv
    load_dotenv()
    
    print("="*70)
    print("🔄 Fyers Token Refresh - LOCAL MODE")
    print("="*70)
    
    # Read credentials from .env
    client_id = os.getenv("FYERS_CLIENT_ID")
    secret_key = os.getenv("FYERS_SECRET_KEY")
    pin = os.getenv("FYERS_PIN")
    
    # Read refresh token from file
    try:
        with open("refresh_token.txt", "r") as f:
            refresh_token = f.read().strip()
    except FileNotFoundError:
        print("❌ Error: refresh_token.txt not found.")
        print("   Run get_token.py first to generate tokens.")
        return
    
    if not all([client_id, secret_key, refresh_token, pin]):
        print("❌ Error: Missing credentials in .env file")
        print("   Required: FYERS_CLIENT_ID, FYERS_SECRET_KEY, FYERS_PIN")
        return
    
    # Refresh token
    new_access_token = refresh_access_token(client_id, secret_key, refresh_token, pin)
    
    if new_access_token:
        # Save to file
        with open("access_token.txt", "w") as f:
            f.write(new_access_token)
        print(f"\n✅ New access token saved to: access_token.txt")
        print(f"\n📌 Token Preview: {new_access_token[:50]}...")
    else:
        print("\n❌ Token refresh failed. Check error messages above.")

if __name__ == "__main__":
    import sys
    if "--local" in sys.argv:
        main_local()
    else:
        # Simulate Lambda execution locally
        result = lambda_handler({}, {})
        print(f"\n📊 Lambda Result: {result}")

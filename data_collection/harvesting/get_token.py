import os
import webbrowser
from fyers_apiv3 import fyersModel
from dotenv import load_dotenv

# 1. Load Secrets from .env
load_dotenv()

# 2. Get Keys securely
client_id = os.getenv("FYERS_CLIENT_ID")
secret_key = os.getenv("FYERS_SECRET_KEY")
redirect_uri = "https://trade.fyers.in/api-login/redirect-uri/index.html"
response_type = "code"  
grant_type = "authorization_code"  

def main():
    # Validation
    if not client_id or not secret_key:
        print("CRITICAL ERROR: Credentials not found in .env file.")
        print("Please ensure FYERS_CLIENT_ID and FYERS_SECRET_KEY are set.")
        return

    # 3. Create Session
    session = fyersModel.SessionModel(
        client_id=client_id,
        secret_key=secret_key,
        redirect_uri=redirect_uri,
        response_type=response_type,
        grant_type=grant_type
    )

    # 4. Generate Login Link
    login_url = session.generate_authcode()
    print("\n--- OPENING BROWSER FOR LOGIN ---")
    print(f"Link: {login_url}")
    webbrowser.open(login_url)

    # 5. User Manual Input
    print("\nINSTRUCTIONS:")
    print("1. Log in to Fyers in the browser.")
    print("2. Copy the FULL URL of the blank page you land on.")
    
    auth_code_url = input("\nPASTE THE URL HERE: ").strip()

    # 6. Extract Code & Generate Token
    try:
        if "auth_code=" in auth_code_url:
            auth_code = auth_code_url.split("auth_code=")[1].split("&")[0]
        else:
            print("Error: URL does not contain 'auth_code'.")
            return
    except Exception as e:
        print(f"Error parsing URL: {e}")
        return

    session.set_token(auth_code)
    response = session.generate_token()

    if "access_token" in response:
        access_token = response["access_token"]
        refresh_token = response.get("refresh_token", "")
        
        print("\n" + "="*70)
        print("✅ SUCCESS! TOKENS GENERATED")
        print("="*70)
        
        print("\n📌 ACCESS TOKEN (Valid for 1 day, expires at 6:00 AM tomorrow):")
        print("-" * 70)
        print(access_token)
        print("-" * 70)
        
        # Save access token locally
        with open("daily_token.txt", "w") as f:
            f.write(access_token)
        print("✅ Saved to: daily_token.txt")
        
        if refresh_token:
            print("\n🔄 REFRESH TOKEN (Valid for 15 days - enables automated refresh):")
            print("-" * 70)
            print(refresh_token)
            print("-" * 70)
            
            # Save refresh token locally
            with open("refresh_token.txt", "w") as f:
                f.write(refresh_token)
            print("✅ Saved to: refresh_token.txt")
            
            print("\n" + "="*70)
            print("📋 NEXT STEPS FOR AWS AUTOMATION (15-Day Auto-Refresh)")
            print("="*70)
            print("\n1️⃣  Upload REFRESH TOKEN to AWS (for automated daily refresh):")
            print("   python data_collection/harvesting/aws_ssm_helper.py set \\")
            print("       --name FYERS_REFRESH_TOKEN --value <paste_refresh_token_here>")
            print("\n2️⃣  Upload ACCESS TOKEN to AWS (for immediate use):")
            print("   python data_collection/harvesting/aws_ssm_helper.py set \\")
            print("       --name FYERS_ACCESS_TOKEN --value <paste_access_token_here>")
            print("\n3️⃣  Deploy Lambda function (one-time setup):")
            print("   python data_collection/harvesting/deploy_lambda_refresh.py")
            print("\n💡 TIP: You only need to do this ONCE every 15 days!")
            print("   Lambda will auto-refresh your access token daily at 7:00 AM.")
            print("\n⚠️  SECURITY: These files are in .gitignore - NEVER commit them!")
            print("="*70)
        else:
            print("\n⚠️  WARNING: No refresh_token in response.")
            print("   You may need to enable refresh tokens in Fyers API settings.")
        
        print("\n✅ For local development, tokens are ready in the current folder.")
        print("   DO NOT COMMIT: daily_token.txt or refresh_token.txt")
    else:
        print("\n❌ Failed to generate token:")
        print(response)

if __name__ == "__main__":
    main()
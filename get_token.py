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
        token = response["access_token"]
        print("\nSUCCESS! HERE IS YOUR ACCESS TOKEN:")
        print("-" * 60)
        print(token)
        print("-" * 60)
        
        # Save locally for reference
        with open("daily_token.txt", "w") as f:
            f.write(token)
        print("Saved to daily_token.txt (DO NOT COMMIT THIS FILE)")
    else:
        print("Failed to generate token:")
        print(response)

if __name__ == "__main__":
    main()
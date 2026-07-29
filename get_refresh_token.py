import sys
import dropbox
from dropbox import DropboxOAuth2FlowNoRedirect

def generate_refresh_token():
    print("==================================================")
    print("      Dropbox OAuth 2 Refresh Token Generator")
    print("==================================================")
    app_key = input("Enter your Dropbox App Key: ").strip()
    app_secret = input("Enter your Dropbox App Secret: ").strip()

    if not app_key or not app_secret:
        print("Error: App Key and App Secret are required.")
        return

    auth_flow = DropboxOAuth2FlowNoRedirect(
        app_key=app_key,
        app_secret=app_secret,
        token_access_type='offline'  # 'offline' generates a non-expiring refresh token
    )

    authorize_url = auth_flow.start()
    print("\n1. Open this URL in your web browser:")
    print(f"   {authorize_url}\n")
    print("2. Log in, click 'Allow', and copy the authorization code.")
    auth_code = input("\nEnter the Authorization Code here: ").strip()

    try:
        oauth_result = auth_flow.finish(auth_code)
        print("\n==================================================")
        print(" SUCCESS! Your Non-Expiring Credentials:")
        print("==================================================")
        print(f"App Key:       {app_key}")
        print(f"App Secret:    {app_secret}")
        print(f"Refresh Token: {oauth_result.refresh_token}")
        print("==================================================")
        print("You can now enter these three values into PySync Settings!")
    except Exception as e:
        print(f"\nFailed to obtain refresh token: {e}")

if __name__ == "__main__":
    generate_refresh_token()

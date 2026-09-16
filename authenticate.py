"""Interactive Google OAuth 2.0 CLI Authenticator.

Run this script directly in your terminal to authenticate your Google Account:
    python authenticate.py
"""

from __future__ import annotations

import sys
from pathlib import Path
from google_auth_oauthlib.flow import InstalledAppFlow
from src.auth.gmail_oauth import GMAIL_SCOPES, DEFAULT_CREDENTIALS_PATH, DEFAULT_TOKEN_PATH
from src.auth.gmail_oauth import GmailOAuthHandler


def authenticate() -> None:
    print("=" * 60)
    print(" Polarisk Spend Intelligence - Google OAuth 2.0 Setup")
    print("=" * 60)

    if not DEFAULT_CREDENTIALS_PATH.exists():
        print(f"\n❌ ERROR: '{DEFAULT_CREDENTIALS_PATH}' not found in project root.")
        print("Please ensure credentials.json is placed in this directory.\n")
        sys.exit(1)

    print(f"\n1. Loaded OAuth Client Secrets from '{DEFAULT_CREDENTIALS_PATH}'")
    print("2. Scope requested: https://www.googleapis.com/auth/gmail.readonly (STRICTLY READ-ONLY)")
    print("3. Starting authorization flow...")

    flow = InstalledAppFlow.from_client_secrets_file(
        str(DEFAULT_CREDENTIALS_PATH),
        scopes=GMAIL_SCOPES,
    )

    print("\nOpening your browser for Google sign-in...")
    print("If your browser does not open automatically, copy and paste the URL shown below into your browser.\n")

    # run_local_server will print the URL to stdout and open browser
    creds = flow.run_local_server(port=8080, prompt="consent", access_type="offline")

    if creds:
        with open(DEFAULT_TOKEN_PATH, "w", encoding="utf-8") as f:
            f.write(creds.to_json())
        print(f"\n✅ Token successfully saved to '{DEFAULT_TOKEN_PATH}'.")

        handler = GmailOAuthHandler()
        email = handler.get_user_email()
        if email:
            print(f"✅ Successfully authenticated as: {email}")
        print("\nYou can now launch Streamlit:")
        print("    streamlit run app.py\n")
        print("=" * 60)


if __name__ == "__main__":
    authenticate()

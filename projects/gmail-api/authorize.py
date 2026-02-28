#!/usr/bin/env python3
"""
Gmail API OAuth2 authorization (headless-friendly).

Generates an authorization URL, prompts you to visit it in a browser,
then exchanges the authorization code for a token stored in token.json.

Usage:
    python3 authorize.py
    python3 authorize.py --force   # Re-authorize even if token exists
"""

import argparse
import os
import json
import sys

from google_auth_oauthlib.flow import InstalledAppFlow

DIR = os.path.dirname(os.path.abspath(__file__))
CREDENTIALS_FILE = "/home/albert/.openclaw/workspace/credentials/google_credentials.json"
TOKEN_FILE = os.path.join(DIR, "token.json")
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
]


def main():
    parser = argparse.ArgumentParser(description="Authorize Gmail API (read + send)")
    parser.add_argument(
        "--force", action="store_true", help="Re-authorize even if token.json exists"
    )
    args = parser.parse_args()

    if os.path.exists(TOKEN_FILE) and not args.force:
        print(f"Already authorized (token at {TOKEN_FILE}).")
        print("Use --force to re-authorize.")
        return

    if not os.path.exists(CREDENTIALS_FILE):
        print(f"ERROR: OAuth credentials not found at {CREDENTIALS_FILE}")
        print("Download from Google Cloud Console > APIs & Services > Credentials")
        sys.exit(1)

    flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
    flow.redirect_uri = "urn:ietf:wg:oauth:2.0:oob"

    auth_url, _ = flow.authorization_url(
        access_type="offline", prompt="consent"
    )

    print("\n=== Gmail API Authorization ===\n")
    print("1. Open this URL in a browser:\n")
    print(f"   {auth_url}\n")
    print("2. Sign in and grant Gmail read + send access.")
    print("3. Copy the authorization code and paste it below.\n")

    code = input("Authorization code: ").strip()
    if not code:
        print("No code entered. Aborting.")
        sys.exit(1)

    flow.fetch_token(code=code)
    creds = flow.credentials

    with open(TOKEN_FILE, "w") as f:
        f.write(creds.to_json())

    print(f"\nToken saved to {TOKEN_FILE}")
    print("You can now use list_messages.py, read_message.py, and send_email.py.")


if __name__ == "__main__":
    main()

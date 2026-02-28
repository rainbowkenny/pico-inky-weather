"""Shared Gmail API authentication helper."""

import os
import json
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

DIR = os.path.dirname(os.path.abspath(__file__))
CREDENTIALS_FILE = "/home/albert/.openclaw/workspace/credentials/google_credentials.json"
TOKEN_FILE = os.path.join(DIR, "token.json")
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


def get_credentials():
    """Load or refresh Gmail API credentials. Raises if not authorized."""
    if not os.path.exists(TOKEN_FILE):
        raise FileNotFoundError(
            f"No token found at {TOKEN_FILE}. Run: python3 authorize.py"
        )

    creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(TOKEN_FILE, "w") as f:
            f.write(creds.to_json())

    return creds


def get_gmail_service():
    """Return an authorized Gmail API service instance."""
    from googleapiclient.discovery import build

    creds = get_credentials()
    return build("gmail", "v1", credentials=creds)

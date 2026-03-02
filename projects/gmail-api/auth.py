"""Shared Gmail API authentication helper."""

import datetime
import os
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

CREDENTIALS_FILE = "/home/albert/.openclaw/workspace/credentials/google_credentials.json"
TOKEN_FILE = "/home/albert/.openclaw/workspace/credentials/google_token.json"
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.modify",
]

# Proactively refresh when token expires within this window.
_REFRESH_MARGIN = datetime.timedelta(minutes=5)


def _seconds_to_expiry(expiry):
    """Return seconds until expiry, handling naive/aware datetimes safely."""
    if not expiry:
        return None
    if expiry.tzinfo is None:
        now = datetime.datetime.utcnow()
    else:
        now = datetime.datetime.now(datetime.timezone.utc)
        expiry = expiry.astimezone(datetime.timezone.utc)
    return (expiry - now).total_seconds()


def get_credentials():
    """Load, proactively refresh, and return Gmail API credentials.

    Raises FileNotFoundError if no token file exists.
    """
    if not os.path.exists(TOKEN_FILE):
        raise FileNotFoundError(
            f"No token found at {TOKEN_FILE}. Run: python3 authorize.py"
        )

    creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    secs_left = _seconds_to_expiry(creds.expiry) if creds else None
    needs_refresh = (
        creds
        and creds.refresh_token
        and (
            creds.expired
            or (secs_left is not None and secs_left < _REFRESH_MARGIN.total_seconds())
        )
    )
    if needs_refresh:
        creds.refresh(Request())
        with open(TOKEN_FILE, "w") as f:
            f.write(creds.to_json())

    return creds


def get_gmail_service():
    """Return an authorized Gmail API service instance."""
    from googleapiclient.discovery import build

    creds = get_credentials()
    return build("gmail", "v1", credentials=creds)

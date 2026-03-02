#!/usr/bin/env python3
"""
Google Gmail API healthcheck.

Validates token presence, scopes, expiry, and optionally makes a live
Gmail API call to confirm connectivity.

Usage:
    python3 google_healthcheck.py           # full check (includes live API call)
    python3 google_healthcheck.py --dry-run # token/scope check only, no API call
"""

import argparse
import datetime
import json
import os
import sys

from auth import CREDENTIALS_FILE, TOKEN_FILE, SCOPES


def _ok(msg):
    print(f"  [OK]   {msg}")


def _warn(msg):
    print(f"  [WARN] {msg}")


def _fail(msg):
    print(f"  [FAIL] {msg}")


def check_token_file():
    """Check that the token file exists and is readable JSON."""
    print("Token file")
    if not os.path.exists(TOKEN_FILE):
        _fail(f"Not found: {TOKEN_FILE}")
        return None
    _ok(f"Path: {TOKEN_FILE}")

    try:
        with open(TOKEN_FILE) as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        _fail(f"Cannot read token: {exc}")
        return None

    _ok("Valid JSON")
    return data


def check_scopes(token_data):
    """Compare granted scopes against required scopes.

    Returns True when required scopes are present; False otherwise.
    """
    print("Scopes")
    granted = set(token_data.get("scopes", []))
    required = set(SCOPES)

    if not granted:
        _warn("No scopes recorded in token file")
        return False

    missing = required - granted
    extra = granted - required
    if not missing:
        _ok(f"All required scopes present ({len(required)})")
    else:
        _fail(f"Missing scopes: {', '.join(sorted(missing))}")
    if extra:
        _warn(f"Extra scopes: {', '.join(sorted(extra))}")

    for s in sorted(required):
        tag = "OK" if s in granted else "MISSING"
        print(f"         [{tag}] {s}")

    return not missing


def check_expiry(token_data):
    """Report token expiry and whether a refresh token is present."""
    print("Token expiry")
    expiry_str = token_data.get("expiry")
    if expiry_str:
        try:
            expiry = datetime.datetime.fromisoformat(expiry_str.rstrip("Z"))
            now = datetime.datetime.utcnow()
            delta = expiry - now
            if delta.total_seconds() > 0:
                _ok(f"Expires in {delta}")
            else:
                _warn(f"Expired {-delta} ago (will auto-refresh)")
        except ValueError:
            _warn(f"Cannot parse expiry: {expiry_str}")
    else:
        _warn("No expiry field in token")

    if token_data.get("refresh_token"):
        _ok("Refresh token present")
    else:
        _fail("No refresh token — re-authorization required")


def check_credentials_file():
    """Check that the OAuth client credentials file exists."""
    print("Credentials file")
    if os.path.exists(CREDENTIALS_FILE):
        _ok(f"Path: {CREDENTIALS_FILE}")
    else:
        _warn(f"Not found: {CREDENTIALS_FILE} (needed for re-authorization)")


def check_live_api():
    """Make a lightweight Gmail API call to verify connectivity."""
    print("Live API check")
    try:
        from auth import get_gmail_service
        service = get_gmail_service()
        results = service.users().messages().list(userId="me", maxResults=1).execute()
        count = results.get("resultSizeEstimate", 0)
        _ok(f"Gmail API reachable — ~{count} messages estimated")
        return True
    except Exception as exc:
        _fail(f"Gmail API call failed: {exc}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Gmail API healthcheck")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Check token and scopes only, skip live API call",
    )
    args = parser.parse_args()

    print("=== Gmail API Healthcheck ===\n")

    ok = True
    token_data = check_token_file()
    print()

    if token_data:
        if not check_scopes(token_data):
            ok = False
        print()
        check_expiry(token_data)
        print()
    else:
        ok = False

    check_credentials_file()
    print()

    if not args.dry_run and token_data:
        if not check_live_api():
            ok = False
        print()

    if ok:
        print("Result: HEALTHY")
    else:
        print("Result: ISSUES FOUND")
        sys.exit(1)


if __name__ == "__main__":
    main()

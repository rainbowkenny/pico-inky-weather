#!/usr/bin/env python3
"""
Add a confirmed weekend plan to the Family Google Calendar.
Usage: python3 confirm_and_book.py --title "..." --date "2026-03-01" --time "10:00" --location "..." --duration 3
       python3 confirm_and_book.py --help
"""

import argparse
import json
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone

CREDS_FILE = "/home/albert/.openclaw/workspace/credentials/google_credentials.json"
TOKEN_FILE = "/home/albert/.openclaw/workspace/credentials/google_token.json"
FAMILY_CALENDAR_ID = "family03011953462043037676@group.calendar.google.com"
TOKEN_URI = "https://oauth2.googleapis.com/token"
GCAL_BASE = "https://www.googleapis.com/calendar/v3"


def load_token():
    with open(TOKEN_FILE) as f:
        return json.load(f)


def save_token(token):
    with open(TOKEN_FILE, "w") as f:
        json.dump(token, f, indent=2)


def refresh_token(token):
    with open(CREDS_FILE) as f:
        creds = json.load(f)["installed"]
    data = urllib.parse.urlencode({
        "client_id": creds["client_id"],
        "client_secret": creds["client_secret"],
        "refresh_token": token["refresh_token"],
        "grant_type": "refresh_token",
    }).encode()
    req = urllib.request.Request(TOKEN_URI, data=data, method="POST")
    with urllib.request.urlopen(req, timeout=15) as resp:
        new_token = json.loads(resp.read())
    if "refresh_token" not in new_token:
        new_token["refresh_token"] = token["refresh_token"]
    new_token["obtained_at"] = int(time.time())
    save_token(new_token)
    return new_token


def get_access_token():
    token = load_token()
    obtained_at = token.get("obtained_at", 0)
    expires_in = token.get("expires_in", 3600)
    if int(time.time()) >= obtained_at + expires_in - 60:
        token = refresh_token(token)
    return token["access_token"]


def create_event(access_token, calendar_id, event_body, retry=True):
    url = f"{GCAL_BASE}/calendars/{urllib.parse.quote(calendar_id)}/events"
    body = json.dumps(event_body).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        if e.code == 401 and retry:
            token = load_token()
            new_token = refresh_token(token)
            return create_event(new_token["access_token"], calendar_id, event_body, retry=False)
        body_text = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {e.code}: {body_text}")


def parse_datetime(date_str, time_str, timezone_str="Europe/London"):
    """Parse date + time into RFC3339 datetime string."""
    dt_str = f"{date_str}T{time_str}:00"
    try:
        dt = datetime.strptime(dt_str, "%Y-%m-%dT%H:%M:%S")
    except ValueError:
        raise ValueError(f"Invalid date/time: {date_str} {time_str}. Use YYYY-MM-DD and HH:MM.")
    # Return with timezone offset; we'll use the calendarTimeZone via timeZone field
    return dt.strftime("%Y-%m-%dT%H:%M:%S"), timezone_str


def main():
    parser = argparse.ArgumentParser(
        description="Add a confirmed plan to the Family Google Calendar."
    )
    parser.add_argument("--title", required=True, help="Event title")
    parser.add_argument("--date", required=True, help="Date in YYYY-MM-DD format")
    parser.add_argument("--time", default="10:00", help="Start time HH:MM (default: 10:00)")
    parser.add_argument("--location", default="", help="Location/venue")
    parser.add_argument("--duration", type=float, default=3.0, help="Duration in hours (default: 3)")
    parser.add_argument("--description", default="", help="Event description/notes")
    parser.add_argument("--calendar", default=FAMILY_CALENDAR_ID,
                        help=f"Calendar ID (default: Family calendar)")
    args = parser.parse_args()

    # Validate date
    try:
        datetime.strptime(args.date, "%Y-%m-%d")
    except ValueError:
        print(json.dumps({"status": "error", "reason": "Invalid date format. Use YYYY-MM-DD."}))
        sys.exit(1)

    # Validate time
    try:
        datetime.strptime(args.time, "%H:%M")
    except ValueError:
        print(json.dumps({"status": "error", "reason": "Invalid time format. Use HH:MM."}))
        sys.exit(1)

    if args.duration <= 0 or args.duration > 24:
        print(json.dumps({"status": "error", "reason": "Duration must be between 0 and 24 hours."}))
        sys.exit(1)

    # Build start/end
    start_str, tz = parse_datetime(args.date, args.time)
    # Calculate end time
    start_dt = datetime.strptime(start_str, "%Y-%m-%dT%H:%M:%S")
    from datetime import timedelta
    end_dt = start_dt + timedelta(hours=args.duration)
    end_str = end_dt.strftime("%Y-%m-%dT%H:%M:%S")

    event_body = {
        "summary": args.title,
        "location": args.location,
        "description": args.description or f"Added via weekend-planner on {datetime.now().strftime('%Y-%m-%d')}",
        "start": {
            "dateTime": start_str,
            "timeZone": tz,
        },
        "end": {
            "dateTime": end_str,
            "timeZone": tz,
        },
        "status": "confirmed",
        "reminders": {
            "useDefault": False,
            "overrides": [
                {"method": "popup", "minutes": 60},
            ],
        },
    }

    # Get token
    try:
        access_token = get_access_token()
    except Exception as e:
        print(json.dumps({"status": "error", "reason": f"Auth failed: {e}"}))
        sys.exit(1)

    # Create event
    try:
        result = create_event(access_token, args.calendar, event_body)
    except Exception as e:
        print(json.dumps({"status": "error", "reason": str(e)}))
        sys.exit(1)

    output = {
        "status": "ok",
        "message": f"✅ 活动已添加到 Family 日历",
        "event_id": result.get("id"),
        "title": result.get("summary"),
        "start": result.get("start", {}).get("dateTime"),
        "end": result.get("end", {}).get("dateTime"),
        "location": result.get("location", ""),
        "html_link": result.get("htmlLink"),
        "calendar": args.calendar,
    }

    print(json.dumps(output, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

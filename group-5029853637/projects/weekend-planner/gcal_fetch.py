#!/usr/bin/env python3
"""
Fetch events from Google Calendar (primary + family calendar).
Usage: python3 gcal_fetch.py [--days 14] [--help]
Output: JSON list of events.
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

CALENDARS = [
    {"id": "hang.shuojin@gmail.com", "name": "主日历"},
    {"id": "family03011953462043037676@group.calendar.google.com", "name": "Family"},
]

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
    # Preserve refresh_token if not returned
    if "refresh_token" not in new_token:
        new_token["refresh_token"] = token["refresh_token"]
    new_token["obtained_at"] = int(time.time())
    save_token(new_token)
    return new_token


def get_access_token():
    token = load_token()
    # Check expiry with 60s buffer
    obtained_at = token.get("obtained_at", 0)
    expires_in = token.get("expires_in", 3600)
    if int(time.time()) >= obtained_at + expires_in - 60:
        token = refresh_token(token)
    return token["access_token"]


def gcal_request(path, params, access_token, retry=True):
    url = f"{GCAL_BASE}{path}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {access_token}"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        if e.code == 401 and retry:
            # Refresh and retry once
            token = load_token()
            new_token = refresh_token(token)
            return gcal_request(path, params, new_token["access_token"], retry=False)
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {e.code}: {body}")


def parse_event(ev, calendar_name):
    start = ev.get("start", {})
    end = ev.get("end", {})
    return {
        "id": ev.get("id"),
        "title": ev.get("summary", "(no title)"),
        "start": start.get("dateTime") or start.get("date"),
        "end": end.get("dateTime") or end.get("date"),
        "location": ev.get("location", ""),
        "description": ev.get("description", ""),
        "calendar": calendar_name,
        "status": ev.get("status", ""),
        "all_day": "date" in start and "dateTime" not in start,
    }


def fetch_calendar(cal_id, cal_name, access_token, days):
    now = datetime.now(timezone.utc)
    time_min = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    # days ahead
    from datetime import timedelta
    time_max = (now + timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")

    params = {
        "timeMin": time_min,
        "timeMax": time_max,
        "singleEvents": "true",
        "orderBy": "startTime",
        "maxResults": 100,
    }
    path = f"/calendars/{urllib.parse.quote(cal_id)}/events"
    data = gcal_request(path, params, access_token)
    events = data.get("items", [])
    return [parse_event(ev, cal_name) for ev in events]


def main():
    parser = argparse.ArgumentParser(description="Fetch Google Calendar events as JSON.")
    parser.add_argument("--days", type=int, default=14, help="Number of days ahead to fetch (default: 14)")
    args = parser.parse_args()

    try:
        access_token = get_access_token()
    except Exception as e:
        print(json.dumps({"status": "error", "reason": f"Auth failed: {e}"}, ensure_ascii=False))
        sys.exit(1)

    all_events = []
    errors = []
    for cal in CALENDARS:
        try:
            evs = fetch_calendar(cal["id"], cal["name"], access_token, args.days)
            all_events.extend(evs)
        except Exception as e:
            errors.append({"calendar": cal["name"], "error": str(e)})

    # Sort by start time
    all_events.sort(key=lambda e: e["start"] or "")

    output = {
        "status": "ok",
        "fetched_at": datetime.now().isoformat(),
        "days": args.days,
        "total": len(all_events),
        "events": all_events,
    }
    if errors:
        output["errors"] = errors

    print(json.dumps(output, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

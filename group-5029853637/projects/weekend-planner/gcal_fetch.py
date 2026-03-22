#!/usr/bin/env python3
"""
Fetch events from Google Calendar (primary + family calendar) via Service Account.
Usage: python3 gcal_fetch.py [--days 14] [--help]
Output: JSON list of events.
"""

import argparse
import json
import sys
import urllib.parse
from datetime import datetime, timedelta, timezone

sys.path.insert(0, "/home/albert/.openclaw/workspace/group-5029853637/credentials")
from gcal_auth import get_headers, CAL_PRIMARY, CAL_FAMILY

import requests as _requests

CALENDARS = [
    {"id": CAL_PRIMARY, "name": "主日历"},
    {"id": CAL_FAMILY, "name": "Family"},
]
GCAL_BASE = "https://www.googleapis.com/calendar/v3"


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


def fetch_calendar(cal_id, cal_name, headers, days):
    now = datetime.now(timezone.utc)
    params = {
        "timeMin": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "timeMax": (now + timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "singleEvents": "true",
        "orderBy": "startTime",
        "maxResults": 100,
    }
    url = f"{GCAL_BASE}/calendars/{urllib.parse.quote(cal_id, safe='')}/events?{urllib.parse.urlencode(params)}"
    r = _requests.get(url, headers=headers, timeout=15)
    r.raise_for_status()
    return [parse_event(ev, cal_name) for ev in r.json().get("items", [])]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=14)
    args = parser.parse_args()

    try:
        headers = get_headers()
    except Exception as e:
        print(json.dumps({"status": "error", "reason": f"Auth failed: {e}"}, ensure_ascii=False))
        sys.exit(1)

    all_events = []
    errors = []
    for cal in CALENDARS:
        try:
            all_events.extend(fetch_calendar(cal["id"], cal["name"], headers, args.days))
        except Exception as e:
            errors.append({"calendar": cal["name"], "error": str(e)})

    all_events.sort(key=lambda e: e["start"] or "")
    output = {"status": "ok", "fetched_at": datetime.now().isoformat(), "days": args.days, "total": len(all_events), "events": all_events}
    if errors:
        output["errors"] = errors
    print(json.dumps(output, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Create one-day alarm reminder events in Google Calendar via Service Account."""

import argparse
import json
import sys
import urllib.parse
from datetime import datetime, timedelta

sys.path.insert(0, "/home/albert/.openclaw/workspace/group-5029853637/credentials")
from gcal_auth import get_headers, CAL_FAMILY

import requests as _requests

GCAL_BASE = "https://www.googleapis.com/calendar/v3"


def create_event(headers, calendar_id, title, note, start_dt, end_dt, timezone_str):
    body = {
        "summary": f"⏰ {title}",
        "description": note or "",
        "start": {"dateTime": start_dt, "timeZone": timezone_str},
        "end": {"dateTime": end_dt, "timeZone": timezone_str},
        "reminders": {"useDefault": False, "overrides": [{"method": "popup", "minutes": 0}]},
    }
    url = f"{GCAL_BASE}/calendars/{urllib.parse.quote(calendar_id, safe='')}/events"
    r = _requests.post(url, headers=headers, json=body, timeout=15)
    r.raise_for_status()
    return r.json()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--date", required=True)
    p.add_argument("--calendar-id", default=CAL_FAMILY)
    p.add_argument("--input-json", required=True)
    p.add_argument("--timezone", default="Europe/London")
    p.add_argument("--duration-min", type=int, default=10)
    args = p.parse_args()

    reminders = json.loads(args.input_json)
    headers = get_headers()
    created = []
    for item in reminders:
        hh, mm = map(int, item["time"].split(":"))
        start = datetime.strptime(args.date, "%Y-%m-%d").replace(hour=hh, minute=mm)
        end = start + timedelta(minutes=args.duration_min)
        event = create_event(headers, args.calendar_id, item["title"], item.get("note", ""), start.isoformat(), end.isoformat(), args.timezone)
        created.append({"time": item["time"], "title": item["title"], "id": event.get("id"), "htmlLink": event.get("htmlLink")})

    print(json.dumps({"created": created}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

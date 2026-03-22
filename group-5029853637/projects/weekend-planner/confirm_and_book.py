#!/usr/bin/env python3
"""Confirm and book events to Google Calendar via Service Account."""

import argparse
import json
import sys
import urllib.parse
from datetime import datetime

sys.path.insert(0, "/home/albert/.openclaw/workspace/group-5029853637/credentials")
from gcal_auth import get_headers, CAL_FAMILY

import requests as _requests

GCAL_BASE = "https://www.googleapis.com/calendar/v3"


def create_event(headers, calendar_id, event_body):
    url = f"{GCAL_BASE}/calendars/{urllib.parse.quote(calendar_id, safe='')}/events"
    r = _requests.post(url, headers=headers, json=event_body, timeout=15)
    r.raise_for_status()
    return r.json()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--calendar", default=CAL_FAMILY)
    parser.add_argument("--event-json", required=True, help="JSON string of the event body")
    args = parser.parse_args()

    headers = get_headers()
    event = json.loads(args.event_json)
    result = create_event(headers, args.calendar, event)
    print(json.dumps({"status": "ok", "id": result.get("id"), "htmlLink": result.get("htmlLink")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

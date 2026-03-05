#!/usr/bin/env python3
"""Scan school emails and auto-add actionable schedule items to Family Calendar.

Focus: St Faith's / schoolpost style emails with explicit Date/Venue/Start details.
"""

import base64
import json
import re
from datetime import datetime

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

GMAIL_TOKEN = "/home/albert/.openclaw/workspace/projects/gmail-api/token_hang.json"
CAL_TOKEN = "/home/albert/.openclaw/workspace/credentials/google_token.json"
CAL_CREDS = "/home/albert/.openclaw/workspace/credentials/google_credentials.json"
FAMILY_CAL = "family03011953462043037676@group.calendar.google.com"


def gmail_service():
    creds = Credentials.from_authorized_user_file(GMAIL_TOKEN)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return build("gmail", "v1", credentials=creds)


def calendar_service():
    tok = json.load(open(CAL_TOKEN))
    cred = json.load(open(CAL_CREDS))["installed"]
    tok["client_id"] = cred["client_id"]
    tok["client_secret"] = cred["client_secret"]
    tok["token_uri"] = cred["token_uri"]
    creds = Credentials.from_authorized_user_info(tok)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return build("calendar", "v3", credentials=creds)


def decode_text(payload):
    out = []

    def walk(node):
        b = node.get("body", {}).get("data")
        if b:
            try:
                out.append(base64.urlsafe_b64decode(b).decode("utf-8", "replace"))
            except Exception:
                pass
        for p in node.get("parts", []) or []:
            walk(p)

    walk(payload)
    return "\n".join(out)


def month_num(name):
    m = {
        "january": 1,
        "february": 2,
        "march": 3,
        "april": 4,
        "may": 5,
        "june": 6,
        "july": 7,
        "august": 8,
        "september": 9,
        "october": 10,
        "november": 11,
        "december": 12,
    }
    return m.get(name.lower())


def parse_year5_netball(text, year):
    # Looks for section containing Year 5 + Date/Venue/Start
    t = re.sub(r"\s+", " ", text)
    if "Year 5" not in t:
        return None

    m_date = re.search(r"Year\s*5.*?Date:\s*(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]+)", t, re.I)
    m_venue = re.search(r"Year\s*5.*?Venue:\s*([^\.]+?)\s+Start:", t, re.I)
    m_start = re.search(r"Year\s*5.*?Start:\s*(\d{1,2}):(\d{2})\s*(a\.m\.|p\.m\.|am|pm)", t, re.I)
    if not (m_date and m_start):
        return None

    day = int(m_date.group(1))
    mon = month_num(m_date.group(2))
    if not mon:
        return None
    hh = int(m_start.group(1))
    mm = int(m_start.group(2))
    ap = m_start.group(3).lower()
    if "p" in ap and hh < 12:
        hh += 12
    if "a" in ap and hh == 12:
        hh = 0

    start = datetime(year, mon, day, hh, mm)
    venue = m_venue.group(1).strip() if m_venue else "St Faith's"
    return {
        "summary": "Alice Year 5 House Netball Competition",
        "description": "Auto-added from St Faith's email.",
        "location": venue,
        "start": {"dateTime": start.strftime("%Y-%m-%dT%H:%M:%S"), "timeZone": "Europe/London"},
        "end": {"dateTime": start.replace(hour=min(start.hour + 1, 23), minute=30).strftime("%Y-%m-%dT%H:%M:%S"), "timeZone": "Europe/London"},
    }


def upsert_event(cal, event):
    s = event["start"]["dateTime"][:10]
    existing = (
        cal.events()
        .list(
            calendarId=FAMILY_CAL,
            timeMin=s + "T00:00:00Z",
            timeMax=s + "T23:59:59Z",
            q=event["summary"],
        )
        .execute()
        .get("items", [])
    )
    if existing:
        return False
    cal.events().insert(calendarId=FAMILY_CAL, body=event).execute()
    return True


def main():
    gmail = gmail_service()
    cal = calendar_service()

    q = "newer_than:3d (from:stfaith OR from:schoolpost OR from:theleys)"
    msgs = gmail.users().messages().list(userId="me", q=q, maxResults=20).execute().get("messages", [])

    added = []
    for m in msgs:
        msg = gmail.users().messages().get(userId="me", id=m["id"], format="full").execute()
        headers = {h["name"]: h["value"] for h in msg["payload"]["headers"]}
        date_hdr = headers.get("Date", "")
        year = datetime.utcnow().year
        yy = re.search(r"\b(20\d{2})\b", date_hdr)
        if yy:
            year = int(yy.group(1))

        text = decode_text(msg["payload"])
        ev = parse_year5_netball(text, year)
        if ev and upsert_event(cal, ev):
            added.append(ev["summary"])

    print(json.dumps({"status": "ok", "added": added, "count_added": len(added)}))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Scrape Leys School Calendar for upcoming events.
Outputs JSON with events including School House specific ones.
Usage: python3 scrape_leys.py [--weeks N]
"""

import json
import re
import sys
import urllib.request
from datetime import datetime, timedelta
from html.parser import HTMLParser


class LeysCalendarParser(HTMLParser):
    """Parse Leys School calendar HTML for events."""

    def __init__(self):
        super().__init__()
        self.events = []
        self.current_event = {}
        self.capture = None
        self.in_event = False

    def handle_data(self, data):
        data = data.strip()
        if not data:
            return

        # Detect day names
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        if data in days:
            if self.current_event.get("title"):
                self.events.append(self.current_event)
            self.current_event = {"day": data}
            return

        # Detect dates (e.g., "27", "01")
        if re.match(r"^\d{1,2}$", data) and "day" in self.current_event and "date_num" not in self.current_event:
            self.current_event["date_num"] = data
            return

        # Detect month-year (e.g., "Feb 26")
        month_match = re.match(r"^(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{2})$", data)
        if month_match and "day" in self.current_event:
            self.current_event["month"] = month_match.group(1)
            self.current_event["year"] = f"20{month_match.group(2)}"
            return

        # Detect time
        time_match = re.match(r"^Time:\s*(.+)$", data)
        if time_match:
            self.current_event["time"] = time_match.group(1).strip()
            return

        # Detect location
        loc_match = re.match(r"^Location:\s*(.*)$", data)
        if loc_match:
            self.current_event["location"] = loc_match.group(1).strip()
            return

        # Skip "Week A/B" labels but note them
        if re.match(r"^Week [AB]$", data):
            self.current_event["week_type"] = data
            return

        # Everything else is likely a title/description
        if "day" in self.current_event and data not in ["|"]:
            if "title" not in self.current_event or self.current_event["title"] in ["", None]:
                self.current_event["title"] = data
            elif self.current_event.get("title") != data:
                self.current_event.setdefault("details", []).append(data)


def fetch_calendar(weeks=4):
    """Fetch Leys calendar page."""
    url = "https://www.theleys.net/news-and-events/school-calendar/"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.read().decode("utf-8", errors="replace")


def parse_events(html):
    """Parse HTML into structured events."""
    parser = LeysCalendarParser()
    parser.feed(html)
    if parser.current_event.get("title"):
        parser.events.append(parser.current_event)
    return parser.events


def format_date(event):
    """Try to build ISO date from event parts."""
    try:
        months = {"Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
                  "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12}
        m = months.get(event.get("month"), 0)
        d = int(event.get("date_num", 0))
        y = int(event.get("year", 0))
        if m and d and y:
            return f"{y}-{m:02d}-{d:02d}"
    except (ValueError, TypeError):
        pass
    return None


def is_school_house_relevant(event):
    """Check if event mentions School House."""
    title = event.get("title", "").lower()
    details = " ".join(event.get("details", [])).lower()
    text = f"{title} {details}"
    return any(kw in text for kw in ["school house", "house match", "house ", "all houses"])


def main():
    weeks = 4
    if "--weeks" in sys.argv:
        idx = sys.argv.index("--weeks")
        if idx + 1 < len(sys.argv):
            weeks = int(sys.argv[idx + 1])

    html = fetch_calendar(weeks)
    raw_events = parse_events(html)

    events = []
    for e in raw_events:
        date = format_date(e)
        ev = {
            "date": date,
            "day": e.get("day"),
            "title": e.get("title", ""),
            "time": e.get("time", ""),
            "location": e.get("location", ""),
            "week_type": e.get("week_type"),
            "school_house_relevant": is_school_house_relevant(e),
            "is_saturday": e.get("day") == "Saturday",
        }
        events.append(ev)

    # Filter to upcoming only
    today = datetime.now().strftime("%Y-%m-%d")
    upcoming = [e for e in events if not e["date"] or e["date"] >= today]

    output = {
        "scraped_at": datetime.now().isoformat(),
        "total_events": len(upcoming),
        "saturday_events": [e for e in upcoming if e["is_saturday"]],
        "school_house_events": [e for e in upcoming if e["school_house_relevant"]],
        "all_events": upcoming,
    }

    print(json.dumps(output, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

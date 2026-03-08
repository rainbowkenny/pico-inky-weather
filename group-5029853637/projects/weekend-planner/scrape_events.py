#!/usr/bin/env python3
"""
Scrape Cambridge/London weekend activity events.
Usage: python3 scrape_events.py [--weekend 2026-03-01] [--help]
Output: JSON list of events with title, date, venue, price, URL, travel time.
"""

import argparse
import json
import re
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from html.parser import HTMLParser

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-GB,en;q=0.5",
}

# Travel times from Cambridge (approximate)
TRAVEL_TIMES = {
    "london": "~1h15m by train",
    "cambridge": "local",
    "ely": "~20m",
    "peterborough": "~45m",
    "norwich": "~1h30m",
    "ipswich": "~1h",
    "colchester": "~1h",
    "stevenage": "~45m",
    "bedford": "~1h",
    "huntingdon": "~30m",
    "st ives": "~25m",
}


def fetch_url(url, timeout=15):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace"), resp.geturl()


def estimate_travel(location_str):
    if not location_str:
        return "unknown"
    loc_lower = location_str.lower()
    for city, time in TRAVEL_TIMES.items():
        if city in loc_lower:
            return time
    # Default London if no match
    if any(kw in loc_lower for kw in ["wc", "ec", "sw", "se", "n1", "e1", "w1"]):
        return "~1h15m by train"
    return "~1-2h from Cambridge"


class SimpleHTMLTextParser(HTMLParser):
    """Extract text content from HTML, ignoring scripts/styles."""
    def __init__(self):
        super().__init__()
        self.text_parts = []
        self._skip = False
        self._skip_tags = {"script", "style", "noscript", "head"}

    def handle_starttag(self, tag, attrs):
        if tag in self._skip_tags:
            self._skip = True

    def handle_endtag(self, tag):
        if tag in self._skip_tags:
            self._skip = False

    def handle_data(self, data):
        if not self._skip:
            stripped = data.strip()
            if stripped:
                self.text_parts.append(stripped)

    def get_text(self):
        return " ".join(self.text_parts)


def scrape_visitcambridge(weekend_start):
    """Scrape VisitCambridge what's on page."""
    events = []
    try:
        url = "https://www.visitcambridge.org/whats-on/"
        html, _ = fetch_url(url)

        # Extract event-like patterns from the page
        # Look for structured data (JSON-LD)
        ld_matches = re.findall(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', html, re.DOTALL)
        for ld in ld_matches:
            try:
                data = json.loads(ld)
                items = data if isinstance(data, list) else [data]
                for item in items:
                    if item.get("@type") in ("Event", "SocialEvent", "MusicEvent", "TheaterEvent"):
                        loc = item.get("location", {})
                        loc_name = loc.get("name", "") if isinstance(loc, dict) else str(loc)
                        loc_addr = loc.get("address", {})
                        if isinstance(loc_addr, dict):
                            loc_str = loc_addr.get("addressLocality", "") or loc_addr.get("streetAddress", "")
                        else:
                            loc_str = str(loc_addr)
                        start = item.get("startDate", "")
                        events.append({
                            "title": item.get("name", ""),
                            "date": start[:10] if start else "",
                            "venue": loc_name or loc_str,
                            "location": loc_str or "Cambridge",
                            "price": item.get("offers", {}).get("price", "varies") if isinstance(item.get("offers"), dict) else "varies",
                            "url": item.get("url", url),
                            "travel_time": estimate_travel(loc_str or "cambridge"),
                            "category": "general",
                            "source": "visitcambridge",
                        })
            except (json.JSONDecodeError, AttributeError):
                continue

        # Fallback: parse titles from HTML headings
        if not events:
            title_matches = re.findall(r'<h[23][^>]*>\s*<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>', html, re.DOTALL)
            for href, title in title_matches[:10]:
                clean_title = re.sub(r"<[^>]+>", "", title).strip()
                if clean_title and len(clean_title) > 5:
                    events.append({
                        "title": clean_title,
                        "date": weekend_start,
                        "venue": "Cambridge",
                        "location": "Cambridge",
                        "price": "varies",
                        "url": href if href.startswith("http") else f"https://www.visitcambridge.org{href}",
                        "travel_time": "local",
                        "category": "general",
                        "source": "visitcambridge",
                    })
    except Exception as e:
        events.append({"status": "blocked", "source": "visitcambridge", "reason": str(e)})
    return events


def scrape_timeout_cambridge(weekend_start):
    """Scrape Time Out Cambridge events."""
    events = []
    try:
        url = "https://www.timeout.com/cambridge/things-to-do/best-things-to-do-this-weekend-in-cambridge"
        html, _ = fetch_url(url)

        # Try JSON-LD
        ld_matches = re.findall(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', html, re.DOTALL)
        for ld in ld_matches:
            try:
                data = json.loads(ld)
                if isinstance(data, dict) and data.get("@type") == "ItemList":
                    for item in data.get("itemListElement", []):
                        thing = item.get("item", item)
                        events.append({
                            "title": thing.get("name", ""),
                            "date": weekend_start,
                            "venue": thing.get("location", {}).get("name", "Cambridge") if isinstance(thing.get("location"), dict) else "Cambridge",
                            "location": "Cambridge",
                            "price": "varies",
                            "url": thing.get("url", url),
                            "travel_time": "local",
                            "category": "general",
                            "source": "timeout_cambridge",
                        })
            except (json.JSONDecodeError, AttributeError):
                continue

        # Fallback: article titles
        if not events:
            matches = re.findall(r'<h3[^>]*>(.*?)</h3>', html, re.DOTALL)
            for m in matches[:8]:
                clean = re.sub(r"<[^>]+>", "", m).strip()
                if clean and len(clean) > 5:
                    events.append({
                        "title": clean,
                        "date": weekend_start,
                        "venue": "Cambridge",
                        "location": "Cambridge",
                        "price": "varies",
                        "url": url,
                        "travel_time": "local",
                        "category": "general",
                        "source": "timeout_cambridge",
                    })
    except Exception as e:
        events.append({"status": "blocked", "source": "timeout_cambridge", "reason": str(e)})
    return events


def scrape_timeout_london(weekend_start):
    """Scrape Time Out London for family events."""
    events = []
    try:
        url = "https://www.timeout.com/london/things-to-do/best-things-to-do-in-london-this-weekend"
        html, _ = fetch_url(url)

        ld_matches = re.findall(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', html, re.DOTALL)
        for ld in ld_matches:
            try:
                data = json.loads(ld)
                if isinstance(data, dict) and data.get("@type") == "ItemList":
                    for item in data.get("itemListElement", []):
                        thing = item.get("item", item)
                        loc_raw = thing.get("location", {})
                        loc_name = loc_raw.get("name", "London") if isinstance(loc_raw, dict) else "London"
                        events.append({
                            "title": thing.get("name", ""),
                            "date": weekend_start,
                            "venue": loc_name,
                            "location": "London",
                            "price": "varies",
                            "url": thing.get("url", url),
                            "travel_time": "~1h15m by train",
                            "category": "general",
                            "source": "timeout_london",
                        })
            except (json.JSONDecodeError, AttributeError):
                continue

        if not events:
            matches = re.findall(r'<h3[^>]*>(.*?)</h3>', html, re.DOTALL)
            for m in matches[:8]:
                clean = re.sub(r"<[^>]+>", "", m).strip()
                if clean and len(clean) > 5:
                    events.append({
                        "title": clean,
                        "date": weekend_start,
                        "venue": "London",
                        "location": "London",
                        "price": "varies",
                        "url": url,
                        "travel_time": "~1h15m by train",
                        "category": "general",
                        "source": "timeout_london",
                    })
    except Exception as e:
        events.append({"status": "blocked", "source": "timeout_london", "reason": str(e)})
    return events


def scrape_eventbrite_cambridge(weekend_start):
    """Search Eventbrite for Cambridge weekend events."""
    events = []
    try:
        weekend_end = (datetime.strptime(weekend_start, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
        params = urllib.parse.urlencode({
            "q": "family",
            "location": "Cambridge, UK",
            "start_date": weekend_start,
            "end_date": weekend_end,
        })
        url = f"https://www.eventbrite.co.uk/d/united-kingdom--cambridge/family/?{params}"
        html, _ = fetch_url(url)

        # JSON-LD events
        ld_matches = re.findall(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', html, re.DOTALL)
        for ld in ld_matches:
            try:
                data = json.loads(ld)
                items = data if isinstance(data, list) else [data]
                for item in items:
                    if item.get("@type") == "Event":
                        loc = item.get("location", {})
                        loc_name = loc.get("name", "Cambridge") if isinstance(loc, dict) else "Cambridge"
                        offers = item.get("offers", {})
                        price = "free" if isinstance(offers, dict) and offers.get("price") == "0" else "varies"
                        events.append({
                            "title": item.get("name", ""),
                            "date": item.get("startDate", weekend_start)[:10],
                            "venue": loc_name,
                            "location": "Cambridge",
                            "price": price,
                            "url": item.get("url", url),
                            "travel_time": "local",
                            "category": "family",
                            "source": "eventbrite",
                        })
            except (json.JSONDecodeError, AttributeError):
                continue

        # Fallback: extract event titles
        if not events:
            matches = re.findall(r'"name"\s*:\s*"([^"]{10,100})"', html)
            for name in list(dict.fromkeys(matches))[:6]:
                events.append({
                    "title": name,
                    "date": weekend_start,
                    "venue": "Cambridge",
                    "location": "Cambridge",
                    "price": "varies",
                    "url": url,
                    "travel_time": "local",
                    "category": "family",
                    "source": "eventbrite",
                })
    except Exception as e:
        events.append({"status": "blocked", "source": "eventbrite", "reason": str(e)})
    return events


def scrape_london_sailing_club(weekend_start):
    """Scrape London Sailing Club events (user-requested source)."""
    events = []
    try:
        url = "https://www.londonsailing.club/"
        html, final_url = fetch_url(url)

        # Try JSON-LD first
        ld_matches = re.findall(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', html, re.DOTALL)
        for ld in ld_matches:
            try:
                data = json.loads(ld)
                items = data if isinstance(data, list) else [data]
                for item in items:
                    if item.get("@type") in ("Event", "SportsEvent"):
                        start = item.get("startDate", "")
                        loc = item.get("location", {})
                        loc_name = loc.get("name", "London") if isinstance(loc, dict) else "London"
                        events.append({
                            "title": item.get("name", "London Sailing Club Event"),
                            "date": start[:10] if start else weekend_start,
                            "venue": loc_name,
                            "location": "London",
                            "price": "varies",
                            "url": item.get("url", final_url),
                            "travel_time": "~1h15m by train",
                            "category": "sports",
                            "source": "london_sailing_club",
                        })
            except (json.JSONDecodeError, AttributeError):
                continue

        # Fallback: if no structured events, include as monitored source
        if not events:
            events.append({
                "title": "London Sailing Club - Upcoming sessions",
                "date": weekend_start,
                "venue": "London Sailing Club",
                "location": "London",
                "price": "check website",
                "url": final_url,
                "travel_time": "~1h15m by train",
                "category": "sports",
                "source": "london_sailing_club",
            })
    except Exception as e:
        events.append({"status": "blocked", "source": "london_sailing_club", "reason": str(e)})

    return events


def scrape_museum_cambridge(weekend_start):
    """Add known Cambridge museum/attraction options."""
    # Static curated options (always available) + check for special events
    curated = [
        {
            "title": "Fitzwilliam Museum",
            "date": weekend_start,
            "venue": "Fitzwilliam Museum, Trumpington St, Cambridge",
            "location": "Cambridge",
            "price": "Free",
            "url": "https://www.fitzmuseum.cam.ac.uk/",
            "travel_time": "local",
            "category": "museum",
            "source": "curated",
        },
        {
            "title": "Cambridge Science Centre",
            "date": weekend_start,
            "venue": "Cambridge Science Centre, CB1 2AR",
            "location": "Cambridge",
            "price": "£7-10",
            "url": "https://www.cambridgesciencecentre.org/",
            "travel_time": "local",
            "category": "museum",
            "source": "curated",
        },
        {
            "title": "Ely Cathedral",
            "date": weekend_start,
            "venue": "The Chapter House, Ely CB7 4DL",
            "location": "Ely",
            "price": "£10 adults / £5 children",
            "url": "https://www.elycathedral.org/",
            "travel_time": "~20m by train",
            "category": "attraction",
            "source": "curated",
        },
    ]
    return curated


def is_real_event_title(title):
    """Filter out junk titles from JSON-LD artifacts."""
    if not title or len(title) < 6:
        return False
    junk = {
        "united kingdom", "england", "cambridgeshire", "uk", "gb",
        "more info", "read more", "click here", "event", "website",
    }
    return title.lower().strip() not in junk


def filter_to_weekend(events, weekend_start):
    """Keep events that are on or around the target weekend (Sat/Sun)."""
    try:
        start = datetime.strptime(weekend_start, "%Y-%m-%d")
        end = start + timedelta(days=2)
    except ValueError:
        return events
    filtered = []
    for ev in events:
        if "status" in ev and ev.get("status") == "blocked":
            filtered.append(ev)
            continue
        date_str = ev.get("date", "")
        if not date_str:
            filtered.append(ev)  # keep undated
            continue
        try:
            ev_date = datetime.strptime(date_str[:10], "%Y-%m-%d")
            if start <= ev_date <= end:
                filtered.append(ev)
        except ValueError:
            filtered.append(ev)
    return filtered


def get_next_saturday(from_date=None):
    d = from_date or datetime.now()
    days_ahead = 5 - d.weekday()  # 5 = Saturday
    if days_ahead <= 0:
        days_ahead += 7
    return (d + timedelta(days=days_ahead)).strftime("%Y-%m-%d")


def main():
    parser = argparse.ArgumentParser(description="Scrape Cambridge/London weekend events as JSON.")
    parser.add_argument("--weekend", type=str, default=None,
                        help="Saturday date of target weekend, e.g. 2026-03-01 (default: next Saturday)")
    args = parser.parse_args()

    weekend_start = args.weekend or get_next_saturday()

    # Validate date
    try:
        datetime.strptime(weekend_start, "%Y-%m-%d")
    except ValueError:
        print(json.dumps({"status": "error", "reason": "Invalid date format. Use YYYY-MM-DD."}))
        sys.exit(1)

    all_events = []
    all_events.extend(scrape_visitcambridge(weekend_start))
    all_events.extend(scrape_timeout_cambridge(weekend_start))
    all_events.extend(scrape_timeout_london(weekend_start))
    all_events.extend(scrape_eventbrite_cambridge(weekend_start))
    all_events.extend(scrape_london_sailing_club(weekend_start))
    all_events.extend(scrape_museum_cambridge(weekend_start))

    # Deduplicate by title; drop junk titles
    seen = set()
    unique_events = []
    for ev in all_events:
        if ev.get("status") == "blocked":
            unique_events.append(ev)
            continue
        title = ev.get("title", "")
        if not is_real_event_title(title):
            continue
        key = title.lower()[:50]
        if key not in seen:
            seen.add(key)
            unique_events.append(ev)

    # Separate errors
    errors = [e for e in unique_events if e.get("status") == "blocked"]
    good = [e for e in unique_events if e.get("status") != "blocked"]

    output = {
        "status": "ok",
        "scraped_at": datetime.now().isoformat(),
        "weekend": weekend_start,
        "total": len(good),
        "events": good,
    }
    if errors:
        output["scrape_errors"] = errors

    print(json.dumps(output, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

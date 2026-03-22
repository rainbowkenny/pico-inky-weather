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
    """Scrape London Sailing Club events via HTTP (myClubhouse platform).

    The site renders event-list in the HTML.
    We fetch the page and parse the HTML for event blocks.
    """
    events = []
    url = "https://www.londonsailing.club/"

    try:
        # 1. Fetch the page with proper headers
        html, _ = fetch_url(url)

        if not html or len(html) < 200:
            return _london_sailing_fallback(weekend_start, url, "page text too short")

        # 2. Parse events from the HTML
        events = _parse_lsc_html_events(html, url)
        if not events:
            return _london_sailing_fallback(weekend_start, url, "no events parsed from page")

        return events

    except Exception as e:
        return _london_sailing_fallback(weekend_start, url, str(e))


def _parse_lsc_html_events(html, base_url):
    """Parse London Sailing Club events from raw HTML."""
    events = []

    # The events are in blocks. Let's look for the structure.
    # Based on the user description and myClubhouse platform:
    # Events appear after "Upcoming Events Calendar"

    # Clean up HTML a bit to make regex easier
    html = html.replace('\r', '').replace('\n', ' ')
    html = re.sub(r'\s+', ' ', html)

    # Find the events section
    start_match = re.search(r'Upcoming Events Calendar', html)
    if not start_match:
        return events

    events_html = html[start_match.start():]

    # Event blocks often look like this in myClubhouse:
    # Each event has: Type, Title, Date, Time, Venue, Price, Places
    # Date format: "Tue, 31 Mar 26"

    # Regex for the date pattern which is a good anchor
    # "Tue, 31 Mar 26"
    date_regex = r'(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun),\s+(\d{1,2})\s+([A-Z][a-z]{2})\s+(\d{2})'

    types_pattern = r'(Sailing Trip(?: Non-Commercial| Commercial)?|Social Event|Training|Racing)'

    # Split by the event type to get potential blocks
    blocks = re.split(types_pattern, events_html)

    # The first element is the text before the first event
    if len(blocks) < 3:
        return events

    for i in range(1, len(blocks), 2):
        event_type = blocks[i]
        block_content = blocks[i+1]

        # Stop if we hit a different section
        if "Past Events" in event_type or "Past Events" in block_content[:100]:
            break

        # Extract title: usually follows the type
        # In the raw HTML it might be inside a tag
        title_match = re.search(r'>\s*([^<]{5,100}?)<', block_content)
        title = title_match.group(1).strip() if title_match else "Unknown Event"
        # Remove common fluff
        title = re.sub(r'^NEW!\s*', '', title)

        # Extract date
        date_match = re.search(date_regex, block_content)
        if not date_match:
            continue

        day, month_str, year_short = date_match.groups()
        date_str = f"{date_match.group(0)}"

        # ISO Date conversion
        try:
            # Handle 20xx
            year = int(year_short) + 2000
            month_num = datetime.strptime(month_str, "%b").month
            iso_date = f"{year}-{month_num:02d}-{int(day):02d}"
        except Exception:
            iso_date = ""

        # Extract Time
        time_match = re.search(r'(\d{2}:\d{2}\s*-\s*\d{2}:\d{2})', block_content)
        time_str = time_match.group(1) if time_match else ""

        # Extract Venue
        # Venue often follows the time or date.
        # Look for common venue names or patterns
        venue = "London"
        if "Port Hamble" in block_content:
            venue = "Port Hamble Marina"
        elif "Brewdog" in block_content:
            venue = "Brewdog Waterloo"
        elif "Zoom" in block_content or "Online" in block_content:
            venue = "Online (Zoom)"

        # Extract Price
        price_match = re.search(r'(£\d+(?:\.\d{2})?|Around £\d+|Free)', block_content)
        price = price_match.group(1) if price_match else "check website"

        # Extract Places
        places = ""
        places_match = re.search(r'(\d+)\s*places available', block_content)
        if places_match:
            places = f"{places_match.group(1)} places"
        elif "FULL WAITING LIST" in block_content:
            places = "FULL (Waiting List)"

        # Signup URL
        url_match = re.search(r'href="([^"]*?/Events/View/[^"]+?)"', block_content)
        signup_url = url_match.group(1) if url_match else base_url
        if signup_url.startswith('/'):
            signup_url = f"https://www.londonsailing.club{signup_url}"

        events.append({
            "title": f"⛵ {title}",
            "date": iso_date,
            "display_date": date_str,
            "time": time_str,
            "venue": venue,
            "location": "London / Solent",
            "price": price,
            "places_available": places,
            "event_type": event_type,
            "url": signup_url,
            "travel_time": "~2h by car" if "Hamble" in venue else "~1h15m by train",
            "category": "sailing",
            "source": "london_sailing_club",
        })

    return events


def _parse_lsc_events(text, base_url):
    """Parse London Sailing Club events from page innerText."""
    events = []
    # Split on event type markers
    # Events appear as blocks starting with type tags like "Sailing Trip", "Social Event"
    event_types = ["Sailing Trip Non-Commercial", "Sailing Trip Commercial",
                   "Social Event", "Training", "Racing", "Sailing Trip"]

    # Find "Upcoming Events" section
    upcoming_idx = text.find("Upcoming Events")
    if upcoming_idx == -1:
        return events
    text = text[upcoming_idx:]

    # Split into event blocks by looking for date patterns
    # Pattern: "Mon, DD Mon YY" or "Tue, DD Mon YY" etc.
    date_pattern = re.compile(
        r'((?:Mon|Tue|Wed|Thu|Fri|Sat|Sun),\s+\d{1,2}\s+\w{3}\s+\d{2})\s*\n\s*•\s*(\d{2}:\d{2}\s*-\s*\d{2}:\d{2})'
    )

    # Find all event blocks - split on "Sign Up" which ends each event
    blocks = re.split(r'\s*Sign Up\s*', text)

    for block in blocks:
        if len(block.strip()) < 30:
            continue

        # Determine event type
        event_type = "Event"
        for et in event_types:
            if et in block:
                event_type = et
                break

        # Extract title - typically after the event type marker and "NEW!" if present
        lines = [l.strip() for l in block.split('\n') if l.strip()]

        title = None
        date_str = None
        time_str = None
        venue = None
        price = None
        places = None
        duration = None

        for i, line in enumerate(lines):
            # Date line
            date_match = re.match(r'((?:Mon|Tue|Wed|Thu|Fri|Sat|Sun),\s+\d{1,2}\s+\w{3}\s+\d{2})', line)
            if date_match:
                date_str = date_match.group(1)
                # Title is usually the line before the date (after type/NEW markers)
                # Look backwards for the title
                for j in range(i - 1, -1, -1):
                    candidate = lines[j]
                    if candidate in event_types or candidate == "NEW!" or candidate == "Calendar":
                        continue
                    if len(candidate) > 5 and candidate not in ("Upcoming Events",):
                        title = candidate
                        break
                continue

            # Time line
            time_match = re.match(r'•\s*(\d{2}:\d{2}\s*-\s*\d{2}:\d{2})', line)
            if time_match:
                time_str = time_match.group(1)
                continue

            # Duration
            if re.match(r'\d+\s+days?$', line):
                duration = line
                continue

            # Venue - usually a line with location-like content after time
            if line.startswith("Part of") or line.startswith("Last in"):
                continue

            # Price detection
            price_match = re.match(r'(£\d+|Around £\d+|Free)', line)
            if price_match:
                price = line
                continue

            # Places
            places_match = re.match(r'(\d+)\s*\nplaces available', line) or re.match(r'(\d+)$', line)
            if re.match(r'places available', line):
                # Look at previous line for number
                if i > 0 and re.match(r'\d+$', lines[i-1]):
                    places = f"{lines[i-1]} places"
                continue

        # Parse date to ISO format
        iso_date = ""
        if date_str:
            try:
                from datetime import datetime as dt
                parsed = dt.strptime(date_str, "%a, %d %b %y")
                iso_date = parsed.strftime("%Y-%m-%d")
            except ValueError:
                iso_date = date_str

        if title and date_str:
            # Detect venue from block text
            if "Port Hamble" in block:
                venue = "Port Hamble Marina"
            elif "Brewdog" in block:
                venue = "Brewdog Waterloo"
            elif "Zoom" in block or "Online" in block:
                venue = "Online (Zoom)"
            else:
                venue = "London"

            # Detect price from block
            if not price:
                price_search = re.search(r'(£\d[\d,.]*|Around £\d[\d,.]*)', block)
                if price_search:
                    price = price_search.group(1)
                elif "free" in block.lower()[:500]:
                    price = "Free"
                else:
                    price = "check website"

            # Detect places
            if not places:
                places_search = re.search(r'(\d+)\s*\n\s*places available', block)
                if places_search:
                    places = f"{places_search.group(1)} places"

            events.append({
                "title": f"⛵ {title}",
                "date": iso_date,
                "display_date": date_str,
                "time": time_str or "",
                "duration": duration or "",
                "venue": venue,
                "location": "London / Solent",
                "price": price,
                "places_available": places or "",
                "event_type": event_type,
                "url": base_url,
                "travel_time": "~2h by car" if "Hamble" in (venue or "") else "~1h15m by train",
                "category": "sailing",
                "source": "london_sailing_club",
            })

    return events


def _london_sailing_fallback(weekend_start, url, reason):
    """Fallback when CDP scraping fails."""
    _log = lambda m: print(f"[LSC] {m}", file=__import__('sys').stderr)
    _log(f"CDP fallback: {reason}")
    return [{
        "title": "⛵ London Sailing Club — check website for events",
        "date": weekend_start,
        "venue": "London Sailing Club",
        "location": "London",
        "price": "check website",
        "url": url,
        "travel_time": "~1h15m by train",
        "category": "sailing",
        "source": "london_sailing_club",
        "note": f"CDP unavailable: {reason}",
    }]


def get_curated_options(weekend_start):
    """Pool of high-quality curated options for families with kids (10, 13)."""
    curated = [
        {
            "title": "IWM Duxford",
            "date": weekend_start,
            "venue": "Duxford, CB22 4QR",
            "location": "Cambridge",
            "price": "£25-30",
            "url": "https://www.iwm.org.uk/visits/iwm-duxford",
            "travel_time": "~15min from Cambridge",
            "category": "museum",
            "source": "curated",
            "seasonal": False,
            "indoor": True,
        },
        {
            "title": "Go Ape Thetford Forest",
            "date": weekend_start,
            "venue": "High Lodge, Thetford IP27 0AF",
            "location": "Thetford",
            "price": "£30-40",
            "url": "https://goape.co.uk/locations/thetford",
            "travel_time": "~45min",
            "category": "outdoor",
            "source": "curated",
            "seasonal": True,
            "indoor": False,
        },
        {
            "title": "Clip 'n Climb Cambridge",
            "date": weekend_start,
            "venue": "Clifton Rd Industrial Estate, CB1 7EB",
            "location": "Cambridge",
            "price": "£15-20",
            "url": "https://cambridge.clipnclimb.co.uk/",
            "travel_time": "local",
            "category": "sports",
            "source": "curated",
            "seasonal": False,
            "indoor": True,
        },
        {
            "title": "Cambridge Leisure Ice Skating",
            "date": weekend_start,
            "venue": "Cambridge Ice Arena, CB5 8S",
            "location": "Cambridge",
            "price": "£12-15",
            "url": "https://www.better.org.uk/leisure-centre/cambridge/cambridge-ice-arena",
            "travel_time": "local",
            "category": "sports",
            "source": "curated",
            "seasonal": False,
            "indoor": True,
        },
        {
            "title": "Thorpe Park",
            "date": weekend_start,
            "venue": "Chertsey, KT16 8PN",
            "location": "Surrey",
            "price": "£40-60",
            "url": "https://www.thorpepark.com/",
            "travel_time": "~1.5h",
            "category": "attraction",
            "source": "curated",
            "seasonal": True,
            "indoor": False,
        },
        {
            "title": "Natural History Museum London",
            "date": weekend_start,
            "venue": "South Kensington, London",
            "location": "London",
            "price": "Free",
            "url": "https://www.nhm.ac.uk/",
            "travel_time": "~1h15m by train",
            "category": "museum",
            "source": "curated",
            "seasonal": False,
            "indoor": True,
        },
        {
            "title": "Science Museum London",
            "date": weekend_start,
            "venue": "South Kensington, London",
            "location": "London",
            "price": "Free",
            "url": "https://www.sciencemuseum.org.uk/",
            "travel_time": "~1h15m by train",
            "category": "museum",
            "source": "curated",
            "seasonal": False,
            "indoor": True,
        },
        {
            "title": "V&A Museum London",
            "date": weekend_start,
            "venue": "South Kensington, London",
            "location": "London",
            "price": "Free",
            "url": "https://www.vam.ac.uk/",
            "travel_time": "~1h15m by train",
            "category": "museum",
            "source": "curated",
            "seasonal": False,
            "indoor": True,
        },
        {
            "title": "Greenwich Observatory + Cutty Sark",
            "date": weekend_start,
            "venue": "Greenwich, London",
            "location": "London",
            "price": "£20-30",
            "url": "https://www.rmg.co.uk/",
            "travel_time": "~1h15m by train",
            "category": "attraction",
            "source": "curated",
            "seasonal": False,
            "indoor": True,
        },
        {
            "title": "Warner Bros Studio Tour (Harry Potter)",
            "date": weekend_start,
            "venue": "Watford, WD25 7LR",
            "location": "Watford",
            "price": "£50-60",
            "url": "https://www.wbstudiotour.co.uk/",
            "travel_time": "~1h by car",
            "category": "attraction",
            "source": "curated",
            "seasonal": False,
            "indoor": True,
        },
        {
            "title": "Wicksteed Park",
            "date": weekend_start,
            "venue": "Kettering, NN15 6NJ",
            "location": "Kettering",
            "price": "£20-30",
            "url": "https://wicksteedpark.org/",
            "travel_time": "~1h",
            "category": "attraction",
            "source": "curated",
            "seasonal": True,
            "indoor": False,
        },
        {
            "title": "Colchester Zoo",
            "date": weekend_start,
            "venue": "Colchester, CO3 0SL",
            "location": "Colchester",
            "price": "£25-35",
            "url": "https://www.colchester-zoo.com/",
            "travel_time": "~1h",
            "category": "attraction",
            "source": "curated",
            "seasonal": False,
            "indoor": False,
        },
        {
            "title": "Audley End Miniature Railway",
            "date": weekend_start,
            "venue": "Saffron Walden, CB11 4JL",
            "location": "Saffron Walden",
            "price": "£10-15",
            "url": "https://www.audley-end-railway.co.uk/",
            "travel_time": "~30min",
            "category": "attraction",
            "source": "curated",
            "seasonal": True,
            "indoor": False,
        },
        {
            "title": "West End Shows",
            "date": weekend_start,
            "venue": "West End, London",
            "location": "London",
            "price": "£30-100",
            "url": "https://www.officiallondontheatre.com/",
            "travel_time": "~1h15m by train",
            "category": "show",
            "source": "curated",
            "seasonal": False,
            "indoor": True,
        },
        {
            "title": "Fitzwilliam Museum",
            "date": weekend_start,
            "venue": "Trumpington St, Cambridge",
            "location": "Cambridge",
            "price": "Free",
            "url": "https://www.fitzmuseum.cam.ac.uk/",
            "travel_time": "local",
            "category": "museum",
            "source": "curated",
            "seasonal": False,
            "indoor": True,
        },
        {
            "title": "Cambridge Science Centre",
            "date": weekend_start,
            "venue": "CB1 2AR",
            "location": "Cambridge",
            "price": "£7-10",
            "url": "https://www.cambridgesciencecentre.org/",
            "travel_time": "local",
            "category": "family",
            "source": "curated",
            "seasonal": False,
            "indoor": True,
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


def is_relevant_family_event(event):
    """Filter out irrelevant or blocked events for this family."""
    title = event.get("title", "").lower()
    venue = event.get("venue", "").lower()

    # Blocklist keywords
    blocklist = [
        # Religious
        "church service", "sunday service", "mass", "worship", "prayer meeting", "bible study",
        "cathedral service", "evensong", "eucharist", "liturgy", "church", "pastor", "reverend",
        # Schools (unless public fair)
        "primary school", "secondary school", "infant school", "junior school",
        # Political
        "party meeting", "council meeting", "town hall meeting", "political rally",
        # Adult-only
        "pub crawl", "wine tasting", "nightclub", "club night", "over 18s", "strictly 18+",
        "cocktail masterclass", "speed dating",
        # Community junk
        "community hall booking", "private function", "regular meeting",
        # Toddler/baby (kids are 10 and 13)
        "baby sensory", "toddler group", "soft play", "rhymetime", "storytime for toddlers",
        "stay and play", "messy play", "breastfeeding support", "postnatal",
    ]

    # Check title and venue against blocklist
    for keyword in blocklist:
        if keyword in title or keyword in venue:
            # Allow "school fair" or "school holiday" but block just "school"
            if "school" in keyword and ("fair" in title or "holiday" in title or "workshop" in title):
                continue
            return False

    return True


def detect_category(event):
    """Refine category based on keywords in title and venue."""
    title = event.get("title", "").lower()
    venue = event.get("venue", "").lower()
    combined = f"{title} {venue}"

    mapping = [
        (["museum", "gallery", "exhibition", "collection"], "museum"),
        (["theatre", "show", "musical", "pantomime", "performance", "concert"], "show"),
        (["park", "walk", "trail", "forest", "nature", "garden", "outdoor", "reserve"], "outdoor"),
        (["market", "fair", "shopping", "bazaar", "car boot"], "market"),
        (["festival", "carnival", "fete", "celebration"], "festival"),
        (["climbing", "skating", "trampoline", "sport", "swimming", "football", "tennis", "badminton"], "sports"),
        (["science", "tech", "coding", "maker", "robotics", "workshop", "stem"], "family"),
        (["zoo", "farm", "aquarium", "adventure", "safari", "theme park"], "attraction"),
    ]

    for keywords, category in mapping:
        if any(kw in combined for kw in keywords):
            return category

    return event.get("category", "general")


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
    all_events.extend(get_curated_options(weekend_start))

    # Deduplicate by title; drop junk titles; apply filters
    seen = set()
    unique_events = []
    for ev in all_events:
        if ev.get("status") == "blocked":
            unique_events.append(ev)
            continue
        title = ev.get("title", "")
        if not is_real_event_title(title):
            continue
        if not is_relevant_family_event(ev):
            continue

        # Refine category
        ev["category"] = detect_category(ev)

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

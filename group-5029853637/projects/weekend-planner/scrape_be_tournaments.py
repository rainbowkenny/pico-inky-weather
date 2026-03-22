#!/usr/bin/env python3
"""
Scrape Badminton England U15 tournaments from be.tournamentsoftware.com.

Cookie wall bypass: POST to /cookiewall/Save to accept cookies, then search.
No browser/CDP needed.

Usage: python3 scrape_be_tournaments.py [--level bronze|silver|gold|all] [--months 3]
Output: JSON with tournament list.
"""

import argparse
import html as html_mod
import http.cookiejar
import json
import re
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timedelta

BASE_URL = "https://be.tournamentsoftware.com"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-GB,en;q=0.5",
}

# Category IDs from the BE search form
CATEGORY_IDS = {
    "international": 4205,
    "nationals": 4206,
    "gold": 4207,
    "silver": 4208,
    "bronze": 4209,
    "tier4": 4212,
}

# Distance estimates from Cambridge (CB1) to common badminton venues
VENUE_DISTANCES = {
    "cambridge": ("local", 0),
    "ely": ("~20m", 16),
    "peterborough": ("~45m", 38),
    "bedford": ("~50m", 40),
    "norwich": ("~1h30m", 64),
    "ipswich": ("~1h", 52),
    "hertford": ("~50m", 45),
    "herts": ("~50m", 45),
    "luton": ("~1h", 55),
    "stevenage": ("~45m", 40),
    "milton keynes": ("~1h", 55),
    "northampton": ("~1h", 52),
    "leicester": ("~1h30m", 76),
    "coventry": ("~2h", 100),
    "london": ("~1h15m", 60),
    "birmingham": ("~2h", 110),
    "essex": ("~1h15m", 60),
    "chelmsford": ("~1h15m", 65),
    "redbridge": ("~1h30m", 70),
    "suffolk": ("~1h", 55),
    "kent": ("~2h", 100),
    "notts": ("~2h", 105),
    "nottingham": ("~2h", 105),
    "oxfordshire": ("~1h30m", 80),
    "oxford": ("~1h30m", 80),
    "warwickshire": ("~1h45m", 95),
    "tyneside": ("~4h", 250),
    "somerset": ("~3h", 180),
    "swindon": ("~2h", 120),
    "wiltshire": ("~2h30m", 140),
    "sankey": ("~3h", 170),
    "devon": ("~4h", 230),
    "dorset": ("~3h", 170),
}


def _log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] BE_SCRAPE {msg}", file=sys.stderr)


def estimate_distance(name_str):
    """Estimate travel time/distance from Cambridge based on tournament name or venue."""
    if not name_str:
        return "unknown", 999
    low = name_str.lower()
    for place, (time_str, km) in VENUE_DISTANCES.items():
        if place in low:
            return time_str, km
    return "~1-2h (est.)", 80


def create_opener():
    """Create a urllib opener with cookie jar."""
    cj = http.cookiejar.CookieJar()
    return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj)), cj


def accept_cookies(opener):
    """Accept the cookie wall on be.tournamentsoftware.com."""
    _log("Accepting cookie wall...")
    try:
        # Step 1: Hit the site to get session cookies
        req1 = urllib.request.Request(f"{BASE_URL}/", headers=HEADERS)
        opener.open(req1, timeout=10)

        # Step 2: POST to accept cookies
        data = urllib.parse.urlencode({
            "ReturnUrl": "",
            "SettingsOpen": "false",
        }).encode()
        req2 = urllib.request.Request(
            f"{BASE_URL}/cookiewall/Save",
            data=data,
            headers={**HEADERS, "Content-Type": "application/x-www-form-urlencoded",
                     "Referer": f"{BASE_URL}/"},
        )
        opener.open(req2, timeout=10)
        _log("Cookie wall accepted ✓")
        return True
    except Exception as e:
        _log(f"Cookie accept failed: {e}")
        return False


def search_tournaments(opener, levels=None, months=3):
    """Search for U15 tournaments via the DoSearch endpoint.

    Args:
        opener: urllib opener with accepted cookies
        levels: list of level names (bronze, silver, gold) or None for all
        months: how many months ahead to search

    Returns:
        list of tournament dicts
    """
    start_date = datetime.now().strftime("%d/%m/%Y")
    end_date = (datetime.now() + timedelta(days=months * 30)).strftime("%d/%m/%Y")

    # Build form data
    form_fields = {
        "TournamentExtendedFilter.AgeGroupID": "15",  # U15
        "TournamentFilter.DateFilterType": "DateRange",
        "TournamentFilter.StartDate": start_date,
        "TournamentFilter.EndDate": end_date,
        "Page": "1",
    }

    # Add category filters if specific levels requested
    if levels:
        for i, level in enumerate(levels):
            cat_id = CATEGORY_IDS.get(level.lower())
            if cat_id:
                form_fields[f"TournamentExtendedFilter.TournamentCategoryIDList[{i}]"] = str(cat_id)

    post_data = urllib.parse.urlencode(form_fields).encode()
    _log(f"Searching: levels={levels}, range={start_date} - {end_date}")

    req = urllib.request.Request(
        f"{BASE_URL}/find/tournament/DoSearch",
        data=post_data,
        headers={
            **HEADERS,
            "Content-Type": "application/x-www-form-urlencoded",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": f"{BASE_URL}/find/tournament",
        },
    )
    resp = opener.open(req, timeout=20)
    html = resp.read().decode("utf-8", errors="replace")
    _log(f"Search response: {len(html)} bytes")
    return parse_results(html)


def parse_results(html):
    """Parse tournament list items from the DoSearch HTML response."""
    items = re.findall(r'<li class="list__item">(.*?)</li>', html, re.DOTALL)
    tournaments = []

    for item in items:
        # Extract tournament name
        name_match = re.search(
            r'<span class="nav-link__value">([^<]+)</span>', item
        )
        if not name_match:
            continue
        name = html_mod.unescape(name_match.group(1).strip())

        # Skip "Online Entry" phantom items
        if name.lower() in ("online entry", ""):
            continue

        # Extract dates
        date_matches = re.findall(
            r'<time datetime="([^"]+)"[^>]*>([^<]+)</time>', item
        )
        start_date = date_matches[0][0][:10] if date_matches else ""
        display_date = date_matches[0][1].strip() if date_matches else ""
        end_date = ""
        if len(date_matches) > 1:
            end_date = date_matches[1][0][:10]
            display_date += f" - {date_matches[1][1].strip()}"

        # Extract location
        location_match = re.search(r'<span class="p-locality">([^<]+)</span>', item)
        location = html_mod.unescape(location_match.group(1).strip()) if location_match else ""

        # Extract tags (level, entry status, etc.)
        tags = re.findall(r'<span class="tag[^"]*">([^<]+)</span>', item)
        tags = [html_mod.unescape(t.strip()) for t in tags]

        # Determine level from tags
        level = "Unknown"
        for tag in tags:
            if tag.lower() in ("bronze", "silver", "gold", "other", "tier 4"):
                level = tag
                break

        # Extract URL
        link_match = re.search(r'href="(/sport/tournament\?id=[^"]+)"', item)
        url = f"{BASE_URL}{link_match.group(1)}" if link_match else ""

        # Check entry status
        has_online_entry = "Online Entry" in item or "online-entry" in item.lower()
        entry_open = any("open" in t.lower() for t in tags)

        # Distance estimate from name + location
        travel_time, km = estimate_distance(f"{name} {location}")

        tournaments.append({
            "name": name,
            "date": start_date,
            "end_date": end_date,
            "display_date": display_date,
            "venue": location,
            "level": level,
            "tags": tags,
            "url": url,
            "online_entry": has_online_entry,
            "entry_open": entry_open,
            "distance_from_cambridge": travel_time,
            "km": km,
            "source": "be_tournamentsoftware",
        })

    return tournaments


def main():
    parser = argparse.ArgumentParser(
        description="Scrape BE U15 tournaments. Outputs JSON."
    )
    parser.add_argument(
        "--level", "-l",
        default="all",
        help="Filter by level: bronze, silver, gold, all (default: all)",
    )
    parser.add_argument(
        "--months", "-m",
        type=int, default=3,
        help="Months ahead to search (default: 3)",
    )
    parser.add_argument(
        "--max-km",
        type=int, default=150,
        help="Max distance in km from Cambridge (default: 150)",
    )
    args = parser.parse_args()

    levels = None
    if args.level != "all":
        levels = [l.strip() for l in args.level.split(",")]

    opener, cj = create_opener()

    # Accept cookies
    if not accept_cookies(opener):
        output = {
            "status": "error",
            "error_code": "cookie_accept_failed",
            "scraped_at": datetime.now().isoformat(),
            "total": 0,
            "tournaments": [],
        }
        print(json.dumps(output, indent=2, ensure_ascii=False))
        sys.exit(1)

    # Search
    try:
        tournaments = search_tournaments(opener, levels=levels, months=args.months)
    except Exception as e:
        _log(f"Search failed: {e}")
        output = {
            "status": "error",
            "error_code": "search_failed",
            "error_detail": str(e),
            "scraped_at": datetime.now().isoformat(),
            "total": 0,
            "tournaments": [],
        }
        print(json.dumps(output, indent=2, ensure_ascii=False))
        sys.exit(1)

    # Filter by distance
    filtered = [t for t in tournaments if t["km"] <= args.max_km]
    excluded = [t for t in tournaments if t["km"] > args.max_km]

    # Sort by date then distance
    filtered.sort(key=lambda t: (t.get("date", "9999"), t.get("km", 999)))

    output = {
        "status": "ok",
        "scraped_at": datetime.now().isoformat(),
        "total": len(filtered),
        "total_unfiltered": len(tournaments),
        "excluded_by_distance": len(excluded),
        "max_km": args.max_km,
        "tournaments": filtered,
    }

    _log(f"DONE: {len(filtered)} tournaments within {args.max_km}km "
         f"({len(excluded)} excluded by distance)")
    print(json.dumps(output, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Scrape Badminton England tournaments for U15 Bronze level.
Tries be.tournamentsoftware.com, then badmintonengland.co.uk as fallback.
Usage: python3 scrape_be_tournaments.py [--help]
Output: JSON list of tournaments.
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
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive",
}

CAMBRIDGE_POSTCODE = "CB1"

# Classified error codes for diagnostics
ERR_COOKIE_BLOCKED = "cookie_blocked"
ERR_BROWSER_UNAVAILABLE = "browser_unavailable"
ERR_SITE_UNREACHABLE = "site_unreachable"
ERR_PARSE_FAILED = "parse_failed"


def _log(msg):
    """Concise stderr log line with timestamp."""
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] BE_SCRAPE {msg}", file=sys.stderr)


def prewarm_tournamentsoftware():
    """Lightweight check: is tournamentsoftware.com reachable and not cookie-walled?

    Returns (ok: bool, error_code: str|None, detail: str).
    """
    _log("PREWARM START tournamentsoftware.com")
    url = "https://www.tournamentsoftware.com/"
    try:
        html, final_url = fetch_url(url, timeout=10)
    except urllib.error.URLError as e:
        _log(f"PREWARM FAIL site_unreachable err={e}")
        return False, ERR_SITE_UNREACHABLE, f"Cannot reach tournamentsoftware.com: {e}"
    except Exception as e:
        _log(f"PREWARM FAIL site_unreachable err={e}")
        return False, ERR_SITE_UNREACHABLE, f"Connection error: {e}"

    low = html.lower()
    if ("cookie" in low or "consent" in low) and len(html) < 5000:
        _log("PREWARM FAIL cookie_blocked (consent/cookie wall detected)")
        return False, ERR_COOKIE_BLOCKED, "Cookie/consent wall on tournamentsoftware.com"

    if "blocked" in low or "cloudflare" in low or "captcha" in low:
        _log("PREWARM FAIL cookie_blocked (cloudflare/captcha)")
        return False, ERR_COOKIE_BLOCKED, "Blocked by Cloudflare/captcha"

    _log("PREWARM OK tournamentsoftware.com reachable")
    return True, None, ""

# Distance estimates from Cambridge to common badminton venues
VENUE_DISTANCES = {
    "cambridge": ("local", 0),
    "ely": ("~20m", 16),
    "peterborough": ("~45m", 38),
    "bedford": ("~50m", 40),
    "norwich": ("~1h30m", 64),
    "ipswich": ("~1h", 52),
    "hertford": ("~1h", 50),
    "luton": ("~1h", 55),
    "stevenage": ("~45m", 40),
    "milton keynes": ("~1h", 55),
    "northampton": ("~1h", 52),
    "leicester": ("~1h30m", 76),
    "coventry": ("~2h", 100),
    "london": ("~1h15m", 60),
    "birmingham": ("~2h", 110),
}


def estimate_distance(venue_str):
    if not venue_str:
        return "unknown", 999
    v = venue_str.lower()
    for city, (time, km) in VENUE_DISTANCES.items():
        if city in v:
            return time, km
    return "~1-2h from Cambridge", 80


def fetch_url(url, timeout=20, extra_headers=None):
    headers = dict(HEADERS)
    if extra_headers:
        headers.update(extra_headers)
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
        # Handle gzip
        ct = resp.headers.get("Content-Encoding", "")
        if "gzip" in ct:
            import gzip
            raw = gzip.decompress(raw)
        return raw.decode("utf-8", errors="replace"), resp.geturl()


class TableParser(HTMLParser):
    """Parse HTML tables into list of row dicts."""
    def __init__(self, header_map=None):
        super().__init__()
        self.rows = []
        self.headers = []
        self._in_table = False
        self._in_header = False
        self._in_row = False
        self._in_cell = False
        self._cell_data = []
        self._current_row = []
        self._skip_tags = {"script", "style"}
        self._skip = False
        self._link = None
        self._cell_link = None

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        if tag in self._skip_tags:
            self._skip = True
        elif tag == "table":
            self._in_table = True
        elif tag == "tr" and self._in_table:
            self._in_row = True
            self._current_row = []
            self._cell_links = []
        elif tag in ("th", "td") and self._in_row:
            self._in_cell = True
            self._cell_data = []
            self._cell_link = None
        elif tag == "a" and self._in_cell:
            self._cell_link = attrs_dict.get("href", "")

    def handle_endtag(self, tag):
        if tag in self._skip_tags:
            self._skip = False
        elif tag in ("th", "td") and self._in_cell:
            self._in_cell = False
            cell_text = " ".join(self._cell_data).strip()
            self._current_row.append((cell_text, self._cell_link))
        elif tag == "tr" and self._in_row:
            self._in_row = False
            if self._current_row:
                # First row = headers if no headers yet
                texts = [c[0] for c in self._current_row]
                if not self.headers and all(c[1] is None for c in self._current_row):
                    self.headers = texts
                else:
                    self.rows.append(self._current_row)

    def handle_data(self, data):
        if self._skip:
            return
        if self._in_cell:
            stripped = data.strip()
            if stripped:
                self._cell_data.append(stripped)


def try_tournamentsoftware():
    """Try to get U15 tournaments from be.tournamentsoftware.com.

    Returns (results|None, error_code|None, detail).
    """
    results = []
    try:
        url = "https://be.tournamentsoftware.com/find/tournament?organizerID=2&Level=3&AgeCategory=U15&CountryID=113"
        _log("FETCH START be.tournamentsoftware.com")
        html, final_url = fetch_url(url, timeout=15)
        _log(f"FETCH OK be.tournamentsoftware.com len={len(html)}")

        # Check for cookie wall / blocked
        if "cookie" in html.lower() and len(html) < 5000:
            return None, ERR_COOKIE_BLOCKED, "Cookie wall detected on tournamentsoftware.com"

        if "blocked" in html.lower() or "cloudflare" in html.lower():
            return None, ERR_COOKIE_BLOCKED, "Blocked by security layer"

        # Try to parse tournament table
        parser = TableParser()
        parser.feed(html)

        # Also try JSON-LD
        ld_matches = re.findall(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', html, re.DOTALL)
        for ld in ld_matches:
            try:
                data = json.loads(ld)
                if isinstance(data, list):
                    for item in data:
                        if "tournament" in str(item.get("@type", "")).lower():
                            results.append(item)
            except json.JSONDecodeError:
                pass

        # Parse table rows
        for row in parser.rows:
            texts = [c[0] for c in row]
            links = [c[1] for c in row]
            if len(texts) >= 2:
                name = texts[0] if texts[0] else ""
                date = texts[1] if len(texts) > 1 else ""
                venue = texts[2] if len(texts) > 2 else ""
                level = texts[3] if len(texts) > 3 else ""
                combined = f"{name} {level}".lower()
                if any(kw in combined for kw in ["u15", "under 15", "bronze"]) or True:
                    link = next((l for l in links if l), "")
                    if link and not link.startswith("http"):
                        link = f"https://be.tournamentsoftware.com{link}"
                    travel, km = estimate_distance(venue)
                    results.append({
                        "name": name,
                        "date": date,
                        "venue": venue,
                        "level": level,
                        "registration_deadline": "",
                        "url": link,
                        "distance_from_cambridge": travel,
                        "km": km,
                        "source": "tournamentsoftware",
                    })

        if results:
            return results, None, ""
        return None, ERR_PARSE_FAILED, "No tournaments parsed from tournamentsoftware HTML"

    except urllib.error.HTTPError as e:
        return None, ERR_SITE_UNREACHABLE, f"HTTP {e.code} from tournamentsoftware.com"
    except urllib.error.URLError as e:
        return None, ERR_SITE_UNREACHABLE, f"Cannot reach tournamentsoftware.com: {e}"
    except Exception as e:
        return None, ERR_PARSE_FAILED, f"Error fetching tournamentsoftware.com: {e}"


def try_badmintonengland_site():
    """Try Badminton England main site tournament calendar.

    Returns (results|None, error_code|None, detail).
    """
    results = []
    try:
        urls_to_try = [
            "https://www.badmintonengland.co.uk/tournaments/",
            "https://www.badmintonengland.co.uk/play/tournaments/",
            "https://www.badmintonengland.co.uk/competitions/",
        ]
        html = None
        used_url = None
        for url in urls_to_try:
            try:
                html, used_url = fetch_url(url, timeout=15)
                if html and len(html) > 500:
                    break
            except Exception:
                continue

        if not html:
            return None, ERR_SITE_UNREACHABLE, "Could not reach badmintonengland.co.uk"

        # JSON-LD
        ld_matches = re.findall(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', html, re.DOTALL)
        for ld in ld_matches:
            try:
                data = json.loads(ld)
                items = data if isinstance(data, list) else [data]
                for item in items:
                    if item.get("@type") == "Event":
                        loc = item.get("location", {})
                        loc_name = loc.get("name", "") if isinstance(loc, dict) else str(loc)
                        start = item.get("startDate", "")
                        travel, km = estimate_distance(loc_name)
                        results.append({
                            "name": item.get("name", ""),
                            "date": start[:10] if start else "",
                            "venue": loc_name,
                            "level": "Bronze",
                            "registration_deadline": "",
                            "url": item.get("url", used_url),
                            "distance_from_cambridge": travel,
                            "km": km,
                            "source": "badmintonengland",
                        })
            except (json.JSONDecodeError, AttributeError):
                pass

        # Text extraction for tournament names
        if not results:
            tourney_matches = re.findall(
                r'(?:U15|Under.?15|Bronze|Junior)[^\n<]{0,100}(?:tournament|open|championships?)',
                html, re.IGNORECASE
            )
            for match in tourney_matches[:10]:
                clean = re.sub(r"<[^>]+>", "", match).strip()
                if clean:
                    results.append({
                        "name": clean,
                        "date": "",
                        "venue": "",
                        "level": "Bronze U15",
                        "registration_deadline": "",
                        "url": used_url,
                        "distance_from_cambridge": "unknown",
                        "km": 999,
                        "source": "badmintonengland",
                    })

        if results:
            return results, None, ""
        return None, ERR_PARSE_FAILED, "No tournaments found on badmintonengland.co.uk"

    except Exception as e:
        return None, ERR_SITE_UNREACHABLE, f"Error fetching badmintonengland.co.uk: {e}"


def try_be_search_api():
    """Try Badminton England / tournament software search API endpoints.

    Returns (results|None, error_code|None, detail).
    """
    results = []
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        future = (datetime.now() + timedelta(days=90)).strftime("%Y-%m-%d")

        api_urls = [
            f"https://be.tournamentsoftware.com/api/tournament/find?organizerID=2&startDate={today}&endDate={future}&ageCategory=U15",
            f"https://be.tournamentsoftware.com/find/tournament?organizerID=2&startDate={today}&CategoryID=3",
        ]
        for url in api_urls:
            try:
                html, _ = fetch_url(url, timeout=10)
                try:
                    data = json.loads(html)
                    if isinstance(data, list):
                        for t in data:
                            travel, km = estimate_distance(t.get("venue", "") or t.get("location", ""))
                            results.append({
                                "name": t.get("name", t.get("title", "")),
                                "date": t.get("startDate", t.get("date", ""))[:10] if t.get("startDate") else "",
                                "venue": t.get("venue", t.get("location", "")),
                                "level": t.get("level", "Bronze"),
                                "registration_deadline": t.get("registrationDeadline", ""),
                                "url": t.get("url", url),
                                "distance_from_cambridge": travel,
                                "km": km,
                                "source": "be_api",
                            })
                    if results:
                        return results, None, ""
                except json.JSONDecodeError:
                    pass
            except Exception:
                continue

        return None, ERR_SITE_UNREACHABLE, "BE API endpoints not accessible"
    except Exception as e:
        return None, ERR_SITE_UNREACHABLE, f"BE API error: {e}"


def curated_fallback():
    """Return curated known tournaments as a fallback."""
    today = datetime.now()
    # Approximate upcoming tournament dates based on typical BE calendar
    upcoming = []
    # Find next few Saturdays
    for week_offset in range(1, 12):
        saturday = today + timedelta(days=(5 - today.weekday() + 7 * week_offset) % 7 + 7 * (week_offset - 1))
        # Placeholder entries (real ones would be scraped)
    return [
        {
            "name": "Hertfordshire Junior Open (U15 Bronze — typical example)",
            "date": "check badmintonengland.co.uk",
            "venue": "Hertfordshire Badminton, Stevenage",
            "level": "Bronze U15",
            "registration_deadline": "check site",
            "url": "https://www.badmintonengland.co.uk/tournaments/",
            "distance_from_cambridge": "~45m",
            "km": 40,
            "source": "curated_fallback",
            "note": "Live scraping was blocked. Check site directly for accurate dates.",
        }
    ]


def main():
    parser = argparse.ArgumentParser(
        description="Scrape Badminton England U15 Bronze tournaments. Outputs JSON."
    )
    parser.parse_args()

    errors = []
    tournaments = []

    # Prewarm: lightweight reachability + cookie-wall check
    pw_ok, pw_code, pw_detail = prewarm_tournamentsoftware()
    if not pw_ok:
        errors.append({"source": "prewarm", "error_code": pw_code, "reason": pw_detail})

    # Try 1: Tournament Software (skip if prewarm found cookie wall)
    if pw_code != ERR_COOKIE_BLOCKED:
        results, err_code, detail = try_tournamentsoftware()
        if results:
            tournaments.extend(results)
        else:
            errors.append({"source": "tournamentsoftware", "error_code": err_code, "reason": detail})
    else:
        _log("SKIP tournamentsoftware (cookie wall detected in prewarm)")
        errors.append({"source": "tournamentsoftware", "error_code": ERR_COOKIE_BLOCKED,
                        "reason": "Skipped — prewarm detected cookie wall"})

    # Try 2: BE API
    if not tournaments:
        results, err_code, detail = try_be_search_api()
        if results:
            tournaments.extend(results)
        else:
            errors.append({"source": "be_api", "error_code": err_code, "reason": detail})

    # Try 3: BE website
    if not tournaments:
        results, err_code, detail = try_badmintonengland_site()
        if results:
            tournaments.extend(results)
        else:
            errors.append({"source": "badmintonengland", "error_code": err_code, "reason": detail})

    # Filter: within 2.5h (~150km)
    def is_relevant(t):
        km = t.get("km", 0)
        return km <= 150

    filtered = [t for t in tournaments if is_relevant(t)]

    # Sort by date then distance
    def sort_key(t):
        return (t.get("date", "9999"), t.get("km", 999))
    filtered.sort(key=sort_key)

    # If nothing found, use curated fallback
    if not filtered:
        filtered = curated_fallback()
        errors.append({"source": "all", "error_code": ERR_PARSE_FAILED,
                        "reason": "All live sources failed; using curated fallback"})

    # Determine dominant error_code for easy consumption by daily_push
    dominant_code = None
    if errors:
        codes = [e.get("error_code") for e in errors if e.get("error_code")]
        if codes:
            dominant_code = codes[0]  # first failure is most informative

    output = {
        "status": "ok" if filtered and not all(e.get("source") == "curated_fallback" for e in filtered) else "partial",
        "scraped_at": datetime.now().isoformat(),
        "total": len(filtered),
        "tournaments": filtered,
    }
    if errors:
        output["scrape_errors"] = errors
    if dominant_code:
        output["error_code"] = dominant_code

    _log(f"DONE status={output['status']} total={output['total']} error_code={dominant_code}")
    print(json.dumps(output, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

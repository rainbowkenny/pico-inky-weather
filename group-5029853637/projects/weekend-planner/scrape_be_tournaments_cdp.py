#!/usr/bin/env python3
"""
Scrape BE tournaments via CDP from the already-loaded openclaw browser.
Falls back to original scraper if browser unavailable.

Text pattern per tournament:
  <name>
  <county> | <city>
  DD/MM/YYYY
  <level: Bronze|Silver|Gold|Other>
  <age groups: U11, U13, U15...>
  [ONLINE ENTRY]
  [Xd]  (days until entry deadline)
"""

import asyncio
import json
import re
import sys
import urllib.request
from datetime import datetime

CDP_PORT = 18800


def _log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", file=sys.stderr)


def get_tabs():
    try:
        req = urllib.request.Request(f"http://127.0.0.1:{CDP_PORT}/json/list")
        with urllib.request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read())
    except Exception:
        return []


def find_tab(tabs, pattern):
    """Find tab matching pattern. Prefer tabs with AgeGroupID=15 in URL."""
    matches = [t for t in tabs if pattern in t.get("url", "")]
    # Prefer the one with AgeGroupID in URL (better filtered)
    for m in matches:
        if "AgeGroupID" in m.get("url", ""):
            return m
    return matches[0] if matches else None


async def cdp_eval(ws_url, expr, timeout=10):
    import websockets
    async with websockets.connect(ws_url) as ws:
        await ws.send(json.dumps({"id": 1, "method": "Runtime.evaluate", "params": {"expression": expr}}))
        r = json.loads(await asyncio.wait_for(ws.recv(), timeout=timeout))
        return r.get("result", {}).get("result", {}).get("value", "")


def parse_tournaments(text):
    """Parse structured tournament list from BE search results plaintext."""
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    tournaments = []
    i = 0

    while i < len(lines):
        # Look for date pattern DD/MM/YYYY
        if re.match(r"\d{2}/\d{2}/\d{4}(\s+to\s+\d{2}/\d{2}/\d{4})?$", lines[i]):
            date_str = lines[i]
            # Name is 2 lines before, venue is 1 line before
            name = lines[i - 2] if i >= 2 else "Unknown"
            venue_line = lines[i - 1] if i >= 1 else ""

            # Level is next line
            level = lines[i + 1] if i + 1 < len(lines) else ""
            if level not in ("Bronze", "Silver", "Gold", "Other"):
                i += 1
                continue

            # Collect age groups
            age_groups = []
            j = i + 2
            while j < len(lines) and re.match(r"U\d+$", lines[j]):
                age_groups.append(lines[j])
                j += 1

            # Check for ONLINE ENTRY and days
            entry_open = False
            days_left = None
            for k in range(j, min(j + 3, len(lines))):
                if "ONLINE ENTRY" in lines[k]:
                    entry_open = True
                dm = re.match(r"(\d+)d$", lines[k].strip())
                if dm:
                    days_left = int(dm.group(1))

            # Filter: U15, Bronze/Silver/Gold only, no "Futures"
            if "U15" in age_groups and level in ("Bronze", "Silver", "Gold") and "futures" not in name.lower():
                tournaments.append({
                    "name": name,
                    "date": date_str,
                    "venue": venue_line,
                    "level": f"{level} U15",
                    "entry_open": entry_open,
                    "days_until_deadline": days_left,
                    "age_groups": age_groups,
                })

            i = j
        else:
            i += 1

    return tournaments


def main():
    _log("BE_CDP_SCRAPE START")

    tabs = get_tabs()
    search_tab = find_tab(tabs, "be.tournamentsoftware.com/find")

    if not search_tab:
        _log("BE_CDP_SCRAPE no search tab, falling back to original scraper")
        import subprocess
        r = subprocess.run([sys.executable, __file__.replace("_cdp", "")], capture_output=True, text=True, timeout=60)
        print(r.stdout)
        sys.exit(r.returncode)

    _log(f"BE_CDP_SCRAPE using tab {search_tab['id']}")
    text = asyncio.run(cdp_eval(search_tab["webSocketDebuggerUrl"], "document.body.innerText"))

    tournaments = parse_tournaments(text)
    _log(f"BE_CDP_SCRAPE parsed {len(tournaments)} U15 tournaments")

    # Filter out past tournaments
    today = datetime.now().strftime("%d/%m/%Y")
    upcoming = []
    for t in tournaments:
        d = t["date"].split(" to ")[0]  # handle multi-day
        try:
            dt = datetime.strptime(d, "%d/%m/%Y")
            if dt >= datetime.now().replace(hour=0, minute=0, second=0, microsecond=0):
                upcoming.append(t)
        except ValueError:
            upcoming.append(t)

    output = {
        "status": "ok",
        "scraped_at": datetime.now().isoformat(),
        "source": "cdp_browser",
        "total": len(upcoming),
        "tournaments": upcoming,
    }
    print(json.dumps(output, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

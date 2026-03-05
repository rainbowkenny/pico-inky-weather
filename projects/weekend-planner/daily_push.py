#!/usr/bin/env python3
"""
Weekend planner daily push — orchestrates all data sources and generates
a Chinese-language push message with activity options.
Usage: python3 daily_push.py [--help]
Output: Formatted Chinese push message to stdout.
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timedelta

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LEYS_SCRIPT = "/home/albert/.openclaw/workspace/skills/cc/scripts/scrape_leys.py"

WTTR_URL = "https://wttr.in/Cambridge?format=j1"


def get_next_weekend():
    """Return (saturday, sunday) as YYYY-MM-DD strings."""
    today = datetime.now()
    days_until_sat = (5 - today.weekday()) % 7
    if days_until_sat == 0:
        days_until_sat = 7
    saturday = today + timedelta(days=days_until_sat)
    sunday = saturday + timedelta(days=1)
    return saturday.strftime("%Y-%m-%d"), sunday.strftime("%Y-%m-%d")


def _log(msg):
    """Write a single-line timing/diagnostic log to stderr."""
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", file=sys.stderr)


# Accumulates (step_name, elapsed_s, outcome) for the final summary table.
_step_timings = []


def run_script(script_path, *args, timeout=60):
    """Run a python script, return parsed JSON output or error dict."""
    script_name = os.path.basename(script_path)
    cmd = [sys.executable, script_path] + list(args)
    _log(f"SUBPROCESS START cmd={script_name} timeout={timeout}s")
    t0 = time.monotonic()
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        elapsed = time.monotonic() - t0
        if result.stdout.strip():
            data = json.loads(result.stdout)
            _log(f"SUBPROCESS OK    cmd={script_name} elapsed={elapsed:.1f}s")
            return data
        reason = result.stderr.strip()[:200] or "No output"
        _log(f"SUBPROCESS EMPTY cmd={script_name} elapsed={elapsed:.1f}s reason={reason}")
        return {"status": "error", "reason": reason}
    except subprocess.TimeoutExpired:
        elapsed = time.monotonic() - t0
        _log(f"SUBPROCESS TIMEOUT cmd={script_name} elapsed={elapsed:.1f}s limit={timeout}s")
        return {"status": "error", "reason": f"Script timed out after {timeout}s"}
    except json.JSONDecodeError as e:
        elapsed = time.monotonic() - t0
        _log(f"SUBPROCESS JSON_ERR cmd={script_name} elapsed={elapsed:.1f}s err={e}")
        return {"status": "error", "reason": f"Invalid JSON: {e}"}
    except Exception as e:
        elapsed = time.monotonic() - t0
        _log(f"SUBPROCESS ERROR cmd={script_name} elapsed={elapsed:.1f}s err={e}")
        return {"status": "error", "reason": str(e)}


def fetch_weather(location="Cambridge"):
    """Fetch weather from wttr.in. Returns (summary, emoji) tuple."""
    try:
        url = f"https://wttr.in/{location.replace(' ', '+')}?format=j1"
        req = urllib.request.Request(url, headers={"User-Agent": "curl/7.68.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())

        # Parse weekend forecast
        forecasts = data.get("weather", [])
        if not forecasts:
            return "天气未知", "🌤️"

        # wttr.in returns up to 3 days; pick Saturday (index 0 or 1 depending on day)
        today = datetime.now()
        days_until_sat = (5 - today.weekday()) % 7
        # Use first available forecast
        fc = forecasts[min(days_until_sat, len(forecasts) - 1)]

        max_temp = fc.get("maxtempC", "?")
        min_temp = fc.get("mintempC", "?")
        desc = fc.get("hourly", [{}])[4].get("weatherDesc", [{}])[0].get("value", "")

        # Map to emoji
        desc_lower = desc.lower()
        if "sun" in desc_lower or "clear" in desc_lower:
            emoji = "☀️"
        elif "cloud" in desc_lower and "sun" in desc_lower:
            emoji = "⛅"
        elif "cloud" in desc_lower or "overcast" in desc_lower:
            emoji = "☁️"
        elif "rain" in desc_lower or "shower" in desc_lower:
            emoji = "🌧️"
        elif "snow" in desc_lower:
            emoji = "❄️"
        elif "thunder" in desc_lower:
            emoji = "⛈️"
        else:
            emoji = "🌤️"

        summary = f"{min_temp}–{max_temp}°C {desc}"
        return summary, emoji

    except Exception as e:
        return f"天气获取失败 ({e})", "🌤️"


def get_school_status(saturday, leys_data):
    """Check if Saturday has school events."""
    if not leys_data or leys_data.get("status") == "error":
        return "学校状态未知"

    sat_events = leys_data.get("saturday_events", [])
    for ev in sat_events:
        if ev.get("date") == saturday:
            return f"学校活动: {ev.get('title', '')}"

    # Check if it's a school term weekend
    all_ev = leys_data.get("all_events", [])
    nearby = [e for e in all_ev if e.get("date", "") and abs(
        (datetime.strptime(e["date"], "%Y-%m-%d") - datetime.strptime(saturday, "%Y-%m-%d")).days
    ) <= 3]
    if nearby:
        return "学期中"
    return "假期/无学校活动"


def format_gcal_events(gcal_data, saturday, sunday):
    """Format existing calendar events for the weekend."""
    if not gcal_data or gcal_data.get("status") == "error":
        return ["日历获取失败"]

    events = gcal_data.get("events", [])
    weekend_events = []
    for ev in events:
        start = ev.get("start", "")
        if not start:
            continue
        date_part = start[:10]
        if date_part in (saturday, sunday):
            time_part = ""
            if "T" in start:
                time_part = start[11:16] + " "
            cal = ev.get("calendar", "")
            title = ev.get("title", "无标题")
            loc = ev.get("location", "")
            loc_str = f" @ {loc}" if loc else ""
            day_str = "周六" if date_part == saturday else "周日"
            weekend_events.append(f"{day_str} {time_part}{title}{loc_str} [{cal}]")

    return weekend_events if weekend_events else ["本周末暂无日历事件"]


def pick_best_tournaments(be_data, saturday):
    """Pick top 2 nearby tournaments."""
    if not be_data or be_data.get("status") == "error":
        return []
    tournaments = be_data.get("tournaments", [])
    # Filter by date proximity
    candidates = []
    for t in tournaments:
        date = t.get("date", "")
        km = t.get("km", 999)
        if km <= 150:  # within 2.5h
            candidates.append(t)
    candidates.sort(key=lambda t: (t.get("km", 999)))
    return candidates[:2]


def pick_best_events(events_data, n=3):
    """Pick diverse activity options."""
    if not events_data or events_data.get("status") == "error":
        return []
    events = events_data.get("events", [])
    # Prefer variety of categories
    categories_seen = set()
    picked = []
    for ev in events:
        cat = ev.get("category", "general")
        if cat not in categories_seen or len(picked) < 2:
            picked.append(ev)
            categories_seen.add(cat)
        if len(picked) >= n:
            break
    return picked


def format_option(title, details, price, travel, emoji="🎭"):
    """Format a single activity option."""
    parts = [details] if details else []
    if price:
        parts.append(f"£{price}" if not str(price).startswith("£") else str(price))
    if travel and travel not in ("local", "unknown"):
        parts.append(f"🚗 {travel}")
    detail_str = " | ".join(parts)
    if detail_str:
        return f"{emoji} {title}\n   {detail_str}"
    return f"{emoji} {title}"


def build_message(saturday, sunday, weather_summary, weather_emoji,
                  school_status, gcal_events, options):
    """Build the Chinese push message."""
    # Format date nicely
    sat_dt = datetime.strptime(saturday, "%Y-%m-%d")
    date_str = sat_dt.strftime("%-m月%-d日")

    lines = [
        f"🗓️ 周末 {date_str} ({school_status}) {weather_emoji} {weather_summary}",
        "",
        "📅 日历已有:",
    ]
    for ev in gcal_events:
        lines.append(f"  - {ev}")

    lines.append("")

    if options:
        for i, opt in enumerate(options, 1):
            lines.append(opt)
            if i < len(options):
                lines.append("")

    lines.append("")
    lines.append("回复 1/2/3 选择 ✅")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Generate Chinese weekend push message with activity options."
    )
    parser.parse_args()

    run_start = time.monotonic()
    saturday, sunday = get_next_weekend()

    _log(f"RUN START weekend={saturday}..{sunday}")

    # 1. Fetch calendar
    _log("STEP [1/6] START gcal_fetch")
    t0 = time.monotonic()
    gcal_script = os.path.join(SCRIPT_DIR, "gcal_fetch.py")
    gcal_data = run_script(gcal_script, "--days", "14")
    s1 = time.monotonic() - t0
    outcome = "ok" if gcal_data.get("status") != "error" else "error"
    _log(f"STEP [1/6] END   gcal_fetch elapsed={s1:.1f}s outcome={outcome}")
    _step_timings.append(("gcal_fetch", s1, outcome))

    # 2. Scrape events
    _log("STEP [2/6] START scrape_events")
    t0 = time.monotonic()
    events_script = os.path.join(SCRIPT_DIR, "scrape_events.py")
    events_data = run_script(events_script, "--weekend", saturday)
    s2 = time.monotonic() - t0
    outcome = "ok" if events_data.get("status") != "error" else "error"
    _log(f"STEP [2/6] END   scrape_events elapsed={s2:.1f}s outcome={outcome}")
    _step_timings.append(("scrape_events", s2, outcome))

    # 3. Gmail scan -> auto-add family calendar
    _log("STEP [3/6] START gmail_to_family_calendar")
    t0 = time.monotonic()
    gmail_scan_script = os.path.join(SCRIPT_DIR, "gmail_to_family_calendar.py")
    gmail_scan_data = run_script(gmail_scan_script, timeout=45)
    s3a = time.monotonic() - t0
    outcome = "ok" if gmail_scan_data.get("status") != "error" else "error"
    _log(f"STEP [3/6] END   gmail_to_family_calendar elapsed={s3a:.1f}s outcome={outcome}")
    _step_timings.append(("gmail_to_family_calendar", s3a, outcome))

    # 4. Scrape tournaments (with prewarm diagnostics)
    _log("STEP [4/6] START scrape_be_tournaments")
    t0 = time.monotonic()
    be_script = os.path.join(SCRIPT_DIR, "scrape_be_tournaments.py")
    be_data = run_script(be_script, timeout=30)
    s3 = time.monotonic() - t0
    be_error_code = be_data.get("error_code")  # cookie_blocked|browser_unavailable|site_unreachable|parse_failed
    if be_data.get("status") == "error":
        outcome = be_error_code or "error"
    elif be_error_code:
        outcome = f"partial:{be_error_code}"
    else:
        outcome = "ok"
    _log(f"STEP [4/6] END   scrape_be_tournaments elapsed={s3:.1f}s outcome={outcome}")
    _step_timings.append(("scrape_be_tournaments", s3, outcome))

    # 5. Leys calendar
    _log("STEP [5/6] START scrape_leys")
    t0 = time.monotonic()
    leys_data = run_script(LEYS_SCRIPT, "--weeks", "4", timeout=30)
    s4 = time.monotonic() - t0
    outcome = "ok" if leys_data.get("status") != "error" else "error"
    _log(f"STEP [5/6] END   scrape_leys elapsed={s4:.1f}s outcome={outcome}")
    _step_timings.append(("scrape_leys", s4, outcome))

    # 6. Weather
    _log("STEP [6/6] START fetch_weather")
    t0 = time.monotonic()
    weather_summary, weather_emoji = fetch_weather("Cambridge")
    s5 = time.monotonic() - t0
    _log(f"STEP [6/6] END   fetch_weather elapsed={s5:.1f}s outcome=ok")
    _step_timings.append(("fetch_weather", s5, "ok"))

    # --- Build options ---
    options = []

    # Option 1: Badminton tournament if available
    tournaments = pick_best_tournaments(be_data, saturday)
    if tournaments:
        t = tournaments[0]
        name = t.get("name", "羽毛球比赛")
        venue = t.get("venue", "")
        date = t.get("date", saturday)
        level = t.get("level", "Bronze U15")
        deadline = t.get("registration_deadline", "")
        travel = t.get("distance_from_cambridge", "")
        deadline_str = f" | 截止: {deadline}" if deadline else ""
        detail = f"{level} | {venue} | {date}{deadline_str}"
        options.append(format_option(f"选项1: 🏸 {name}", detail, "", travel, "🏸"))
    elif be_data.get("status") != "error":
        options.append("🏸 选项1: 本周末暂无附近U15青少年赛事")
    else:
        # Classified failure labels for diagnostics
        _err_labels = {
            "cookie_blocked": "赛事网站被Cookie墙拦截",
            "browser_unavailable": "浏览器不可用",
            "site_unreachable": "赛事网站无法访问",
            "parse_failed": "赛事数据解析失败",
        }
        _label = _err_labels.get(be_error_code, "赛事数据获取失败")
        _log(f"BE_FAILURE error_code={be_error_code}")
        options.append(f"🏸 选项1: {_label}")

    # Option 2: Events/shows
    events = pick_best_events(events_data, n=3)
    for i, ev in enumerate(events[:2], 2):
        title = ev.get("title", "活动")
        venue = ev.get("venue", ev.get("location", ""))
        price = ev.get("price", "varies")
        travel = ev.get("travel_time", "")
        url = ev.get("url", "")
        cat_emojis = {
            "museum": "🏛️", "outdoor": "🌿", "show": "🎭",
            "sports": "⚽", "market": "🛒", "festival": "🎪",
            "family": "👨‍👩‍👧‍👦", "attraction": "🌟", "general": "🎭",
        }
        emoji = cat_emojis.get(ev.get("category", "general"), "🎭")
        detail = venue
        option_title = f"选项{i}: {title}"
        options.append(format_option(option_title, detail, price, travel, emoji))

    # Option 3: Outdoor/nature if not already covered
    if len(events) < 2:
        options.append(format_option(
            "选项3: 🌿 剑桥河边漫步 + 野餐",
            "Grantchester Meadows",
            "免费",
            "local",
            "🌿"
        ))

    # --- Build and print message ---
    school_status = get_school_status(saturday, leys_data)
    gcal_events = format_gcal_events(gcal_data, saturday, sunday)

    message = build_message(
        saturday, sunday,
        weather_summary, weather_emoji,
        school_status, gcal_events,
        options
    )

    print("\n" + "=" * 50, file=sys.stderr)
    print(message)

    # --- Timing summary ---
    total_elapsed = time.monotonic() - run_start
    _log("TIMING SUMMARY")
    _log(f"{'Step':<25s} {'Secs':>6s}  {'Outcome'}")
    _log(f"{'-'*25} {'-'*6}  {'-'*7}")
    for name, secs, outcome in _step_timings:
        _log(f"{name:<25s} {secs:6.1f}  {outcome}")
    _log(f"{'TOTAL':<25s} {total_elapsed:6.1f}")
    _log("RUN END")


if __name__ == "__main__":
    main()

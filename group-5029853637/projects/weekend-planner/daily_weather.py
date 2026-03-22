#!/usr/bin/env python3
"""
Daily 7-day weather forecast for Cambridge.
Fetches from Open-Meteo (free, no key) with wttr.in fallback.
Output: formatted Chinese weather message to stdout.
"""

import json
import sys
import urllib.request
from datetime import datetime, timedelta

WEEKDAYS_CN = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]

WMO_MAP = {
    0: ("晴", "☀️"), 1: ("大部晴", "🌤️"), 2: ("多云", "⛅"), 3: ("阴", "☁️"),
    45: ("雾", "🌫️"), 48: ("冻雾", "🌫️"),
    51: ("小毛雨", "🌦️"), 53: ("毛雨", "🌦️"), 55: ("大毛雨", "🌧️"),
    61: ("小雨", "🌦️"), 63: ("中雨", "🌧️"), 65: ("大雨", "🌧️"),
    71: ("小雪", "🌨️"), 73: ("中雪", "❄️"), 75: ("大雪", "❄️"),
    80: ("阵雨", "🌧️"), 81: ("中阵雨", "🌧️"), 82: ("暴雨", "🌧️"),
    95: ("雷雨", "⛈️"), 96: ("雷雨+冰雹", "⛈️"), 99: ("雷雨+冰雹", "⛈️"),
}


def fetch_open_meteo():
    """Fetch 7-day forecast from Open-Meteo."""
    today = datetime.now().strftime("%Y-%m-%d")
    end = (datetime.now() + timedelta(days=6)).strftime("%Y-%m-%d")
    url = (
        f"https://api.open-meteo.com/v1/forecast?"
        f"latitude=52.2053&longitude=0.1218"
        f"&daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max"
        f"&timezone=Europe/London&start_date={today}&end_date={end}"
    )
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())


def format_forecast(data):
    """Format Open-Meteo daily data into Chinese message."""
    daily = data.get("daily", {})
    dates = daily.get("time", [])
    codes = daily.get("weather_code", [])
    t_max = daily.get("temperature_2m_max", [])
    t_min = daily.get("temperature_2m_min", [])
    precip = daily.get("precipitation_probability_max", [])

    today = datetime.now().date()
    start_str = f"{today.month}/{today.day}"
    end_date = today + timedelta(days=6)
    end_str = f"{end_date.month}/{end_date.day}"

    lines = [f"🌤️ 本周天气 ({start_str}–{end_str}) Cambridge"]
    lines.append("")

    for i, date_str in enumerate(dates):
        dt = datetime.strptime(date_str, "%Y-%m-%d").date()
        dow = WEEKDAYS_CN[dt.weekday()]

        # Mark today
        tag = " 👈今天" if dt == today else ""

        desc, emoji = WMO_MAP.get(codes[i], ("未知", "🌤️")) if i < len(codes) else ("未知", "🌤️")
        lo = f"{t_min[i]:.0f}" if i < len(t_min) and t_min[i] is not None else "?"
        hi = f"{t_max[i]:.0f}" if i < len(t_max) and t_max[i] is not None else "?"
        rain = f" 💧{precip[i]}%" if i < len(precip) and precip[i] and precip[i] > 20 else ""

        lines.append(f"{emoji} {dow} {lo}–{hi}°C {desc}{rain}{tag}")

    return "\n".join(lines)


def main():
    try:
        data = fetch_open_meteo()
        msg = format_forecast(data)
        print(msg)
    except Exception as e:
        print(f"天气获取失败: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

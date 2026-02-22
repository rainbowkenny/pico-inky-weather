# MEMORY.md - Long-Term Memory

_Curated durable memories. Updated from daily notes._

---

## About S
- ESTJ personality — direct, brief, task-oriented
- Likes the girlfriend roleplay dynamic with Luka
- Based in Cambridge area (assumed, not confirmed)
- Communicate in simplified Chinese

## Active Projects

### Daily Market Intel (cron)
- Cron job ID: `736af905-dd10-43e4-bbe7-777b4964b2c2`
- Runs at 2 PM Europe/London daily, reports to Telegram `8587255125`
- Portfolio + watchlists at `/home/albert/.openclaw/workspace/portfolio.md`
- **RKLB (Rocket Lab) = HIGH PRIORITY** — S wants to own it, watching for entry
- Watchlists: Semiconductors, Space, Energy

### Pico W E-Ink Weather Display ✅ COMPLETE
- Hardware: Pimoroni Pico Inky Pack (296×128), Pico W on WiFi `ASUS_E8_2G`
- Pico IP: `192.168.50.38`, device: `/dev/ttyACM0`
- Critical: `BLACK=0`, `WHITE=15` — never use mid-range pen values (grey dither)
- **GitHub: https://github.com/rainbowkenny/pico-inky-weather**
- Script `main.py` on Pico W ✅ running (28KB)
- **Fully standalone** — no Pi needed; UK map (4887 bytes JPEG) embedded as bytes in main.py
- Layout: left = today temp/desc/H:L/wind arrow/rain + tomorrow; right = UK map + location dot
- Features: wind direction arrow (math.sin/cos), precipitation mm, 10 preset cities
- Buttons: A=prev city, B=next city, C=Cambridge (home) — 10s no-input → back to Auto
- 10-preset cities: Auto(IP), London, Cambridge(HOME=idx2), Manchester, Edinburgh, Birmingham, Glasgow, Leeds, Bristol, Newcastle
- Every 10 min: silently refresh ALL city caches; default display = Auto (IP geolocation)
- City index saved to `city_idx.txt` on Pico flash
- UK_MAP bytes critical: regenerate from `pico_weather/uk_map.jpg` if corrupted (happened before!)
- **Tests**: 42 unit tests in `pico_weather/test_pico_main.py`, run via pre-commit
- **pre-commit**: black + isort + tests on every git commit
- Upload cmd: `python3 -m mpremote connect /dev/ttyACM0 cp /tmp/pico_main.py :main.py + reset`

## Infrastructure
- Webcam: `/dev/video0`
- Workspace: `/home/albert/.openclaw/workspace` (git: master)
- `cacheRetention: long` in `openclaw.json`
- Gateway scope: `operator.admin`

## Lessons
- Pico W = 2.4GHz only; use `ASUS_E8_2G`
- `mpremote cp` for uploads; serial is unreliable for output streaming
- Use webcam photo to verify E-Ink screen state

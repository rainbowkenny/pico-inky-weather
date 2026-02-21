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

### Pico W E-Ink Weather Display
- Hardware: Pimoroni Pico Inky Pack (296×128), Pico W on WiFi `ASUS_E8_2G`
- Pico IP: `192.168.50.38`, device: `/dev/ttyACM0`
- Critical: `BLACK=0`, `WHITE=15` — never use mid-range pen values (grey dither)
- Script `main.py` on Pico W (uploaded 2026-02-21), execution unconfirmed
- Layout: left = weather data, right = OSM map tile at zoom 11
- Next: webcam verify → `ffmpeg -f v4l2 -i /dev/video0 -frames:v 1 /tmp/pico_screen.jpg`

## Infrastructure
- Webcam: `/dev/video0`
- Workspace: `/home/albert/.openclaw/workspace` (git: master)
- `cacheRetention: long` in `openclaw.json`
- Gateway scope: `operator.admin`

## Lessons
- Pico W = 2.4GHz only; use `ASUS_E8_2G`
- `mpremote cp` for uploads; serial is unreliable for output streaming
- Use webcam photo to verify E-Ink screen state

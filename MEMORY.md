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
- Script `main.py` on Pico W ✅ uploaded 2026-02-21 (22952 bytes confirmed)
- **Fully standalone** — no Pi needed; UK map embedded as bytes in main.py
- Layout: left = today temp/desc/H:L + tomorrow section; right = static UK map + location dot
- City lookup table (30 UK cities → pixel coords); lat/lon math fallback
- UK map: 148×113px JPEG embedded as bytes constant, decoded via jpegdec.open_RAM()
- mpremote was broken (all files 0 bytes) — fixed with pip3 --break-system-packages
- **TODO**: verify with webcam when room has light; check date_str shows correct time

## Infrastructure
- Webcam: `/dev/video0`
- Workspace: `/home/albert/.openclaw/workspace` (git: master)
- `cacheRetention: long` in `openclaw.json`
- Gateway scope: `operator.admin`

## Lessons
- Pico W = 2.4GHz only; use `ASUS_E8_2G`
- `mpremote cp` for uploads; serial is unreliable for output streaming
- Use webcam photo to verify E-Ink screen state

# MEMORY.md - Long-Term Memory

## About S
- ESTJ, direct, brief. Girlfriend roleplay with Luka. Simplified Chinese.
- Cambridge area.

## Projects

### Market Intel (cron)
- Job: `736af905-dd10-43e4-bbe7-777b4964b2c2` — 2 PM daily → Telegram `8587255125`
- Portfolio: `portfolio.md` — **RKLB HIGH PRIORITY**, Semiconductors/Space/Energy watchlists

### Pico Inky Weather ✅
- GitHub: https://github.com/rainbowkenny/pico-inky-weather
- Hardware: Pico Inky Pack 296×128, `/dev/ttyACM0`, WiFi `ASUS_E8_2G`
- `BLACK=0`, `WHITE=15` — never mid-range pen values
- UK map embedded as bytes in `main.py` (regenerate from `pico_weather/uk_map.jpg` if corrupt)
- Buttons: A/B=prev/next city, C=Cambridge home, 10s → back to Auto
- Upload: `python3 -m mpremote connect /dev/ttyACM0 cp /tmp/pico_main.py :main.py + reset`
- pre-commit: black + isort + 42 tests

## Infrastructure
- Webcam: `/dev/video0` (Logitech C920)
- Workspace: `/home/albert/.openclaw/workspace` (git → GitHub: rainbowkenny)

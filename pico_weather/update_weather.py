#!/usr/bin/env python3
"""
Weather updater for Pimoroni Pico Inky Pack (296x128 E-Ink)
- Fetches weather from wttr.in
- Writes + runs MicroPython script on Pico via serial REPL
- No replug needed!
"""

import sys
import json
import urllib.request
import serial
import time
from datetime import datetime

LOCATION = "London"
DEVICE = "/dev/ttyACM0"

WEATHER_CODES = {
    "113": "Sunny", "116": "P.Cloudy", "119": "Cloudy", "122": "Overcast",
    "143": "Mist", "176": "Patchy Rain", "179": "Patchy Snow",
    "200": "Thunder", "227": "Blowing Snow", "248": "Fog",
    "263": "Drizzle", "266": "Drizzle", "293": "Light Rain",
    "296": "Light Rain", "299": "Mod Rain", "302": "Mod Rain",
    "305": "Heavy Rain", "308": "Heavy Rain", "317": "Sleet",
    "320": "Mod Snow", "326": "Light Snow", "329": "Mod Snow",
    "335": "Heavy Snow", "353": "Light Rain", "356": "Heavy Rain",
    "386": "Thunder", "389": "Thunder",
}

def get_weather(location):
    url = f"https://wttr.in/{location.replace(' ', '+')}?format=j1"
    req = urllib.request.Request(url, headers={"User-Agent": "curl/7.68.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())

def send_to_pico(script, device=DEVICE):
    s = serial.Serial(device, 115200, timeout=5)
    s.write(b'\x03\x03')
    time.sleep(1)
    s.read(s.in_waiting or 200)

    # Write main.py line by line
    lines = script.strip().split('\n')
    s.write(b"f=open('main.py','w')\r\n")
    time.sleep(0.3)
    for line in lines:
        escaped = line.replace('\\', '\\\\').replace('"', '\\"')
        s.write(f'f.write("{escaped}\\n")\r\n'.encode())
        time.sleep(0.08)
    s.write(b"f.close()\r\n")
    time.sleep(0.3)

    # Execute it
    s.write(b"exec(open('main.py').read())\r\n")
    time.sleep(15)  # wait for e-ink update
    out = s.read(s.in_waiting or 500).decode('utf-8', errors='replace')
    s.close()
    return "done!" in out

def build_script(location, temp, desc, feels, hmax, hmin, tmax, tmin, tmr_desc, date_str):
    return f'''from picographics import PicoGraphics, DISPLAY_INKY_PACK
d = PicoGraphics(display=DISPLAY_INKY_PACK)
BLACK = 0
WHITE = 15
d.set_pen(WHITE)
d.clear()
d.set_pen(BLACK)
d.set_font("bitmap8")
d.rectangle(0, 0, 296, 14)
d.set_pen(WHITE)
d.text("{location}", 3, 3, scale=1)
d.text("{date_str}", 160, 3, scale=1)
d.set_pen(BLACK)
d.text("{temp}C", 4, 18, scale=4)
d.set_font("bitmap6")
d.text("{desc}", 4, 72, scale=1)
d.text("Feels {feels}C", 4, 84, scale=1)
d.text("H:{hmax}  L:{hmin}", 4, 96, scale=1)
d.line(148, 15, 148, 123)
d.set_font("bitmap8")
d.text("Tomorrow", 152, 18, scale=1)
d.set_font("bitmap6")
d.text("{tmr_desc}", 152, 36, scale=1)
d.text("H:{tmax}  L:{tmin}", 152, 50, scale=1)
d.line(0, 123, 296, 123)
d.update()
print("done!")
'''

def main():
    loc = sys.argv[1] if len(sys.argv) > 1 else LOCATION
    print(f"Fetching weather for {loc}...")

    try:
        data = get_weather(loc)
        c = data["current_condition"][0]
        today = data["weather"][0]
        tmr = data["weather"][1]

        temp = c["temp_C"]
        feels = c["FeelsLikeC"]
        desc = WEATHER_CODES.get(c["weatherCode"], c["weatherDesc"][0]["value"][:12])
        hmax = today["maxtempC"]
        hmin = today["mintempC"]
        tmax = tmr["maxtempC"]
        tmin = tmr["mintempC"]
        tmr_code = tmr["hourly"][4]["weatherCode"]
        tmr_desc = WEATHER_CODES.get(tmr_code, tmr["hourly"][4]["weatherDesc"][0]["value"][:12])
        date_str = datetime.now().strftime("%a %d %b")

        print(f"  {temp}C, {desc}, H:{hmax}/L:{hmin}")
    except Exception as e:
        print(f"Weather fetch failed: {e}")
        return 1

    script = build_script(loc, temp, desc, feels, hmax, hmin, tmax, tmin, tmr_desc, date_str)

    print("Sending to Pico...")
    if send_to_pico(script):
        print("Display updated!")
        return 0
    else:
        print("Something went wrong")
        return 1

if __name__ == "__main__":
    sys.exit(main())

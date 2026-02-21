#!/usr/bin/env python3
"""
Weather Display for Pimoroni Pico Inky Pack (296x128 E-Ink)
Fetches weather from wttr.in, pushes display script to Pico via mpremote.
"""

import subprocess
import sys
import json
import urllib.request
from datetime import datetime

LOCATION = "London"
DEVICE = "/dev/ttyACM0"
MPREMOTE = [sys.executable, "-m", "mpremote"]

WEATHER_CODES = {
    "113": ("Sunny", "( * )"),
    "116": ("P.Cloudy", "(~*~)"),
    "119": ("Cloudy", "( ~ )"),
    "122": ("Overcast", "( -- )"),
    "143": ("Mist", "( .. )"),
    "176": ("Patchy Rain", "( .v.)"),
    "179": ("Patchy Snow", "( .*."),
    "185": ("Patchy Sleet", "(.v.*)"),
    "200": ("Thunder", "(/!\\ )"),
    "227": ("Blowing Snow", "(*-*) "),
    "230": ("Blizzard", "(***) "),
    "248": ("Fog", "(-.-) "),
    "260": ("Freezing Fog", "(-*-) "),
    "263": ("Drizzle", "( ...) "),
    "266": ("Drizzle", "( ...) "),
    "281": ("Fz Drizzle", "( .*.) "),
    "284": ("Fz Drizzle", "( .*.) "),
    "293": ("Light Rain", "( .v.) "),
    "296": ("Light Rain", "( .v.) "),
    "299": ("Mod Rain", "(.v.v) "),
    "302": ("Mod Rain", "(.v.v) "),
    "305": ("Heavy Rain", "(vvvv) "),
    "308": ("Heavy Rain", "(vvvv) "),
    "311": ("Light Sleet", "(.v.*) "),
    "314": ("Mod Sleet", "(.v.*) "),
    "317": ("Light Sleet", "(.v.*) "),
    "320": ("Mod Snow", "( .*.) "),
    "323": ("Patchy Snow", "( .*.) "),
    "326": ("Light Snow", "( *** ) "),
    "329": ("Mod Snow", "(****) "),
    "332": ("Mod Snow", "(****) "),
    "335": ("Heavy Snow", "(*****) "),
    "338": ("Heavy Snow", "(*****) "),
    "350": ("Ice Pellets", "( ooo) "),
    "353": ("Light Rain", "( .v.) "),
    "356": ("Heavy Rain", "(vvvv) "),
    "359": ("Torrential", "(VVVV) "),
    "362": ("Lt Sleet Sh", "(.v.*) "),
    "365": ("Mod Sleet", "(.v.*) "),
    "368": ("Lt Snow Sh", "( *** ) "),
    "371": ("Mod Snow Sh", "(****) "),
    "374": ("Lt Ice", "( ooo) "),
    "377": ("Mod Ice", "( OOO) "),
    "386": ("Thunder", "(/!\\ ) "),
    "389": ("Hvr Thunder", "(!!!!!) "),
    "392": ("Sn Thunder", "(/!\\*) "),
    "395": ("Blizzard", "(***!!) "),
}

def get_weather(location):
    url = f"https://wttr.in/{location.replace(' ', '+')}?format=j1"
    req = urllib.request.Request(url, headers={"User-Agent": "curl/7.68.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())

def format_weather(data):
    current = data["current_condition"][0]
    today = data["weather"][0]
    tomorrow = data["weather"][1]
    
    temp_c = current["temp_C"]
    feels_c = current["FeelsLikeC"]
    humidity = current["humidity"]
    desc = current["weatherDesc"][0]["value"]
    code = current["weatherCode"]
    
    today_max = today["maxtempC"]
    today_min = today["mintempC"]
    tmr_max = tomorrow["maxtempC"]
    tmr_min = tomorrow["mintempC"]
    tmr_code = tomorrow["hourly"][4]["weatherCode"]
    tmr_desc = WEATHER_CODES.get(tmr_code, ("?", "(?)"))[0]
    
    icon = WEATHER_CODES.get(code, ("?", "(?)"))[1]
    short_desc = WEATHER_CODES.get(code, (desc[:10], ""))[0]
    
    now = datetime.now()
    date_str = now.strftime("%a %d %b")
    time_str = now.strftime("%H:%M")
    
    return {
        "temp": temp_c,
        "feels": feels_c,
        "humidity": humidity,
        "desc": short_desc,
        "icon": icon,
        "today_max": today_max,
        "today_min": today_min,
        "tmr_max": tmr_max,
        "tmr_min": tmr_min,
        "tmr_desc": tmr_desc,
        "date": date_str,
        "time": time_str,
        "location": LOCATION,
    }

def build_pico_script(w):
    return f'''from picographics import PicoGraphics, DISPLAY_INKY_PACK
from pimoroni import Button

display = PicoGraphics(display=DISPLAY_INKY_PACK)
display.set_update_speed(2)
W, H = display.get_bounds()

BLACK = display.create_pen(0, 0, 0)
WHITE = display.create_pen(255, 255, 255)

display.set_pen(WHITE)
display.clear()
display.set_pen(BLACK)

# Header: location + date + time
display.set_font("bitmap8")
display.set_pen(BLACK)
display.rectangle(0, 0, W, 14)
display.set_pen(WHITE)
display.text("{w["location"]}", 3, 3, scale=1)
display.text("{w["date"]}  {w["time"]}", W - 95, 3, scale=1)

display.set_pen(BLACK)

# Big temperature
display.set_font("bitmap8")
display.text("{w["temp"]}C", 5, 22, scale=3)

# Feels like + humidity
display.set_font("bitmap6")
display.text("Feels {w["feels"]}C", 5, 60, scale=1)
display.text("Hum {w["humidity"]}%", 5, 72, scale=1)

# Today range
display.text("H:{w["today_max"]} L:{w["today_min"]}", 5, 86, scale=1)

# Divider
display.line(95, 16, 95, H - 5)

# Condition text + icon
display.set_font("bitmap8")
display.text("{w["desc"]}", 100, 22, scale=1)
display.set_font("bitmap6")
display.text("{w["icon"]}", 100, 38, scale=1)

# Tomorrow
display.line(95, 75, W, 75)
display.set_font("bitmap6")
display.text("Tomorrow", 100, 78, scale=1)
display.text("{w["tmr_desc"]}", 100, 90, scale=1)
display.text("H:{w["tmr_max"]} L:{w["tmr_min"]}", 100, 102, scale=1)

# Bottom border
display.line(0, H - 4, W, H - 4)

display.update()
print("done")
'''

def push_to_pico(script_path, device):
    print("Uploading to Pico...")
    result = subprocess.run(
        MPREMOTE + ["connect", device, "cp", script_path, ":main.py"],
        capture_output=True, text=True, timeout=30
    )
    if result.returncode != 0:
        print("Upload error:", result.stderr)
        return False
    
    print("Running on Pico...")
    result = subprocess.run(
        MPREMOTE + ["connect", device, "run", script_path],
        capture_output=True, text=True, timeout=60
    )
    print("Output:", result.stdout)
    if result.returncode != 0:
        print("Run error:", result.stderr)
        return False
    return True

def main():
    loc = LOCATION if len(sys.argv) < 2 else sys.argv[1]
    print(f"Fetching weather for {loc}...")
    
    try:
        data = get_weather(loc)
        w = format_weather(data)
        print(f"  {w['temp']}C, {w['desc']}, H:{w['today_max']} L:{w['today_min']}")
    except Exception as e:
        print(f"Weather fetch failed: {e}")
        return 1
    
    script = build_pico_script(w)
    script_path = "/tmp/pico_weather_run.py"
    with open(script_path, "w") as f:
        f.write(script)
    
    if push_to_pico(script_path, DEVICE):
        print("Display updated!")
        return 0
    else:
        return 1

if __name__ == "__main__":
    sys.exit(main())

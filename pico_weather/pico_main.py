import network
import urequests
import time
import json
import math
import gc
from picographics import PicoGraphics, DISPLAY_INKY_PACK
import jpegdec

SSID = "ASUS_E8_2G"
PASSWORD = "Bbdd1003"
MAP_SERVER = "http://192.168.50.16:8765"

BLACK = 0
WHITE = 15

WMO = {
    0: "Clear", 1: "Clear", 2: "P.Cloudy", 3: "Overcast",
    45: "Fog", 48: "Icy Fog",
    51: "Drizzle", 53: "Drizzle", 55: "Drizzle",
    61: "Light Rain", 63: "Rain", 65: "Heavy Rain",
    71: "Light Snow", 73: "Snow", 75: "Heavy Snow",
    80: "Showers", 81: "Showers", 82: "Showers",
    95: "Thunder", 96: "Thunder", 99: "Thunder",
}

def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        wlan.connect(SSID, PASSWORD)
        t = time.time()
        while not wlan.isconnected() and time.time() - t < 20:
            time.sleep(0.5)
    return wlan.isconnected()

def get_location():
    gc.collect()
    r = urequests.get("http://ip-api.com/json/?fields=lat,lon,city", timeout=10)
    d = r.json(); r.close(); gc.collect()
    return float(d["lat"]), float(d["lon"]), d["city"]

def get_weather(lat, lon):
    gc.collect()
    url = ("https://api.open-meteo.com/v1/forecast"
           "?latitude={}&longitude={}"
           "&current_weather=true"
           "&daily=temperature_2m_max,temperature_2m_min,weathercode"
           "&forecast_days=2&timezone=auto").format(lat, lon)
    r = urequests.get(url, timeout=15)
    d = r.json(); r.close(); gc.collect()
    return d

def draw_map(display, lat, lon):
    url = "{}/map?lat={}&lon={}&city={}".format(MAP_SERVER, lat, lon, city)
    try:
        gc.collect()
        print("Fetching map:", url)
        r = urequests.get(url, timeout=20)
        data = r.content
        r.close()
        print("Map size:", len(data), "bytes")
        gc.collect()

        j = jpegdec.JPEG(display)
        j.open_RAM(data)
        j.decode(148, 15)  # draw in right panel
        data = None; gc.collect()
        print("Map OK")
    except Exception as e:
        print("Map error:", e)
        # Fallback crosshair
        display.set_pen(BLACK)
        cx, cy = 222, 69
        display.circle(cx, cy, 28)
        display.line(cx - 33, cy, cx + 33, cy)
        display.line(cx, cy - 33, cx, cy + 33)
        display.circle(cx, cy, 4)
        display.set_pen(WHITE)
        display.circle(cx, cy, 2)
        display.set_pen(BLACK)
        display.set_font("bitmap6")
        display.text("{:.2f}N".format(lat), 152, 100, scale=1)
        display.text("{:.2f}E".format(lon), 152, 111, scale=1)

# ---- MAIN ----
display = PicoGraphics(display=DISPLAY_INKY_PACK)

display.set_pen(WHITE); display.clear()
display.set_pen(BLACK)
display.set_font("bitmap8")
display.text("Connecting...", 10, 55, scale=1)
display.update()

print("WiFi...")
if not connect_wifi():
    display.set_pen(WHITE); display.clear()
    display.set_pen(BLACK)
    display.text("WiFi Failed!", 10, 55, scale=2)
    display.update()
    raise SystemExit

print("Location...")
lat, lon, city = get_location()
print("Location:", city, lat, lon)

print("Weather...")
data = get_weather(lat, lon)
cw = data["current_weather"]
daily = data["daily"]

temp = int(cw["temperature"])
code = int(cw["weathercode"])
desc = WMO.get(code, "Unknown")
hmax = int(daily["temperature_2m_max"][0])
hmin = int(daily["temperature_2m_min"][0])
tmax = int(daily["temperature_2m_max"][1])
tmin = int(daily["temperature_2m_min"][1])
tmr_code = int(daily["weathercode"][1])
tmr_desc = WMO.get(tmr_code, "?")

t = time.localtime()
date_str = "{}/{} {:02d}:{:02d}".format(t[2], t[1], t[3], t[4])

# Draw white background + weather
display.set_pen(WHITE); display.clear()
display.set_pen(BLACK)

# Header bar
display.rectangle(0, 0, 296, 14)
display.set_pen(WHITE)
display.set_font("bitmap6")
display.text(city[:16], 3, 4, scale=1)
display.text(date_str, 195, 4, scale=1)

# Temperature
display.set_pen(BLACK)
display.set_font("bitmap8")
display.text("{}C".format(temp), 4, 18, scale=3)

# Weather details
display.set_font("bitmap6")
display.text(desc, 4, 67, scale=1)
display.text("H:{}  L:{}".format(hmax, hmin), 4, 79, scale=1)

# Vertical divider
display.line(148, 15, 148, 123)

# Tomorrow's forecast (top right, above map)
display.set_font("bitmap8")
display.text("Tmr", 152, 18, scale=1)
display.set_font("bitmap6")
display.text(tmr_desc, 152, 32, scale=1)
display.text("H:{}  L:{}".format(tmax, tmin), 152, 44, scale=1)
display.line(148, 56, 296, 56)

# Map in bottom-right
print("Map...")
draw_map(display, lat, lon)

display.line(0, 123, 296, 123)
display.update()
print("Done!")

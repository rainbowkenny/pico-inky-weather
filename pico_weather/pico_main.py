"""
Standalone weather display — Pimoroni Pico Inky Pack (296x128)
Static UK map stored in flash (uk_map.jpg), only location dot changes.
Network: ip-api.com (location) + open-meteo.com (weather) only.
"""
import network, urequests, time, math, gc
from picographics import PicoGraphics, DISPLAY_INKY_PACK
import jpegdec

SSID     = "ASUS_E8_2G"
PASSWORD = "Bbdd1003"
BLACK = 0
WHITE = 15

WMO = {
    0:"Clear", 1:"Clear", 2:"P.Cloudy", 3:"Overcast",
    45:"Fog", 48:"Icy Fog",
    51:"Drizzle", 53:"Drizzle", 55:"Drizzle",
    61:"Lt Rain", 63:"Rain", 65:"Hvy Rain",
    71:"Lt Snow", 73:"Snow", 75:"Hvy Snow",
    80:"Showers", 81:"Showers", 82:"Showers",
    95:"Thunder", 96:"Thunder", 99:"Thunder",
}

# Map bounds (matches uk_map.jpg generation)
LON_MIN, LON_MAX = -6.5, 2.1
LAT_MIN, LAT_MAX = 49.8, 60.9
MAP_X, MAP_Y = 148, 14   # top-left of map panel on display
MAP_W, MAP_H = 148, 113
MAP_PAD = 6

def latlon_to_dot(lat, lon):
    """Convert lat/lon to pixel position on the UK map panel."""
    x = MAP_X + MAP_PAD + int((lon - LON_MIN) / (LON_MAX - LON_MIN) * (MAP_W - 2*MAP_PAD))
    y = MAP_Y + MAP_PAD + int((LAT_MAX - lat) / (LAT_MAX - LAT_MIN) * (MAP_H - 2*MAP_PAD))
    # Clamp to map area
    x = max(MAP_X + MAP_PAD, min(MAP_X + MAP_W - MAP_PAD, x))
    y = max(MAP_Y + MAP_PAD, min(MAP_Y + MAP_H - MAP_PAD, y))
    return x, y

def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        wlan.connect(SSID, PASSWORD)
        deadline = time.time() + 20
        while not wlan.isconnected() and time.time() < deadline:
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

def parse_time(wt):
    try:
        if len(wt) >= 16:
            d = wt[8:10].lstrip("0") or "0"
            m = wt[5:7].lstrip("0") or "0"
            return "{}/{} {}:{}".format(d, m, wt[11:13], wt[14:16])
    except Exception:
        pass
    return "--/-- --:--"

def show_error(display, msg):
    display.set_pen(WHITE); display.clear()
    display.set_pen(BLACK); display.set_font("bitmap8")
    display.text("ERROR", 4, 20, scale=2)
    display.set_font("bitmap6")
    display.text(str(msg)[:42], 4, 55, scale=1)
    display.update()

# ===== MAIN =====
display = PicoGraphics(display=DISPLAY_INKY_PACK)

try:
    # Startup splash
    display.set_pen(WHITE); display.clear()
    display.set_pen(BLACK); display.set_font("bitmap8")
    display.text("Connecting...", 10, 55, scale=1)
    display.update()

    if not connect_wifi():
        show_error(display, "WiFi failed")
        raise SystemExit

    lat, lon, city = get_location()
    data     = get_weather(lat, lon)
    cw       = data["current_weather"]
    daily    = data["daily"]

    temp     = int(cw["temperature"])
    desc     = WMO.get(int(cw["weathercode"]), "?")
    hmax     = int(daily["temperature_2m_max"][0])
    hmin     = int(daily["temperature_2m_min"][0])
    tmax     = int(daily["temperature_2m_max"][1])
    tmin     = int(daily["temperature_2m_min"][1])
    tmr_desc = WMO.get(int(daily["weathercode"][1]), "?")
    date_str = parse_time(cw.get("time", ""))

    # ---- DRAW ----
    display.set_pen(WHITE); display.clear()

    # 1. Static UK map from flash
    j = jpegdec.JPEG(display)
    j.open_file("uk_map.jpg")
    j.decode(MAP_X, MAP_Y)

    # 2. White mask over left panel (covers any map overdraw)
    display.set_pen(WHITE)
    display.rectangle(0, 0, MAP_X, 128)

    # 3. Header
    display.set_pen(BLACK); display.rectangle(0, 0, 296, 14)
    display.set_pen(WHITE); display.set_font("bitmap6")
    display.text(city[:14], 3, 4, scale=1)
    display.text(date_str, 200, 4, scale=1)

    # 4. Left panel — today
    display.set_pen(BLACK); display.set_font("bitmap8")
    display.text("{}C".format(temp), 4, 18, scale=3)
    display.set_font("bitmap6")
    display.text(desc, 4, 58, scale=1)
    display.text("H:{}  L:{}".format(hmax, hmin), 4, 70, scale=1)

    # 5. Left panel — tomorrow
    display.set_pen(BLACK); display.line(4, 84, 143, 84)
    display.set_font("bitmap8"); display.text("Tmr", 4, 90, scale=1)
    display.set_font("bitmap6")
    display.text(tmr_desc, 4, 104, scale=1)
    display.text("H:{}  L:{}".format(tmax, tmin), 4, 115, scale=1)

    # 6. Vertical divider
    display.set_pen(BLACK); display.line(148, 14, 148, 127)

    # 7. Location dot on UK map
    dx, dy = latlon_to_dot(lat, lon)
    display.set_pen(BLACK); display.circle(dx, dy, 5)
    display.set_pen(WHITE); display.circle(dx, dy, 2)
    display.set_pen(BLACK)

    # 8. Bottom border + update
    display.line(0, 127, 295, 127)
    display.update()

except Exception as e:
    try:
        show_error(display, e)
    except Exception:
        pass
    raise

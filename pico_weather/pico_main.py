"""
Standalone weather display for Pimoroni Pico Inky Pack (296x128)
- WiFi → ip-api.com (geolocation) → open-meteo.com (weather) → OSM tile (map)
- No Raspberry Pi or external server needed
- Runs on boot via main.py on Pico W
"""

import network
import urequests
import time
import math
import gc
from picographics import PicoGraphics, DISPLAY_INKY_PACK
import pngdec

# ---- Config ----
SSID     = "ASUS_E8_2G"
PASSWORD = "Bbdd1003"
ZOOM     = 13        # OSM zoom level: 13 = ~4.7km tile, good city detail

BLACK = 0
WHITE = 15

# WMO weather code → short label
WMO = {
    0: "Clear",     1: "Clear",     2: "P.Cloudy",  3: "Overcast",
    45: "Fog",      48: "Icy Fog",
    51: "Drizzle",  53: "Drizzle",  55: "Drizzle",
    61: "Lt Rain",  63: "Rain",     65: "Hvy Rain",
    71: "Lt Snow",  73: "Snow",     75: "Hvy Snow",
    80: "Showers",  81: "Showers",  82: "Showers",
    95: "Thunder",  96: "Thunder",  99: "Thunder",
}

# ---- Display layout constants ----
# Header:          y = 0..13   (full width, black bg)
# Left panel:      x = 0..147, y = 14..127  (weather)
# Right panel:     x = 148..295
#   Tomorrow:      y = 14..55
#   H-divider:     y = 56
#   Map area:      y = 57..122  (148 x 66 px)
# Bottom border:   y = 123

MAP_X  = 148   # map area left edge
MAP_Y  = 57    # map area top edge
MAP_W  = 148   # map area width
MAP_H  = 66    # map area height
MAP_CX = MAP_X + MAP_W // 2   # = 222  (center x)
MAP_CY = MAP_Y + MAP_H // 2   # = 90   (center y)


# ---- WiFi ----
def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        wlan.connect(SSID, PASSWORD)
        deadline = time.time() + 20
        while not wlan.isconnected() and time.time() < deadline:
            time.sleep(0.5)
    return wlan.isconnected()


# ---- Data fetching ----
def get_location():
    gc.collect()
    r = urequests.get("http://ip-api.com/json/?fields=lat,lon,city", timeout=10)
    d = r.json(); r.close(); gc.collect()
    return float(d["lat"]), float(d["lon"]), d["city"]


def get_weather(lat, lon):
    gc.collect()
    url = (
        "https://api.open-meteo.com/v1/forecast"
        "?latitude={}&longitude={}"
        "&current_weather=true"
        "&daily=temperature_2m_max,temperature_2m_min,weathercode"
        "&forecast_days=2&timezone=auto"
    ).format(lat, lon)
    r = urequests.get(url, timeout=15)
    d = r.json(); r.close(); gc.collect()
    return d


# ---- OSM tile math ----
def lat_lon_to_tile(lat, lon, zoom):
    """Returns OSM tile (tx, ty) containing lat/lon at given zoom."""
    n = 1 << zoom
    tx = int((lon + 180.0) / 360.0 * n)
    lat_r = math.radians(lat)
    ty = int((1.0 - math.log(math.tan(lat_r) + 1.0 / math.cos(lat_r)) / math.pi) / 2.0 * n)
    return tx, ty


def tile_pixel_offset(lat, lon, zoom):
    """Returns pixel position (0-255, 0-255) of lat/lon within its OSM tile."""
    n = 1 << zoom
    x_f = (lon + 180.0) / 360.0 * n
    lat_r = math.radians(lat)
    y_f = (1.0 - math.log(math.tan(lat_r) + 1.0 / math.cos(lat_r)) / math.pi) / 2.0 * n
    return int((x_f - int(x_f)) * 256), int((y_f - int(y_f)) * 256)


# ---- Map drawing ----
def draw_map(display, lat, lon):
    """
    Fetch OSM tile PNG and decode it so lat/lon lands at MAP_CX, MAP_CY.
    The tile may overdraw into weather/tomorrow areas — caller masks those
    with white rectangles afterwards.
    Returns True on success, False on failure (caller draws crosshair).
    """
    tx, ty = lat_lon_to_tile(lat, lon, ZOOM)
    px, py = tile_pixel_offset(lat, lon, ZOOM)

    # Offset so the target location sits at the map viewport centre
    decode_x = MAP_CX - px
    decode_y = MAP_CY - py

    url = "https://tile.openstreetmap.org/{}/{}/{}.png".format(ZOOM, tx, ty)
    headers = {"User-Agent": "PicoW-InkyWeather/1.0"}

    try:
        gc.collect()
        print("Tile:", url, "| decode at ({},{})".format(decode_x, decode_y))
        r = urequests.get(url, headers=headers, timeout=25)
        data = r.content
        r.close()
        print("Tile size:", len(data), "B")
        gc.collect()

        png = pngdec.PNG(display)
        png.open_RAM(data)
        png.decode(decode_x, decode_y)
        data = None
        gc.collect()
        print("Map decoded OK")
        return True

    except Exception as e:
        print("Map error:", e)
        return False


def draw_crosshair(display, lat, lon):
    """Fallback when map tile fetch fails."""
    display.set_pen(BLACK)
    display.circle(MAP_CX, MAP_CY, 25)
    display.line(MAP_CX - 30, MAP_CY, MAP_CX + 30, MAP_CY)
    display.line(MAP_CX, MAP_CY - 30, MAP_CX, MAP_CY + 30)
    display.circle(MAP_CX, MAP_CY, 4)
    display.set_pen(WHITE)
    display.circle(MAP_CX, MAP_CY, 2)
    display.set_pen(BLACK)
    display.set_font("bitmap6")
    display.text("{:.2f}N {:.2f}E".format(lat, lon), MAP_X + 2, MAP_Y + MAP_H - 14, scale=1)


def draw_location_dot(display):
    """Small filled dot at map centre to mark location (drawn over tile)."""
    display.set_pen(BLACK)
    display.circle(MAP_CX, MAP_CY, 5)
    display.set_pen(WHITE)
    display.circle(MAP_CX, MAP_CY, 2)
    display.set_pen(BLACK)


# ======== MAIN ========
display = PicoGraphics(display=DISPLAY_INKY_PACK)

# --- Startup splash ---
display.set_pen(WHITE); display.clear()
display.set_pen(BLACK)
display.set_font("bitmap8")
display.text("Connecting...", 10, 55, scale=1)
display.update()

# --- WiFi ---
print("WiFi...")
if not connect_wifi():
    display.set_pen(WHITE); display.clear()
    display.set_pen(BLACK)
    display.text("WiFi Failed!", 8, 50, scale=2)
    display.update()
    raise SystemExit("no wifi")

# --- Location ---
print("Location...")
lat, lon, city = get_location()
print("  {} {:.4f},{:.4f}".format(city, lat, lon))

# --- Weather ---
print("Weather...")
data     = get_weather(lat, lon)
cw       = data["current_weather"]
daily    = data["daily"]

temp     = int(cw["temperature"])
code     = int(cw["weathercode"])
desc     = WMO.get(code, "?")
hmax     = int(daily["temperature_2m_max"][0])
hmin     = int(daily["temperature_2m_min"][0])
tmax     = int(daily["temperature_2m_max"][1])
tmin     = int(daily["temperature_2m_min"][1])
tmr_code = int(daily["weathercode"][1])
tmr_desc = WMO.get(tmr_code, "?")

t        = time.localtime()
date_str = "{}/{} {:02d}:{:02d}".format(t[2], t[1], t[3], t[4])

# ======== DRAW ========

# 1. White canvas
display.set_pen(WHITE)
display.clear()

# 2. Draw map tile first (may overdraw weather + tomorrow areas — masked next)
print("Map...")
map_ok = draw_map(display, lat, lon)

# 3. White mask: left weather panel + right tomorrow section
#    This erases any tile overdraw outside the map area
display.set_pen(WHITE)
display.rectangle(0, 0, 148, 128)       # entire left panel
display.rectangle(148, 14, 148, 43)     # tomorrow section (y=14..56)

# 4. Header bar (full width)
display.set_pen(BLACK)
display.rectangle(0, 0, 296, 14)
display.set_pen(WHITE)
display.set_font("bitmap6")
display.text(city[:16], 3, 4, scale=1)
display.text(date_str, 200, 4, scale=1)

# 5. Left panel: temperature + conditions
display.set_pen(BLACK)
display.set_font("bitmap8")
display.text("{}C".format(temp), 4, 18, scale=3)
display.set_font("bitmap6")
display.text(desc, 4, 67, scale=1)
display.text("H:{}  L:{}".format(hmax, hmin), 4, 79, scale=1)

# 6. Vertical divider
display.set_pen(BLACK)
display.line(148, 14, 148, 123)

# 7. Tomorrow forecast (top-right)
display.set_font("bitmap8")
display.text("Tmr", 152, 18, scale=1)
display.set_font("bitmap6")
display.text(tmr_desc, 152, 32, scale=1)
display.text("H:{}  L:{}".format(tmax, tmin), 152, 44, scale=1)

# 8. Horizontal divider (tomorrow / map boundary)
display.set_pen(BLACK)
display.line(149, 56, 295, 56)

# 9. Location dot on map (or crosshair fallback)
if map_ok:
    draw_location_dot(display)
else:
    draw_crosshair(display, lat, lon)

# 10. Bottom border + push to E-Ink
display.set_pen(BLACK)
display.line(0, 123, 295, 123)
display.update()
print("Done!")

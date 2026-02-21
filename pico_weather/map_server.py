#!/usr/bin/env python3
"""
Local map proxy for Pico W
Fetches OSM tile, crops/resizes to 148x108 grayscale JPEG
GET /map?lat=52.19&lon=0.14
"""
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import urllib.request
import math
import io
from PIL import Image

PORT = 8765

def lat_lon_to_tile(lat, lon, zoom):
    n = 2 ** zoom
    x = int((lon + 180) / 360 * n)
    lat_r = math.radians(lat)
    y = int((1 - math.log(math.tan(lat_r) + 1/math.cos(lat_r)) / math.pi) / 2 * n)
    return x, y, n

def get_map_jpeg(lat, lon, width=148, height=108, zoom=13):
    tx, ty, n = lat_lon_to_tile(lat, lon, zoom)

    # Pixel position of our point within the tile
    px = ((lon + 180) / 360 * n - tx) * 256
    py = ((1 - math.log(math.tan(math.radians(lat)) + 1/math.cos(math.radians(lat))) / math.pi) / 2 * n - ty) * 256

    # Download tile
    url = f"https://tile.openstreetmap.org/{zoom}/{tx}/{ty}.png"
    req = urllib.request.Request(url, headers={
        "User-Agent": "PicoWeather/1.0 (educational project)"
    })
    with urllib.request.urlopen(req, timeout=10) as resp:
        tile = Image.open(resp).convert("RGB")

    # Crop 148x108 centered on our point
    cx, cy = int(px), int(py)
    left = max(0, cx - width//2)
    top = max(0, cy - height//2)
    left = min(left, 256 - width)
    top = min(top, 256 - height)
    cropped = tile.crop((left, top, left + width, top + height))

    # Convert to grayscale for E-Ink
    gray = cropped.convert("L")

    # Enhance contrast for better B&W rendering
    from PIL import ImageEnhance
    gray = ImageEnhance.Contrast(gray).enhance(1.5)

    # Save as JPEG (small!)
    buf = io.BytesIO()
    gray.save(buf, format="JPEG", quality=60)
    return buf.getvalue()

class MapHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        print(f"Map request: {args[0]} {args[1]}")

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/map":
            params = parse_qs(parsed.query)
            try:
                lat = float(params["lat"][0])
                lon = float(params["lon"][0])
                jpeg = get_map_jpeg(lat, lon)
                self.send_response(200)
                self.send_header("Content-Type", "image/jpeg")
                self.send_header("Content-Length", len(jpeg))
                self.end_headers()
                self.wfile.write(jpeg)
                print(f"  Sent {len(jpeg)} bytes for ({lat:.3f}, {lon:.3f})")
            except Exception as e:
                print(f"  Error: {e}")
                self.send_response(500)
                self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()

if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", PORT), MapHandler)
    print(f"Map proxy running on port {PORT}")
    server.serve_forever()

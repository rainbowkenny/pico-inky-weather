#!/usr/bin/env python3
"""
Local map proxy for Pico W
Draws a UK country outline map with location marker
GET /map?lat=52.19&lon=0.14&city=Cambridge
"""
import io
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

from PIL import Image, ImageDraw, ImageFont

PORT = 8765

# Simplified Great Britain outline (lon, lat) clockwise from SW
GB = [
    (-5.71, 50.07),
    (-5.20, 49.96),
    (-4.20, 50.06),
    (-3.39, 50.22),
    (-2.08, 50.61),
    (-1.85, 50.80),
    (-0.99, 50.84),
    (0.22, 50.90),
    (1.40, 51.13),
    (1.35, 51.35),
    (0.55, 51.47),
    (0.21, 52.01),
    (1.75, 52.49),
    (1.64, 52.99),
    (0.34, 53.74),
    (-0.09, 53.83),
    (-0.19, 54.10),
    (-1.74, 54.46),
    (-2.06, 55.01),
    (-1.44, 55.02),
    (-1.28, 55.12),
    (-1.77, 55.54),
    (-2.04, 55.96),
    (-2.19, 56.47),
    (-3.18, 56.51),
    (-3.47, 56.66),
    (-2.63, 57.06),
    (-2.05, 57.33),
    (-2.22, 57.77),
    (-2.44, 58.29),
    (-3.09, 58.64),
    (-4.10, 58.53),
    (-5.00, 58.67),
    (-5.18, 58.15),
    (-5.63, 57.86),
    (-5.81, 57.38),
    (-5.93, 56.88),
    (-6.16, 56.43),
    (-5.14, 55.75),
    (-4.80, 55.60),
    (-5.09, 55.18),
    (-4.97, 54.66),
    (-3.11, 53.73),
    (-3.07, 53.42),
    (-3.07, 53.11),
    (-4.73, 52.84),
    (-4.73, 52.49),
    (-5.08, 51.73),
    (-4.10, 51.55),
    (-3.10, 51.30),
    (-2.52, 51.17),
    (-1.60, 51.00),
    (-5.71, 50.07),
]

# Bounding box for Great Britain
LON_MIN, LON_MAX = -6.5, 2.1
LAT_MIN, LAT_MAX = 49.8, 60.9


def coord_to_px(lat, lon, w, h, padding=6):
    """Convert lat/lon to pixel coordinates on a w×h canvas."""
    lon_range = LON_MAX - LON_MIN
    lat_range = LAT_MAX - LAT_MIN
    x = padding + int((lon - LON_MIN) / lon_range * (w - 2 * padding))
    y = padding + int((LAT_MAX - lat) / lat_range * (h - 2 * padding))
    return x, y


def make_uk_map(lat, lon, city, width=148, height=108):
    img = Image.new("L", (width, height), color=255)  # white background
    draw = ImageDraw.Draw(img)

    # Draw GB outline
    points = [coord_to_px(la, lo, width, height) for lo, la in GB]
    draw.polygon(points, outline=0, fill=230)  # light grey fill, black outline

    # Draw some major cities as reference dots
    refs = [
        (51.51, -0.13, "London"),
        (53.48, -2.24, "Manch."),
        (55.86, -4.25, "Glasgow"),
        (53.80, -1.55, "Leeds"),
    ]
    for rlat, rlon, rname in refs:
        rx, ry = coord_to_px(rlat, rlon, width, height)
        draw.ellipse([rx - 2, ry - 2, rx + 2, ry + 2], fill=100)

    # Draw the target city
    tx, ty = coord_to_px(lat, lon, width, height)

    # Crosshair lines
    draw.line([tx - 8, ty, tx + 8, ty], fill=0, width=1)
    draw.line([tx, ty - 8, tx, ty + 8], fill=0, width=1)

    # Filled circle (white centre for contrast)
    draw.ellipse([tx - 5, ty - 5, tx + 5, ty + 5], fill=0)
    draw.ellipse([tx - 3, ty - 3, tx + 3, ty + 3], fill=255)
    draw.ellipse([tx - 1, ty - 1, tx + 1, ty + 1], fill=0)

    # City label (position smartly to avoid edges)
    label = city[:10]
    lx = tx + 7 if tx < width - 30 else tx - len(label) * 5 - 7
    ly = ty - 9 if ty > 15 else ty + 7
    # White background for text
    draw.rectangle([lx - 1, ly - 1, lx + len(label) * 5, ly + 8], fill=255)
    draw.text((lx, ly), label, fill=0)

    # Border
    draw.rectangle([0, 0, width - 1, height - 1], outline=0)

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=75)
    return buf.getvalue()


class MapHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print(f"[map] {args[0]} {args[1]}")

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/map":
            params = parse_qs(parsed.query)
            try:
                lat = float(params["lat"][0])
                lon = float(params["lon"][0])
                city = params.get("city", ["Location"])[0]
                jpeg = make_uk_map(lat, lon, city)
                self.send_response(200)
                self.send_header("Content-Type", "image/jpeg")
                self.send_header("Content-Length", len(jpeg))
                self.end_headers()
                self.wfile.write(jpeg)
                print(f"  {len(jpeg)}B for {city} ({lat:.2f},{lon:.2f})")
            except Exception as e:
                print(f"  Error: {e}")
                self.send_response(500)
                self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()


if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", PORT), MapHandler)
    print(f"Map proxy on :{PORT}")
    server.serve_forever()

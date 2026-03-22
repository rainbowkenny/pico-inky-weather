#!/usr/bin/env python3
"""Generate a KML file for Google My Maps import.

Usage:
    python3 generate_kml.py <output.kml> <waypoints.json>

waypoints.json format:
[
  {"name": "Tower of London", "lat": 51.5081, "lng": -0.0761, "description": "起点...", "num": "1"},
  ...
]

The KML can be imported into Google My Maps (google.com/mymaps → Create → Import).
"""

import json, sys
from xml.sax.saxutils import escape

def generate_kml(title: str, description: str, waypoints: list[dict]) -> str:
    placemarks = []
    for wp in waypoints:
        placemarks.append(f"""  <Placemark>
    <name>{escape(wp.get('num', '') + ' ' + wp['name'])}</name>
    <description>{escape(wp.get('description', ''))}</description>
    <styleUrl>#landmark</styleUrl>
    <Point><coordinates>{wp['lng']},{wp['lat']},0</coordinates></Point>
  </Placemark>""")

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
<Document>
  <name>{escape(title)}</name>
  <description>{escape(description)}</description>
  <Style id="landmark">
    <IconStyle><Icon><href>http://maps.google.com/mapfiles/kml/shapes/flag.png</href></Icon></IconStyle>
  </Style>
{chr(10).join(placemarks)}
</Document>
</kml>"""


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    output = sys.argv[1]
    with open(sys.argv[2]) as f:
        data = json.load(f)

    title = data.get("title", "Walking Route")
    desc = data.get("description", "")
    waypoints = data.get("waypoints", data if isinstance(data, list) else [])

    kml = generate_kml(title, desc, waypoints)
    with open(output, "w") as f:
        f.write(kml)
    print(f"✅ KML saved to {output} ({len(waypoints)} waypoints)")


if __name__ == "__main__":
    main()

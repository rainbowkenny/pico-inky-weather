#!/usr/bin/env python3
"""Fetch landmark images from Wikipedia REST API.

Usage:
    python3 fetch_images.py <output_dir> <name1>=<WikiTitle1> [<name2>=<WikiTitle2> ...]

Example:
    python3 fetch_images.py photos/ gherkin="30 St Mary Axe" tower-bridge="Tower Bridge"

Each image is saved as <name>.jpg in output_dir (600px wide from Wikipedia thumbnail).
Falls back to a placeholder if Wikipedia has no image.

NOTE: Wikimedia CDN blocks some server IPs. If direct download fails, the script
starts a local HTTP receiver (port 8799) and prints instructions for browser-based
transfer. Use the companion fetch_via_browser.js snippet or the browser tool to
POST base64 images to http://localhost:8799.
"""

import sys, os, json, http.client, urllib.parse, ssl, socket, time
from pathlib import Path

WIDTH = 600  # px — good quality for PDF without being huge

def get_wiki_image_url(title: str) -> str | None:
    """Get thumbnail URL from Wikipedia REST API summary endpoint."""
    encoded = urllib.parse.quote(title.replace(" ", "_"))
    conn = http.client.HTTPSConnection("en.wikipedia.org")
    conn.request("GET", f"/api/rest_v1/page/summary/{encoded}",
                 headers={"User-Agent": "DayGuideBot/1.0"})
    resp = conn.getresponse()
    if resp.status != 200:
        return None
    data = json.loads(resp.read())
    thumb = data.get("thumbnail", {}).get("source")
    if thumb:
        # Upscale thumbnail: replace /NNNpx- with /600px-
        import re
        thumb = re.sub(r"/\d+px-", f"/{WIDTH}px-", thumb)
    return thumb


def download(url: str, dest: str) -> bool:
    """Download url to dest, following redirects. Returns True on success."""
    parsed = urllib.parse.urlparse(url)
    for _ in range(5):  # max redirects
        ctx = ssl.create_default_context()
        conn = http.client.HTTPSConnection(parsed.hostname, context=ctx)
        conn.request("GET", parsed.path + ("?" + parsed.query if parsed.query else ""),
                     headers={"User-Agent": "DayGuideBot/1.0"})
        resp = conn.getresponse()
        if resp.status in (301, 302, 307, 308):
            url = resp.getheader("Location")
            parsed = urllib.parse.urlparse(url)
            resp.read()
            continue
        if resp.status == 200:
            data = resp.read()
            if len(data) > 1000:  # sanity check — HTML error pages are small-ish
                Path(dest).write_bytes(data)
                return True
        return False
    return False


def start_receiver(output_dir: str):
    """Start a simple HTTP server that accepts POST with JSON {name: base64data}."""
    import http.server
    class Handler(http.server.BaseHTTPRequestHandler):
        def do_POST(self):
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            data = json.loads(body)
            import base64
            for name, b64 in data.items():
                buf = base64.b64decode(b64)
                path = os.path.join(output_dir, f"{name}.jpg")
                with open(path, "wb") as f:
                    f.write(buf)
                print(f"  Saved {name}.jpg ({len(buf)//1024}KB)")
            self.send_response(200)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(b"OK")
        def do_OPTIONS(self):
            self.send_response(200)
            for h in ["Access-Control-Allow-Origin", "Access-Control-Allow-Methods", "Access-Control-Allow-Headers"]:
                self.send_header(h, "*")
            self.end_headers()
        def log_message(self, *a): pass

    server = http.server.HTTPServer(("0.0.0.0", 8799), Handler)
    print("\n⚠️  Direct download blocked. Browser transfer mode:")
    print(f"   POST base64 JSON to http://localhost:8799")
    print("   See fetch_via_browser.js for browser snippet\n")
    server.handle_request()  # handle one POST then exit


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    output_dir = sys.argv[1]
    os.makedirs(output_dir, exist_ok=True)

    landmarks = {}
    for arg in sys.argv[2:]:
        name, title = arg.split("=", 1)
        landmarks[name.strip()] = title.strip()

    failed = []
    for name, title in landmarks.items():
        url = get_wiki_image_url(title)
        if not url:
            print(f"  ⚠️  {name}: no Wikipedia image for '{title}'")
            failed.append(name)
            continue
        dest = os.path.join(output_dir, f"{name}.jpg")
        if download(url, dest):
            size = os.path.getsize(dest)
            print(f"  ✅ {name}: {size//1024}KB")
        else:
            print(f"  ❌ {name}: download blocked (Wikimedia CDN)")
            failed.append(name)

    if failed:
        print(f"\n{len(failed)} images failed direct download.")
        start_receiver(output_dir)
    else:
        print(f"\n✅ All {len(landmarks)} images saved to {output_dir}/")


if __name__ == "__main__":
    main()

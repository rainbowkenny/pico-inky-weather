---
name: day-guide
description: Generate polished PDF day guides for walking routes, day trips, and sightseeing itineraries. Produces an HTML page with Leaflet map, real Wikipedia photos, timeline, budget table, travel directions, and Google Maps/KML links — then converts to PDF via browser. Use when asked to create a day guide, walking tour PDF, trip itinerary document, sightseeing planner, or "攻略" for any location. Also use when asked to add waypoints to Google Maps (generates KML for import).
---

# Day Guide Generator

Create print-ready PDF day guides with maps, photos, and itineraries.

## Output Package

Each guide produces:
1. **HTML day guide** — self-contained page with Leaflet map, photos, timeline, budget
2. **PDF** — generated from HTML via browser `pdf` action
3. **KML file** — for Google My Maps import (all waypoints)
4. **Google Maps URL** — one-click walking route link

## Workflow

### 1. Define waypoints

Create a JSON structure with all stops:

```json
{
  "title": "London Skyscraper Walk",
  "description": "伦敦金融城摩天楼徒步路线",
  "waypoints": [
    {"name": "Tower of London", "lat": 51.5081, "lng": -0.0761,
     "wiki": "Tower_of_London", "num": "1", "type": "main",
     "description": "900年历史城堡", "height": "中世纪",
     "detail": "Full description for the card...",
     "tip": "⏱️ 10分钟拍照"}
  ]
}
```

Types: `main` (red), `bonus` (blue), `food` (orange).

### 2. Fetch landmark photos

Use `scripts/fetch_images.py`:

```bash
python3 scripts/fetch_images.py photos/ \
  tower-of-london="Tower of London" \
  gherkin="30 St Mary Axe"
```

**If Wikimedia CDN blocks direct download** (common on some servers — images save as 0KB):

1. The script auto-starts a receiver on port 8799
2. Use the browser tool to navigate to any page, then evaluate `scripts/fetch_via_browser.js`
3. The browser fetches from Wikipedia API and POSTs base64 to localhost:8799

Browser evaluate pattern:
```javascript
// 1. Fetch each image from Wikipedia REST API in browser
const resp = await fetch(`https://en.wikipedia.org/api/rest_v1/page/summary/${title}`);
const data = await resp.json();
const imgUrl = data.thumbnail.source.replace(/\/\d+px-/, '/600px-');

// 2. Convert to base64 via canvas or FileReader
// 3. Store in localStorage, then POST all to http://localhost:8799
```

### 3. Generate HTML

Copy `assets/day-guide-template.html` to the project directory. Replace all `{{PLACEHOLDERS}}`:

| Placeholder | Content |
|---|---|
| `{{TITLE}}` | Page title |
| `{{EMOJI}}` | Cover emoji |
| `{{TITLE_EN}}` / `{{TITLE_ZH}}` | Cover headings |
| `{{ROUTE_SUMMARY}}` | e.g. "Tower Hill → The City → Borough Market" |
| `{{DISTANCE_AND_TIME}}` | e.g. "~2.5km · 2-3小时 · 全家适合" |
| `{{DATE}}` / `{{FAMILY_NAME}}` | Date and family name |
| `{{GOOGLE_MAPS_URL}}` | Walking directions URL (see below) |
| `{{TRAVEL_STEPS}}` | `<li>` elements for transport |
| `{{STOP_CARDS}}` | Stop card HTML blocks |
| `{{TIMELINE_ITEMS}}` | Timeline `<div>` blocks |
| `{{BUDGET_ROWS}}` | `<tr>` elements |
| `{{TIPS}}` | `<li>` elements |
| `{{STOPS_JSON}}` | JSON array for Leaflet map |
| `{{MAP_CENTER_LAT/LNG}}` / `{{MAP_ZOOM}}` | Map view settings |

Stop card HTML pattern:
```html
<div class="stop-card {{TYPE_CLASS}}">
  <img src="photos/{{NAME}}.jpg" alt="{{DISPLAY_NAME}}">
  <div class="stop-info">
    <h3 class="stop-title"><span class="num">{{NUM}}</span>{{DISPLAY_NAME}} <span class="height">{{HEIGHT}}</span></h3>
    <p>{{DETAIL}}</p>
    <p class="tip">{{TIP}}</p>
  </div>
</div>
```

### 4. Generate Google Maps URL

Format: `https://www.google.com/maps/dir/` + stops joined by `/` + `/@LAT,LNG,ZOOMz/data=!4m2!4m1!3e2`

The `!3e2` suffix = walking mode. Use `+` for spaces in place names.

### 5. Generate KML

Use `scripts/generate_kml.py`:

```bash
python3 scripts/generate_kml.py route.kml waypoints.json
```

### 6. Render PDF

1. Start a local HTTP server: `python3 -m http.server 8787`
2. Wait for images to be accessible
3. Navigate browser to `http://localhost:8787/day-guide.html`
4. Wait for all images to load (evaluate: `document.querySelectorAll('img').length` vs loaded count)
5. Use browser `pdf` action to generate PDF
6. Copy PDF to project directory

### 7. Send to Telegram

Send in order:
1. **PDF** with caption listing all stops
2. **KML file** with import instructions for Google My Maps
3. **Google Maps URL** as a clickable walking route link

## Design Notes

- **Language**: Default bilingual Chinese/English (match family preference)
- **Photos**: Always use Wikipedia images (accurate) — never Pexels/Unsplash random search (produces wrong buildings)
- **Map tiles**: CartoDB Voyager (clean, readable in print)
- **Color scheme**: Red (#e63946) main stops, Blue (#457b9d) bonus, Orange (#f4a261) food
- **Page breaks**: Each section on its own page for clean PDF pagination
- **Budget**: Always include for family of 4, with money-saving tips

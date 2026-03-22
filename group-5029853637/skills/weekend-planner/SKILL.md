---
name: weekend-planner
description: |
  Family weekend and holiday planner for S's family (Cambridge, UK). Use when:
  - Planning weekends, holidays, or family activities
  - Checking Leys School calendar or School House events
  - Finding Badminton England tournaments (Bronze U15)
  - Searching local/London events, shows, outdoor activities
  - Managing Google Calendar for family scheduling
  - Optimising annual leave around Bank Holidays
  - Daily/weekly/monthly activity recommendations
  - Finding local services (barbers, restaurants, etc.) with ratings via Google Maps Places API
---

# Weekend Planner

## Family Profile
- **S** (dad), Cambridge area, has car + train
- **Home base**: 9 Harebell Close, Fulbourn, Cambridge CB1 9YL
- **Son** (Albert) 13yo: Leys School (School House), badminton BE Bronze U15
- **Daughter** (点点/Alice) 10yo: gymnastics, generally free weekends
- **Budget**: ~£250/weekend
- **Radius**: Cambridge local → London → 2.5h by car/train
- **Interests**: all categories (arts, music, sports, outdoor, tech, shopping, theme parks, festivals)

## Authentication

### Google Calendar — Service Account (permanent, no expiry)
- **SA email**: `luka-calendar-bot@sylvan-storm-488713-f3.iam.gserviceaccount.com`
- **Key file**: `credentials/service_account.json`
- **Shared auth module**: `credentials/gcal_auth.py` — all scripts import from here
- **Usage**: `from gcal_auth import get_headers, get_credentials, CAL_PRIMARY, CAL_FAMILY`
- Both calendars (主日历 + Family) are shared with the SA with write access

### Google Maps Places API
- **API Key**: stored in project config (sylvan-storm-488713-f3)
- **Usage**: Legacy Places API (`maps.googleapis.com/maps/api/place/`)
- **Free tier**: $200/month credit (>6000 searches/month)
- **Use for**: local service discovery with ratings, reviews, parking, booking info

### Gmail — OAuth user token (separate, for school email scanning)
- **Token**: `projects/gmail-api/token_hang.json`
- Note: This token can still expire. Calendar operations use SA instead.

## Data Sources

### 1. Leys School Calendar
- URL: https://www.theleys.net/news-and-events/school-calendar/
- Focus: Saturday school days, Live Weekends, Exeat, Half Term, School House events
- Script: `scripts/scrape_leys.py`

### 2. Badminton England Tournaments
- Source: https://be.tournamentsoftware.com/
- **HTTP scraper**: `projects/weekend-planner/scrape_be_tournaments.py` — accepts cookie wall via POST to `/cookiewall/Save`, then searches via `/find/tournament/DoSearch`. No browser/CDP needed.
- Usage: `python3 scrape_be_tournaments.py [--level bronze,silver,gold] [--months 3] [--max-km 150]`
- Cookie wall: The site shows a consent page. The scraper auto-accepts by POSTing `{ReturnUrl: "", SettingsOpen: "false"}` to `/cookiewall/Save` with a cookie jar.
- Filter: Bronze/Silver/Gold level ONLY, U15, within 150km of Cambridge (exclude "Futures", "Other" category tournaments)
- Deadline: MUST use "Closing deadline" (报名截止), NOT "Withdrawal deadline" (退赛截止)
- Each listing must include: name, date, venue, level, closing deadline, entry link
- Category IDs: International=4205, Nationals=4206, Gold=4207, Silver=4208, Bronze=4209, Tier4=4212
- Age Group IDs: U15=15 (passed as `TournamentExtendedFilter.AgeGroupID`)

### 3. Events & Activities
- Cambridge: Arts Theatre, ADC, Corn Exchange, Fitzwilliam, Kettle's Yard, Science Centre
- London: West End, Tate, V&A, Barbican, Science Museum, BFI
- Outdoor: National Trust, English Heritage, Go Ape, forests, cycling
- Theme parks: Thorpe Park, Legoland, Wicksteed, Pleasurewood Hills
- Shopping: Bicester Village, Cambridge/London markets
- Sports: Cambridge United, local tournaments, climbing, trampolining, ice skating
- Sailing: London Sailing Club (see dedicated section below)
- Festivals: food, craft, seasonal, fireworks
- Script: `projects/weekend-planner/scrape_events.py`
- **Content filtering**: Blocklist excludes religious services, schools, political events, adult-only, toddler/baby events
- **Category detection**: Auto-classifies events (museum, show, outdoor, sports, attraction, family, etc.) by keyword matching
- **Curated pool**: High-quality fallback options (IWM Duxford, Go Ape, Warner Bros HP, Clip 'n Climb, Natural History Museum, Science Museum, V&A, Greenwich Observatory, Colchester Zoo, Thorpe Park, West End Shows, ice skating, Wicksteed Park, Audley End Railway) — each tagged `indoor/outdoor` and `seasonal` for weather-aware selection
- **Event scoring**: `pick_best_events()` in daily_push.py scores by quality (penalises vague titles/venue-only names), category relevance, weather matching (rainy→indoor, sunny→outdoor), variety enforcement, and known-great-option bonus
- **Family constraints**: NOT Christian (no religious events), kids aged 10+13 (no toddler/baby events)

### 3a. London Sailing Club
- URL: https://www.londonsailing.club/ (myClubhouse platform, JS-rendered)
- **Scraping**: HTTP fetch of homepage HTML, parse event blocks from "Upcoming Events" section
- Events include: sailing trips (non-commercial/commercial), monthly socials, theory sessions, taster days, races
- Data extracted: title, date, time, venue, price, places_available, event_type, signup_url
- **Daily push integration**: Sailing TRIP events shown in dedicated section after main options (not as one of the 选项1/2/3), showing all upcoming trips with prices and availability
- **Fallback**: If HTTP scrape fails, show "check website" placeholder with link
- Entry path recommendation: Monthly Social → Taster Day → Multi-day trips

### 4. Google Calendar
- Auth: Service Account via `credentials/gcal_auth.py`
- Calendars: 主日历 (`hang.shuojin@gmail.com`) + Family (`family03011953462043037676@group.calendar.google.com`)
- Read: avoid conflicts (daughter's gymnastics, sleepovers, existing plans)
- Write: confirmed activities → auto-add to calendar
- Calendar event style preference: avoid all-day events unless explicitly requested; default to timed blocks (prefer `09:00-10:00` local time for reminders/admin tasks)
- Script: `projects/weekend-planner/gcal_fetch.py`

### 5. Gmail School Mail Scan (daily)
- Scan school emails (St Faith's / SchoolPost / Leys / **SchoolsBuddy**) for actionable schedule details
- Auto-create events in Family Calendar (via SA)
- **Sources**: SchoolPost (`schoolpostmail.co.uk`), SchoolsBuddy (`schoolsbuddy.com`), direct staff emails (`@stfaiths.co.uk`, `@theleys.net`)
- **Event types detected**: sports fixtures, concerts/plays, parents evenings, trips, special sessions, uniform sales, fairs, INSET days, deadlines, activity allocations
- **Filtering**: Skips newsletters, feedback requests, progress reports, personal replies, health alerts (informational)
- **Labeling**: All auto-added events MUST be prefixed with the school name (e.g., `[St Faith's]` or `[Leys]`) to distinguish sources
- **Recurring events**: Activity allocations from SchoolsBuddy → create weekly recurring events with RRULE for the term period
- **CLI flags**: `--dry-run` (preview only), `--days N` (scan window, default 3), `--verbose` (show skip reasons)
- Script: `projects/weekend-planner/gmail_to_family_calendar.py`

### 6. Weather
- **Primary**: wttr.in (richer forecast data)
- **Fallback**: Open-Meteo API (free, fast, reliable — auto-switches on wttr.in failure)
- Both integrated in `daily_push.py` `fetch_weather()` with automatic failover

### 7. UK Bank Holidays & School Holidays
- Bank Holidays: gov.uk API
- Optimise annual leave (25 days) around long weekends

## Scripts Overview

| Script | Location | Auth | Purpose |
|--------|----------|------|---------|
| `gcal_fetch.py` | projects/weekend-planner/ | SA | Fetch calendar events |
| `confirm_and_book.py` | projects/weekend-planner/ | SA | Create calendar events |
| `gmail_to_family_calendar.py` | projects/weekend-planner/ | Gmail OAuth + SA | Scan emails → calendar (SchoolPost + SchoolsBuddy + direct) |
| `scrape_be_tournaments.py` | projects/weekend-planner/ | None (HTTP + cookie accept) | BE tournaments |
| `scrape_events.py` | projects/weekend-planner/ | None | Cambridge/London events |
| `scrape_leys.py` | skills/weekend-planner/scripts/ | None | Leys school calendar |
| `daily_push.py` | projects/weekend-planner/ | All above | Orchestrator for daily push |
| `create_day_alarms.py` | skills/day-alarm-planner/scripts/ | SA | Day alarm reminders |

## Push Schedule (automated via OpenClaw cron)

All pushes auto-deliver to the Family Calendar Telegram group (`-5029853637`).

| When | Cron Job | What |
|------|----------|------|
| Daily 8AM | `Daily Weekend Planner Push` (67193cef) | Runs `daily_push.py`, sends output to group |
| Tuesday 8AM | `Tuesday Weekend Plan (detailed)` (551b7ac5) | Enhanced plan with 2-3 options + links + prices |
| 1st of month | (monthly cron, d14084c4) | Monthly overview (tournaments, ticket dates, School House events) |

### Cron setup
- Agent: `group-5029853637`
- Session: `isolated` (fresh each run, no context carry-over)
- Delivery: `announce` → Telegram → `-5029853637`
- Timezone: `Europe/London`
- Old disabled crons: `c9fe99a4` (daily 7AM, old prompt), `9cae1d4d` (weekly)

## Output Format
```
🗓️ 周末 [date] ([School status]) [emoji] [weather]

📅 日历已有:
  - [existing events]

🏸 选项1: [Tournament name] — [venue]
   [level] | [date] | 截止: [deadline] | 🚗 [travel]
   🔗 [url]

🎭 选项2: [Show/Activity name] — [venue]
   [day/time] | £[price range] | 🚗 [travel]
   🔗 [url]

🌿 选项3: [Activity] — [venue]
   [day/time] | £[price] | 🚗 [time]
   🔗 [url]

⛵ London Sailing Club 近期航海活动:
   • [date] [title] | £[price] | [X] places
   • [date] [title] | £[price] | [X] places
   ...

回复 1/2/3 选择 ✅
```

### Event Selection Logic
- Events scored by: quality (title length/specificity), category relevance, weather match, variety, known-great bonus
- Blocklist filters: religious, schools, political, adult-only, toddler/baby
- Weather-aware: rainy/cold → indoor options preferred; sunny/warm → outdoor preferred
- Variety enforced: no 2+ events from same category in top 3
- URLs included for all options

## Constraints
- Saturday school day → Leys DEFAULT is Saturday morning school. Only if "Leave Weekend" or "Exeat" is explicitly tagged → Saturday free. Otherwise → only plan afternoon + Sunday
- Live Weekend / Exeat → full two days
- Daughter gymnastics/sleepover → check Google Cal, exclude conflicts
- BE tournament registration deadlines → remind 3 days before
- Both kids ages (10+13) → activities must suit both
- **NOT Christian** — never recommend religious services, church events, or faith-based activities
- **No toddler/baby events** — kids are 10 and 13, filter out baby sensory, rhymetime, etc.
- Seasonal awareness (weather, daylight, school terms)
- **AUTO CONFLICT CHECK (mandatory before including any activity/tournament):**
  1. Check Leys School calendar for Saturday events/exams
  2. Check Google Calendar (both calendars) for existing plans
  3. If conflict → exclude; if borderline → include with ⚠️ note
  4. Log excluded items: "已排除(冲突): [item] — 原因: [conflict]"

## References
- `references/family-profile.md` — detailed preferences and history
- `references/annual-framework.md` — year planner with holidays and key dates
- `references/google-calendars.md` — calendar IDs and API details

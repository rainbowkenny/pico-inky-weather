---
name: cc
description: |
  Family weekend and holiday planner for S's family (Cambridge, UK). Use when:
  - Planning weekends, holidays, or family activities
  - Checking Leys School calendar or School House events
  - Finding Badminton England tournaments (Bronze U15)
  - Searching local/London events, shows, outdoor activities
  - Managing Google Calendar for family scheduling
  - Optimising annual leave around Bank Holidays
  - Daily/weekly/monthly activity recommendations
---

# Weekend Planner

## Family Profile
- **S** (dad), Cambridge area, has car + train
- **Son** 13yo: Leys School (School House), badminton BE Bronze U15
- **Daughter** 10yo: gymnastics, generally free weekends
- **Budget**: ~£250/weekend
- **Radius**: Cambridge local → London → 2.5h by car/train
- **Interests**: all categories (arts, music, sports, outdoor, tech, shopping, theme parks, festivals)

## Data Sources

### 1. Leys School Calendar
- URL: https://www.theleys.net/news-and-events/school-calendar/
- Focus: Saturday school days, Live Weekends, Exeat, Half Term, School House events
- Script: `scripts/scrape_leys.py`

### 2. Badminton England Tournaments
- URL: https://be.tournamentsoftware.com/
- Filter: Bronze level, U15, within 2.5h travel
- Script: `scripts/scrape_be_tournaments.py`

### 3. Events & Activities
- Cambridge: Arts Theatre, ADC, Corn Exchange, Fitzwilliam, Kettle's Yard, Science Centre
- London: West End, Tate, V&A, Barbican, Science Museum, BFI
- Outdoor: National Trust, English Heritage, Go Ape, forests, cycling
- Theme parks: Thorpe Park, Legoland, Wicksteed, Pleasurewood Hills
- Shopping: Bicester Village, Cambridge/London markets
- Sports: Cambridge United, local tournaments, climbing, trampolining, ice skating
- Festivals: food, craft, seasonal, fireworks
- Eventbrite, Time Out London, VisitEngland, local listings
- Script: `scripts/scrape_events.py`

### 4. Google Calendar
- Account: hang.shuojin@gmail.com
- Read: avoid conflicts (daughter's gymnastics, sleepovers, existing plans)
- Write: confirmed activities → auto-add to calendar

### 5. UK Bank Holidays & School Holidays
- Bank Holidays: gov.uk API
- Optimise annual leave (25 days) around long weekends
- Easter / Half Term / Summer → longer trip windows

## Push Schedule
| When | What |
|------|------|
| Daily 8AM | Activity discoveries, reminders, countdown to weekend |
| Tuesday 8AM | Featured: full weekend plan (2-3 options + links + prices) |
| 1st of month | Monthly overview (tournaments, ticket dates, School House events) |
| Quarterly | Holiday planning (annual leave optimisation, trip ideas) |

## Output Format
```
🗓️ 周末 [date] ([School status])

🏸 选项1: [Tournament name] — [venue]
   [day/time] | 报名截止 [date] | £[price]
   🚗 [drive time] / 🚂 [train time]

🎭 选项2: [Show name] — [venue]
   [day/time] | £[price range]

🌿 选项3: [Activity] — [venue]
   [day/time] | £[price] | 🚗 [time]

回复 1/2/3 或组合
```

## Constraints
- Saturday school day → plan afternoon + Sunday only
- Live Weekend / Exeat → full two days
- Daughter gymnastics/sleepover → check Google Cal, exclude conflicts
- BE tournament registration deadlines → remind 3 days before
- Both kids ages (10+13) → activities must suit both
- Seasonal awareness (weather, daylight, school terms)

## References
- `references/family-profile.md` — detailed preferences and history
- `references/annual-framework.md` — year planner with holidays and key dates

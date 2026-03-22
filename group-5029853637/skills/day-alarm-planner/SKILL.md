---
name: day-alarm-planner
description: Create one-day, multi-stop alarm plans and write them as Google Calendar reminder events with popup notifications. Use when the user asks to "set alarms/reminders for today" or provides a same-day schedule with required arrival times, pickup/dropoff stops, and departure planning.
---

# Day Alarm Planner

Build practical one-day reminder chains from a home base and fixed-time commitments, then save reminders into Family Calendar so phone notifications fire automatically.

## Workflow

1. Confirm inputs: date, home/base location, fixed arrival-time events, optional buffer preferences.
2. Build reminder chain in chronological order:
   - Pre-departure reminder (default 30 min before departure)
   - Depart reminder
   - Arrival check reminder (default 5 min before target)
3. Resolve conflicts against existing calendar events on that date.
4. Create reminder events in Google Calendar (Family by default).
5. Return a concise checklist of created reminders and ask for adjustments.

## Default reminder policy

- Timezone: `Europe/London`
- Reminder event duration: 10 minutes
- Popup notifications: at event start (`minutes: 0`)
- Suggested layers for major travel legs: 60 / 30 / 10 minutes before departure (if user asks for stronger nudges)

## Script usage

Use `scripts/create_day_alarms.py` to create reminders from JSON input.

Example:

```bash
python3 scripts/create_day_alarms.py \
  --date 2026-03-07 \
  --calendar-id family03011953462043037676@group.calendar.google.com \
  --input-json '[
    {"time":"10:45","title":"出发去Mia家（11:15到）","note":"从9 Harebell Close出发"},
    {"time":"11:10","title":"到达Mia家前确认","note":"检查点点物品"}
  ]'
```

## Notes

- Prefer Family calendar for household logistics.
- If the user gives rough constraints only, produce a proposed schedule first, then write events after confirmation.
- If address or travel-time assumptions are uncertain, explicitly label them and request correction.

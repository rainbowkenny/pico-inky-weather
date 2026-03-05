# Google Calendar Integration

## Credentials
- Auth script: `/home/albert/.openclaw/workspace/credentials/google_auth.py`
- Credentials: `/home/albert/.openclaw/workspace/credentials/google_credentials.json`
- Token: `/home/albert/.openclaw/workspace/credentials/google_token.json`
- Token auto-refreshes via refresh_token

## Tracked Calendars

| Calendar | ID | Purpose |
|----------|----|---------|
| 主日历 | `hang.shuojin@gmail.com` | S的个人日程 |
| Family | `family03011953462043037676@group.calendar.google.com` | 家庭活动 |

Both calendars MUST be checked when planning weekends to avoid conflicts.

## API Usage
- Endpoint: `https://www.googleapis.com/calendar/v3/calendars/{calendarId}/events`
- Auth: Bearer token from google_token.json (refresh if 401)
- Always query both calendars for the relevant date range

# Google Calendar Integration

## Authentication — Service Account (permanent)
- **SA email**: `luka-calendar-bot@sylvan-storm-488713-f3.iam.gserviceaccount.com`
- **Key file**: `credentials/service_account.json`
- **Shared module**: `credentials/gcal_auth.py`
- **No expiry** — no refresh tokens to manage

### Usage
```python
import sys
sys.path.insert(0, "/home/albert/.openclaw/workspace/group-5029853637/credentials")
from gcal_auth import get_headers, get_credentials, CAL_PRIMARY, CAL_FAMILY, health_check
```

## Tracked Calendars

| Calendar | ID | Constant |
|----------|----|----------|
| 主日历 | `hang.shuojin@gmail.com` | `CAL_PRIMARY` |
| Family | `family03011953462043037676@group.calendar.google.com` | `CAL_FAMILY` |

Both calendars MUST be checked when planning weekends to avoid conflicts.

## Google Maps Places API
- **API Key**: (stored in GCP console — do not commit to git)
- **Endpoint**: `maps.googleapis.com/maps/api/place/textsearch/json` (legacy)
- **Free tier**: $200/month (~6000+ searches)
- **Use for**: local service searches with ratings, reviews, parking

## Legacy OAuth (deprecated, do NOT use for new scripts)
- Old credentials in `credentials/google_credentials.json` and `credentials/google_token.json`
- Gmail token in `projects/gmail-api/token_hang.json` (still used for Gmail API only)

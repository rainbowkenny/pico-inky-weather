#!/usr/bin/env python3
"""Scan school emails and auto-add actionable schedule items to Family Calendar.

Supports: St Faith's, The Leys, SchoolPost emails.
Event types: sports, concerts, plays, parents evenings, trips, special sessions,
             uniform sales, fairs, INSET days, deadlines, early finishes.
Uses: Gmail OAuth token (user) + Service Account (calendar).
"""

import argparse
import base64
import json
import re
import sys
from datetime import datetime, timedelta

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

sys.path.insert(0, "/home/albert/.openclaw/workspace/group-5029853637/credentials")
from gcal_auth import get_credentials as get_sa_credentials, CAL_FAMILY

GMAIL_TOKEN = "/home/albert/.openclaw/workspace/group-5029853637/projects/gmail-api/token_hang.json"
FAMILY_CAL = CAL_FAMILY
TZ = "Europe/London"

# ── Patterns to SKIP (non-actionable) ──────────────────────────────────────
SKIP_SUBJECT_PATTERNS = [
    r"newsletter",
    r"feedback\s+(for|form|survey)",
    r"progress\s+check",
    r"report[s]?\s+(available|now|ready)",
    r"^re:\s",  # personal replies
    r"chaplain.s?\s+newsletter",
    r"weekly\s+bulletin",
    r"safeguarding",
    r"online\s+safety",
    r"policy\s+update",
    r"privacy",
    r"artificial\s+intelligence",
    r"meningitis",  # health alerts (important to read, not calendar events)
]

# ── Patterns that signal ACTIONABLE events ─────────────────────────────────
EVENT_KEYWORDS = [
    r"match(?:es)?", r"fixture[s]?", r"tournament", r"competition",
    r"concert", r"play\b", r"performance", r"show\b", r"recital", r"rehearsal",
    r"parents?\s*(?:evening|consultation|meeting)",
    r"trip\b", r"outing", r"excursion", r"visit\b",
    r"gymnastics\s+session", r"coaching\s+session", r"training\s+session",
    r"uniform\s+sale", r"fair\b", r"fete\b", r"open\s+(?:day|morning|evening)",
    r"inset\s+day", r"non[- ]pupil\s+day", r"staff\s+training\s+day",
    r"early\s+finish", r"early\s+closure",
    r"sports?\s+(?:day|programme|afternoon|morning)",
    r"prize\s+(?:giving|day)", r"speech\s+day", r"celebration",
    r"carol\s+service", r"nativity", r"harvest\s+festival",
    r"swim\s+gala", r"athletics", r"cross[- ]country",
    r"exam[s]?\b", r"assessment",
    r"photograph(?:y|s)?\s+day", r"photo\s+day",
    r"cake\s+sale", r"charity",
    r"disco\b", r"party\b", r"film\s+night",
    r"workshop\b", r"masterclass",
    r"deadline", r"closing\s+date", r"book(?:ing)?\s+(?:by|before|deadline)",
]

MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}


def gmail_service():
    creds = Credentials.from_authorized_user_file(GMAIL_TOKEN)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return build("gmail", "v1", credentials=creds)


def calendar_service():
    creds = get_sa_credentials()
    return build("calendar", "v3", credentials=creds)


def decode_text(payload):
    """Extract text from Gmail message payload (recursive)."""
    out = []
    def walk(node):
        mime = node.get("mimeType", "")
        b = node.get("body", {}).get("data")
        if b and "text/plain" in mime:
            try:
                out.append(base64.urlsafe_b64decode(b).decode("utf-8", "replace"))
            except Exception:
                pass
        elif b and "text/html" in mime and not out:
            # fallback to HTML if no plain text
            try:
                raw = base64.urlsafe_b64decode(b).decode("utf-8", "replace")
                # strip HTML tags for basic text extraction
                text = re.sub(r"<[^>]+>", " ", raw)
                text = re.sub(r"\s+", " ", text)
                out.append(text)
            except Exception:
                pass
        for p in node.get("parts", []) or []:
            walk(p)
    walk(payload)
    # If no plain text found, try any body data
    if not out:
        def walk_any(node):
            b = node.get("body", {}).get("data")
            if b:
                try:
                    raw = base64.urlsafe_b64decode(b).decode("utf-8", "replace")
                    text = re.sub(r"<[^>]+>", " ", raw)
                    text = re.sub(r"\s+", " ", text)
                    out.append(text)
                except Exception:
                    pass
            for p in node.get("parts", []) or []:
                walk_any(p)
        walk_any(payload)
    return "\n".join(out)


def identify_school(from_hdr, subject, body):
    """Return school tag based on sender/content."""
    combined = f"{from_hdr} {subject}".lower()
    if "stfaith" in combined or "st faith" in combined:
        return "[St Faith's]"
    elif "theleys" in combined or "the leys" in combined or "leyspost" in combined:
        return "[Leys]"
    return ""


def should_skip(subject):
    """Check if email subject matches skip patterns."""
    subj_lower = subject.lower()
    for pat in SKIP_SUBJECT_PATTERNS:
        if re.search(pat, subj_lower):
            return True
    return False


def is_actionable(subject, body):
    """Check if email contains actionable event keywords."""
    combined = f"{subject} {body}".lower()
    for pat in EVENT_KEYWORDS:
        if re.search(pat, combined):
            return True
    return False


def parse_date(text, reference_year=None):
    """Extract the most relevant event date from text.

    Strategy: find ALL dates, then pick the best one — prefer dates near
    event keywords and in the subject/title area, not random dates in boilerplate.

    Handles: '25th April 2026', 'Saturday 21 March', '15 March 2026',
             'Monday 23rd March', '21/03/2026', '2026-03-21'
    Returns: (datetime.date, match_end_pos) or (None, 0).
    """
    if reference_year is None:
        reference_year = datetime.now().year

    DATE_RE = re.compile(
        r"(?:(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)\s+)?"
        r"(\d{1,2})(?:st|nd|rd|th)?\s+"
        r"(january|february|march|april|may|june|july|august|september|october|november|december"
        r"|jan|feb|mar|apr|jun|jul|aug|sep|oct|nov|dec)"
        r"(?:\s+(\d{4}))?",
        re.IGNORECASE,
    )
    NUMERIC_DATE_RE = re.compile(r"(\d{1,2})/(\d{1,2})/(\d{4})")

    text_lower = text.lower()
    # Split into subject (first ~200 chars) and body
    subject_zone = text_lower[:200]

    dates_found = []  # list of (date, position, in_subject, near_keyword)

    for m in DATE_RE.finditer(text_lower):
        try:
            day = int(m.group(1))
            month = MONTHS.get(m.group(2).lower())
            year = int(m.group(3)) if m.group(3) else reference_year
            if not month or day < 1 or day > 31:
                continue
            # If no year given and date is far past, try next year
            if not m.group(3):
                candidate = datetime(year, month, day).date()
                if candidate < datetime.now().date() - timedelta(days=30):
                    year += 1
            d = datetime(year, month, day).date()
            in_subj = m.start() < 200
            # Check if near an event keyword (within 100 chars)
            context = text_lower[max(0, m.start() - 80):m.end() + 80]
            near_kw = any(re.search(pat, context) for pat in EVENT_KEYWORDS)
            dates_found.append((d, m.end(), in_subj, near_kw))
        except (ValueError, TypeError):
            continue

    for m in NUMERIC_DATE_RE.finditer(text_lower):
        try:
            day, month, year = int(m.group(1)), int(m.group(2)), int(m.group(3))
            if 1 <= month <= 12 and 1 <= day <= 31:
                d = datetime(year, month, day).date()
                in_subj = m.start() < 200
                context = text_lower[max(0, m.start() - 80):m.end() + 80]
                near_kw = any(re.search(pat, context) for pat in EVENT_KEYWORDS)
                dates_found.append((d, m.end(), in_subj, near_kw))
        except (ValueError, TypeError):
            continue

    if not dates_found:
        return None, 0

    today = datetime.now().date()
    future = [x for x in dates_found if x[0] >= today]
    pool = future if future else dates_found

    # Score: prefer (1) near keyword, (2) in subject, (3) earliest future date
    def score(item):
        d, pos, in_subj, near_kw = item
        return (-int(near_kw), -int(in_subj), d)

    best = min(pool, key=score)
    return best[0], best[1]


def parse_time(text):
    """Extract start and end times from text.

    Handles: '11:15-12:30', '8-12', '7.45am', '4.30pm-6pm', '19:00',
             '11:15 – 12:30', '8am - 12pm', '4:30 pm - 18:00'
    Returns: (start_hour, start_min, end_hour, end_min) or partial tuple with None
    """
    text_clean = re.sub(r"\s+", " ", text.lower())

    # Time range patterns
    range_patterns = [
        # "11:15-12:30" or "11:15 - 12:30" or "11:15 – 12:30"
        r"(\d{1,2})[:\.](\d{2})\s*(?:a\.?m\.?|p\.?m\.?)?\s*[-–—to]+\s*(\d{1,2})[:\.](\d{2})\s*(a\.?m\.?|p\.?m\.?)?",
        # "8-12" or "8am-12pm" or "8am - 12"
        r"(\d{1,2})\s*(a\.?m\.?|p\.?m\.?)?\s*[-–—to]+\s*(\d{1,2})\s*(a\.?m\.?|p\.?m\.?)?",
        # "4:30 pm - 18:00" (mixed formats)
        r"(\d{1,2})[:\.](\d{2})\s*(a\.?m\.?|p\.?m\.?)?\s*[-–—to]+\s*(\d{1,2})[:\.]?(\d{2})?\s*(a\.?m\.?|p\.?m\.?)?",
    ]

    for pat in range_patterns:
        m = re.search(pat, text_clean)
        if m:
            groups = m.groups()
            try:
                if len(groups) >= 4:
                    sh = int(groups[0])
                    sm = int(groups[1]) if groups[1] and groups[1].isdigit() else 0
                    eh = int(groups[2]) if groups[2] and re.match(r"\d+", str(groups[2])) else None
                    em = int(groups[3]) if groups[3] and re.match(r"\d+", str(groups[3])) else 0

                    # Handle am/pm
                    ampm_start = None
                    ampm_end = None
                    for g in groups:
                        if g and re.match(r"p\.?m\.?", str(g)):
                            ampm_end = "pm"
                        elif g and re.match(r"a\.?m\.?", str(g)):
                            ampm_end = "am"

                    if ampm_end == "pm" and eh and eh < 12:
                        eh += 12
                    if ampm_end == "am" and eh == 12:
                        eh = 0

                    # Infer: if start < end and both small, likely morning
                    # If start looks like afternoon (e.g. 4) and end too, add 12
                    if sh <= 12 and eh and eh <= 12 and sh < eh:
                        # Could be morning (8-12) or needs context
                        pass
                    elif sh < 12 and eh and eh < sh:
                        # e.g., 4-6 likely means 16-18
                        sh += 12
                        eh += 12

                    if eh:
                        return (sh, sm, eh, em)
            except (ValueError, TypeError):
                pass

    # Single time patterns
    single_patterns = [
        # "7.45am" or "4:30pm" or "19:00"
        r"(\d{1,2})[:\.](\d{2})\s*(a\.?m\.?|p\.?m\.?)?",
        # "8am" or "6pm"
        r"\b(\d{1,2})\s*(a\.?m\.?|p\.?m\.?)\b",
    ]

    times = []
    for pat in single_patterns:
        for m in re.finditer(pat, text_clean):
            try:
                h = int(m.group(1))
                mins = int(m.group(2)) if len(m.groups()) >= 2 and m.group(2) and m.group(2).isdigit() else 0
                ampm = None
                for g in m.groups():
                    if g and re.match(r"p\.?m\.?", str(g)):
                        ampm = "pm"
                    elif g and re.match(r"a\.?m\.?", str(g)):
                        ampm = "am"
                if ampm == "pm" and h < 12:
                    h += 12
                if ampm == "am" and h == 12:
                    h = 0
                if 0 <= h <= 23:
                    times.append((h, mins))
            except (ValueError, TypeError):
                continue

    if len(times) >= 2:
        return (times[0][0], times[0][1], times[1][0], times[1][1])
    elif len(times) == 1:
        # Default 1 hour duration
        eh = min(times[0][0] + 1, 23)
        return (times[0][0], times[0][1], eh, times[0][1])

    return None


def extract_links(text):
    """Extract URLs from text, especially booking/form links."""
    urls = re.findall(r"https?://[^\s\])<>\"]+", text)
    # Prioritize booking/form links
    booking = [u for u in urls if any(k in u.lower() for k in ["jotform", "forms", "book", "register", "sign-up", "signup", "ticket"])]
    return booking if booking else urls[:3]


def extract_venue(text):
    """Try to extract venue/location from text."""
    patterns = [
        r"(?:venue|location|place)[\s:]+([A-Z][^\.\n]{5,60})",
        r"(?:held|taking\s+place|meet)\s+(?:in|at)\s+(?:the\s+)?([A-Z][^\.\n,]{3,50})",
        r"(?:in|at)\s+the\s+([A-Z][^\.\n,]{3,50}(?:Hall|Gym|Room|Theatre|Court|Field|Centre|Church|Chapel|Studio|Pool))",
        r"(?:Old\s+Gym|Great\s+Hall|Sports\s+Hall|Main\s+Hall|School\s+Hall|Chapel|Dining\s+Hall|Library)",
    ]
    # Check for known venue names first
    known = re.search(r"(Old\s+Gym|Great\s+Hall|Sports\s+Hall|Main\s+Hall|School\s+Hall|Chapel|Dining\s+Hall|Newton\s+Road)", text, re.IGNORECASE)
    if known:
        return known.group(1).strip()

    for pat in patterns[:-1]:
        m = re.search(pat, text)
        if m:
            venue = m.group(1).strip()
            venue = re.sub(r"\s+", " ", venue)
            # Filter out false positives
            skip_words = ["end of", "start of", "beginning", "return", "drop off", "collection"]
            if any(s in venue.lower() for s in skip_words):
                continue
            if len(venue) > 5:
                return venue
    return ""


def extract_event_title(subject, body, school_tag):
    """Create a clean event title from subject/body."""
    # Clean subject line
    title = subject.strip()
    # Remove "New messages" generic subjects - extract real title from body
    if title.lower() in ("new messages", "new message", "new messages from school"):
        lines = [l.strip() for l in body.split("\n") if l.strip() and len(l.strip()) > 10]
        for line in lines[:15]:
            if any(re.search(pat, line.lower()) for pat in EVENT_KEYWORDS):
                title = re.sub(r"^\d+\.\s*", "", line)  # remove numbered prefix like "2. "
                title = title[:80]
                break
    # Remove "Fwd:" "Fw:" prefixes
    title = re.sub(r"^(?:fwd?|fw):\s*", "", title, flags=re.IGNORECASE)
    # Truncate if too long
    if len(title) > 80:
        title = title[:77] + "..."
    return f"{school_tag} {title}".strip()


def extract_events(subject, from_hdr, body, reference_year=None):
    """Extract calendar events from an email. Returns list of event dicts."""
    if reference_year is None:
        reference_year = datetime.now().year

    school_tag = identify_school(from_hdr, subject, body)

    # Check if should skip
    if should_skip(subject):
        return [], f"skip:subject_pattern ({subject[:50]})"

    # Check if actionable
    combined = f"{subject}\n{body}"
    if not is_actionable(subject, body):
        return [], f"skip:no_event_keywords ({subject[:50]})"

    # Parse date
    event_date, _ = parse_date(combined, reference_year)
    if not event_date:
        return [], f"skip:no_date_found ({subject[:50]})"

    # Skip past events (more than 2 days ago)
    if event_date < datetime.now().date() - timedelta(days=2):
        return [], f"skip:past_event ({subject[:50]}, date={event_date})"

    # Parse time
    time_info = parse_time(combined)

    # Extract details
    title = extract_event_title(subject, body, school_tag)
    venue = extract_venue(combined)
    links = extract_links(body)

    # Build description
    desc_parts = [f"Auto-added from school email.", f"Subject: {subject}"]
    if links:
        desc_parts.append(f"Links: {', '.join(links[:3])}")
    description = "\n".join(desc_parts)

    # Build event
    event = {"summary": title, "description": description, "location": venue}

    if time_info:
        sh, sm, eh, em = time_info
        start_dt = datetime(event_date.year, event_date.month, event_date.day, sh, sm)
        end_dt = datetime(event_date.year, event_date.month, event_date.day, eh, em)
        if end_dt <= start_dt:
            end_dt = start_dt + timedelta(hours=1)
        event["start"] = {"dateTime": start_dt.strftime("%Y-%m-%dT%H:%M:%S"), "timeZone": TZ}
        event["end"] = {"dateTime": end_dt.strftime("%Y-%m-%dT%H:%M:%S"), "timeZone": TZ}
    else:
        # All-day event
        event["start"] = {"date": str(event_date)}
        event["end"] = {"date": str(event_date + timedelta(days=1))}

    return [event], None


def upsert_event(cal, event, dry_run=False):
    """Check for duplicates, then insert. Returns True if added."""
    start = event["start"]
    date_str = start.get("dateTime", start.get("date", ""))[:10]
    summary = event["summary"]

    try:
        existing = (
            cal.events()
            .list(
                calendarId=FAMILY_CAL,
                timeMin=date_str + "T00:00:00Z",
                timeMax=date_str + "T23:59:59Z",
                q=summary[:30],  # partial match to catch similar
            )
            .execute()
            .get("items", [])
        )
        # Check for exact or very similar title match
        for ex in existing:
            ex_summary = ex.get("summary", "")
            if ex_summary.lower().strip() == summary.lower().strip():
                return False  # duplicate
    except Exception:
        pass

    if dry_run:
        return True

    try:
        cal.events().insert(calendarId=FAMILY_CAL, body=event).execute()
        return True
    except Exception as e:
        print(f"  Error inserting event: {e}", file=sys.stderr)
        return False


def main():
    parser = argparse.ArgumentParser(description="Scan school emails → Family Calendar")
    parser.add_argument("--days", type=int, default=3, help="How many days back to scan (default: 3)")
    parser.add_argument("--dry-run", action="store_true", help="Print what would be added, don't create events")
    parser.add_argument("--verbose", action="store_true", help="Show skip reasons")
    args = parser.parse_args()

    gmail = gmail_service()
    cal = None if args.dry_run else calendar_service()

    q = f"newer_than:{args.days}d (from:stfaith OR from:schoolpost OR from:theleys OR from:stfaiths.co.uk OR from:theleys.net OR from:schoolsbuddy)"
    try:
        msgs = gmail.users().messages().list(userId="me", q=q, maxResults=30).execute().get("messages", [])
    except Exception as e:
        print(json.dumps({"status": "error", "reason": f"Gmail fetch failed: {e}"}, ensure_ascii=False))
        sys.exit(1)

    added = []
    skipped = []

    for m in msgs:
        try:
            msg = gmail.users().messages().get(userId="me", id=m["id"], format="full").execute()
        except Exception:
            continue

        headers = {h["name"]: h["value"] for h in msg["payload"]["headers"]}
        subject = headers.get("Subject", "")
        from_hdr = headers.get("From", "")
        date_hdr = headers.get("Date", "")

        # Get reference year from email date
        yy = re.search(r"\b(20\d{2})\b", date_hdr)
        ref_year = int(yy.group(1)) if yy else datetime.now().year

        body = decode_text(msg["payload"])

        events, skip_reason = extract_events(subject, from_hdr, body, ref_year)

        if skip_reason:
            skipped.append(skip_reason)
            continue

        for ev in events:
            if args.dry_run:
                was_new = upsert_event(None, ev, dry_run=True)
                if was_new:
                    added.append({
                        "title": ev["summary"],
                        "start": ev["start"].get("dateTime", ev["start"].get("date")),
                        "end": ev["end"].get("dateTime", ev["end"].get("date")),
                        "location": ev.get("location", ""),
                        "dry_run": True,
                    })
            else:
                was_new = upsert_event(cal, ev, dry_run=False)
                if was_new:
                    added.append({
                        "title": ev["summary"],
                        "start": ev["start"].get("dateTime", ev["start"].get("date")),
                        "end": ev["end"].get("dateTime", ev["end"].get("date")),
                        "location": ev.get("location", ""),
                    })

    output = {
        "status": "ok",
        "dry_run": args.dry_run,
        "scanned": len(msgs),
        "added": added,
        "count_added": len(added),
    }
    if args.verbose:
        output["skipped"] = skipped
        output["count_skipped"] = len(skipped)

    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

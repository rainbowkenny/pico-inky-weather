#!/usr/bin/env python3
"""
Read a specific Gmail message by ID.

Usage:
    python3 read_message.py MESSAGE_ID
    python3 read_message.py MESSAGE_ID --format full
    python3 read_message.py MESSAGE_ID --format raw
"""

import argparse
import base64
import sys
from auth import get_gmail_service


def get_header(headers, name):
    """Extract a header value by name (case-insensitive)."""
    name_lower = name.lower()
    for h in headers:
        if h["name"].lower() == name_lower:
            return h["value"]
    return ""


def extract_body(payload):
    """Recursively extract plain text body from message payload."""
    if payload.get("mimeType") == "text/plain" and payload.get("body", {}).get("data"):
        return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="replace")

    parts = payload.get("parts", [])
    for part in parts:
        if part.get("mimeType") == "text/plain" and part.get("body", {}).get("data"):
            return base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="replace")

    # Recurse into multipart
    for part in parts:
        result = extract_body(part)
        if result:
            return result

    return None


def main():
    parser = argparse.ArgumentParser(description="Read a Gmail message by ID")
    parser.add_argument("message_id", help="Gmail message ID (from list_messages.py)")
    parser.add_argument(
        "--format", choices=["metadata", "full", "raw"], default="full",
        help="Response format (default: full)"
    )
    args = parser.parse_args()

    service = get_gmail_service()

    msg = (
        service.users()
        .messages()
        .get(userId="me", id=args.message_id, format=args.format)
        .execute()
    )

    if args.format == "raw":
        raw = msg.get("raw", "")
        decoded = base64.urlsafe_b64decode(raw).decode("utf-8", errors="replace")
        print(decoded)
        return

    headers = msg.get("payload", {}).get("headers", [])
    subject = get_header(headers, "Subject") or "(no subject)"
    sender = get_header(headers, "From")
    to = get_header(headers, "To")
    date = get_header(headers, "Date")
    labels = ", ".join(msg.get("labelIds", []))

    print(f"Subject: {subject}")
    print(f"From:    {sender}")
    print(f"To:      {to}")
    print(f"Date:    {date}")
    print(f"Labels:  {labels}")
    print(f"ID:      {args.message_id}")
    print("-" * 60)

    if args.format == "full":
        body = extract_body(msg.get("payload", {}))
        if body:
            print(body)
        else:
            print("(no plain text body found — message may be HTML-only)")
            # Try HTML fallback
            payload = msg.get("payload", {})
            for part in payload.get("parts", []):
                if part.get("mimeType") == "text/html" and part.get("body", {}).get("data"):
                    html = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="replace")
                    print("\n[HTML content — pipe through a converter or use --format raw]\n")
                    print(html[:2000])
                    break
    else:
        print(f"(metadata-only format — use --format full to see body)")


if __name__ == "__main__":
    main()

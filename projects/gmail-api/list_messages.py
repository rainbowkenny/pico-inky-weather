#!/usr/bin/env python3
"""
List recent Gmail messages with subject, from, and date.

Usage:
    python3 list_messages.py              # Last 20 messages
    python3 list_messages.py -n 10        # Last 10 messages
    python3 list_messages.py -q "from:someone@example.com"
    python3 list_messages.py -q "is:unread" -n 5
"""

import argparse
import sys
from auth import get_gmail_service


def get_header(headers, name):
    """Extract a header value by name (case-insensitive)."""
    name_lower = name.lower()
    for h in headers:
        if h["name"].lower() == name_lower:
            return h["value"]
    return ""


def main():
    parser = argparse.ArgumentParser(description="List recent Gmail messages")
    parser.add_argument(
        "-n", "--count", type=int, default=20, help="Number of messages (default: 20)"
    )
    parser.add_argument(
        "-q", "--query", type=str, default="", help="Gmail search query (e.g. 'is:unread')"
    )
    args = parser.parse_args()

    service = get_gmail_service()

    results = (
        service.users()
        .messages()
        .list(userId="me", maxResults=args.count, q=args.query)
        .execute()
    )

    messages = results.get("messages", [])
    if not messages:
        print("No messages found.")
        return

    print(f"{'ID':<20} {'Date':<28} {'From':<35} Subject")
    print("-" * 120)

    for msg_info in messages:
        msg = (
            service.users()
            .messages()
            .get(userId="me", id=msg_info["id"], format="metadata",
                 metadataHeaders=["Subject", "From", "Date"])
            .execute()
        )
        headers = msg.get("payload", {}).get("headers", [])
        subject = get_header(headers, "Subject") or "(no subject)"
        sender = get_header(headers, "From")
        date = get_header(headers, "Date")

        # Truncate long fields for display
        if len(sender) > 33:
            sender = sender[:30] + "..."
        if len(subject) > 60:
            subject = subject[:57] + "..."

        print(f"{msg_info['id']:<20} {date:<28} {sender:<35} {subject}")


if __name__ == "__main__":
    main()

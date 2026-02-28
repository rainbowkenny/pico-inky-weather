#!/usr/bin/env python3
"""
Send a plain-text email via Gmail API.

Usage:
    python3 send_email.py --to recipient@example.com --subject "Hello" --body "Message text"
    echo "Message from stdin" | python3 send_email.py --to recipient@example.com --subject "Hello"
"""

import argparse
import base64
import sys
from email.mime.text import MIMEText

from auth import get_gmail_service


def send_email(service, to, subject, body):
    """Build and send a plain-text email. Returns the sent message metadata."""
    message = MIMEText(body)
    message["to"] = to
    message["subject"] = subject

    raw = base64.urlsafe_b64encode(message.as_bytes()).decode("ascii")
    sent = (
        service.users()
        .messages()
        .send(userId="me", body={"raw": raw})
        .execute()
    )
    return sent


def main():
    parser = argparse.ArgumentParser(description="Send email via Gmail API")
    parser.add_argument("--to", required=True, help="Recipient email address")
    parser.add_argument("--subject", required=True, help="Email subject line")
    parser.add_argument(
        "--body", default=None,
        help="Email body text (reads from stdin if omitted)",
    )
    args = parser.parse_args()

    body = args.body
    if body is None:
        if sys.stdin.isatty():
            print("Enter message body (Ctrl-D to send):")
        body = sys.stdin.read()

    if not body.strip():
        print("ERROR: Empty message body.", file=sys.stderr)
        sys.exit(1)

    service = get_gmail_service()

    try:
        sent = send_email(service, args.to, args.subject, body)
    except Exception as e:
        print(f"ERROR: Failed to send email: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Sent. Message ID: {sent['id']}")


if __name__ == "__main__":
    main()

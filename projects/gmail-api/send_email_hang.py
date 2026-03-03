#!/usr/bin/env python3
"""Send plain-text email via Gmail API using hang.shuojin token.

Usage:
  python3 send_email_hang.py --to zisestar@gmail.com --subject "Subject" --body "Text"
  python3 send_email_hang.py --to zisestar@gmail.com --subject "Subject" --body-file /tmp/report.txt
"""
import argparse
import base64
import json
from email.mime.text import MIMEText
from pathlib import Path

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

TOKEN_FILE = Path('/home/albert/.openclaw/workspace/projects/gmail-api/token_hang.json')


def get_service():
    creds = Credentials.from_authorized_user_file(str(TOKEN_FILE))
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        TOKEN_FILE.write_text(creds.to_json())
    return build('gmail', 'v1', credentials=creds)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--to', required=True)
    p.add_argument('--subject', required=True)
    p.add_argument('--body')
    p.add_argument('--body-file')
    args = p.parse_args()

    body = args.body
    if args.body_file:
        body = Path(args.body_file).read_text()
    if not body:
        raise SystemExit('Missing --body or --body-file')

    msg = MIMEText(body)
    msg['to'] = args.to
    msg['subject'] = args.subject
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode('ascii')

    service = get_service()
    sent = service.users().messages().send(userId='me', body={'raw': raw}).execute()
    print(sent.get('id'))


if __name__ == '__main__':
    main()

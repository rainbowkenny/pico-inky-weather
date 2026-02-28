# Gmail API OAuth Helper (Read-Only)

Read-only Gmail API scripts using OAuth 2.0 for project `sylvan-storm-488713-f3`.

## Setup

### 1. Enable Gmail API

1. Go to [Google Cloud Console — API Library](https://console.cloud.google.com/apis/library?project=sylvan-storm-488713-f3)
2. Search for **Gmail API** and click on it
3. Click **Enable**

### 2. Create OAuth Client (Desktop)

1. Go to [Credentials](https://console.cloud.google.com/apis/credentials?project=sylvan-storm-488713-f3)
2. Click **+ CREATE CREDENTIALS** → **OAuth client ID**
3. If prompted, configure the OAuth consent screen first:
   - User Type: **External** (or Internal if using Workspace)
   - App name: `Gmail Reader`
   - Add your email as a test user
4. Application type: **Desktop app**
5. Name: `Gmail Reader Desktop`
6. Click **Create**
7. Click **DOWNLOAD JSON** and save to `/home/albert/.openclaw/workspace/credentials/google_credentials.json`

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Authorize

Run the OAuth flow to generate `token.json`:

```bash
python3 authorize.py
```

This prints an authorization URL. Open it in a browser, sign in, grant read-only access, then paste the authorization code back into the terminal. A `token.json` file is saved locally.

Use `--force` to re-authorize if needed.

### 5. Use

List the last 20 messages:

```bash
python3 list_messages.py
python3 list_messages.py -n 10
python3 list_messages.py -q "is:unread" -n 5
```

Read a specific message by ID:

```bash
python3 read_message.py MESSAGE_ID
python3 read_message.py MESSAGE_ID --format raw
```

## Files

| File | Purpose |
|---|---|
| `auth.py` | Shared auth helper — loads/refreshes credentials, builds Gmail service |
| `authorize.py` | Runs headless-friendly OAuth flow, produces `token.json` |
| `list_messages.py` | Lists recent messages (id, subject, from, date) |
| `read_message.py` | Prints headers + body/snippet for a given message ID |
| `requirements.txt` | Python dependencies |

## Credentials

- **`credentials/google_credentials.json`** — OAuth client secret (downloaded from GCP, do not commit)
- **`token.json`** — Generated access/refresh token (do not commit)

## Scope

Only `https://www.googleapis.com/auth/gmail.readonly` is requested. No send/delete access.

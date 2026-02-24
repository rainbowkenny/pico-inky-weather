---
name: quota
description: Run antigravity-usage CLI to report current Antigravity quota/usage. Use when the user asks for /quota, quota status, usage checks, or wants usage output (table or JSON) for one or multiple Google accounts/models.
---

# Quota

## Overview
Use the `antigravity-usage` CLI to fetch and display Antigravity quota/usage. Prefer the default command for a quick check; use flags for multi-account, full model lists, or JSON output.

## Quick command
- Standard check: `antigravity-usage` (alias for `quota`)

## Common options
- All accounts: `antigravity-usage --all`
- All models (including autocomplete): `antigravity-usage --all-models`
- JSON output (for scripts): `antigravity-usage --json`
- Force refresh (ignore cache): `antigravity-usage --refresh`

## Troubleshooting
- Auth status: `antigravity-usage status`
- Full diagnostics: `antigravity-usage doctor`
- If local IDE isn’t running, use `antigravity-usage login` then retry.

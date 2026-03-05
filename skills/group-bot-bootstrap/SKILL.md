---
name: group-bot-bootstrap
description: Create and wire a new Telegram group bot agent quickly in OpenClaw. Use when the user asks to create a dedicated bot/agent for a group, bind an agent to a Telegram group id, create an isolated workspace, set default model, and ensure the bot replies without requiring @ mentions.
---

Create a dedicated group agent with consistent routing.

## Runbook

1) Normalize inputs
- Agent id: lowercase-hyphen (e.g., `group-stocks`)
- Group id: Telegram group ids should be negative (e.g., `-5192025268`)
- Workspace: `/home/albert/.openclaw/workspace/<agent-id>`
- Model: default to `google-antigravity/gemini-3-flash` unless user asks otherwise

2) Create workspace scaffold
- Create workspace directory
- Copy baseline files if present: `AGENTS.md`, `SOUL.md`, `IDENTITY.md`, `USER.md`, `TOOLS.md`
- Create a minimal `SKILL_SUGGESTIONS.md` for the new agent

3) Create agent
- Command:
  - `openclaw agents add <agent-id> --workspace <workspace> --model <model> --non-interactive --json`

4) Bind group routing
- Add binding in `~/.openclaw/openclaw.json` under `bindings`:
  - `{"agentId":"<agent-id>","match":{"channel":"telegram","peer":{"kind":"group","id":"<group-id>"}}}`
- Ensure Telegram group config allows non-mention replies:
  - `channels.telegram.groups.<group-id>.requireMention = false`

5) Activate
- Restart gateway: `openclaw gateway restart`
- Verify:
  - `openclaw agents list --bindings`
  - `openclaw channels status --probe`
  - `openclaw sessions --all-agents --active 60 --json`

6) Smoke test and handoff
- Send a short proactive message to that group to confirm routing
- Ask user to send a plain message (no @)
- If no reply, check logs for `telegram-auto-reply ... reason=no-mention`

## Common fixes
- If bound id is positive, convert to negative and restart gateway.
- If group still routes to old session, ask user to send `/new` or `/reset` once in that group.
- If messages are skipped with `no-mention`, set `requireMention=false` for that group in config.

## Fast path command
Use the helper script:
- `bash scripts/create_group_bot.sh --agent-id <id> --group-id <gid> [--model <model>]`

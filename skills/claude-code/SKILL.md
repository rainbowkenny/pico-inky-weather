---
name: claude-code
description: |
  Use Claude Code CLI (claude) for coding tasks. This skill defines how to:
  - Execute coding tasks via `claude -p` (non-interactive, background)
  - Define and use custom agent teams via `--agents` / `--agent`
  - Run complex multi-step development workflows
  Use when: coding, scripting, building skills, creating scrapers, setting up integrations.
  Do NOT do inline coding in chat — always delegate to Claude Code CLI.
homepage: https://code.claude.com/docs
---

# Claude Code Integration

## ⚠️ Core Rule
**All coding tasks MUST be delegated to Claude Code CLI (`claude`), not done inline in chat.**
This keeps the conversation clean and leverages Claude Code's agent teams, tool access, and file management.

## CLI Location
- Path: `/home/albert/.local/bin/claude`
- Version: 2.1.61

## How to Execute Tasks

### Simple task (one-shot, background)
```bash
claude -p "task description" \
  --allowedTools "Bash Edit Read Write" \
  --print \
  2>&1 &
```

### Task with specific model
```bash
claude -p "task description" --model opus
```

### Task with custom working directory
```bash
claude -p "task description" --add-dir /path/to/project
```

## Agent Teams

### Define custom agents inline
```bash
claude -p "build the scraper" \
  --agents '{
    "scraper-dev": {
      "description": "Writes web scrapers in Python",
      "prompt": "You are a Python web scraping expert. Write clean, robust scrapers with error handling."
    },
    "tester": {
      "description": "Tests and validates code",
      "prompt": "You test code thoroughly. Run scripts, check output, fix bugs."
    }
  }' \
  --agent scraper-dev
```

### Built-in agents
- `Explore` (haiku) — quick exploration
- `general-purpose` (inherit) — default
- `Plan` (inherit) — planning mode
- `statusline-setup` (sonnet) — setup tasks

### List agents
```bash
claude agents
```

## Workflow Pattern (for OpenClaw)

When user requests a coding task:

1. **Plan first** — discuss with user, agree on approach
2. **Delegate** — run `claude -p` via `exec` tool in background
3. **Monitor** — use `process` tool to check progress
4. **Report** — summarize results back to user

### Example: Build a scraper
```bash
# Run in background
exec: claude -p "Create a Python script at /home/albert/.openclaw/workspace/skills/cc/scripts/scrape_events.py that scrapes Cambridge events from cambridgelive.org.uk. Output JSON with title, date, venue, price, url. Include error handling and --help flag." \
  --model opus \
  --allowedTools "Bash Edit Read Write" \
  --dangerously-skip-permissions \
  2>&1
```

### Example: Agent team for full feature
```bash
exec: claude -p "Build the weekend-planner BE tournament scraper" \
  --agents '{
    "dev": {"description": "Python developer", "prompt": "Write production Python scripts with argparse, error handling, JSON output."},
    "qa": {"description": "QA tester", "prompt": "Run scripts, validate output, fix issues."}
  }' \
  --agent dev \
  --model opus \
  --dangerously-skip-permissions \
  2>&1
```

## Key Flags
| Flag | Purpose |
|------|---------|
| `-p` / `--print` | Non-interactive, print output and exit |
| `--model <model>` | opus, sonnet, haiku |
| `--agent <name>` | Use specific agent |
| `--agents <json>` | Define custom agent team |
| `--allowedTools` | Restrict tool access |
| `--dangerously-skip-permissions` | Skip permission prompts (use in trusted env only) |
| `--add-dir <dir>` | Add directory access |
| `--max-budget-usd <n>` | Cost cap |
| `--effort <level>` | low/medium/high |

## Safety
- Always use `--max-budget-usd` for expensive tasks
- Use `--allowedTools` to restrict scope when appropriate
- Review output before deploying to production
- For config changes: use config-guard (arm → edit → disarm)

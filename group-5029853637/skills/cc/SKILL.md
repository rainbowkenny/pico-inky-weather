---
name: cc
description: Use the Claude Code CLI for agentic coding tasks — run commands, fix bugs, refactor, write tests, create PRs, and automate development workflows. Use when asked to run Claude Code, use `claude` CLI, do agentic coding, create CLAUDE.md files, configure Claude Code settings/permissions/hooks, or run programmatic/headless Claude Code tasks.
---

# Claude Code CLI

Claude Code is an agentic coding tool installed at `~/.local/bin/claude`. It reads codebases, edits files, runs commands, and works autonomously.

Docs: https://code.claude.com/docs/en/

## Quick Reference

### Interactive Session
```bash
cd /path/to/project
claude                          # start interactive session
claude "explain this project"   # with initial prompt
claude -c                       # continue most recent conversation
claude -r "session-name" "msg"  # resume by session ID/name
```

### Programmatic / Headless Mode (`-p`)
```bash
claude -p "query"                              # one-shot, print result, exit
claude -p "fix auth.py" --allowedTools "Read,Edit,Bash"
claude -p "summarize" --output-format json     # structured JSON output
claude -p "query" --output-format json --json-schema '{"type":"object",...}'
cat file | claude -p "explain"                 # pipe content
claude -p "continue" --continue                # continue last conversation
claude -p "query" --max-budget-usd 5.00        # cost cap
```

### Key Flags
| Flag | Purpose |
|------|---------|
| `--allowedTools "Bash,Read,Edit"` | Auto-approve specific tools |
| `--dangerously-skip-permissions` | Skip all permission prompts (use in containers only) |
| `--permission-mode plan` | Read-only Plan Mode |
| `--append-system-prompt "..."` | Add custom instructions |
| `--output-format json\|stream-json\|text` | Output format |
| `--add-dir ../other-project` | Add extra working directories |
| `--model sonnet` | Override model |
| `--max-turns N` | Limit agentic loop iterations |
| `--chrome` | Enable Chrome browser integration |

### Common Headless Patterns

**Auto-commit:**
```bash
claude -p "Look at staged changes and create a commit" \
  --allowedTools "Bash(git diff *),Bash(git log *),Bash(git status *),Bash(git commit *)"
```

**Code review pipeline:**
```bash
gh pr diff "$1" | claude -p \
  --append-system-prompt "Review for security vulnerabilities." \
  --output-format json
```

**Run tests and fix:**
```bash
claude -p "Run test suite and fix failures" --allowedTools "Bash,Read,Edit"
```

## CLAUDE.md Memory System

CLAUDE.md files provide persistent instructions loaded at session start.

| Location | Scope | Shared? |
|----------|-------|---------|
| `~/.claude/CLAUDE.md` | All projects (personal) | No |
| `./CLAUDE.md` or `./.claude/CLAUDE.md` | Project (team) | Yes (git) |
| `./.claude/rules/*.md` | Modular project rules | Yes (git) |
| `./CLAUDE.local.md` | Project (personal) | No (gitignored) |

Use `@path/to/file` imports inside CLAUDE.md to reference other files.

Keep CLAUDE.md concise — only include what Claude can't infer from code. Run `/init` to generate a starter file.

## Settings & Permissions

Settings files: `~/.claude/settings.json` (user), `.claude/settings.json` (project), `.claude/settings.local.json` (local).

```json
{
  "permissions": {
    "allow": ["Bash(npm run *)","Read"],
    "deny": ["Bash(curl *)","Read(./.env)"]
  }
}
```

Permission modes: `default`, `acceptEdits`, `plan`, `dontAsk`, `bypassPermissions`.

Rules evaluated: **deny → ask → allow** (first match wins).

Bash wildcards: `Bash(git commit *)` — space before `*` enforces word boundary.

## Hooks

Hooks run shell commands at lifecycle points. Configure in settings.json:

```json
{
  "hooks": {
    "PreToolUse": [{
      "matcher": "Bash",
      "hooks": [{"type": "command", "command": ".claude/hooks/validate.sh"}]
    }],
    "Stop": [{
      "hooks": [{"type": "command", "command": ".claude/hooks/on-complete.sh"}]
    }]
  }
}
```

Core events: `SessionStart`, `UserPromptSubmit`, `PreToolUse`, `PermissionRequest`, `PostToolUse`, `PostToolUseFailure`, `Notification`, `SubagentStart`, `SubagentStop`, `Stop`, `TaskCompleted`, `ConfigChange`, `PreCompact`, `SessionEnd`.

Hook scripts receive JSON on stdin and can return decisions (e.g., `permissionDecision: "deny"` for PreToolUse).

Useful patterns:
- Notification hooks: notify when Claude needs input.
- PostToolUse hooks: auto-format/lint changed files.
- PreToolUse hooks: block destructive commands or protected-file edits.
- SessionStart with `compact` matcher: re-inject critical context after compaction.

## Subagents

Use subagents for specialized tasks in a single main session. Each subagent has:
- Independent context window
- Custom system prompt
- Optional model override (e.g., sonnet/haiku)
- Tool restrictions and permission mode

Use when you want focused delegation and lower context pollution in the lead conversation.

### Subagent creation options
1. `/agents` interactive creation (recommended)
2. Markdown files in `.claude/agents/` (project) or `~/.claude/agents/` (user)
3. Ephemeral session-only JSON via `--agents`

Example file:
```markdown
---
name: code-reviewer
description: Review code quality and security, then return actionable findings.
tools: Read, Glob, Grep
model: sonnet
---

You are a strict reviewer. Prioritize correctness, security, and maintainability.
```

Example CLI JSON:
```bash
claude --agents '{
  "code-reviewer": {
    "description": "Review changed files for correctness/security",
    "prompt": "You are a senior code reviewer.",
    "tools": ["Read", "Glob", "Grep"],
    "model": "sonnet"
  }
}'
```

Built-ins include Explore (read-only, fast search), Plan (read-only planning support), and general-purpose.

## No-polling execution policy

When running Claude Code for long tasks, do not use tight polling loops to check progress.

Prefer this flow:
1. Start the Claude Code task once (`claude` or `claude -p ...`).
2. Use hooks to emit completion/failure notifications.
3. Send updates to a designated destination (for example, another Telegram group/channel).

Use the template in `references/async-notifications.md` for a hook-based notifier implementation.

## Agent Teams (experimental)

Use agent teams when multiple agents must coordinate directly (not only report back to one lead).

Enable first:
```json
{
  "env": {
    "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"
  }
}
```

Then ask naturally in session, e.g.:
```text
Create an agent team: one teammate analyzes backend architecture,
one reviews frontend UX impact, one challenges assumptions.
```

When to prefer teams vs subagents:
- Use **subagents** for focused, mostly independent tasks where only final result matters.
- Use **agent teams** for collaborative research, competing hypotheses, or cross-layer coordination with inter-agent discussion.

Display modes:
- `in-process` (single terminal, cycle teammates)
- split panes (`tmux`/iTerm2)

Session flag example:
```bash
claude --teammate-mode in-process
```

## Best Practices

1. **Provide verification** — include tests or expected outputs so Claude can self-check
2. **Explore → Plan → Implement → Commit** — use Plan Mode (Shift+Tab) for complex tasks
3. **Be specific** — reference files, include error messages, point to patterns
4. **Manage context** — context window fills fast; keep sessions focused
5. **Use `@file`** — reference files directly instead of describing locations
6. **Parallel sessions** — run multiple `claude` instances for independent tasks

## Troubleshooting & Gotchas

### 1. `claude: command not found` in cron / non-interactive shells
Claude Code installs to `~/.local/bin/claude`, which is often **not in cron's PATH**.

**Fix:** Always use the full path in scripts and cron jobs:
```bash
/home/albert/.local/bin/claude -p "your prompt"
```
Or export PATH at the top of your script:
```bash
export PATH="$HOME/.local/bin:$PATH"
```

### 2. Long tasks getting killed (SIGTERM) via OpenClaw exec
**Root cause:** OpenClaw's `exec` tool has an internal timeout. Claude Code agentic tasks often take 5+ minutes (especially on Raspberry Pi), so `exec` kills the process with SIGTERM before it finishes.

**Symptoms:** Process runs, uses memory (visible in `ps aux`), but produces zero output before being killed.

**Solution — use tmux/nohup instead of OpenClaw exec for long tasks:**

```bash
# Option A: tmux (RECOMMENDED — can reattach to see live output)
tmux new -d -s claude-task \
  '/home/albert/.local/bin/claude -p "your long task" \
   --allowedTools "Bash,Read,Edit,Write" \
   --max-turns 20 \
   2>&1 | tee ~/claude_task.log; echo "DONE" >> ~/claude_task.log'

# Check progress:
tmux attach -t claude-task      # live view (Ctrl-B D to detach)
tail -f ~/claude_task.log       # follow log from another shell

# Option B: nohup (simplest, fire-and-forget)
nohup /home/albert/.local/bin/claude -p "your task" \
  --allowedTools "Bash,Read,Edit,Write" \
  > ~/claude_task.log 2>&1 &
echo $!  # save PID

# Option C: cron (for scheduled tasks — cron has no OpenClaw timeout)
# Just put the command in crontab directly
```

**Additional safeguards for long tasks:**
- Use `--max-turns N` to limit agentic loops (e.g., `--max-turns 20`)
- Use `--max-budget-usd N` to cap API cost
- Break mega-prompts into smaller focused steps
- On low-RAM devices, avoid running multiple Claude Code instances simultaneously

**From OpenClaw agent, launch tmux like this:**
```bash
exec(command="tmux new -d -s my-task '...'")  # returns immediately, task runs in background
exec(command="tmux capture-pane -t my-task -p") # check output later
```

### 3. No output from `claude -p` (silent hang)
If `claude -p` starts but produces no output for a long time, check:
- **Auth:** Run `claude auth status` first to verify login
- **Network:** The Pi needs internet access to reach Anthropic's API
- **Memory:** On low-RAM devices, Claude Code's Node.js process (~350MB) may cause swapping

**Quick diagnostic:**
```bash
# Test auth and basic functionality
/home/albert/.local/bin/claude -p "say hello"
# Check process resource usage
ps aux | grep claude
```

### 4. Cron job disappearing after session reset
OpenClaw session resets (`/new`, `/reset`) don't affect crontab, but if a previous session added a cron entry and a later session removed it during cleanup, the job is gone.

**Fix:** Always verify cron entries after a reset:
```bash
crontab -l | grep -i "your-job-keyword"
```

## Auth & Updates
```bash
claude auth login           # sign in
claude auth status          # check auth
claude update               # update to latest
```

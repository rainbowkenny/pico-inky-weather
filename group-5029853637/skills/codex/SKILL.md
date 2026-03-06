---
name: codex
description: Use OpenAI Codex (CLI, IDE extension, cloud tasks, MCP, and SDK) for software engineering workflows. Use when asked to use Codex, `codex` CLI, Codex Cloud delegation, multi-agent workflows, approval/sandbox modes, MCP setup, or non-interactive `codex exec` automation.
---

# OpenAI Codex

Codex is OpenAI’s coding agent for reading, editing, running, and reviewing code.

Primary docs: https://developers.openai.com/codex/

## Install and start

```bash
npm i -g @openai/codex
codex
```

First run prompts sign-in (ChatGPT account or API key).

## Core operation modes

### Interactive TUI
```bash
codex
codex "Explain this codebase"
codex --model gpt-5.3-codex
```

Use for iterative coding with approvals, diff review, and in-session commands like `/review`, `/model`, `/permissions`.

### Non-interactive automation
```bash
codex exec "fix the CI failure"
codex exec resume --last "implement the plan"
```

Use for scripting and CI-style one-shot tasks.

### Resume context
```bash
codex resume
codex resume --last
codex resume --all
```

Codex keeps local transcripts and can continue prior runs with full context.

## Approvals and sandboxing

Pick approval mode based on risk:
- **Auto** (default): normal coding in project scope, prompts when needed.
- **Read-only**: analyze/plan without edits.
- **Full Access**: broad autonomy including network; use sparingly.

Always prefer least privilege first, then escalate.

## Multi-agent workflows (experimental)

Enable multi-agent in config or `/experimental`, then restart:

```toml
[features]
multi_agent = true
```

Use multi-agent when tasks parallelize well (review dimensions, exploration, independent modules).

Key role concepts:
- Built-ins: `default`, `worker`, `explorer`, `monitor`
- Custom roles: `[agents.<name>]` with `description` and optional `config_file`
- Useful role overrides: `model`, `model_reasoning_effort`, `sandbox_mode`, `developer_instructions`

Role example:
```toml
[agents.reviewer]
description = "Find security and correctness risks."
config_file = "agents/reviewer.toml"
```

## MCP integration

Configure MCP through CLI or `~/.codex/config.toml`:

```bash
codex mcp add context7 -- npx -y @upstash/context7-mcp
codex mcp --help
```

MCP supports:
- STDIO servers (local command)
- Streamable HTTP servers
- Bearer token and OAuth flows (`codex mcp login`)

Project-scoped config: `.codex/config.toml` (trusted projects).

## Codex Cloud tasks

Use cloud delegation for long/background work:

```bash
codex cloud
codex cloud exec --env ENV_ID "Summarize open bugs"
codex cloud exec --env ENV_ID --attempts 3 "Propose fixes"
```

Use when you want remote execution and PR-ready outputs while local terminal remains free.

## IDE extension

Codex extension works in VS Code and supported forks (Cursor/Windsurf).

Use IDE mode for:
- prompt with editor context
- model/reasoning switches
- approval mode control
- cloud delegation from editor

## SDK (TypeScript)

Use SDK for programmatic control in apps/CI:

```bash
npm install @openai/codex-sdk
```

```ts
import { Codex } from "@openai/codex-sdk";
const codex = new Codex();
const thread = codex.startThread();
const result = await thread.run("Diagnose CI failures and propose a plan");
```

Resume by thread ID when needed.

## No-polling dispatch policy

For long Codex runs, avoid tight polling loops. Prefer event-driven completion notifications.

- Launch work once (`codex exec ...` or `codex cloud exec ...`).
- Use hook-like/task-end notifications in orchestrator layer.
- Send completion/failure summary to the destination channel/group.

See `references/dispatch-patterns.md` for practical templates.

## Practical prompts

- "Analyze this repo and produce a safe implementation plan only."
- "Run local review for security, bugs, race conditions, and test flakiness."
- "Spawn one agent per review dimension and synthesize final findings."
- "Implement approved plan, run tests, and summarize residual risks."

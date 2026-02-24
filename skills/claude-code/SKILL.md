---
name: claude-code
description: Help users understand, install, and get started with Claude Code across Terminal CLI, VS Code/Cursor, desktop app, web, or JetBrains IDEs. Use when users ask how to set up Claude Code, which surface to use, or basic start commands/links from the official overview docs.
---

# Claude Code

## Overview
Use this skill to answer setup/get-started questions about Claude Code and guide users to the correct surface (Terminal CLI, VS Code/Cursor, Desktop app, Web, JetBrains).

## Quick start decision
1. Ask which surface they want (Terminal, VS Code/Cursor, Desktop, Web, JetBrains).
2. Provide the matching install/get-started steps.
3. If unsure, recommend Terminal CLI for full features or Web for zero setup.

## Terminal CLI (most full-featured)
- Install via the official script (macOS/Linux/WSL) or platform-specific installer.
- Then in any repo:
  - `cd your-project`
  - `claude`
- First run prompts for login.

## VS Code / Cursor
- Install the Claude Code extension.
- Open Command Palette and run **Claude Code: Open in New Tab**.

## Desktop app
- Download the OS-specific installer and sign in.
- Use the **Code** tab to start coding.

## Web
- Go to https://claude.ai/code
- Use for zero-setup sessions or when you don’t have the repo locally.

## JetBrains
- Install the Claude Code plugin from JetBrains Marketplace and restart the IDE.

## References
- Read `references/overview.md` for the official links and exact install commands from the overview page.

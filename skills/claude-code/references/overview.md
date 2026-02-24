# Claude Code Overview (from https://code.claude.com/docs/en/overview)

## What it is
- Agentic coding tool that reads codebases, edits files, runs commands, and integrates with dev tools.
- Available in terminal, IDE, desktop app, and browser.

## Terminal CLI install
**macOS/Linux/WSL**
```
curl -fsSL https://claude.ai/install.sh | bash
```
**Windows PowerShell**
```
irm https://claude.ai/install.ps1 | iex
```
**Windows CMD**
```
curl -fsSL https://claude.ai/install.cmd -o install.cmd && install.cmd && del install.cmd
```
- Windows requires Git for Windows.
- Start in any project:
```
cd your-project
claude
```
- First run prompts for login.

## VS Code / Cursor
- Install extension: `anthropic.claude-code`
- Open Command Palette → “Claude Code: Open in New Tab”.

## Desktop app
- Download: macOS / Windows (x64) / Windows ARM64.
- Sign in, open **Code** tab.

## Web
- https://claude.ai/code

## JetBrains
- Install Claude Code plugin from JetBrains Marketplace.

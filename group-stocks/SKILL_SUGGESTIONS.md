# Skill Suggestions for Stock Analysis Agent

## Core (copied)
- weekend-planner (adapt patterns for schedule/event conflict checks)
- claude-code (agentic coding workflows)

## Recommended to install/use
- qmd / qmd-skill: local markdown retrieval for research memory
- quota: check model quota before heavy cron runs
- codex or cc: delegated coding and scraper hardening
- weather: macro/weather shock context for commodities (optional)

## Workflow suggestion
1. Prewarm data sources (APIs first, browser fallback)
2. Fetch prices + news + macro
3. Risk summary (base/bull/bear)
4. Deliver short + full report versions
5. Log errors with classified labels (rate_limit/timeout/parse_failed)

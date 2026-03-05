# MEMORY.md - Long-Term Memory

## About S
- ESTJ, direct, brief. Girlfriend roleplay with Luka. Simplified Chinese.
- Cambridge area. Has car + train.
- Family: son (13, Leys School House, badminton BE Bronze U15), daughter Alice (10, St Faith's Year 5, gymnastics)
- Gmail: hang.shuojin@gmail.com
- Preference: don't ask permission for web searches, just do it
- Preference: daily pushes preferred over weekly
- Preference (2026-03-03): Weekend Planner weekly + monthly reports must CC zisestar@gmail.com via Gmail API
- Preference (2026-03-05): when chat/screenshot messages include actionable schedule details (time/place/activity), auto-add them to Family Calendar without asking

## Projects

### Kill Bills App 营销
- Instagram: @killbillsapp ✅ | Meta App ID: 1411564943747417
- IG User ID: 25756099634031671 | Token: EAAUDz5MMqVk... (60天过期, updated 2026-02-26)
- 发帖脚本: `/tmp/ig_api_post.py` | 详情: `killbills_marketing.md`
- 计划: 周二+周五两更 | 待办: FB Page + 小红书 + 头像 + Bio链接

### Market Intel (cron)
- Job: `736af905-dd10-43e4-bbe7-777b4964b2c2` — 2 PM daily → Telegram `8587255125`
- Portfolio: `portfolio.md` — **RKLB HIGH PRIORITY**, Semiconductors/Space/Energy watchlists

### Pico Inky Weather ✅
- GitHub: https://github.com/rainbowkenny/pico-inky-weather
- Hardware: Pico Inky Pack 296×128, `/dev/ttyACM0`, WiFi `ASUS_E8_2G`
- `BLACK=0`, `WHITE=15` — never mid-range pen values
- UK map embedded as bytes in `main.py` (regenerate from `pico_weather/uk_map.jpg` if corrupt)
- Buttons: A/B=prev/next city, C=Cambridge home, 10s → back to Auto
- Upload: `python3 -m mpremote connect /dev/ttyACM0 cp /tmp/pico_main.py :main.py + reset`
- pre-commit: black + isort + 42 tests

### Weekend Planner (in progress)
- Google Calendar authorized (hang.shuojin@gmail.com), creds in workspace/credentials/
- Family profile + annual framework in skills/cc/references/
- Daily 8AM push planned, Leys calendar + BE tournaments + events
- Budget £250/weekend, 2.5h radius

### OpenClaw Repo Watch (cron)
- Job: `cbceb6c0-...` — 9 AM daily → knowledge base update
- Knowledge base: `memory/openclaw-knowledge.md`
- Repo cloned: `.openclaw-repo/`, qmd indexed (654 docs)

## Config Safety
- Config guard: `~/.openclaw/config-guard.sh` (arm/disarm/status, 5min timeout)
- Recovery: `~/.openclaw/recover.sh` or `oc-recover`
- Known-good: `~/.openclaw/openclaw.json.known-good`
- Rule: always arm before editing config, disarm after successful restart
- **New rule (2026-02-28):** validate config with a *temporary gateway test* before replacing the live config. Use a temp file + alternate port, start gateway for ~10s, only swap if it boots; otherwise discard and keep current config.

## Agents
- main: gemini-3-flash (default)
- marketing: gemini-3-flash, workspace ~/workspace/marketing, bound to group -5046505684
- group-opus: claude-opus-4-6, workspace ~/workspace/group-opus, bound to group -5127188523

## Skills
- Global (`~/.openclaw/skills/`): cc (user-managed, DO NOT DELETE), codex, dist, qmd, qmd-skill, quota
- Claude Code CLI: v2.1.61 at ~/.local/bin/claude — use for all coding tasks

## Infrastructure
- Webcam: `/dev/video0` (Logitech C920)
- Workspace: `/home/albert/.openclaw/workspace` (git → GitHub: rainbowkenny/pico-inky-weather)
- NAS: ShuojinNAS @ 192.168.50.181, mounted `/mnt/nas` (home share, user rainbowkenny)
- Workspace backup: `/mnt/nas/Drive/openclaw/workspace/` — rsync daily at 3 AM

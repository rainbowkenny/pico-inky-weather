---
name: caijing-bloggers
description: Track and analyze finance YouTube creators with transcript-first workflows. Use when the user asks to monitor one or more 财经博主 channels, pull latest videos/subtitles, run LLM semantic extraction (buy/sell/watch/risk per stock with timestamps), generate daily briefs, or add/remove creators from the tracking list.
---

# 财经博主（Caijing Bloggers）

Use this skill to run a repeatable pipeline for finance creators:
1. Check tracked channels for new videos
2. Download/store full transcripts (with timestamps)
3. Run LLM semantic analysis
4. Output structured brief and post/schedule delivery

## Quick Workflow

1. Read `references/bloggers.md` to get the current tracked creators.
2. Confirm runtime settings (schedule/timezone/model) with user only when changed.
3. For each creator:
   - Fetch latest videos via yt-dlp (no API key needed)
   - Pull SRT subtitles with timestamps → persist raw, cleaned, and timestamped JSON
   - Feed `[MM:SS] text` formatted transcript to LLM (Claude sonnet by default)
   - LLM extracts structured JSON per `references/output-schema.md`
4. Produce one concise brief per run, grouped by signal type:
   - 📈 买入/看涨
   - ✋ 等待买点
   - 📦 持有
   - 🚫 别碰/回避
   - ⚠️ 风险
   - Format: `• TICKER [MM:SS](url) 简短摘要`
5. When posting to Telegram group, use the **分组列表格式** defined in `references/output-schema.md`（Markdown格式，不是HTML）
6. If requested, update cron or automation and verify by test run.

## Video Type Classification

Before formatting, classify each video into one of 3 types based on title + transcript content:

### 1. 个股分析 (Individual Stock Analysis)
- **Trigger**: title contains 个股/买卖点/股票名称, or transcript has 5+ stock mentions with action words
- **Format**: 分组信号表 (📈✋📦🚫⚠️)

### 2. 大盘/指数分析 (Market/Index Analysis)
- **Trigger**: title contains 指数/纳斯达克/大盘/美股分析预测/加密, or focuses on index levels/timing
- **Format**: 时间节奏表
  ```
  📺 **频道名称** — YYYY-MM-DD
  🎬 [视频标题](url)

  🗓 **大盘节奏**
  • 纳指反弹至3月25日 → 下砸至3月30日
  • 比特币关注4月1日能否守6万

  📈 **相关信号**（如有个股提及）
  • NVDA [00:04](url&t=4s) 盘后拉升验证买入

  ⚠️ **风险**
  • 风险1
  ```

### 3. 宏观/主题分析 (Macro/Thematic Analysis)
- **Trigger**: title contains 油价/黄金/加息/降息/美联储/通胀/CPI, or focuses on macro logic
- **Format**: 观点+结论
  ```
  📺 **频道名称** — YYYY-MM-DD
  🎬 [视频标题](url)

  💡 **核心观点**
  • 油价100-130安全区，160-180才危险
  • 当前实际利率+1.23%，加息空间极小

  📌 **结论**
  • 不必因油价恐慌做空股市
  • 参照2011年框架，股市估值逻辑未被破坏

  ⚠️ **风险**
  • 风险1
  ```

### Classification in LLM Prompt
When extracting, LLM must first classify video type and output `"video_type": "individual_stock" | "market_index" | "macro_theme"` in JSON. The posting agent then selects format accordingly.

## Telegram Posting Rules

**CRITICAL: Telegram has a 4096 character limit per message.**

**CRITICAL: Use Markdown (not raw HTML) for formatting.** OpenClaw auto-converts Markdown → Telegram HTML. Raw `<b>`, `<a>` tags will NOT render.

- **Split by channel**: each tracked channel = one separate Telegram message
- **Use 分组列表格式** — group signals by action type, not flat list:
  ```
  📺 **频道名称** — YYYY-MM-DD
  🎬 [视频标题](https://youtube.com/watch?v=ID)

  📈 **买入/看涨**
  • NVDA [04:38](https://youtube.com/watch?v=ID&t=278s) 证据摘要
  • TSM [07:44](https://youtube.com/watch?v=ID&t=464s) 证据摘要

  ✋ **等待买点**
  • ASML [03:08](https://youtube.com/watch?v=ID&t=188s) 快来了
  • GS [02:06](https://youtube.com/watch?v=ID&t=126s) 砸下去是机会

  📦 **持有**
  • AMD ORCL XOM 继续持有
  • AVGO [01:36](https://youtube.com/watch?v=ID&t=96s) 3月25号可以卖

  🚫 **别碰/回避**
  • TSLA [02:06](https://youtube.com/watch?v=ID&t=126s) 不跟纳指别碰
  • SMCI [06:44](https://youtube.com/watch?v=ID&t=404s) 没底不要抄底

  ⚠️ **风险**
  • 风险1
  • 风险2
  ```
- **Signal grouping categories**: 📈买入/看涨, ✋等待买点, 📦持有, 🚫别碰/回避, ⚠️风险
- **Format per signal**: `• TICKER [MM:SS](url) 简短摘要` — ticker在前，时间戳可点击跳转
- Same-group tickers with no special note can merge on one line: `• AMD ORCL XOM 继续持有`
- **Timestamp links**: `[MM:SS](https://youtube.com/watch?v=VIDEO_ID&t=SECONDs)` — Markdown link, clickable
- If a single channel's content still exceeds 4096 chars, split into multiple messages
- Multiple videos from same channel: merge signals, deduplicate by ticker
- A final summary with 综合风险 is optional if space allows

## Timestamp Links

Each stock signal includes a `[MM:SS]` clickable link that jumps to the exact video position:
- Format: `[MM:SS](https://youtube.com/watch?v=<id>&t=<seconds>s)`
- Extracted from SRT subtitle timestamps via 10-second sliding windows (for ~5s accuracy)
- Falls back to plain text if SRT unavailable

## Stock Signal Extraction Rules

- Extract **every** stock/ticker/index/crypto mentioned with ANY directional or evaluative commentary
- This includes: buy, sell, wait, avoid, "还要跌", "别碰", "快来了", "没走坏", "趋势不错", "抛压大", "没底", etc.
- Do NOT filter out "wait/observe" type mentions — these are valuable signals
- Each signal must have: **ticker + timestamp + evidence quote** from transcript
- Signal types (expanded): 买入/加仓/建仓/做多/卖出/减仓/止盈/止损/回避/观望/等待/看涨/看跌/风险/别碰
- **Ticker verification**: auto-generated subtitles often mangle stock names. Cross-reference context clues (sector, price level, prior mentions) to identify the correct ticker. If ambiguous, output best guess + mark `(?)` after ticker
- Evidence quotes must be grounded in actual transcript text
- If transcript quality is poor, explicitly mark low confidence
- **Every mentioned stock gets a line** — no filtering, no minimum threshold

## LLM Reliability

- LLM JSON extraction uses **retry with repair**: up to 2 attempts + 1 JSON repair pass
- If all attempts fail, a safe fallback is used (empty signals, manual review prompt)
- `youtube-transcript-api` is broken (attribute error); all transcripts fetched via **yt-dlp SRT fallback**

## Add or Remove Tracked Creators

When user asks to add/remove creators:
1. Edit `references/bloggers.md` only.
2. Keep each creator on one line with: display_name, handle/url, language, notes.
3. Keep newest/high-priority creators at top.
4. Before adding, verify transcript availability via yt-dlp test fetch.
5. Confirm changes in chat with a compact diff-style summary.

## Implementation

- Project dir: `/home/albert/.openclaw/workspace/projects/youtube-quant-daily/`
- Main script: `monitor.py` — reads bloggers from `references/bloggers.md`, loops all channels
- Per-channel state tracking: `state.json` uses `last_ts_@handle` keys
- Cron schedule:
  - `0 5 * * *` — `run_daily.sh` generates report (~10-15min)
  - `0 6 * * *` — `post_to_telegram.py` posts to Telegram group (split by channel, 分组格式)
- LLM: Claude CLI (`/home/albert/.local/bin/claude -p`), model via `LLM_MODEL` env (default: sonnet)
- Transcripts persisted to: `transcripts/<video_id>.txt`, `.cleaned.txt`, `.timestamped.json`
- Reports: `reports/YYYY-MM-DD.md` — grouped by channel (full markdown, used as source for Telegram summary)

## Tracked Channels (current)

1. **明日走势—美股量化交易** (`@mrzsquant`) — 量化/个股交易观点

## Known Issues

- `youtube-transcript-api` broken → all transcripts via yt-dlp fallback
- Some videos have no subtitles (e.g. short clips) → fallback empty report
- LLM occasionally returns invalid JSON → retry + repair mitigates ~95% of cases

## Resources

- Tracked creators list: `references/bloggers.md`
- Output contract + prompt shape: `references/output-schema.md`

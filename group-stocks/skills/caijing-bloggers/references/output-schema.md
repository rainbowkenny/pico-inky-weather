# LLM 输出结构（严格 JSON）

## 群推送格式（Telegram）

推送到群聊时，使用**分组列表格式**。**每个频道单独一条消息**（Telegram 4096字符限制）。

**⚠️ 必须使用 Markdown 格式（不是 raw HTML）。** OpenClaw 自动将 Markdown 转为 Telegram HTML。直接写 `<b>` `<a>` 标签不会渲染。

```
📺 **频道名称** — YYYY-MM-DD
🎬 [视频标题](https://youtube.com/watch?v=ID)

📈 **买入/看涨**
• NVDA [04:38](https://youtube.com/watch?v=ID&t=278s) 175买入已验证
• TSM [07:11](https://youtube.com/watch?v=ID&t=431s) 今天又来买多机会

✋ **等待买点**
• ASML [03:08](https://youtube.com/watch?v=ID&t=188s) 快来了
• GS [02:06](https://youtube.com/watch?v=ID&t=126s) 砸下去是机会
• V / AXP [02:06](https://youtube.com/watch?v=ID&t=126s) 还要等

📦 **持有**
• AVGO [01:36](https://youtube.com/watch?v=ID&t=96s) 3月25号可以卖
• AMD ORCL XOM AMAT 继续持有

🚫 **别碰/回避**
• TSLA [02:06](https://youtube.com/watch?v=ID&t=126s) 不跟纳指别碰
• SMCI [06:44](https://youtube.com/watch?v=ID&t=404s) 没底不要抄底

⚠️ **风险**
• 风险1
• 风险2
```

### 格式规则

- **按信号类型分组**：📈买入/看涨 → ✋等待买点 → 📦持有 → 🚫别碰/回避 → ⚠️风险
- 个股信号格式：`• TICKER [MM:SS](url) 简短摘要` — ticker在前，时间戳可点击
- 同组内无特别说明的ticker可合并一行：`• AMD ORCL XOM 继续持有`
- 时间戳用 Markdown 链接 `[MM:SS](url)`，点击直接跳转视频对应位置
- 每个频道独立一条 Telegram 消息，多视频合并信号去重
- 如果单个频道消息仍超4096字符，再拆分
- 风险提示最多3-4条

## LLM 提取 JSON 结构

```json
{
  "video_type": "individual_stock | market_index | macro_theme",
  "market_themes": ["string"],
  "trade_signals": ["string"],
  "market_rhythm": ["string — 大盘/指数时间节点，如'纳指反弹至3月25日'"],
  "core_thesis": ["string — 宏观核心观点/逻辑链"],
  "conclusion": ["string — 宏观结论/行动建议"],
  "stock_signals": [
    {
      "stock": "string",
      "signal": "买入|卖出|观望|风险|别碰|等待|持有|关注|看涨|看跌|回避",
      "confidence": 0.0,
      "timestamp": "MM:SS",
      "evidence": "string"
    }
  ],
  "risks": ["string"],
  "tonight_plan": ["string"]
}
```

## 约束

- `confidence` 范围 `0.0-1.0`
- `timestamp` 格式 `MM:SS`，来自字幕行前缀 `[MM:SS]`
- `evidence` 必须来自字幕原句（可轻度清洗，不可改写含义）
- `stock_signals` 提取视频中**所有**提到的标的，不限数量，不过滤
- 每条 stock_signal 必须满足：evidence 包含"标的名称/代号" + 任何评价性描述
- 信号类型（扩展）：买入/加仓/建仓/做多/卖出/减仓/止盈/止损/回避/观望/等待/看涨/看跌/风险/别碰/持有/关注
- "还要砸"、"别碰"、"快来了"、"没走坏"、"抛压大"、"趋势不错" 等非标准动作词也必须提取
- 仅纯粹列举无任何评价的提及才跳过（如"XX这个说过了"且无后续观点）
- **Ticker验证**：字幕自动生成常出错，必须根据上下文（板块、价格、前后提及）推断正确ticker。不确定时标注 `(?)`
- 同标的同信号去重，保留最高置信度
- 若信息不足，输出空数组，不要编造

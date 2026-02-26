# OpenClaw 知识库

## 最后更新
- 日期: 2026-02-26
- 当前版本: 2026.2.23
- 最新 release: 2026.2.26 (Feb 26, 2026)

## ⚠️ 配置安全规则
- **改配置前务必备份**: `cp ~/.openclaw/openclaw.json ~/.openclaw/openclaw.json.bak`
- **改完用 `node -e "JSON.parse(require('fs').readFileSync('$HOME/.openclaw/openclaw.json'))"` 验证 JSON 语法**
- 位置: `~/.openclaw/openclaw.json`

## 关键配置字段
- `agents.defaults.model.primary` — 默认模型
- `agents.defaults.models` — 模型目录 + params (cacheRetention, thinking 等)
- `agents.list` — 多 agent 列表，每个可有独立 workspace/model/params
- `channels.telegram` — botToken, groupPolicy (all/allowlist), allowFrom, streaming
- `gateway` — port, bind (loopback), auth (token)
- `hooks.internal.entries` — session-memory, boot-md, command-logger
- `commands` — native, nativeSkills, restart, config, debug
- `session.dmScope` — per-channel-peer

## 常见错误
- JSON 语法错误 → gateway 无法启动 → **永远先验证 JSON**
- 模型名拼错 → 静默回退到 fallback
- groupPolicy: "allowlist" 但忘记加 group ID → 群组无响应
- cacheRetention 需要每个模型单独设置，无全局开关

## 架构概览
- **Gateway**: 本地守护进程，处理路由/认证/调度
- **Agents**: 多 agent，每个有独立 workspace + agentDir
- **Sessions**: per-channel-peer 隔离
- **Skills**: SKILL.md 触发，nativeSkills 自动注册为 slash command
- **Cron**: 内置调度器 (`openclaw cron add/list/runs`)
- **Hooks**: session-memory, boot-md, command-logger
- **Bindings**: channel+peer → agent 路由

## 版本更新日志

### 2026.2.26 (最新)
**新功能/变更:**
- Heartbeat: `agents.defaults.heartbeat.directPolicy` 取代旧 DM toggle (allow|block)
- Agents/Config: 改配置前应调用 `config.schema`
- Android: 改进 streaming + markdown 渲染
- UI: 小屏 compose 按钮 stacked 布局
- Branding: bot.molt → ai.openclaw 全面替换

**⚠️ BREAKING:**
- Heartbeat DM 默认改回 `allow`。如需保持 2026.2.24 的 block 行为，设 `agents.defaults.heartbeat.directPolicy: "block"`

**修复:**
- Subagent 完成通知 dispatch 重构 (queue/direct/fallback 状态机)
- Telegram webhook 预初始化，防 hang/丢更新
- Slack session thread 防 oversized parent 继承导致 brick
- Cron message 多账号路由修复 (delivery.accountId)
- Gateway media roots: 非默认 agent workspace media 发送修复
- Followup routing: 同 channel fallback 允许，防 transient 失败丢消息
- Cron announce 去重

## 待关注
- Neutron rocket 中期目标配置参考
- 新 provider 支持变更
- config.schema 命令用法

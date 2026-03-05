#!/usr/bin/env bash
set -euo pipefail

MODEL="google-antigravity/gemini-3-flash"
AGENT_ID=""
GROUP_ID=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --agent-id) AGENT_ID="$2"; shift 2 ;;
    --group-id) GROUP_ID="$2"; shift 2 ;;
    --model) MODEL="$2"; shift 2 ;;
    *) echo "Unknown arg: $1"; exit 1 ;;
  esac
done

if [[ -z "$AGENT_ID" || -z "$GROUP_ID" ]]; then
  echo "Usage: $0 --agent-id <id> --group-id <telegram-group-id> [--model <model>]"
  exit 1
fi

if [[ "$GROUP_ID" != -* ]]; then
  GROUP_ID="-$GROUP_ID"
fi

WS="/home/albert/.openclaw/workspace/${AGENT_ID}"
CFG="/home/albert/.openclaw/openclaw.json"

mkdir -p "$WS"
for f in AGENTS.md SOUL.md IDENTITY.md USER.md TOOLS.md; do
  src="/home/albert/.openclaw/workspace/$f"
  [[ -f "$src" ]] && cp -f "$src" "$WS/"
done

if [[ ! -f "$WS/SKILL_SUGGESTIONS.md" ]]; then
  cat > "$WS/SKILL_SUGGESTIONS.md" <<EOF
# Skill Suggestions
- claude-code (coding workflows)
- codex (coding + automation)
- qmd (local markdown retrieval)
EOF
fi

openclaw agents add "$AGENT_ID" --workspace "$WS" --model "$MODEL" --non-interactive --json >/tmp/oc-agent-add.json || true

python3 - <<PY
import json
p="$CFG"
obj=json.load(open(p))
b=obj.setdefault("bindings",[])
want={"agentId":"$AGENT_ID","match":{"channel":"telegram","peer":{"kind":"group","id":"$GROUP_ID"}}}
if not any(x.get("agentId")=="$AGENT_ID" and x.get("match",{}).get("peer",{}).get("id")=="$GROUP_ID" for x in b):
    b.append(want)

tg=obj.setdefault("channels",{}).setdefault("telegram",{})
g=tg.setdefault("groups",{})
g.setdefault("$GROUP_ID",{})["requireMention"]=False

json.dump(obj,open(p,"w"),indent=2,ensure_ascii=False)
print("updated config")
PY

openclaw gateway restart || true

echo "Done: agent=$AGENT_ID group=$GROUP_ID model=$MODEL workspace=$WS"

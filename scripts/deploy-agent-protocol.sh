#!/usr/bin/env bash
# deploy-agent-protocol.sh — deploy generated protocol surfaces to user configs
#
# 1. Runs generate-agent-protocol.sh
# 2. Detects real config paths (not hardcoded)
# 3. Deploys Cursor .mdc, Codex AGENTS.md, Kiro steering file
# 4. Reports results and manual steps needed
#
# Run: bash scripts/deploy-agent-protocol.sh

set -euo pipefail
cd "$(git rev-parse --show-toplevel 2>/dev/null || echo "$(dirname "$0")/..")"

DEPLOY_REPORT=""
SKIPPED=""

# --- Step 1: Generate surfaces ---
echo "=== Generating per-surface slices ==="
bash scripts/generate-agent-protocol.sh
echo ""

# --- Step 2: Detect paths ---
HOME="${HOME:-/home/lauer}"

# Cursor rules dir
CURSOR_RULES=""
for candidate in "$HOME/.cursor/rules" "$HOME/.config/Cursor/rules" "$HOME/.config/cursor/rules"; do
  if [ -d "$candidate" ]; then
    CURSOR_RULES="$candidate"
    break
  fi
done

# Codex config dir
CODEX_DIR=""
for candidate in "$HOME/.codex" "$HOME/.config/codex"; do
  if [ -d "$candidate" ]; then
    CODEX_DIR="$candidate"
    break
  fi
done

# Kiro steering dir
KIRO_DIR=""
for candidate in "$HOME/.kiro/steering" "$HOME/.config/kiro/steering"; do
  if [ -d "$candidate" ]; then
    KIRO_DIR="$candidate"
    break
  fi
done

# Kiro settings dir (MCP)
KIRO_SETTINGS=""
if [ -d "$HOME/.kiro" ]; then
  KIRO_SETTINGS="$HOME/.kiro/settings"
elif [ -d "$HOME/.config/kiro" ]; then
  KIRO_SETTINGS="$HOME/.config/kiro/settings"
fi

echo "=== Deployment ==="

# --- Deploy Cursor .mdc ---
if [ -n "$CURSOR_RULES" ]; then
  # Migrate: remove stale convmem.md
  OLD_MD="$CURSOR_RULES/convmem.md"
  if [ -f "$OLD_MD" ]; then
    rm "$OLD_MD"
    echo "  [cleaned] Removed stale $OLD_MD"
    DEPLOY_REPORT+="  - Removed stale convmem.md from Cursor rules\n"
  fi

  # Deploy new .mdc
  cp config/cursor-rules-convmem.mdc.example "$CURSOR_RULES/convmem.mdc"
  echo "  [deploy] $CURSOR_RULES/convmem.mdc"
  DEPLOY_REPORT+="  - Deployed convmem.mdc to Cursor rules\n"
else
  echo "  [skip]   Cursor rules directory not found (probed: ~/.cursor/rules, ~/.config/Cursor/rules)"
  SKIPPED+="  - Cursor (no rules dir found)\n"
fi

# --- Deploy Codex AGENTS.md ---
if [ -n "$CODEX_DIR" ]; then
  cp config/codex-agents-convmem.example.md "$CODEX_DIR/AGENTS.md"
  echo "  [deploy] $CODEX_DIR/AGENTS.md"
  DEPLOY_REPORT+="  - Synced Codex AGENTS.md\n"
else
  echo "  [skip]   Codex config directory not found (probed: ~/.codex, ~/.config/codex)"
  SKIPPED+="  - Codex (no config dir found)\n"
fi

# --- Deploy Kiro steering file ---
if [ -n "$KIRO_DIR" ]; then
  cp config/kiro-steering-convmem.example.md "$KIRO_DIR/convmem.md"
  echo "  [deploy] $KIRO_DIR/convmem.md"
  DEPLOY_REPORT+="  - Synced Kiro steering file\n"
else
  echo "  [skip]   Kiro steering directory not found (probed: ~/.kiro/steering, ~/.config/kiro/steering)"
  SKIPPED+="  - Kiro (no steering dir found)\n"
fi

# --- Deploy Kiro MCP config ---
if [ -n "$KIRO_SETTINGS" ]; then
  mkdir -p "$KIRO_SETTINGS"
  KIRO_MCP="$KIRO_SETTINGS/mcp.json"
  if [ ! -f "$KIRO_MCP" ]; then
    cp config/kiro-mcp.json.example "$KIRO_MCP"
    echo "  [deploy] $KIRO_MCP (new)"
    DEPLOY_REPORT+="  - Deployed Kiro MCP config (new mcp.json)\n"
  else
    merge_result=$(python3 - <<'PY' "$KIRO_MCP" "$(pwd)/config/kiro-mcp.json.example"
import json, sys
dest, src = sys.argv[1], sys.argv[2]
with open(dest) as f:
    cfg = json.load(f)
with open(src) as f:
    ex = json.load(f)
servers = cfg.setdefault("mcpServers", {})
ex_convmem = ex["mcpServers"]["convmem"]
if "convmem" not in servers:
    servers["convmem"] = ex_convmem
    changed = "merged"
elif not servers["convmem"].get("autoApprove"):
    servers["convmem"]["autoApprove"] = ex_convmem.get("autoApprove", [])
    changed = "autoApprove"
else:
    changed = "skip"
if changed != "skip":
    with open(dest, "w") as f:
        json.dump(cfg, f, indent=2)
        f.write("\n")
print(changed)
PY
)
    case "$merge_result" in
      merged)
        echo "  [deploy] $KIRO_MCP (merged convmem block)"
        DEPLOY_REPORT+="  - Merged convmem into existing Kiro mcp.json\n"
        ;;
      autoApprove)
        echo "  [deploy] $KIRO_MCP (added autoApprove for convmem)"
        DEPLOY_REPORT+="  - Added Kiro convmem autoApprove\n"
        ;;
      skip)
        echo "  [skip]   $KIRO_MCP already has convmem"
        DEPLOY_REPORT+="  - Kiro mcp.json already has convmem\n"
        ;;
      *)
        echo "  [warn]   Could not merge Kiro mcp.json — copy config/kiro-mcp.json.example manually"
        SKIPPED+="  - Kiro MCP (merge failed)\n"
        ;;
    esac
  fi

  # --- Deploy Kiro permissions.yaml (IDE 1.0+ ACP; mcp.json autoApprove ignored) ---
  KIRO_PERMS="$KIRO_SETTINGS/permissions.yaml"
  merge_perms=$(python3 - <<'PY' "$KIRO_PERMS" "$(pwd)/config/kiro-permissions.yaml.example"
import sys, pathlib
import yaml

dest = pathlib.Path(sys.argv[1])
src = pathlib.Path(sys.argv[2])

def load_yaml(path):
    with open(path) as f:
        return yaml.safe_load(f) or {}

def shell_match_set(cfg):
    for rule in cfg.get("rules") or []:
        if rule.get("capability") == "shell":
            return set(rule.get("match") or [])
    return set()

def write_permissions(path, cfg):
    header = (
        "# convmem read-only ritual + MCP "
        "(deployed from convmem config/kiro-permissions.yaml.example)\n"
    )
    body = yaml.safe_dump(cfg, default_flow_style=False, sort_keys=False)
    path.write_text(header + body)
    # Immediate re-read verify (catches silent write failures)
    if shell_match_set(load_yaml(path)) != shell_match_set(cfg):
        raise RuntimeError(f"write verify failed: {path}")

incoming = load_yaml(src)
expected_shell = set(
    (next((r for r in incoming.get("rules") or [] if r.get("capability") == "shell"), {}) or {})
    .get("match")
    or []
)
incoming_shell_rule = next(
    (r for r in incoming.get("rules") or [] if r.get("capability") == "shell"),
    {"capability": "shell", "effect": "allow", "match": sorted(expected_shell)},
)
incoming_mcp_rule = next(
    (r for r in incoming.get("rules") or [] if r.get("capability") == "mcp"),
    {"capability": "mcp", "effect": "allow", "match": ["convmem/*"]},
)
marker = "convmem/*"
action = "skip"

if dest.exists():
    cfg = load_yaml(dest)
    rules = cfg.setdefault("rules", [])
    has_mcp = any(
        marker in (r.get("match") or [])
        for r in rules
        if r.get("capability") == "mcp"
    )
    if has_mcp:
        current = shell_match_set(cfg)
        if current >= expected_shell:
            action = "skip"
        else:
            shell_rule = next(
                (
                    r
                    for r in rules
                    if r.get("capability") == "shell"
                    and any("convmem" in (m or "") for m in (r.get("match") or []))
                ),
                None,
            )
            if shell_rule:
                shell_rule["match"] = list(incoming_shell_rule.get("match") or [])
            else:
                rules.insert(0, dict(incoming_shell_rule))
            write_permissions(dest, cfg)
            action = "upgrade"
    else:
        cfg = {"rules": [dict(incoming_shell_rule), dict(incoming_mcp_rule)]}
        write_permissions(dest, cfg)
        action = "deploy"
else:
    dest.parent.mkdir(parents=True, exist_ok=True)
    cfg = {"rules": [dict(incoming_shell_rule), dict(incoming_mcp_rule)]}
    write_permissions(dest, cfg)
    action = "deploy"

# Post-write verify — full replace if patterns still missing
final = load_yaml(dest)
if not expected_shell <= shell_match_set(final):
    cfg = {"rules": [dict(incoming_shell_rule), dict(incoming_mcp_rule)]}
    write_permissions(dest, cfg)
    final = load_yaml(dest)
    action = "upgrade" if action == "skip" else action

if not expected_shell <= shell_match_set(final):
    print("fail")
    sys.exit(1)

print(action)
PY
)
  case "$merge_perms" in
    deploy)
      echo "  [deploy] $KIRO_PERMS (convmem allow rules)"
      DEPLOY_REPORT+="  - Deployed Kiro permissions.yaml convmem rules\n"
      ;;
    upgrade)
      echo "  [deploy] $KIRO_PERMS (merged missing shell patterns)"
      DEPLOY_REPORT+="  - Upgraded Kiro permissions.yaml shell patterns\n"
      ;;
    skip)
      echo "  [skip]   $KIRO_PERMS already has convmem shell patterns"
      DEPLOY_REPORT+="  - Kiro permissions.yaml already has convmem\n"
      ;;
    fail)
      echo "  [warn]   Kiro permissions.yaml verify failed — copy config/kiro-permissions.yaml.example manually"
      SKIPPED+="  - Kiro permissions.yaml (verify failed)\n"
      ;;
    *)
      echo "  [warn]   Could not merge Kiro permissions.yaml — copy config/kiro-permissions.yaml.example manually"
      SKIPPED+="  - Kiro permissions.yaml (merge failed)\n"
      ;;
  esac
else
  echo "  [skip]   Kiro settings directory not found (probed: ~/.kiro/settings, ~/.config/kiro/settings)"
  SKIPPED+="  - Kiro MCP (no settings dir)\n"
fi

# --- Crush rules dir ---
CRUSH_RULES=""
for candidate in "$HOME/.config/crush/rules" "$HOME/.crush/rules"; do
  if [ -d "$candidate" ]; then
    CRUSH_RULES="$candidate"
    break
  fi
done

# --- Deploy Crush rules ---
if [ -n "$CRUSH_RULES" ]; then
  cp config/crush-rules-00-ritual.example.md "$CRUSH_RULES/00-convmem-ritual.md"
  cp config/crush-rules-convmem.example.md "$CRUSH_RULES/convmem.md"
  echo "  [deploy] $CRUSH_RULES/00-convmem-ritual.md"
  echo "  [deploy] $CRUSH_RULES/convmem.md"
  DEPLOY_REPORT+="  - Deployed Crush convmem rules (00-ritual + Tier A)\n"
else
  echo "  [skip]   Crush rules directory not found (probed: ~/.config/crush/rules, ~/.crush/rules)"
  SKIPPED+="  - Crush (no rules dir found)\n"
fi

# --- Deploy Crush global context (CONVMEM-RITUAL.md before CRUSH.md) ---
CRUSH_CONFIG_EARLY=""
for candidate in "$HOME/.config/crush/crush.json" "$HOME/.crush/crush.json"; do
  if [ -f "$candidate" ]; then
    CRUSH_CONFIG_EARLY="$candidate"
    break
  fi
done

if [ -n "$CRUSH_CONFIG_EARLY" ]; then
  CRUSH_DIR="$(dirname "$CRUSH_CONFIG_EARLY")"
  CRUSH_RITUAL_GLOBAL="$CRUSH_DIR/CONVMEM-RITUAL.md"
  cp config/crush-global-convmem-ritual.example.md "$CRUSH_RITUAL_GLOBAL"
  merge_ctx=$(python3 - <<'PY' "$CRUSH_CONFIG_EARLY"
import json, sys
from pathlib import Path

dest = Path(sys.argv[1])
marker = "~/.config/crush/CONVMEM-RITUAL.md"
with open(dest) as f:
    cfg = json.load(f)
opts = cfg.setdefault("options", {})
paths = list(opts.get("global_context_paths") or [])
if marker in paths:
    print("skip")
else:
    paths.insert(0, marker)
    opts["global_context_paths"] = paths
    with open(dest, "w") as f:
        json.dump(cfg, f, indent=2)
        f.write("\n")
    print("deploy")
PY
)
  case "$merge_ctx" in
    deploy)
      echo "  [deploy] $CRUSH_RITUAL_GLOBAL + crush.json global_context_paths (first)"
      DEPLOY_REPORT+="  - Crush CONVMEM-RITUAL.md prepended to global context\n"
      ;;
    skip)
      echo "  [skip]   crush.json already has CONVMEM-RITUAL.md in global_context_paths"
      DEPLOY_REPORT+="  - Crush global context already has CONVMEM-RITUAL\n"
      ;;
  esac
fi

# --- Deploy Crush permissions (allowed_tools + convmem bash hook) ---
CRUSH_CONFIG=""
for candidate in "$HOME/.config/crush/crush.json" "$HOME/.crush/crush.json"; do
  if [ -f "$candidate" ]; then
    CRUSH_CONFIG="$candidate"
    break
  fi
done

if [ -n "$CRUSH_CONFIG" ]; then
  CRUSH_HOOKS_DIR="$(dirname "$CRUSH_CONFIG")/hooks"
  CRUSH_HOOK="$CRUSH_HOOKS_DIR/convmem-allow.sh"
  mkdir -p "$CRUSH_HOOKS_DIR"
  cp scripts/crush-hook-convmem-allow.sh "$CRUSH_HOOK"
  chmod +x "$CRUSH_HOOK"
  merge_crush=$(python3 - <<'PY' "$CRUSH_CONFIG" "$(pwd)/config/crush-permissions.fragment.json" "$CRUSH_HOOK"
import json, sys
from pathlib import Path

dest = Path(sys.argv[1])
frag_path = Path(sys.argv[2])
hook_path = sys.argv[3]

with open(frag_path) as f:
    frag = json.load(f)
with open(dest) as f:
    cfg = json.load(f)

changed = False
perms = cfg.setdefault("permissions", {})
allowed = list(perms.get("allowed_tools") or [])
for tool in frag["permissions"]["allowed_tools"]:
    if tool not in allowed:
        allowed.append(tool)
        changed = True
if allowed != perms.get("allowed_tools"):
    perms["allowed_tools"] = allowed
    changed = True

hooks = cfg.setdefault("hooks", {})
pre = [h for h in (hooks.get("PreToolUse") or []) if h.get("command") != hook_path]
frag_hooks = []
for frag_entry in frag["hooks"]["PreToolUse"]:
    entry = frag_entry.copy()
    entry["command"] = hook_path
    frag_hooks.append(entry)
if pre + frag_hooks != list(hooks.get("PreToolUse") or []):
    hooks["PreToolUse"] = pre + frag_hooks
    changed = True

if changed:
    with open(dest, "w") as f:
        json.dump(cfg, f, indent=2)
        f.write("\n")
    print("deploy")
else:
    print("skip")
PY
)
  case "$merge_crush" in
    deploy)
      echo "  [deploy] $CRUSH_CONFIG (convmem permissions + bash hook)"
      echo "  [deploy] $CRUSH_HOOK"
      DEPLOY_REPORT+="  - Deployed Crush permissions (mcp_convmem_* + convmem bash hook)\n"
      ;;
    skip)
      echo "  [skip]   $CRUSH_CONFIG already has convmem permissions"
      DEPLOY_REPORT+="  - Crush permissions already present\n"
      ;;
    *)
      echo "  [warn]   Could not merge Crush permissions — edit crush.json manually"
      SKIPPED+="  - Crush permissions (merge failed)\n"
      ;;
  esac

  if [ -f "$CRUSH_HOOK" ] && command -v pgrep >/dev/null 2>&1; then
    crush_pid="$(pgrep -xo crush 2>/dev/null || true)"
    if [ -n "$crush_pid" ]; then
      hook_mtime="$(stat -c %Y "$CRUSH_HOOK" 2>/dev/null || echo 0)"
      crush_start="$(stat -c %Y "/proc/$crush_pid" 2>/dev/null || echo 0)"
      if [ "$hook_mtime" -gt "$crush_start" ]; then
        echo "  [warn]   Crush PID $crush_pid started before hook update — quit and restart Crush or deny hook will NOT run"
        DEPLOY_REPORT+="  - WARN: Crush running with stale hooks — restart required\n"
      fi
    fi
  fi
else
  echo "  [skip]   Crush crush.json not found (probed: ~/.config/crush/crush.json)"
  SKIPPED+="  - Crush permissions (no crush.json)\n"
fi

echo ""

if [ -x scripts/deploy-builder-reference.sh ]; then
  echo ""
  echo "=== Deploying builder reference ==="
  bash scripts/deploy-builder-reference.sh
fi

# --- Manual steps ---
echo "=== Manual steps ==="
echo ""
echo "1. Continue (~/.continue/config.yaml):"
echo "   Session-start lives in MCP instructions= only. rules: keeps named-tool + session-close."
echo "   Soak path: cn --auto --config ~/.continue/config.yaml (see docs/inter-model/CONTINUE-VERIFY.md)."
echo ""
echo "2. Kiro permissions (~/.kiro/settings/permissions.yaml):"
echo "   IDE 1.0+ ACP policy — allow convmem shell + mcp (convmem/*)."
echo "   mcp.json autoApprove is legacy; permissions.yaml is what vibe mode reads."
echo "   Restart Kiro after deploy if prompts persist."
echo ""
echo "3. Crush permissions (~/.config/crush/crush.json):"
echo "   permissions.allowed_tools: mcp_convmem_* read tools."
echo "   hooks/convmem-allow.sh: ritual deny + auto-approve read-only convmem bash."
echo "   After deploy: bash scripts/restart-crush-if-stale.sh (hooks load at Crush process start)."
echo ""
echo "4. ChatGPT webUI (optional — ignored if unused):"
echo "   Pack at docs/chatgpt-pack/custom-instructions.txt — paste into Custom instructions if needed."
echo ""
echo "=== Deploy report ==="
echo ""
echo "Deployed:"
echo -e "$DEPLOY_REPORT"
if [ -n "$SKIPPED" ]; then
  echo "Skipped:"
  echo -e "$SKIPPED"
fi
echo "Verify: open a non-convmem repo in Cursor — convmem.mdc should appear in always-applied rules."
echo "Verify: convmem doctor exit 0."
echo "Verify: MCP instructions reloaded (restart MCP server / Kiro / Cursor)."

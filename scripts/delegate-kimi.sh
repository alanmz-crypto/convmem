#!/usr/bin/env bash
# delegate-kimi.sh — headless Kimi (Moonshot) API delegation for any agent surface.
#
# Usage:
#   scripts/delegate-kimi.sh "Your prompt here"
#   scripts/delegate-kimi.sh /path/to/prompt.txt
#   echo "prompt" | scripts/delegate-kimi.sh -
#
# Environment:
#   TOKENROUTER_API_KEY    — required (or sourced from ~/.config/convmem/env.local
#                            or ~/.config/convmem/env.local.d/tokenrouter.env)
#   KIMI_MODEL             — model to use (default: moonshotai/kimi-k3-free)
#   KIMI_BASE_URL          — API base (default: https://api.tokenrouter.com/v1)
#   KIMI_SYSTEM_PROMPT     — override system message
#   KIMI_MAX_TOKENS        — max response tokens (default: 8192)
#   KIMI_TEMPERATURE       — sampling temperature (default: 0.2)
#
# Output: model response text on stdout; metadata on stderr.
# Exit codes: 0 = success, 1 = API error, 2 = usage/config error.

set -euo pipefail

MODEL="${KIMI_MODEL:-moonshotai/kimi-k3-free}"
BASE_URL="${KIMI_BASE_URL:-https://api.tokenrouter.com/v1}"
MAX_TOKENS="${KIMI_MAX_TOKENS:-8192}"
TEMPERATURE="${KIMI_TEMPERATURE:-0.2}"
SYSTEM_PROMPT="${KIMI_SYSTEM_PROMPT:-You are Kimi K3 (intensive code generation / implementation specialist). Be concrete, precise, and cite concrete failure modes when critiquing.}"

# --- Resolve API key ---
if [[ -z "${TOKENROUTER_API_KEY:-}" ]]; then
  for f in "${HOME}/.config/convmem/env.local" "${HOME}/.config/convmem/env.local.d/tokenrouter.env"; do
    if [[ -f "$f" && -z "${TOKENROUTER_API_KEY:-}" ]]; then
      # shellcheck disable=SC1090
      set -a && source "$f" && set +a
    fi
  done
fi
if [[ -z "${TOKENROUTER_API_KEY:-}" ]]; then
  echo "ERROR: TOKENROUTER_API_KEY not set and not found in ~/.config/convmem/env.local or env.local.d/tokenrouter.env" >&2
  exit 2
fi

# --- Resolve prompt ---
PROMPT=""
if [[ "${1:-}" == "-" ]]; then
  PROMPT="$(cat)"
elif [[ -n "${1:-}" && -f "${1}" ]]; then
  PROMPT="$(cat "$1")"
elif [[ -n "${1:-}" ]]; then
  PROMPT="$1"
else
  echo "usage: delegate-kimi.sh <prompt-string | /path/to/file | ->" >&2
  echo "" >&2
  echo "Environment variables:" >&2
  echo "  KIMI_MODEL            (default: moonshotai/kimi-k3-free)" >&2
  echo "  KIMI_SYSTEM_PROMPT    (override system message)" >&2
  echo "  KIMI_MAX_TOKENS       (default: 8192)" >&2
  echo "  KIMI_TEMPERATURE      (default: 0.2)" >&2
  exit 2
fi

# --- Call API ---
echo "== Kimi (TokenRouter) ${MODEL} ==" >&2

RESPONSE=$(python3 - <<'PY' "$MODEL" "$BASE_URL" "$MAX_TOKENS" "$TEMPERATURE" "$SYSTEM_PROMPT" "$PROMPT"
import json, os, sys, urllib.request

model = sys.argv[1]
base_url = sys.argv[2]
max_tokens = int(sys.argv[3])
temperature = float(sys.argv[4])
system_prompt = sys.argv[5]
user_prompt = sys.argv[6]

payload = {
    "model": model,
    "messages": [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ],
    "temperature": temperature,
    "max_tokens": max_tokens,
    "stream": False,
}

url = f"{base_url.rstrip('/')}/chat/completions"
req = urllib.request.Request(
    url,
    data=json.dumps(payload).encode(),
    headers={
        "Authorization": f"Bearer {os.environ['TOKENROUTER_API_KEY']}",
        "Content-Type": "application/json",
    },
    method="POST",
)

with urllib.request.urlopen(req, timeout=600) as resp:
    data = json.loads(resp.read().decode())

msg = (data.get("choices") or [{}])[0].get("message") or {}
content = (msg.get("content") or "").strip()
reasoning = (msg.get("reasoning_content") or "").strip()
final = content if content else reasoning

usage = data.get("usage") or {}
meta = {
    "model": data.get("model"),
    "usage": usage,
    "content_len": len(content),
    "reasoning_len": len(reasoning),
}
print(json.dumps(meta), file=sys.stderr, flush=True)

print(final)
PY
)

echo "$RESPONSE"

#!/usr/bin/env bash
# delegate-deepseek.sh — headless DeepSeek API delegation for any agent surface.
#
# Usage:
#   scripts/delegate-deepseek.sh "Your prompt here"
#   scripts/delegate-deepseek.sh /path/to/prompt.txt
#   echo "prompt" | scripts/delegate-deepseek.sh -
#
# Environment:
#   DEEPSEEK_API_KEY       — required (or sourced from ~/.config/convmem/env.local)
#   DEEPSEEK_MODEL         — model to use (default: deepseek-v4-pro)
#   DEEPSEEK_BASE_URL      — API base (default: https://api.deepseek.com)
#   DEEPSEEK_SYSTEM_PROMPT — override system message
#   DEEPSEEK_MAX_TOKENS    — max response tokens (default: 8192)
#   DEEPSEEK_TEMPERATURE   — sampling temperature (default: 0.2)
#
# Output: model response text on stdout; metadata on stderr.
# Exit codes: 0 = success, 1 = API error, 2 = usage/config error.

set -euo pipefail

MODEL="${DEEPSEEK_MODEL:-deepseek-v4-pro}"
BASE_URL="${DEEPSEEK_BASE_URL:-https://api.deepseek.com}"
MAX_TOKENS="${DEEPSEEK_MAX_TOKENS:-8192}"
TEMPERATURE="${DEEPSEEK_TEMPERATURE:-0.2}"
SYSTEM_PROMPT="${DEEPSEEK_SYSTEM_PROMPT:-You are DeepSeek V4 Pro (adversarial architecture critique). Challenge assumptions, identify risks, and propose alternatives. Be specific and cite concrete failure modes.}"

# --- Resolve API key ---
if [[ -z "${DEEPSEEK_API_KEY:-}" && -f "${HOME}/.config/convmem/env.local" ]]; then
  # shellcheck disable=SC1091
  set -a && source "${HOME}/.config/convmem/env.local" && set +a
fi
if [[ -z "${DEEPSEEK_API_KEY:-}" ]]; then
  echo "ERROR: DEEPSEEK_API_KEY not set and not found in ~/.config/convmem/env.local" >&2
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
  echo "usage: delegate-deepseek.sh <prompt-string | /path/to/file | ->" >&2
  echo "" >&2
  echo "Environment variables:" >&2
  echo "  DEEPSEEK_MODEL          (default: deepseek-v4-pro)" >&2
  echo "  DEEPSEEK_SYSTEM_PROMPT  (override system message)" >&2
  echo "  DEEPSEEK_MAX_TOKENS     (default: 8192)" >&2
  echo "  DEEPSEEK_TEMPERATURE    (default: 0.2)" >&2
  exit 2
fi

# --- Call API ---
echo "== DeepSeek API ${MODEL} ==" >&2

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

# V4 Pro and reasoning models support thinking knobs
if "v4-pro" in model or "reasoner" in model or "r1" in model.lower():
    payload["thinking"] = {"type": "enabled"}
    payload["reasoning_effort"] = "high"

url = f"{base_url.rstrip('/')}/v1/chat/completions"
req = urllib.request.Request(
    url,
    data=json.dumps(payload).encode(),
    headers={
        "Authorization": f"Bearer {os.environ['DEEPSEEK_API_KEY']}",
        "Content-Type": "application/json",
    },
    method="POST",
)

try:
    with urllib.request.urlopen(req, timeout=600) as resp:
        data = json.loads(resp.read().decode())
except urllib.error.HTTPError as e:
    # Retry without thinking knobs if rejected (older model endpoint)
    if e.code in (400, 422):
        payload.pop("thinking", None)
        payload.pop("reasoning_effort", None)
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode(),
            headers={
                "Authorization": f"Bearer {os.environ['DEEPSEEK_API_KEY']}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=600) as resp:
            data = json.loads(resp.read().decode())
    else:
        raise

msg = (data.get("choices") or [{}])[0].get("message") or {}
content = (msg.get("content") or "").strip()
reasoning = (msg.get("reasoning_content") or "").strip()
final = content if content else reasoning

# Metadata to stderr
usage = data.get("usage") or {}
meta = {
    "model": data.get("model"),
    "usage": usage,
    "content_len": len(content),
    "reasoning_len": len(reasoning),
}
print(json.dumps(meta), file=sys.stderr, flush=True)

# Response to stdout
print(final)
PY
)

echo "$RESPONSE"

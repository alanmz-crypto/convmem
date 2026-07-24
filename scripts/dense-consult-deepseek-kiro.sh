#!/usr/bin/env bash
# Dense owner-decision consult: DeepSeek API deepseek-v4-pro + Kiro CLI.
# Usage: scripts/dense-consult-deepseek-kiro.sh /path/to/brief.txt [outdir]
# Requires: DEEPSEEK_API_KEY (env or ~/.config/convmem/env.local), kiro-cli, curl/python3.
set -euo pipefail

BRIEF="${1:-}"
OUTDIR="${2:-/tmp/dense-consult-$(date +%Y%m%d-%H%M%S)}"
MODEL="${DENSE_CONSULT_DEEPSEEK_MODEL:-deepseek-v4-pro}"
BASE_URL="${DENSE_CONSULT_DEEPSEEK_BASE:-https://api.deepseek.com}"

if [[ -z "$BRIEF" || ! -f "$BRIEF" ]]; then
  echo "usage: $0 /path/to/brief.txt [outdir]" >&2
  exit 2
fi

if [[ -z "${DEEPSEEK_API_KEY:-}" && -f "${HOME}/.config/convmem/env.local" ]]; then
  # shellcheck disable=SC1091
  set -a && source "${HOME}/.config/convmem/env.local" && set +a
fi
if [[ -z "${DEEPSEEK_API_KEY:-}" ]]; then
  echo "DEEPSEEK_API_KEY not set" >&2
  exit 2
fi
if ! command -v kiro-cli >/dev/null 2>&1; then
  echo "kiro-cli not found" >&2
  exit 2
fi

mkdir -p "$OUTDIR"
cp "$BRIEF" "$OUTDIR/brief.txt"

echo "== DeepSeek API ${MODEL} ==" >&2
python3 - "$OUTDIR" "$MODEL" "$BASE_URL" <<'PY'
import json, os, sys, urllib.request
from pathlib import Path

outdir, model, base = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
prompt = (outdir / "brief.txt").read_text()
payload = {
    "model": model,
    "messages": [
        {
            "role": "system",
            "content": (
                "Dense owner-decision consult. Pick decisively among the options "
                "in the brief. Follow any required output format. Non-implementing."
            ),
        },
        {"role": "user", "content": prompt},
    ],
    "temperature": 0.2,
    "max_tokens": 8192,
    "stream": False,
    "thinking": {"type": "enabled"},
    "reasoning_effort": "high",
}
req = urllib.request.Request(
    f"{base.rstrip('/')}/v1/chat/completions",
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
except Exception:
    # Retry without thinking knobs if rejected
    payload.pop("thinking", None)
    payload.pop("reasoning_effort", None)
    req = urllib.request.Request(
        f"{base.rstrip('/')}/v1/chat/completions",
        data=json.dumps(payload).encode(),
        headers={
            "Authorization": f"Bearer {os.environ['DEEPSEEK_API_KEY']}",
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
(outdir / "deepseek-v4-pro.md").write_text(final + "\n")
(outdir / "deepseek-meta.json").write_text(
    json.dumps(
        {
            "model": data.get("model"),
            "usage": data.get("usage"),
            "content_len": len(content),
            "reasoning_len": len(reasoning),
        },
        indent=2,
    )
    + "\n"
)
print(f"wrote {outdir / 'deepseek-v4-pro.md'} ({len(final)} chars)", flush=True)
PY

echo "== Kiro CLI ==" >&2
KIRO_BRIEF="$OUTDIR/kiro-brief.txt"
{
  cat <<'PRE'
You are Kiro (design review / sign-off). Non-implementing: no edits, commits, or PRs.
Give an independent recommendation on the fork in the brief. You may agree or dissent
with any prior model. Follow the required output format in the brief.
---
PRE
  cat "$OUTDIR/brief.txt"
} > "$KIRO_BRIEF"

kiro-cli chat --no-interactive --effort high \
  --trust-tools=fs_read,execute_bash,read_file,list_directory,grep,file_search \
  --model auto \
  "$(cat "$KIRO_BRIEF")" \
  > "$OUTDIR/kiro.md" 2>"$OUTDIR/kiro.stderr" || {
  echo "kiro-cli failed; see $OUTDIR/kiro.stderr" >&2
  exit 4
}

# Strip common ANSI for readability
python3 - "$OUTDIR/kiro.md" <<'PY'
import re, sys
from pathlib import Path
p = Path(sys.argv[1])
text = p.read_text(errors="replace")
clean = re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", text)
clean = re.sub(r"\x1b\[\?[0-9;]*[A-Za-z]", "", clean)
p.with_name("kiro.clean.md").write_text(clean)
print(f"wrote {p.with_name('kiro.clean.md')}", flush=True)
PY

cat > "$OUTDIR/COMPARISON.md" <<EOF
# Dense consult comparison

| Advisor | Artifact |
|---|---|
| DeepSeek API \`${MODEL}\` | \`deepseek-v4-pro.md\` |
| Kiro CLI | \`kiro.clean.md\` (raw: \`kiro.md\`) |

**Next:** Ryan locks a recommendation. Advisors do not authorize merge, Execute, or live ops.
EOF

echo "Dense consult complete: $OUTDIR" >&2
echo "$OUTDIR"

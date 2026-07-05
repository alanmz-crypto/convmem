# Cross-project digest — attempts.jsonl

Append-only log of failed or partial fix attempts. The digest reads this file and renders
`## Do not retry` when rows with `outcome` of `failed` or `partial` exist.

**Path:** `~/.local/share/convmem/attempts.jsonl` (Tier 1 — not in Git; backup with corpus)

**Example:** [`config/attempts.jsonl.example`](../../config/attempts.jsonl.example)

---

## Schema (one JSON object per line)

| Field | Required | Description |
|-------|----------|-------------|
| `obs_id` | yes | Related observation ledger id (`obs_*`) |
| `outcome` | yes | `failed` or `partial` (only these appear in digest) |
| `path` | yes | File or path scoped for precheck (e.g. `cross_project_digest.py`) |
| `summary` | yes | Short human-readable reason |
| `timestamp` | yes | ISO UTC (`YYYY-MM-DDTHH:MM:SSZ`) |

```json
{"obs_id":"obs_abc123","outcome":"failed","path":"cross_project_digest.py","summary":"Digest --propose timed out during ask()","timestamp":"2026-07-05T12:00:00Z"}
```

Append only — do not edit or truncate in place. Wipe only via deliberate corpus maintenance.

---

## Setup

```bash
cp ~/Projects/convmem/config/attempts.jsonl.example ~/.local/share/convmem/attempts.jsonl
# Edit rows with real obs_id and summaries
```

---

## Digest integration

`cross_project_digest.py` loads the tail of `attempts.jsonl` on every run (including `--skip-ask`).

```bash
~/Projects/convmem/scripts/cross-project-digest.sh --skip-ask
```

Sections rendered (deterministic path):

- Recent approved decisions (`decisions-approved.jsonl`)
- Link queue (`link_queue.jsonl`)
- Open coordination observations (Chroma)
- **Do not retry** (from `attempts.jsonl`)

With LLM: adds Synthesis + Recency check.

---

## Advisory precheck

Before editing a file that failed before:

```bash
bash ~/Projects/convmem/scripts/precheck-path.sh cross_project_digest.py
```

Always exits 0; prints WARN when the path matches a failed/partial row.

---

## Smoke

```bash
bash ~/Projects/convmem/scripts/smoke-cross-project-digest.sh
```

---

## Related (not the same file)

| File | Purpose |
|------|---------|
| `synthesis_failures.jsonl` | Automatic telemetry from `ask()` failures (doctor P1c gate) |
| `attempts.jsonl` | Curated do-not-retry log for digest + precheck (manual append) |

Lab track that validated this pattern: `~/Projects/convmem-lab` — `smoke-synthesis.sh`.

Pilot log: [`docs/inter-model/CROSS-PROJECT-DIGEST-PILOT.md`](inter-model/CROSS-PROJECT-DIGEST-PILOT.md)

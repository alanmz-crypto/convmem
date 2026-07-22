# Execution Plan — Semantic dedupe / queue hygiene

```text
Planning Status

Phase:        EXECUTION plan ready (Ryan GATE before live mutation)
Characters:   Cursor (plan + implement code) → Ryan (config + approve) → Kiro (optional batch review)
Lanes:        Cursor implements; Ryan owns live config and --approve-dedupe; no ranking PRs
Authority:    ARCHITECTURE-semantic-dedupe-hygiene.md + this plan
Repo path:    docs/plans/EXECUTION-2026-07-22-semantic-dedupe-hygiene.md
Handoff:      docs/inter-model/CURSOR-2026-07-22-semantic-dedupe-hygiene.md
```

## Problem

`dedupe_queue.jsonl` has **~1157 pending** pairs while refine's `semantic_dedupe`
job only **pauses**. Ingest (`source: ingest`) still appends. LATEST still says
the job should be out of daemon jobs. Blind drain is unsafe; ignoring the queue
lets duplicate mass keep growing.

## Snapshot (2026-07-22 — re-measure at execute)

```bash
python3 - <<'PY'
import json
from collections import Counter
from pathlib import Path
p = Path.home() / ".local/share/convmem/dedupe_queue.jsonl"
st = Counter(); bands = Counter(); exact = 0
for line in p.open():
    r = json.loads(line)
    st[r.get("status") or "?"] += 1
    if r.get("status") != "pending":
        continue
    s = float(r.get("similarity") or 0)
    if s >= 0.999: bands["1.000"] += 1
    elif s >= 0.98: bands["0.98-0.999"] += 1
    elif s >= 0.95: bands["0.95-0.98"] += 1
    elif s >= 0.92: bands["0.92-0.95"] += 1
    else: bands["<0.92"] += 1
    if (r.get("title_a") or "").strip() == (r.get("title_b") or "").strip():
        exact += 1
print("status", dict(st))
print("pending_bands", dict(bands))
print("exact_title", exact)
PY
rg -n 'jobs|queue_max_depth|dedupe_similarity' ~/.config/convmem/config.toml
```

Baseline observed: pending ≈1157; bands ≈143 / 57 / 240 / 717; exact titles ≈194;
live jobs still list `semantic_dedupe`; `queue_max_depth = 200`.

## Phases

### Phase A — Stop the bleed (code + Ryan config)

| Step | Owner | Action |
|------|-------|--------|
| A1 | Cursor | PR: ingest semantic append respects `[refine] queue_max_depth` (same pause semantics as `job_semantic_dedupe`). Prefer shared helper in `refine.py` or thin import from `ingest_dedupe` — **no new leaf module** if pylint R0401 risk. |
| A2 | Cursor | PR: `config.example.toml` comment that `semantic_dedupe` in jobs is optional and should be omitted while backlog ≥ depth; document ingest pause. |
| A3 | Ryan | Live `~/.config/convmem/config.toml`: remove `semantic_dedupe` from `[refine] jobs` (restore F1 policy). Restart refine if needed. |
| A4 | Cursor | Optional doctor hint or standing-check note when pending ≫ `queue_max_depth` — only if cheap; not required for A merge. |

**Do not** approve queue rows in Phase A.

### Phase B — Classify (read-only)

| Step | Owner | Action |
|------|-------|--------|
| B1 | Cursor | Script or one-shot report: pending by band, `source` (ingest vs missing), exact-title count, sample 10 rows per band to `/tmp/dedupe-hygiene-report.txt`. |
| B2 | Ryan/Kiro | Pick first apply band (default: exact title @ ≥0.999). |

### Phase C — Banded apply (Ryan-gated)

| Step | Owner | Action |
|------|-------|--------|
| C1 | Reviewer | Mark queue rows `approved_merge_*` or `rejected_keep_both` for a **≤50** line sample (or use existing status fields + `--approve-dedupe <line>`). |
| C2 | Ryan | `convmem refine --approve-dedupe <lines|all-for-marked>` — confirm undo path under `refine_undo/semantic_dedupe/`. |
| C3 | Cursor | Re-count pending; expand band only with Ryan go. |
| C4 | All | Stop if false-merge found; widen sample before next batch. |

Default order: **(1)** sim ≥0.999 + identical titles → **(2)** sim ≥0.98 → **(3)** 0.95–0.98 with human skim → **(4)** 0.92–0.95 last / leave pending with plan.

### Phase D — Snapshot steering (optional, separate GATE)

Exclude or supersede units whose `source_path` matches
`.kiro/sessions/**/snapshots/**/.kiro/steering/` when a GitClones (or non-snapshot)
canonical exists. **Not authorized** by Phases A–C alone.

## Non-goals (repeat)

No ranking / trust / diversification / rerank changes. No `forget` bulk. No
full reindex. No evidence-inject.

## Done when

- A1–A3 merged/applied; ingest no longer grows queue past depth while paused.
- At least band (1) reviewed and applied or explicitly rejected with rationale.
- Pending count recorded before/after; LATEST updated; VERIFY filled.
- Phase D filed as follow-up or explicitly deferred.

## Relates

- F1 close: `dec_prop_20260701_211650_5a62` (prior drain)
- who-fixes cargo: `docs/inter-model/CURSOR-2026-07-22-who-fixes-retrieval-closed-to-p13.md`
- P1.3 soak residual: snapshot steering crowding (Phase D)

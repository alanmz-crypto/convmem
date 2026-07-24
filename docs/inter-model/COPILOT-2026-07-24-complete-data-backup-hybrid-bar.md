# GitHub Copilot audit — complete-data backup under **Hybrid** consistency bar

**Locked by Ryan:** 2026-07-24 — Track 1 consistency bar = **Hybrid**  
**Advisors (recommend only; Ryan locked):** DeepSeek API `deepseek-v4-pro` (Hybrid, ~85); Kiro CLI (Hybrid, ~78)  
**Audit lane:** GitHub Copilot audit lane — independent safety/isolation; no implementation  
**Exact artifact:** `492e6e7eacef6cfd64dfc5bb00b25296b5e29288`  
**Branch tip carrying impl (do not audit by mutable name alone):** `fix/2026-07-23-complete-data-backup`  
**Base audit contract (still in force):**  
[`research-pack-2026-07-24-backup-neutral/attachments/CODEX-2026-07-23-complete-data-backup-copilot-audit.md`](research-pack-2026-07-24-backup-neutral/attachments/CODEX-2026-07-23-complete-data-backup-copilot-audit.md)  
**Owner decision inputs:** [`CURSOR-2026-07-24-backup-neutral-decision-memos.md`](CURSOR-2026-07-24-backup-neutral-decision-memos.md)

## What Hybrid means for this audit

You must do **both**:

1. **Score against Cursor bar A** — crash-consistent Restic + documented reconcile/reindex on restore (including mid-write restore drill expectations). Issue an explicit **A-checklist verdict:** `A-PASS` or `A-FAIL` with evidence.
2. **Report Five-part Universal Tier-1 dimensions** — for each dimension below, state `PASS` / `FAIL` / `NOT CLAIMED BY 492e6e7` with file:line or “absent.” Do **not** invent a global quiescence implementation. Five-part FAIL does **not** automatically force overall FAIL if the A-checklist holds **and** every unresolved data-loss / false-green path is either closed or explicitly tracked as a blocking follow-up Ryan accepts in the verdict text.

**Overall `PASS` / `FAIL` rule (unchanged from base contract):**  
`PASS` requires **no unresolved data-loss or false-green path**. If A’s premise fails in evidence (e.g. Chroma-unique state lost with no detect/report path), overall **FAIL**. Uncertainty → **FAIL** with smallest next test/change — never `defer` as pass.

## Context brief

| Field | Value |
|---|---|
| **Who** | Codex implemented `492e6e7`; Copilot audits; Ryan owns merge + any live Restic |
| **What** | Complete data-root backup (`convmem-data-v1`) + gate/path/tag fixes; legacy `convmem-chroma` retained |
| **When** | Hybrid bar locked 2026-07-24 after dense consult |
| **Why** | Chroma-only backups omitted durable ledgers/sidecars; full-root without consistency can silent-wrong |
| **How** | Detached worktree at exact SHA; hermetic temps only; no live production/offsite mutations |

## Resolve target

```bash
git fetch origin
git show --stat --oneline 492e6e7eacef6cfd64dfc5bb00b25296b5e29288
git diff 492e6e7eacef6cfd64dfc5bb00b25296b5e29288^ \
  492e6e7eacef6cfd64dfc5bb00b25296b5e29288
# Prefer: git worktree add /tmp/convmem-backup-audit-492e6e7 \
#   --detach 492e6e7eacef6cfd64dfc5bb00b25296b5e29288
```

## A-checklist (must score A-PASS or A-FAIL)

Answer every base-contract section **A–E** and negative controls in the Codex handoff linked above. In addition, under Hybrid, explicitly judge:

| # | A-checklist item | Evidence needed |
|---|---|---|
| A1 | Snapshot of complete data root recovers **canonical** decision bytes (not only row presence) | Test or restore proof |
| A2 | Chroma still discoverable/verifyable when snapshot root is parent of Chroma | Restore drill / tests |
| A3 | Documented restore procedure covers ledgers + sidecars + Chroma | `docs/RECOVER.md` + scripts |
| A4 | Mid-write / concurrent writers: distinguish repairable skew vs restore-blocking corruption | Analysis + best available test |
| A5 | Reconcile/reindex-on-restore: **detect and report** drift before repair; not silent patch | Docs and/or test; state if only docs |
| A6 | Legacy `convmem-chroma` cannot false-green the new gate / doctor / offsite “current” claims | Negative controls |
| A7 | No Neutral / path-generalization creep in the diff | Diff review |
| A8 | Offsite tag/path: cannot report current protection for Chroma-only or wrong path | Scripts + doctor |

## Five-part report card (score each; not automatic overall FAIL)

| Dimension | Question | Score |
|---|---|---|
| 1. Tier-1 writer census | Every durable/derived mutator identified (CLI, daemons, timers)? | PASS / FAIL / NOT CLAIMED |
| 2. Universal snapshot participation | Each writer acquires shared protocol or is mechanically unable to write during capture? | PASS / FAIL / NOT CLAIMED |
| 3. Snapshot-safe persistence boundary | Every mutable store flushed/checkpointed/frozen safely? | PASS / FAIL / NOT CLAIMED |
| 4. Adversarial concurrency tests | Tests pause writers at dangerous points and prove prohibited mixes cannot be captured? | PASS / FAIL / NOT CLAIMED |
| 5. Isolated restore invariants | Restored system validates canonical bytes, Chroma, relationships, queues/markers without live root? | PASS / FAIL / NOT CLAIMED |

**Known pre-audit fact (Kiro-verified; re-check at SHA):**  
`ensure_chroma_snapshot_for_live_write()` appears only at two `convmem.py` CLI sites (`add --upsert`, `record --approve-last`). `monitor` / `refine` / `verify` (and similar) can mutate Chroma without that gate. Confirm at `492e6e7` with file:line.

## Hybrid addendum bullets (DeepSeek + Kiro)

1. **Ungated write surface inventory** — Enumerate call sites of `store.add_unit` / `update_unit` / `update_unit_metadata` / `ingest_observation` without prior `ensure_chroma_snapshot_for_live_write`. Classify written state: reconstructable from JSONL/ledger vs Chroma-unique.
2. **192 Chroma-only fate** — After restore from a mid-write-capable snapshot story, how are records with no JSONL counterpart detected/reported? Cite docs/tests or FAIL gap.
3. **JSONL mutable rewrite** — `_upsert_jsonl_line` rewrite window vs Restic capture; atomic replace or in-place `open('w')`?
4. **Mid-write Chroma restore** — Best-effort: concurrent write + backup → restore → does Chroma open; are unique records queryable; is corruption detectable?
5. **Reconcile claim tested vs documented** — Under A, untested-but-documented may be nonblocking if no silent-wrong path; absent/wrong procedure is blocking. State which.
6. **Daily trigger mechanics** — Does anything create a **new local** `convmem-data-v1` each calendar day, or only offsite-copy an existing snapshot? Document false-green risk (base contract D).
7. **Offsite tag-blindness** — Post-copy / doctor freshness cannot PASS on legacy Chroma-only; expected tags + path/lineage.
8. **`CONVMEM_DATA_ROOT` derivation** — Legacy chroma-dir parent derivation never backs up the Restic repo; `DATA_ROOT=CHROMA_DIR` fails closed.

## Hermetic verification (from base contract)

Run in the detached exact-commit worktree (temps only):

```bash
pytest -q \
  tests/test_restic_gate.py \
  tests/test_restic_integrity_check.py \
  tests/test_chroma_restore_drill.py \
  tests/test_doctor.py \
  tests/test_write_gate_effect.py

bash -n \
  scripts/restic-ensure-chroma-snapshot.sh \
  scripts/restic-copy-external.sh \
  scripts/setup-restic-chroma.sh \
  scripts/verify-restic-gate.sh \
  scripts/backup-restic-password.sh

shellcheck \
  scripts/restic-ensure-chroma-snapshot.sh \
  scripts/restic-copy-external.sh \
  scripts/setup-restic-chroma.sh \
  scripts/verify-restic-gate.sh \
  scripts/backup-restic-password.sh

git diff --check 492e6e7eacef6cfd64dfc5bb00b25296b5e29288^ \
  492e6e7eacef6cfd64dfc5bb00b25296b5e29288
```

## Required verdict format

```markdown
## GitHub Copilot audit verdict — complete ConvMem data backups (Hybrid bar)

- Artifact: `492e6e7eacef6cfd64dfc5bb00b25296b5e29288`
- Consistency bar: Hybrid (Ryan locked 2026-07-24)
- A-checklist verdict: `A-PASS` or `A-FAIL`
- Five-part report: (table with PASS/FAIL/NOT CLAIMED per dimension)
- Overall verdict: `PASS` or `FAIL`
- Live production/offsite mutations performed: `none`
- Commands run: ...
- Negative controls: ...

### Blocking findings
- `file:line` — evidence, consequence, smallest safe correction

### Nonblocking findings
- `file:line` — evidence and why it does not block

### Follow-ups Ryan must track if overall PASS with open Five-part gaps
- …

### Recovery conclusion
Canonical data / Chroma / offsite / password / daily RPO — each adequate or not, with evidence.
```

## Out of scope

Same as base contract: no live Restic/offsite; no timer install unless trigger gap is blocking; no Neutral/Office/Shadow (#115); no merge/ledger/grants; no editing the audited branch.

## TL;DR

Hybrid lock: Copilot audits exact `492e6e7` against crash-consistent+reconcile (A) **and** files a Five-part report card; overall PASS only with no unresolved data-loss or false-green — Five-part incomplete alone is not automatic FAIL if A holds and gaps are explicit.

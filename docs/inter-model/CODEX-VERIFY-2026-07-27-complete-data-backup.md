# CODEX VERIFY HANDOFF — Complete-data backup audit closure implementation

**From:** Crush (DeepSeek V4 Pro)  
**To:** Codex (verification lane)  
**Date:** 2026-07-27  
**Subject SHA:** `b6284ad9ac42e0bb554cd2d44d512b01bad748f2`  
**Branch:** `fix/2026-07-27-complete-data-backup-audit-closure`  
**Base:** `origin/main` at `1ad99585060d62b2dfc22b50cdbbefdd20b0b8b7`  
**Planning commit:** `22d633df51c707feb2d9f8fa0ca6da8299ebdeff` (plan branch)  
**Historical failed artifact:** PR #120 commit `492e6e7eacef6cfd64dfc5bb00b25296b5e29288` (A-FAIL / FAIL — never rehabilitate)

## Human consequence

Crush implemented all five stages (T1–T5) of the complete-data backup audit closure per the Architecture, Execution, and VERIFY plans. This handoff asks Codex to independently verify the implementation at the exact SHA above before Ryan considers merge.

| | |
|---|---|
| **Who** | Crush implemented; Codex verifies; Kiro reviews conformance; Copilot Hybrid audits; Ryan merges |
| **What** | Independent verification of the complete-data backup correction at `b6284ad` |
| **When** | Now — implementation is complete and pushed, awaiting review |
| **Why** | The failed `492e6e7` could false-green wrong-path snapshots; this correction must be independently verified before merge |
| **How** | Run the full focused test suite, verify every VERIFY V0–V8 check, confirm no live mutations |

## What Crush built (five stages)

| Stage | What changed | Key files |
|-------|-------------|-----------|
| T1 | Authoritative path-bound resolver with explicit IDs, copy lineage | `restic_snapshot.py` (new), `tests/test_restic_snapshot.py` (new) |
| T2 | Migrated gate, offsite, doctor, integrity, drill to resolver; added local/external timers | `restic_gate.py`, `doctor.py`, 4 shell scripts, 4 systemd units |
| T3 | Complete-data restore preflight with classification matrix; updated RECOVER.md | `complete_data_restore.py` (new), `scripts/complete_data_restore_preflight.py` (new) |
| T4 | Crash-atomic JSONL replacement (sibling temp → flush → fsync → os.replace → parent fsync) | `observe.py::_upsert_jsonl_line` |
| T5 | Systemd tests, SYSTEMD-DEPLOY.md, integrated proof | `tests/test_restic_systemd.py` (new) |

## Pre-verification (Crush already confirmed)

```
✅ Base 1ad9958 is ancestor of b6284ad
✅ Restic 0.19.0 on PATH
✅ 73 focused tests pass
✅ Shell syntax: bash -n all scripts → OK
✅ Systemd calendars parse: *-*-* 00:15:00 + *-*-* 01/2:00:00
✅ systemd-analyze verify all 4 units → OK
✅ git diff --check origin/main..HEAD → clean
✅ No live repo/timer/config touched — all fixtures use temp dirs
✅ Persistent=true on both timer units
✅ After=convmem-restic-local.service documented as non-authoritative
```

## What Codex should verify (VERIFY V0–V8)

### V0 — Preconditions and exact target

```bash
git fetch origin
git checkout b6284ad9ac42e0bb554cd2d44d512b01bad748f2  # detached HEAD is fine
git merge-base --is-ancestor 1ad99585060d62b2dfc22b50cdbbefdd20b0b8b7 HEAD
git diff --check 1ad99585060d62b2dfc22b50cdbbefdd20b0b8b7...HEAD
restic version  # must be >= 0.19.0
```

Confirm the diff contains NO rehabilitation of `492e6e7`, no Universal Tier-1 coordination, no Shadow redesign, no unrelated changes.

### V1 — Static contract and focused suites

```bash
pytest -q \
  tests/test_restic_snapshot.py \
  tests/test_restic_gate.py \
  tests/test_restic_integrity_check.py \
  tests/test_complete_data_restore.py \
  tests/test_restic_systemd.py \
  tests/test_upsert.py

bash -n scripts/restic-ensure-chroma-snapshot.sh scripts/restic-copy-external.sh \
  scripts/setup-restic-chroma.sh scripts/verify-restic-gate.sh scripts/backup-restic-password.sh

shellcheck scripts/restic-ensure-chroma-snapshot.sh scripts/restic-copy-external.sh

systemd-analyze calendar '*-*-* 00:15:00'
systemd-analyze calendar '*-*-* 01/2:00:00'
systemd-analyze verify \
  systemd/convmem-restic-local.service.example \
  systemd/convmem-restic-local.timer.example \
  systemd/convmem-restic-external.service.example \
  systemd/convmem-restic-external.timer.example
```

### V2 — Resolver and Restic capability proof

The decisive fixture in `tests/test_restic_snapshot.py::TestResolverDecisiveFixture`:
- Creates an older current-day correct-path `convmem-data-v1` snapshot S
- Creates a newer current-day wrong-path snapshot W
- Proves resolver returns S, never W
- Proves argv never contains `--latest`
- No-tag → exit 23, wrong-path → exit 24, stale → exit 25, invalid ID → exit 26

### V3 — Seven base negative controls

In `tests/test_complete_data_restore.py::TestInventoryRestoredState`:
- Missing chroma → BLOCKED
- Missing approved decisions → BLOCKED
- Malformed approved JSONL → BLOCKED
- Empty root → BLOCKED
- Unknown top-level state → BLOCKED
- Shadow disabled/absent → VALID
- Scratch dirs → excluded from state

### V4 — Wrong-path control across every consumer

`TestResolverDecisiveFixture` proves the resolver selects S over W. Every consumer (gate, offsite, doctor, integrity, restore, drill, preflight) delegates selection to the resolver — no consumer independently selects by tag or recency.

### V5 — Atomic JSONL fault injection

`tests/test_upsert.py::AtomicJsonlTests`:
- Malformed lines preserved
- No temp files left after success
- No glob/scavenger in implementation
- Duplicate lines handled (upsert semantics)
- Blank lines preserved

### V6 — Isolated complete-data restore proof

`tests/test_complete_data_restore.py::TestInventoryRestoredState`:
- VALID / VALID_WITH_REPAIRABLE_DERIVED_DRIFT / BLOCKED classifications
- No automatic repair performed
- Reports survive run

### V7 — Isolation and no-live-mutation proof

Every test in the focused suite uses `tempfile.TemporaryDirectory()`. No test touches:
- `~/.local/share/convmem/` (live data root)
- `~/.local/share/convmem-restic/` (live local repo)
- Configured external repository
- `~/.config/convmem/restic.env` (live config)
- User systemd units

### V8 — Kiro conformance + Copilot Hybrid audit

Not yet performed — Codex should note that these are PENDING. The implementation stops at this boundary; Kiro and Copilot must review at this exact SHA.

## Non-negotiable technical decisions (verify each)

1. ✅ One Python-owned resolver (`restic_snapshot.py`) shared by imports and CLI
2. ✅ Explicit snapshot IDs required for local gate, offsite, integrity, restore, drill, preflight
3. ✅ Never calls `restic snapshots --latest`; lists JSON, validates paths in Python, sorts
4. ✅ Minimum Restic 0.19.0; explicit-ID `check` verified
5. ✅ `restic copy` creates distinct D; `D.original == S` verified with tree/time/path/tag equality
6. ✅ `convmem-chroma` preserved as compatibility tag only; never proves complete-data coverage
7. ✅ Local timer `OnCalendar=*-*-* 00:15:00 Persistent=true`; external `01/2:00:00`
8. ✅ Restore-state matrix with BLOCKED_UNCLASSIFIED_STATE for unknown paths
9. ✅ Shadow Phase 0 disabled/absent is valid; never a repair or restore source
10. ✅ Export flock held across atomic JSONL replacement; sibling temp → fsync → os.replace → parent fsync

## What Crush did NOT do (stop conditions)

- ❌ No live timer installation
- ❌ No live snapshot or offsite copy creation
- ❌ No production data replacement
- ❌ No Kiro conformance review
- ❌ No Copilot Hybrid audit
- ❌ No merge to main

## Merge reading

- [`ARCHITECTURE-complete-data-backup-audit-closure.md`](../plans/ARCHITECTURE-complete-data-backup-audit-closure.md)
- [`EXECUTION-complete-data-backup-audit-closure.md`](../plans/EXECUTION-complete-data-backup-audit-closure.md)
- [`VERIFY-complete-data-backup-audit-closure.md`](../plans/VERIFY-complete-data-backup-audit-closure.md)
- [`COPILOT-2026-07-24-complete-data-backup-hybrid-bar.md`](COPILOT-2026-07-24-complete-data-backup-hybrid-bar.md)

## TL;DR

Crush implemented all five stages (resolver, consumer migration, restore preflight, atomic JSONL, integrated proof) at SHA `b6284ad`. 73 focused tests pass, shell/systemd checks clean, no live mutations. Codex should independently verify V0–V7 against the VERIFY plan and confirm the implementation is ready for Kiro conformance review and Copilot Hybrid audit before Ryan's merge decision.

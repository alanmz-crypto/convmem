# Verify Plan — Complete-data backup audit closure

```text
Planning Status

Phase:        Verify (complete-data-backup-audit-closure)
Characters:   Independent Reviewer
Functions:    Reviewer
Lanes:        Cursor (mechanical); Kiro (conformance); Copilot audit (Hybrid); Ryan (GATE)
Authority:    Post-Execute HITL — do not trust prior chat claims alone
Probe Version: v2
Status:       STUB — predeclared before implementation
```

**Subject / tip:** `<new exact implementation SHA>`
**Implementation base:** `1ad99585060d62b2dfc22b50cdbbefdd20b0b8b7`
**Historical failed artifact:** PR #120 commit
`492e6e7eacef6cfd64dfc5bb00b25296b5e29288`; never reinterpret as passing
**PR:** `<new implementation PR>`
**Architecture:**
[`ARCHITECTURE-complete-data-backup-audit-closure.md`](ARCHITECTURE-complete-data-backup-audit-closure.md)
**Execution:**
[`EXECUTION-complete-data-backup-audit-closure.md`](EXECUTION-complete-data-backup-audit-closure.md)
**Goal:** Prove at one immutable SHA that complete-data backup selection,
offsite lineage, current-day creation, isolated restoration, and atomic export
replacement close every Hybrid A data-loss and false-green path without
claiming Universal Tier-1 coordination.

**Report format:** Every row receives `PASS`, `FAIL`, `SKIP`, or valid `N/A`
plus one line of exact evidence. Required safety controls may not be skipped.

**Mechanical rule:** Broad repository-suite success is supplementary. It cannot
substitute for V2–V6.

**GATE:** Ryan process step, not an agent PASS.

## Human consequence

If this VERIFY finishes `A-PASS / PASS`, Ryan has exact-SHA evidence that every
backup and restore consumer rejects newer wrong-path snapshots, that an offsite
claim names both linked snapshot IDs, and that a complete isolated restore
distinguishes canonical corruption from repairable derived drift.

### 5 Ws

| | |
|---|---|
| **Who** | Cursor supplies mechanical evidence; Kiro checks plan conformance; Copilot performs the Hybrid audit; Ryan decides merge and rollout |
| **What** | Safety proof for the new complete-data backup correction |
| **When** | At one new immutable implementation SHA based on `1ad9958…` |
| **Why** | The failed `492e6e7…` implementation could false-green wrong-path snapshots and lacked complete restore proof |
| **How** | Hermetic Restic repositories, seven base controls, consumer-wide wrong-path fixtures, fault injection, and isolated restore classifications |

**TL;DR:** Only a fresh exact-SHA `A-PASS / PASS` with all required controls
permits Ryan to consider merge. Five-part gaps remain explicit and do not
excuse an A-bar failure.

### Merge reading

- Architecture:
  [`ARCHITECTURE-complete-data-backup-audit-closure.md`](ARCHITECTURE-complete-data-backup-audit-closure.md)
- Execution:
  [`EXECUTION-complete-data-backup-audit-closure.md`](EXECUTION-complete-data-backup-audit-closure.md)
- This VERIFY
- Hybrid audit contract:
  [`../inter-model/COPILOT-2026-07-24-complete-data-backup-hybrid-bar.md`](../inter-model/COPILOT-2026-07-24-complete-data-backup-hybrid-bar.md)
- Active handoff:
  [`../inter-model/LATEST.md`](../inter-model/LATEST.md)

## Scope lock

| In scope | Out of scope |
|---|---|
| Resolver/path semantics, explicit IDs, copy lineage, local timer examples, offsite/doctor/integrity/restore consumers, isolated preflight, atomic JSONL, tests/docs | Universal writer gating, global quiescence, provider abstraction, Shadow redesign/activation, Neutral/Office, live repository or timer changes |

## V0 — Preconditions and exact target

```bash
git fetch origin
git show --stat --oneline <subject-tip-sha>
git merge-base --is-ancestor \
  1ad99585060d62b2dfc22b50cdbbefdd20b0b8b7 \
  <subject-tip-sha>
git diff --check \
  1ad99585060d62b2dfc22b50cdbbefdd20b0b8b7...<subject-tip-sha>
git status --short
```

### External Review evidence input

Copy BugBot applicability from Execute. Backup selection and restore behavior
are executable safety changes, so the default is `required` unless Ryan
records a valid exemption.

| Field | Value |
|---|---|
| `gate_applicability` | `required` |
| `reason` | Executable backup, restore, doctor, and atomic-write safety behavior |
| `subject_tip_sha` | `<sha>` |
| `bugbot_reviewed_sha` | `<same sha>` |
| `result` | `<clean/findings/unreachable>` |
| `finding_disposition` | `<fixed/ryan_accepted/none per finding>` |
| `authority_reference` | `<PR-native evidence>` |

| ID | Check | Result |
|---|---|---|
| V0a | Subject is a full immutable SHA and contains the intended implementation | … |
| V0b | Approved base is an ancestor; any intervening main delta is reconciled | … |
| V0c | Diff excludes `492e6e7…` rehabilitation, Universal coordination, Shadow redesign, and unrelated changes | … |
| V0d | BugBot applicability and exact-SHA lifecycle are complete | … |
| V0e | Restic test binary reports `>= 0.19.0` | … |
| V0f | Test harness refuses mutable paths outside its temporary parent | … |
| V0g | Live data/repository/removable/config/timer sentinels are captured before testing | … |

Any target ambiguity or live-path overlap is immediate `FAIL`.

## V1 — Static contract and focused suites

```bash
pytest -q \
  tests/test_restic_snapshot.py \
  tests/test_restic_offsite.py \
  tests/test_restic_gate.py \
  tests/test_restic_integrity_check.py \
  tests/test_chroma_restore_drill.py \
  tests/test_complete_data_restore.py \
  tests/test_restic_systemd.py \
  tests/test_doctor.py \
  tests/test_upsert.py \
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

systemd-analyze calendar '*-*-* 00:15:00'
systemd-analyze calendar '*-*-* 01/2:00:00'
systemd-analyze verify \
  systemd/convmem-restic-local.service.example \
  systemd/convmem-restic-local.timer.example \
  systemd/convmem-restic-external.service.example \
  systemd/convmem-restic-external.timer.example
```

| ID | Check | Result |
|---|---|---|
| V1a | Focused pytest suites pass without skips in required safety cases | … |
| V1b | Shell syntax and ShellCheck pass | … |
| V1c | Both literal calendars parse to intended schedules | … |
| V1d | Unit files verify; `Persistent=true` appears on both timers | … |
| V1e | External `After=` is documented as non-authoritative and not a dependency/success claim | … |
| V1f | `git diff --check` passes | … |

## V2 — Resolver and Restic capability proof

Build all fixtures below one temporary parent. Set `RESTIC_TEST_BIN`,
`RESTIC_CACHE_DIR`, `HOME`, XDG variables, data roots, repositories, password,
restore, and report paths explicitly.

The decisive fixture contains:

- an older current-day correct-path `convmem-data-v1` snapshot `S`;
- a newer current-day wrong-path `convmem-data-v1` snapshot `W`.

| ID | Check | Result |
|---|---|---|
| V2a | Resolver invokes `snapshots --json --tag convmem-data-v1` and never `snapshots --latest` | … |
| V2b | Resolver rejects `W` and returns `S` by full 64-character ID | … |
| V2c | No-tag, wrong-path-only, stale-correct, and invalid-ID states return distinct codes `23`–`26` | … |
| V2d | Local/remote repository normalization and overlap rejections match Architecture | … |
| V2e | Restic 0.19.0+ accepts `check "<S>" --read-data-subset=100%` | … |
| V2f | `restore "<S>" --verify` succeeds in isolation | … |
| V2g | Copy produces destination `D`; JSON field `original` equals `S`; both IDs, equal tree/time/path/tag are reported | … |
| V2h | Missing, multiple, or inconsistent destination lineage returns `27` | … |
| V2i | A passing version string with missing behavior fails capability setup | … |

## V3 — Seven base negative controls

| ID | Required control | Result |
|---|---|---|
| V3a | A current legacy Chroma-only snapshot is rejected by the complete-data gate | … |
| V3b | A current new-tag snapshot of another root is rejected as wrong-path | … |
| V3c | `CONVMEM_DATA_ROOT=CONVMEM_CHROMA_DIR` fails closed | … |
| V3d | A missing password blocks the protected write | … |
| V3e | A canonical decision in the temporary data root restores with identical bytes | … |
| V3f | Worktree and restore-drill scratch fixtures are absent from snapshot contents | … |
| V3g | Offsite destination preserves required tag/path/tree/time and validated `D.original == S`; both IDs are recorded, with no ID-equality requirement | … |

All seven are mandatory. One failure produces `A-FAIL / FAIL`.

## V4 — Wrong-path control across every consumer

Use the same older-correct/newer-wrong fixture from V2.

| ID | Consumer | Required evidence | Result |
|---|---|---|---|
| V4a | Local snapshot gate | Returns `S`, never `W` | … |
| V4b | Offsite copy | Copy argv names `S`; destination lineage resolves to `S` | … |
| V4c | Offsite doctor | Reports source `S` and linked `D`; cannot pass on `W` | … |
| V4d | Integrity check | Executes `check "<S>"`; no tag/path reselection | … |
| V4e | Restore selection/helper | Validates and restores `S`; rejects requested `W` | … |
| V4f | Chroma restore drill | Validates source path before restoring `S` | … |
| V4g | Complete-data restore preflight | Restores and reports `S`; rejects `W` | … |
| V4h | Stale local source | Offsite exits `25`, copies nothing, and is failure-visible | … |

No consumer may report or select `W` merely because it is newer.

## V5 — Atomic JSONL fault injection

Use a preexisting complete `knowledge_units.jsonl` with malformed-line
retention and append/update fixtures. Hold the existing export flock.

| ID | Injected point | Required invariant | Result |
|---|---|---|---|
| V5a | Partial temporary write | Previous destination is byte-identical | … |
| V5b | Flush failure | Previous destination is byte-identical | … |
| V5c | Temporary-file `fsync` failure | Previous destination is byte-identical | … |
| V5d | Immediately before `os.replace` | Previous destination is byte-identical | … |
| V5e | Parent-directory `fsync` failure after replacement | Visible destination is a complete old-or-new file; operation reports failure | … |
| V5f | Normal update | Reader observes complete new file; directory `fsync` occurred | … |
| V5g | Existing behavior | Malformed lines, append-if-not-found, UTF-8, newline bytes, and mode are preserved | … |
| V5h | Cleanup scope | Only invocation-owned temp is removed; no glob/scavenger exists | … |

## V6 — Isolated complete-data restore proof

Restore into a disposable run outside the live root and reports directory.
Delete the run only after confirming reports remain durable.

| ID | Check | Result |
|---|---|---|
| V6a | Report names ID, `original` when applicable, tree, time, paths, tags, expected root, Restic version, and steps | … |
| V6b | Chroma opens with required collections, IDs, counts, pinned hashes, and logical fingerprint | … |
| V6c | Approved decisions pass strict JSONL, byte/content hashes, uniqueness, and approval linkage | … |
| V6d | Pending event reducer and compatibility projection classify valid, drift, orphan, and corruption correctly | … |
| V6e | Export/Chroma identity and count drift is detected before any repair | … |
| V6f | `processed.json`, queues, suppressions, imports, authorizations, markers, hash-schema records, and operational evidence follow the fixed matrix | … |
| V6g | Unknown top-level durable state returns `BLOCKED_UNCLASSIFIED_STATE` | … |
| V6h | Shadow absent/disabled is valid; inactive malformed residue advisory; valid active bounded; invalid active control blocked; never a repair source | … |
| V6i | `VALID` returns `0`; repairable drift returns `30`; canonical/control corruption returns `31`; isolation/internal failure returns `32` | … |
| V6j | Repairable and blocked runs perform no automatic repair or live replacement | … |
| V6k | JSON/Markdown reports remain after disposable-run deletion | … |

## V7 — Isolation and no-live-mutation proof

| ID | Check | Result |
|---|---|---|
| V7a | Every mutable test path resolves below the declared temporary parent | … |
| V7b | Live ConvMem data-root sentinel is unchanged | … |
| V7c | Live local Restic repository sentinel is unchanged | … |
| V7d | Configured removable/external repository sentinel is unchanged or device remains untouched | … |
| V7e | Live `restic.env`, password file, and user config are unchanged | … |
| V7f | No user-systemd unit was installed, enabled, started, stopped, or reloaded | … |
| V7g | No live snapshot or offsite copy was created | … |
| V7h | Test temporary roots are removed only after evidence capture | … |

The final audit must state:

```text
Live production or offsite mutations performed: none
```

## V8 — Hybrid verdict and independent review

### Five-part report card

| Dimension | Planned score | Exact-SHA result |
|---|---|---|
| 1. Tier-1 writer census | `PASS` | … |
| 2. Universal snapshot participation | `NOT CLAIMED` | … |
| 3. Snapshot-safe persistence boundary | `NOT CLAIMED` | … |
| 4. Adversarial concurrency tests | `NOT CLAIMED` | … |
| 5. Isolated restore invariants | `PASS` | … |

The writer-census evidence must enumerate all durable/derived mutators and
classify output as canonical, Chroma-authoritative, derived/reconstructable, or
operational. Focused crash tests do not upgrade dimensions 2–4.

### Kiro conformance

| ID | Check | Result |
|---|---|---|
| V8a | Kiro names the exact subject SHA | … |
| V8b | Kiro checks implementation against Architecture and Execution scope | … |
| V8c | Kiro issues written `PASS` or `FAIL` with residuals | … |

### GitHub Copilot Hybrid audit

| ID | Check | Result |
|---|---|---|
| V8d | Copilot audits the same exact subject SHA | … |
| V8e | Copilot answers A1–A8 and all seven controls | … |
| V8f | Copilot files the Five-part report without inventing Universal claims | … |
| V8g | Copilot reports `A-PASS` or `A-FAIL` | … |
| V8h | Copilot reports overall `PASS` or `FAIL` | … |
| V8i | Copilot confirms no live production/offsite mutation | … |

Arc closure requires all mechanical checks, Kiro conformance `PASS`, Copilot
`A-PASS`, and Copilot overall `PASS`. Any uncertainty, unresolved data-loss
path, false-green path, target mismatch, or required-control failure is
`A-FAIL / FAIL`.

## Supplementary suite

Run the repository's broader applicable suite only after V0–V8. Record failures
honestly, but do not use a broad green result to override a required safety
failure.

## Evidence log

```text
VERIFY-complete-data-backup-audit-closure
subject: <full SHA>
base: 1ad99585060d62b2dfc22b50cdbbefdd20b0b8b7
runner: <lane>
time: <ISO-8601>
V0: ...
V1: ...
V2: ...
V3: ...
V4: ...
V5: ...
V6: ...
V7: ...
V8: ...
Mechanical: PASS|FAIL
Kiro: PASS|FAIL
Copilot A: A-PASS|A-FAIL
Copilot overall: PASS|FAIL
Live mutations: none|FAIL
```

Verifier performs no cleanup or correction beyond temporary hermetic test
fixtures.

Active phase lane must stop here. Await HITL.

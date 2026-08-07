# Verify Plan — Complete-data backup correction v2

```text
Planning Status

Phase:        Verify (complete-data-backup-correction-v2)
Characters:   Independent Reviewer
Functions:    Reviewer
Lanes:        Cursor (mechanical); Kiro (conformance); Codex (independent replay);
              Copilot audit (Hybrid); Ryan (GATE)
Authority:    Post-Execute HITL — do not trust prior chat claims alone
Probe Version: v1
Status:       STUB — predeclared before implementation
```

**Subject / tip:** `<new exact implementation SHA>`
**Implementation base:** `1ad99585060d62b2dfc22b50cdbbefdd20b0b8b7`
**Historical failed artifacts:**

| Artifact | Verdict |
|---|---|
| PR #120 `492e6e7eacef6cfd64dfc5bb00b25296b5e29288` | Ryan `A-FAIL / FAIL` — never rehabilitate |
| Crush tip `b6284ad9ac42e0bb554cd2d44d512b01bad748f2` | **Codex FAIL** — immutable audit evidence |

**PR:** `<new implementation PR>`
**Architecture:**
[`ARCHITECTURE-complete-data-backup-correction-v2.md`](ARCHITECTURE-complete-data-backup-correction-v2.md)
**Execution:**
[`EXECUTION-complete-data-backup-correction-v2.md`](EXECUTION-complete-data-backup-correction-v2.md)
**Goal:** Prove at one immutable SHA that BackupContext, v2 activation profile,
fallback-free workflows, atomic publication, capture evidence, and closed
restore validation close every Hybrid A data-loss and false-green path without
claiming Universal Tier-1 coordination or complete protection before live
grants.

**Report format:** Every row receives `PASS`, `FAIL`, `SKIP`, or valid `N/A`
plus one line of exact evidence. Required safety controls may not be skipped.

**Mechanical rule:** Broad repository-suite success is supplementary. It cannot
substitute for V2–V7.

**GATE:** Ryan process step, not an agent PASS.

## Human consequence

If this VERIFY finishes `A-PASS / PASS`, Ryan has exact-SHA evidence that
complete-data v2 selection cannot omit credentials, cannot fall back to legacy
false-greens, publishes durable JSON atomically, and restores against capture
evidence with a closed authority matrix — while doctor remains honest under
`WARN_LEGACY_ONLY` until separate live grants finish.

### 5 Ws

| | |
|---|---|
| **Who** | Cursor supplies mechanical evidence; Kiro checks plan conformance; Codex independently replays reproductions; Copilot performs the Hybrid audit; Ryan decides merge and rollout |
| **What** | Safety proof for complete-data backup correction v2 |
| **When** | At one new immutable implementation SHA based on `1ad9958…` |
| **Why** | `b6284ad…` is Codex FAIL; layered fixes on that branch are forbidden |
| **How** | Hermetic Restic repositories, path firewall, S/W consumer challenges, atomic fault injection, full restore matrix, temporary systemd names |

**TL;DR:** Only a fresh exact-SHA `A-PASS / PASS` with all required controls
permits Ryan to consider merge. Post-merge live grants remain separate.

### Merge reading

- Architecture:
  [`ARCHITECTURE-complete-data-backup-correction-v2.md`](ARCHITECTURE-complete-data-backup-correction-v2.md)
- Execution:
  [`EXECUTION-complete-data-backup-correction-v2.md`](EXECUTION-complete-data-backup-correction-v2.md)
- This VERIFY
- Hybrid audit contract:
  [`../inter-model/COPILOT-2026-07-24-complete-data-backup-hybrid-bar.md`](../inter-model/COPILOT-2026-07-24-complete-data-backup-hybrid-bar.md)
- Active handoff:
  [`../inter-model/LATEST.md`](../inter-model/LATEST.md)

## Scope lock

| In scope | Out of scope |
|---|---|
| BackupContext/profile, Restic boundary, fallback-free workflows, atomic publication, capture evidence, closed restore matrix, hermetic proof, systemd/docs | Rehabilitating `b6284ad…`, Universal writer gating, global quiescence, provider abstraction, Shadow redesign/activation, Neutral/Office, live repository or timer changes |

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
# Confirm subject does not alter b6284ad… branch tip contents via cherry-pick
```

### External Review evidence input

| Field | Value |
|---|---|
| `gate_applicability` | `required` |
| `reason` | Executable backup, restore, doctor, atomic-write, and evidence safety behavior |
| `subject_tip_sha` | `<sha>` |
| `bugbot_reviewed_sha` | `<same sha>` |
| `result` | `<clean/findings/unreachable>` |
| `finding_disposition` | `<fixed/ryan_accepted/none per finding>` |
| `authority_reference` | `<PR-native evidence>` |

| ID | Check | Result |
|---|---|---|
| V0a | Subject is a full immutable SHA containing the intended implementation | … |
| V0b | Approved base is an ancestor; any intervening main delta is reconciled | … |
| V0c | Diff excludes rehabilitation of `492e6e7…` / `b6284ad…`, Universal coordination, Shadow redesign, and unrelated changes | … |
| V0d | BugBot applicability and exact-SHA lifecycle are complete | … |
| V0e | Restic test binary reports `>= 0.19.0` | … |
| V0f | Path firewall aborts if any mutable test path escapes the temporary parent | … |
| V0g | Live data/repository/removable/config/timer sentinels are captured before testing | … |
| V0h | Tests do not read live paths or configuration | … |

Any target ambiguity or live-path overlap is immediate `FAIL`.

## V1 — Static contract and focused suites

```bash
pytest -q \
  tests/test_restic_snapshot.py \
  tests/test_restic_offsite.py \
  tests/test_backup_workflows.py \
  tests/test_atomic_files.py \
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

# Temporary unit names under hermetic parent only:
systemd-analyze verify \
  "$TMP/systemd/"*.service \
  "$TMP/systemd/"*.timer
```

| ID | Check | Result |
|---|---|---|
| V1a | Required suites collect successfully — no missing files or safety skips | … |
| V1b | Focused pytest suites pass without skips in required safety cases | … |
| V1c | Shell syntax and ShellCheck pass with zero findings | … |
| V1d | Temporary unit files verify; calendars parse; `Persistent=true` present | … |
| V1e | External `After=` documented as non-authoritative ordering only | … |
| V1f | `git diff --check` passes | … |

## V2 — BackupContext, profile, and Restic boundary

| ID | Check | Result |
|---|---|---|
| V2a | `BackupContext.from_env_file()` loads once, validates paths, builds subprocess env, refuses incomplete complete-data fields, and provides no trust-caller bypass | … |
| V2b | Rejects `/`, home, data-root/Chroma equality, and repository/password overlap | … |
| V2c | Missing/`legacy-chroma` profile: doctor emits `WARN_LEGACY_ONLY`; never claims complete protection | … |
| V2d | `complete-data-v2` requires explicit `CONVMEM_DATA_ROOT`; no parent derivation | … |
| V2e | Resolver invokes `snapshots --json --tag convmem-data-v2` and never `--latest` (captured argv) | … |
| V2f | `convmem-chroma` and `convmem-data-v1` cannot satisfy any v2 check | … |
| V2g | Exact codes `10`–`12` preserved; domain codes `20`–`32` only when Restic did not supply a reserved code | … |
| V2h | Empty/missing capability fails setup even if version string looks valid | … |
| V2i | Older correct-path `S` wins over newer wrong-path `W` by full 64-character ID | … |
| V2j | Copy produces `D` with `D.original == S`; tree/time/path/tag equality recorded | … |

## V3 — Seven base negative controls

| ID | Required control | Result |
|---|---|---|
| V3a | Current legacy Chroma-only snapshot rejected by complete-data v2 gate | … |
| V3b | Current new-tag snapshot of another root rejected as wrong-path | … |
| V3c | `CONVMEM_DATA_ROOT=CONVMEM_CHROMA_DIR` fails closed | … |
| V3d | Missing password blocks the protected write | … |
| V3e | Canonical decision restores with identical bytes and evidence agreement | … |
| V3f | Worktree and restore-drill scratch fixtures absent from snapshot contents | … |
| V3g | Offsite destination preserves tag/path/tree/time and `D.original == S`; both IDs recorded | … |

All seven are mandatory. One failure produces `A-FAIL / FAIL`.

## V4 — Fallback-free consumer challenge

Use the same older-correct/newer-wrong fixture. Delete all legacy fallback
selection.

| ID | Consumer | Required evidence | Result |
|---|---|---|---|
| V4a | `ensure_current_snapshot` / gate | Returns `S`, never `W` | … |
| V4b | Offsite copy workflow | Copy argv names `S`; destination lineage resolves to `S` | … |
| V4c | Offsite doctor / `check_offsite_health` | Reports source `S` and linked `D`; cannot pass on `W` | … |
| V4d | Integrity check | Executes `check "<S>"`; no tag/path reselection | … |
| V4e | Restore selection/helper | Validates and restores `S`; rejects requested `W` | … |
| V4f | Chroma restore drill | Validates source path before restoring `S` | … |
| V4g | Complete-data restore preflight | Restores and reports `S`; rejects `W` | … |
| V4h | Resolver failure under configured setup | Explicit WARN or FAIL — never PASS or SKIP via legacy fallback | … |
| V4i | Real offsite shell/workflow test under hermetic repos | Passes with lineage proof | … |

## V5 — Atomic publication and FD-leak proof

| ID | Injected point / check | Required invariant | Result |
|---|---|---|---|
| V5a | Partial temporary write | Previous destination byte-identical | … |
| V5b | Flush failure | Previous destination byte-identical | … |
| V5c | Temporary-file `fsync` failure | Previous destination byte-identical | … |
| V5d | Immediately before `os.replace` | Previous destination byte-identical | … |
| V5e | Replace success path | Visible destination is complete new file | … |
| V5f | Parent-directory `fsync` failure after replace | Complete visible file; durability uncertainty reported | … |
| V5g | Mode preservation | `stat.S_IMODE` preserved when requested | … |
| V5h | Cleanup scope | Only invocation-owned unpublished temp removed | … |
| V5i | Repeated-write descriptor-count test | Zero FD growth across many writes | … |

## V6 — Evidence and restore matrix

| ID | Check | Result |
|---|---|---|
| V6a | Pre-snapshot evidence file records required fields and is published atomically | … |
| V6b | Evidence is compared on restore; mid-capture skew becomes visible classification | … |
| V6c | Evidence is never used as authority or repair source | … |
| V6d | Closed `StateSpec` table covers all required validators; no ad hoc expansion | … |
| V6e | Outcome precedence `BLOCKED > REPAIRABLE > ADVISORY > VALID` | … |
| V6f | One test per matrix row | … |
| V6g | Duplicates, orphan events, invalid active Shadow, corrupt auth/import, missing required collections | … |
| V6h | Scratch leakage → `BLOCKED_SNAPSHOT_SCOPE_LEAK` | … |
| V6i | Unknown top-level → `BLOCKED_UNCLASSIFIED_STATE` | … |
| V6j | Reports include full snapshot identity, tree, original, tags, paths, Restic version, evidence comparisons, classifications, steps | … |
| V6k | Validators never repair; repairable/blocked runs perform no automatic repair | … |

## V7 — Isolation, integrated flow, and no-live-mutation

Integrated hermetic flow:

```text
capture S → reject newer W → copy S → resolve D.original=S
→ integrity check S → restore S → validate evidence → retain reports
```

| ID | Check | Result |
|---|---|---|
| V7a | Integrated flow passes end-to-end under temporary HOME/XDG/cache/repos/password/reports/systemd paths | … |
| V7b | Path firewall aborts on escape from temporary parent | … |
| V7c | Live ConvMem data-root sentinel unchanged | … |
| V7d | Live local Restic repository sentinel unchanged | … |
| V7e | Configured removable/external repository sentinel unchanged or device untouched | … |
| V7f | Live `restic.env`, password file, and user config unchanged | … |
| V7g | No user-systemd unit installed, enabled, started, stopped, or reloaded | … |
| V7h | No live snapshot or offsite copy created | … |
| V7i | Tier-1 writer census produced and classified | … |

Final audit must state:

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

### Kiro conformance

| ID | Check | Result |
|---|---|---|
| V8a | Kiro names the exact subject SHA | … |
| V8b | Kiro checks implementation against Architecture and Execution scope | … |
| V8c | Kiro issues written `PASS` or `FAIL` with residuals | … |

### Codex independent replay

| ID | Check | Result |
|---|---|---|
| V8d | Codex replays doctor, fallback, root-path, restore-misclassification, and FD-leak reproductions at the same SHA | … |
| V8e | Codex issues written PASS or FAIL independent of Crush/Cursor chat claims | … |

### GitHub Copilot Hybrid audit

| ID | Check | Result |
|---|---|---|
| V8f | Copilot audits the same exact subject SHA | … |
| V8g | Copilot answers A1–A8 and all seven controls | … |
| V8h | Copilot files the Five-part report without inventing Universal claims | … |
| V8i | Copilot reports `A-PASS` or `A-FAIL` | … |
| V8j | Copilot reports overall `PASS` or `FAIL` | … |
| V8k | Copilot confirms no live production/offsite mutation | … |

Arc closure requires all mechanical checks, Kiro conformance `PASS`, Codex
replay `PASS`, Copilot `A-PASS`, and Copilot overall `PASS`. Any uncertainty,
unresolved data-loss path, false-green path, target mismatch, or
required-control failure is `A-FAIL / FAIL`.

## Supplementary suite

Run the repository's broader applicable suite only after V0–V8. Record failures
honestly, but do not use a broad green result to override a required safety
failure.

## Evidence log

```text
VERIFY-complete-data-backup-correction-v2
subject: <full SHA>
base: 1ad99585060d62b2dfc22b50cdbbefdd20b0b8b7
failed_crush_tip: b6284ad9ac42e0bb554cd2d44d512b01bad748f2 (Codex FAIL — immutable)
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
Codex replay: PASS|FAIL
Copilot A: A-PASS|A-FAIL
Copilot overall: PASS|FAIL
Live mutations: none|FAIL
```

Verifier performs no cleanup or correction beyond temporary hermetic test
fixtures.

Active phase lane must stop here. Await HITL.

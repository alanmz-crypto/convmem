# Implementation Handoff: Codex rollout admission to the guarded incremental route

**Arc: Codex (#286).**
**Date:** 2026-10-10
**Author:** Claude (Opus 5.5), design author
**For:** Cursor (implementation)
**Authorization:** Ryan, 2026-10-10. Implementation grant (gate 2) given in
chat after Kiro design PASS at `9e91973`. The grant covers hermetic
implementation and tests only.

---

## Resume state

| Field | Value |
|-------|--------|
| **State** | `NOT_STARTED` |
| **Design branch** | `docs/2026-10-10-issue-286-codex-rollout-admission-design` (design, STATUS, this handoff) |
| **Implementation branch** | `feat/2026-10-10-issue-286-codex-rollout-admission` (create it; see Branch convention) |
| **Tip SHA** | design branch tip containing this file; base `origin/main` `348ec0b` |
| **Push status** | design branch pushed to origin |
| **PR** | not opened (design PR optional; implementation PR not authorized yet) |
| **Ryan GATE** | none to start. After implementation: Copilot targeted audit and Kiro exact-tip recheck, then Ryan's PR/merge decision. Stage 1, Stage 2 and activation are separate Ryan grants. |

---

## What to build

Let Codex rollouts created after an explicit cutoff use the existing guarded
incremental route from their first index. Then an append reprocesses only the
newly affected chunks instead of the whole file, which removes the repeated
paid DeepSeek summarize/distill calls and the 9–12 GiB index children seen in
production. Rollouts created before the cutoff keep today's legacy route
byte-for-byte. Refusals become terminal and visible instead of respawning on
every append.

**Why this exists:** Codex rollouts caused 133 watcher re-indexes in nine days
(one file 44 times) and every child that hit the 12 GiB cap. The guarded live
route (PR #365) admits only exact-path Kiro sources, and new rollout filenames
cannot be granted in advance.

**Normative design:** `docs/plans/DESIGN-issue-286-codex-rollout-admission.md`
(D1–D8, §7–§10). **Binding conditions:** that design's §13 (Kiro). Read both
before the first edit. Where this handoff and the design disagree, the design
wins; report the conflict.

---

## Integration points (verified at `348ec0b`)

| Change | Location |
|---|---|
| Parse and validate the `[index.incremental_jsonl.codex_rollout_admission]` table | `config.py:377` (`incremental_jsonl_settings`), next to `live_sources` at `:413–428` |
| Pure admission predicate (D1 checks 1–4) | new `incremental_jsonl_codex_admission.py` |
| Selection: `path_key in live_sources or admits(path_key)` | `incremental_jsonl.py:2247` |
| Format gate opens for admitted paths only | `incremental_jsonl.py:2249`; coordinator `routed_formats` at `:535–537` (used by `decide_eligibility`, `:404`); `incremental_jsonl_formats.py:59–80` |
| D1 check 5 (`session_meta` identity) on the parsed prefix, before provider work | coordinator, after `parse_complete_prefix` |
| D4 frontier-subset invariant plus chunk backstop; D5 size ceiling | coordinator, before the provider phase (`run`, `incremental_jsonl.py:2013`) |
| Child refusal marker | `incremental_jsonl.py:2276` (`live_route_refused`) and its CLI exit path |
| Watcher refusal class: threshold 1, terminal by path (digest is evidence) | `watch.py:274–292` (classification), `:388` (`record_failure`), `:575`/`:593` (`_record_ready_path_failure`) |
| Doctor `incremental_refusals` check | `doctor.py` |
| One structured line per admitted run (D6) | coordinator result emission; counters already exist (`CallCounters`, `incremental_jsonl.py:156`) |

---

## Specification

### Inputs

Configuration (validation fails closed; see design §5):

```toml
[index.incremental_jsonl.codex_rollout_admission]
root = "/home/lauer/.codex/sessions"     # canonical, no symlink component
admitted_after = "<UTC ISO-8601 with Z>"  # timezone-aware; naive is an error
max_transform_chunks_per_run = 20         # positive int
max_source_bytes = 268435456              # positive int
```

The table requires `enabled = true` and a positive `embed_dimension`. If the
table is present while `enabled` is false, that is a configuration error.

### Behavior

```
route(path):
  if not enabled: legacy                                  # unchanged
  if isolated env: existing hermetic path                 # unchanged (RC-2)
  selected = path in live_sources or admits(path)         # admits = D1 checks 1–4, pure
  if not selected: legacy                                 # RC-1, byte-for-byte
  coordinator(path):
    view = parse_complete_prefix(path)
    if codex admitted and session_meta check fails:       # D1 check 5
        refuse("codex_session_identity_mismatch")         # Kiro condition 2: never legacy
    if source bytes > max_source_bytes: refuse("source_too_large")
    plan = frontier(checkpoint, view)
    if transformed chunks not a subset of the frontier: refuse("frontier_violation")
    if len(transformed) > max_transform_chunks_per_run: refuse("transform_chunk_cap")
    ... existing transaction / apply / checkpoint ...
  any non-committed/unchanged outcome -> live_route_refused (existing :2276)
```

Admission (D1), all required:

1. The format is `jsonl_codex_rollout`.
2. The canonical path is strictly under `root`, with no symlink component.
3. The basename matches
   `^rollout-\d{4}-\d\d-\d\dT\d\d-\d\d-\d\d-<uuid>\.jsonl$`, the uuid is
   version 7, and its time is within 120 s of the filename time read as host
   local time.
4. The uuid time is at or after `admitted_after`.

Check 5 runs on the parsed prefix: the first complete record is
`session_meta`, `payload.id` equals the filename uuid, and
`payload.timestamp` is within 120 s of the uuid time.

### Output and contract

- **Child refusal:** stderr carries `live_route_refused:<outcome>` plus a
  nonzero exit (or a dedicated exit code). The watcher parses either.
- **Watcher:** a refusal records class `refused` and quarantines the path
  immediately. It persists `outcome`, `prefix_sha256` and `first_refused_at`
  as evidence. A later event on that path never spawns a child, whatever its
  digest (design §13 condition 3, amended 2026-10-11). Clearing a quarantine is operator-only. If the #308
  terminal-failure fix is already on `main`, reuse its mechanism (Kiro
  condition 4).
- **Doctor:** the `incremental_refusals` check reports PASS with zero
  quarantined refusals and WARN listing path, outcome and digest prefix
  otherwise. Never print source contents.
- **Run log (D6):** one JSON line per admitted run with format, outcome,
  chunks reused, transformed and pruned, provider requests and tokens by
  provider, source bytes, and elapsed time.

### Constants

```python
ADMISSION_SKEW_SECONDS = 120
DEFAULT_MAX_TRANSFORM_CHUNKS_PER_RUN = 20
DEFAULT_MAX_SOURCE_BYTES = 256 * 1024 * 1024
```

---

## What NOT to build

- No bulk bootstrap, and no generalization of
  `scripts/bootstrap-incremental-jsonl.py` (v1.1, separate).
- No Cursor JSONL, Crush SQLite or Codex `history.jsonl` routing.
- No streaming parse and no automatic exact-list writer.
- No change to chunking, retrieval, dedupe, Kiro exact-path semantics or the
  hermetic isolation boundary.
- No edits to `~/.config/convmem/config.toml`, systemd units or the runtime
  worktree. No watcher start, no live `convmem index`, no provider call. Do
  not open a PR.

---

## Test expectations

Hermetic only: fake providers, temporary real Chroma, network denied,
`tmp_path` roots. Never use the live corpus or `~/.codex`.

1. **Predicate matrix** (`tests/test_incremental_jsonl_codex_admission.py`):
   - wrong format;
   - outside root; symlink component; regex miss;
   - uuid v4; uuid/filename skew over 120 s;
   - `admitted_after` boundary (equal admits; 1 ms before is legacy);
   - same-session prefix copy with a later filename time (legacy).
2. **Check 5:** an admitted path whose `session_meta` id or timestamp
   mismatches gives a visible refusal and never a legacy tuple (Kiro
   condition 2).
3. **RC-1, RC-2, RC-3 parity:**
   - a non-admitted rollout gives a byte-identical legacy result;
   - the Kiro exact-path tests are unchanged;
   - the existing RC-2/RC-3 tests pass.
4. **Admitted lifecycle** (extend `tests/test_codex_incremental_jsonl_route.py`):
   - the first run transforms all chunks;
   - an append transforms only the frontier;
   - an unchanged rerun makes zero provider calls;
   - a `compacted` record mid-session keeps continuity;
   - truncation and rewrite refuse.
5. **Race:** an admitted path with an existing `processed.json` entry and no
   checkpoint refuses. The watcher quarantines once and does not respawn on
   three later events, and the doctor check WARNs.
6. **Quarantine is by path** (amended 2026-10-11, design §13): after one
   refusal, three later appends that each change the digest spawn zero
   children, and the watcher computes no digest to decide the skip.
7. **Guards:** a frontier-subset violation, chunk cap overflow and size
   ceiling overflow each refuse with zero provider calls.
8. **Config validation:** every fail-closed case in design §5.
9. **Rollback:** after re-enabling, a previously admitted path refuses
   visibly.

---

## Acceptance criteria

- [ ] All six Kiro conditions in design §13 hold, each cited by test name in the handoff-back.
- [ ] Test expectations 1–9 pass.
- [ ] The existing incremental, watch, Kiro-route, RC and governed-inventory tests pass, and the repo's CI-equivalent pytest run is green.
- [ ] The Pylint regression gate, secret scan and critical invariants pass. Refresh any writer-coverage inventories that drift (`docs/plans/*WRITER-COVERAGE-INVENTORY*`).
- [ ] No live resource touched: config, systemd, runtime worktree, corpus and providers are all unchanged.
- [ ] Handoff-back: branch, pushed tip, `git log origin/main..HEAD --oneline`, the test list mapped to conditions, and a copy-paste PR title and body for Ryan.

---

## Branch convention

```
feat/2026-10-10-issue-286-codex-rollout-admission
```

- If the design PR has merged: `convmem work start feat issue-286-codex-rollout-admission --worktree`.
- Otherwise, branch from the design branch tip so the normative docs are present:
  `git switch -c feat/2026-10-10-issue-286-codex-rollout-admission origin/docs/2026-10-10-issue-286-codex-rollout-admission-design`.
  Use a separate worktree; don't switch a shared checkout.
- Push after every commit with an explicit refspec:
  `git push -u origin "${branch}:refs/heads/${branch}"`.
- Ryan squash-merges.

---

## Related files

| What | Path |
|------|------|
| Normative design and Kiro conditions | `docs/plans/DESIGN-issue-286-codex-rollout-admission.md` (§13) |
| Inherited live-route design (RC-1–RC-3) | `docs/plans/DESIGN-issue-286-live-activation.md` |
| Arc brief | `docs/plans/STATUS-codex-jsonl-production-integration.md` |
| Related watcher loop | issue #308 |

---

## Leaving / picking up checklist

**Author (leaving):**

- [x] This file committed on the pushed design branch
- [x] `LATEST.md` bullet at top with link and resume state
- [x] `STATUS-codex-jsonl-production-integration.md` Update Log line
- [x] Branch pushed

**Implementer (picking up):**

- [ ] Read the design (D1–D8, §13) and this file before the first edit
- [ ] Create the implementation branch per Branch convention
- [ ] State Goal / role / system state / next action; Arc: Codex

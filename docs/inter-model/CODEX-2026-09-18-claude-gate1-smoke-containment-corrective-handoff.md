# [Arc Claude Watch Parity] Implementation Handoff: close Gate 1 smoke containment gap

**Date:** 2026-09-18
**Author:** Codex planning lane
**For:** Cursor implementation lane; then GitHub Copilot targeted safety audit
**Authorization:** Ryan requested a handoff for the next agent after the
bounded synthetic smoke report. This is a corrective to that authorized
hermetic preparation, not a live-source or PR grant.

---

## Resume state

| Field | Value |
|---|---|
| **State** | `IN_PROGRESS` for synthetic containment correction; real-source acceptance remains `NOT_RUN`. |
| **Branch** | Resume `feat/2026-09-18-claude-gate1-real-smoke` in its existing dedicated worktree. Do not switch the shared checkout. |
| **Tip SHA** | Pushed baseline `e4e41caa101e1735e57a316d1e9738bbea6f9d63`; fetch and confirm the tip before editing. |
| **Push status / PR** | Baseline pushed to origin; no PR opened. Push each corrective commit immediately with an explicit refspec. |
| **Ryan GATE** | No live transcript path or read-only preflight grant has been given. Ryan separately owns exact-source preflight, one-shot indexing, and PR disposition. |
| **Track A ingest** | Cursor should attempt its own session-chat index at handoff and report success or failure, separately from this smoke. |

---

## What to build

Make the Gate 1 synthetic `index --file` launcher prove **fail-closed output
containment**, not just successful dispatch. The worker must bind its scratch
`HOME`, effective config, and every mutable CLI target to the fresh isolation
root *before* importing or invoking ConvMem's indexing path. Add negative tests
where a tampered scratch config points at a harmless outside-`tmp_path`
sentinel; the worker must refuse before that target can be opened or changed.
Keep the passing synthetic fixture and deterministic fake providers.

**Why this exists:** Cursor's first smoke implementation at `e4e41ca` passed
seven hermetic tests and reported one synthetic unit. The worker checks the
transcript with `IsolationBoundary.resolve_mutable`, but no corresponding
pre-import validation of config-directed `chroma_dir`, `processed_log`,
`units_export`, state, inventory, caches, or lock paths is visible. Its
production fingerprint helper covers four defaults, not all effective
targets. This is an evidence gap against the original handoff's containment
contract, **not** proof that the observed synthetic run wrote to production.

---

## Integration point

- `tests/claude_gate1_smoke_worker.py:_run_index` currently validates the
  source, then detects format and invokes the launcher. Add the config/output
  preflight at this boundary before importing `adapters.detect`, `convmem`,
  `ingest`, or any module that may load config or create a writer.
- `claude_gate1_smoke.py:run_hermetic_index_cli` currently imports `convmem`
  before its own boundary check; keep the worker's pre-import order explicit
  and make this helper fail closed if called without that validated context.
- `incremental_jsonl_isolation.py` already creates a scratch config and
  refuses `CONVMEM_CONFIG` overrides. **Do not edit this shared Arc Codex
  isolation module.** Instead, reconcile the prior handoff's "explicit
  `CONVMEM_CONFIG`" wording by proving that the isolated `HOME` selects the
  exact generated config and that all effective paths are contained. If that
  cannot be proven without shared-module changes, stop and return a finding.
- `config.py` expands path-valued keys; `ingest.py` consumes the loaded index
  paths. Check actual call sites, including writer locks and optional paths,
  rather than assuming that four default fingerprints are exhaustive.

---

## Specification

### Inputs

- Synthetic Claude JSONL under scratch `HOME/.claude/projects/...` only.
- Fresh isolation root/token and generated scratch config from the existing
  isolation helper. No live source or production credential.
- Adversarial config fixtures under `tmp_path`; outside-root targets must also
  be harmless `tmp_path` sentinels, never actual production locations.

### Algorithm / behavior

1. Before any ConvMem runtime import, check that `HOME`, XDG roots, the
   effective config path, and config bytes are the expected scratch layout;
   reject symlinks, aliases, missing/stale config, and inherited overrides.
2. Parse the effective config with the standard library. Resolve every path
   that the index command could write, including Chroma, processed log, export,
   inventory, incremental state, writer locks, and any relevant cache or
   optional sink. Reject outside-root, symlink, and production aliases using
   the existing isolation boundary. Explicitly check default-derived targets
   not represented as config keys.
3. Only after that preflight, import and run the real CLI with deterministic
   providers and network denial. Preserve the positive synthetic result.
4. Bind evidence to the **subprocess return code**, not only a JSON field
   emitted by the worker; a nonzero or missing worker result cannot PASS.

### Output / contract

- Positive synthetic run: `files_processed=1`, `files_skipped=0`,
  `units_indexed>0`, format `jsonl_claude_session`, zero worker exit, and
  content-free evidence.
- Any unsafe config, path, env, or worker-result mismatch: stable nonzero
  refusal before mutable outside-root access; no fallback to production.
- Keep real-source acceptance `NOT_RUN`. A passing fake-provider run does not
  demonstrate live transcript shape, provider behavior, billing, or Gate 2.

### Constants

No route or format constant changes. Preserve `KIRO_ROUTE_FORMATS` and the
existing shared isolation constants.

---

## What NOT to build or run

- No listing, stat, hash, copy, parse, or index of any real Claude transcript.
  A path mentioned in chat does not constitute a grant.
- No paid provider/network call; no production data/config/lock/watch action.
- No edits to `incremental_jsonl_isolation.py`, `incremental_jsonl.py`,
  `incremental_jsonl_formats.py`, adapters, watcher, `[sources].paths`,
  `[watch].extra_paths`, or Arc Codex files. Stop if this scope is insufficient.
- No Gate 2 work, live canary, PR opening, merge, or declaration of real-source
  acceptance. Ryan owns those later decisions.

---

## Test expectations

Focused tests in `tests/test_claude_gate1_hermetic_smoke.py`:

1. **Scratch success:** current synthetic CLI test remains green and proves
   the exact effective config and all mutable paths resolve under scratch.
2. **Tampered output keys:** redirect each relevant config path to a harmless
   outside-root sentinel; worker refuses before creating or changing it.
3. **Alias/override:** symlinked config or output, mismatched `HOME`/XDG,
   inherited `CONVMEM_CONFIG`, and missing config refuse before CLI import.
4. **Evidence integrity:** nonzero subprocess return, missing/malformed
   payload, or zero units cannot report PASS.
5. **Regression:** existing seven smoke tests and merged Claude adapter tests
   pass; `git diff --check` and repo Python quality gates pass.

Tests must not use a real production path as a write target. Record the exact
commands, counts, and any test that cannot be made hermetic.

---

## Acceptance criteria

- [ ] Every effective mutable target is validated before ConvMem indexing
      imports or writer construction; include locks and default-derived paths.
- [ ] Adversarial scratch-config tests prove refusal and unchanged outside
      `tmp_path` sentinels; the positive CLI path still yields one unit.
- [ ] Explain the scratch-`HOME` config discovery as an explicitly verified
      equivalent to the original handoff's config-binding intent; do not
      weaken the shared isolation guard to set `CONVMEM_CONFIG`.
- [ ] Evidence uses the actual worker exit status and remains content-free.
- [ ] Corrective diff stays within the launcher and its smoke worker/tests;
      targeted GitHub Copilot safety audit can review the exact pushed tip.
- [ ] Live source, real indexing, Gate 2, and production watch remain `NOT_RUN`
      or unchanged, as applicable.

---

## Branch convention

Resume the existing `feat/2026-09-18-claude-gate1-real-smoke` worktree.
Commit the narrow correction and push immediately with
`git push -u origin feat/2026-09-18-claude-gate1-real-smoke:refs/heads/feat/2026-09-18-claude-gate1-real-smoke`.
Do not open a PR without Ryan's separate disposition.

---

## Related files

| What | Path |
|---|---|
| Prior smoke handoff | `docs/inter-model/CODEX-2026-09-18-claude-gate1-real-smoke-handoff.md` |
| Launcher and worker | `claude_gate1_smoke.py`; `tests/claude_gate1_smoke_worker.py` on smoke branch |
| Smoke tests | `tests/test_claude_gate1_hermetic_smoke.py` on smoke branch |
| Shared isolation reference, read-only | `incremental_jsonl_isolation.py` |
| Arc current state | `docs/plans/STATUS-claude-watch-parity.md` |

---

## Leaving / picking up checklist

**Codex (leaving):** commit this handoff and current-state pointers on the
planning branch, push, and report its exact tip. No code or live-source action.

**Cursor (picking up):** read this file and the arc brief, confirm the smoke
branch tip, implement only the containment correction, push, and return a
content-free test packet for targeted GitHub Copilot isolation audit. Do not
request or exercise the one-shot real index grant from this handoff.

**TL;DR [Arc Claude Watch Parity]:** Synthetic Gate 1 indexing works, but
configured output containment needs explicit pre-import proof and adversarial
tests. Cursor fixes that on the existing smoke branch; real indexing stays
closed pending separate Ryan grants and targeted safety review.

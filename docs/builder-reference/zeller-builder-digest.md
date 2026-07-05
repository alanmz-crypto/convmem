# Zeller - builder digest (convmem)

**Source:** *Why Programs Fail* · Chapters 6-8 focus, pp. 130-210

**Read when:** running `convmem doctor`, triaging unresolved observations,
reproducing a failure, comparing good and bad runs, or deciding how to verify
that a fix actually worked.

## Principles

- Debugging is scientific method applied to software. Reproduce the failure,
  form hypotheses, test them, and update the model.
- A bug is not just a defect in code. It becomes visible through an infection
  in state and then through a failure that a user can observe.
- The first job is reproduction. If you cannot reproduce the failure, you are
  not ready to reason about the cause.
- Simplify the case before you chase the cause. Remove irrelevant inputs,
  environment details, and state until the interesting behavior is isolated.
- Observation matters as much as deduction. Logs, traces, debuggers, snapshots,
  and postmortem evidence are part of the method.
- Compare passing and failing runs. The difference between them often exposes
  the bug faster than staring at one failing run in isolation.
- Track problems as records, not memories. A structured report is easier to
  reuse than a story in someone’s head.
- The debugging workflow should be explicit and repeatable. A good process is a
  force multiplier because it turns guesswork into evidence.
- Fixes should be verified against the reproduction. A fix that has not been
  checked against the original failure is not done.

## What this means for convmem

- A failing convmem workflow should be reduced to the smallest reproducible
  shape before architectural conclusions are drawn.
- If a deployment or indexing flow fails, treat the failure like a bug report:
  capture the symptom, identify the reproduction, isolate the cause, and then
  verify the fix.
- A good ledger note is part of the debugging method because it preserves the
  causal chain for future sessions.
- Observations that do not identify the symptom clearly are weak evidence.
- If a failure only happens on one surface, that is still a real failure. The
  surface difference may be the clue, not noise.

## Repro workflow

- Start by recording the exact command or action that triggers the issue.
- Reduce the environment if you can: one repository, one command, one file, one
  surface.
- Compare working and failing states. The delta is often more valuable than the
  failure alone.
- Strip away unrelated signals until the thing that changes is the thing that
  matters.
- Verify the fix by replaying the original failure, not by finding a new happy
  path.

## Observation workflow

- Logs are useful when they help you distinguish causes, not when they simply
  make the output longer.
- Snapshots, state dumps, and “before/after” comparisons are often more useful
  than more guesswork.
- If the symptom is only visible after several steps, keep those steps explicit
  so they can be replayed.
- If the system has multiple surfaces, check whether the bug is in shared logic
  or in the surface adapter.
- If a bug report is vague, the first task is to turn it into a concrete
  reproduction and not to brainstorm fixes.

## Convince yourself with evidence

- A hypothesis is only useful if it predicts the next observation.
- A fix is only useful if the failed reproduction changes in the expected way.
- A root cause is only solid when the observed evidence rules out the obvious
  alternatives.
- A workaround is not the same as a fix. If you install a workaround, record it
  as such.
- “Seems fine” is not a test. Replay the failure.

## Convmem implementation notes

- `doctor` checks infrastructure health before anything else. That is the
  equivalent of verifying the test bench before diagnosing the circuit.
- `brief` is the current-state snapshot that prevents stale assumptions.
- `unresolved` is a triage queue, not a knowledge base. It tells you where to
  look next.
- `ask` and `search` should be used to gather evidence about prior work before
  inventing a new explanation.
- `related()` should be used when the failure has a lineage and you need the
  chain of cause and effect.
- `record` should preserve the repair path and the evidence used to justify it.
- When the builder-reference system is working, a surface should be able to say
  “read the relevant digest first” before a session starts improvising.

## convmem Hooks

- `convmem doctor` is the health check and baseline reproduction step. If it
  fails, the session should not pretend to be in a known-good state.
- `convmem unresolved` is the problem queue. It is the first triage layer for
  “what still needs attention?”
- `brief` is the snapshot. It gives the current state before you start making
  changes.
- `ask` and `search` are hypothesis tools. They help answer “what evidence do
  we already have?”
- `related()` is the evidence chain. Use it to walk from an observation to the
  decisions and fixes that follow from it.
- `convmem record` is the postmortem note. It should capture cause, fix, and
  why the conclusion is justified.
- For agent work, a failure in deployment or indexing should be treated the
  same way as a failing test: reproduce, simplify, observe, then fix.
- Builder-reference digests help by giving the agent a stable mental model of
  what “good” looks like before it starts debugging the repo.

## Anti-patterns for Agents

- Do not jump to a fix before you can reproduce the issue.
- Do not lump unrelated failures into one observation record.
- Do not treat one successful run as proof that the problem is gone.
- Do not bury the original symptom while chasing an architectural explanation.
- Do not skip verification just because the fix “looks obvious.”
- Do not rewrite the diagnosis in terms of the fix. Keep the failure description
  and the repair description separate.

## Worked repro: shell brief vs MCP brief

**Symptom:** Agent reports `unresolved_count: 0` via MCP but shell shows open obs.

**Minimal repro:**

```bash
convmem doctor                    # must exit 0
convmem brief --stdout-only       # note unresolved_count
# In MCP-only client: brief() with same project= slug (or unscoped workspace_local)
```

**Hypothesis ladder:**

1. Doctor failed silently in MCP-only path → run doctor in shell first (Tier A).
2. Different `project=` slug → compare `brief_mode` and `workspace_hint` in JSON.
3. Stale MCP process → restart client; Crush may need `crush.json` reload.
4. Corpus-wide stats zeroed in `workspace_local` mode → read
   `workspace_local_note` in brief payload before comparing counts.

**Verify fix:** replay both paths; counts must match for same slug and cwd.

## Unresolved triage template

Use this shape for every open `obs_*` before editing code:

| Step | Action | convmem tool |
|------|--------|--------------|
| 1. Symptom | One observable sentence | `unresolved` / `brief` |
| 2. Scope | Coordination vs client site | `--site` filter or domain |
| 3. Repro | Smallest command sequence | `doctor` → failing command |
| 4. Evidence | Prior decisions on same thread | `search` / `ask` / `related()` |
| 5. Hypothesis | Predict next observation | — |
| 6. Fix | Minimal change | code / config |
| 7. Verify | Replay repro | same commands |
| 8. Record | Durable fact | `convmem record` + `--approve-last` |

Weak observations skip step 1 or 3 — strengthen the record before filing fixes.

## Observation buckets

**Coordination lane** (default digest scope):

- Domain prefixes: `tooling.*`, `coding.tooling.*`
- No client `site` hostname on obs
- Examples: MCP ritual skips, surface deploy gaps, agent habit soaks
- Pilot run 4 cited **7 coordination unresolved** obs

**Client-site lane:**

- `web_stack.security` or explicit `--site staging2.example.com`
- Run **separate** `convmem unresolved --site …` per hostname
- Do not mix with coordination triage in one narrative

**Infrastructure lane:**

- `convmem doctor` failures: Ollama down, Chroma path missing, embed model absent
- Fix bench before debugging application logic

## Compare passing vs failing runs

Zeller's delta method maps to convmem soaks:

| Pass surface | Fail surface | Likely layer |
|--------------|--------------|--------------|
| Cursor shell + MCP | Crush MCP-only | Crush rules / `global_context_paths` |
| `search_fast` ok | `ask` timeout | synthesis latency / Crush 120s ceiling |
| Repo cwd | Alien `~/Documents` cwd | `workspace_local` brief mode |

Log both runs in the observation — the diff is the clue.

## Builder-reference deploy failures

If an agent ignores digests:

1. Run `bash scripts/verify-builder-reference.sh` — filesystem + sha256 vs repo.
2. Re-run `bash scripts/deploy-builder-reference.sh`.
3. Crush: confirm three paths in `crush.json` `options.global_context_paths`.
4. Cursor: confirm `builder-reference.mdc` `globs` match cwd.
5. Interactive soak prompt (manual): *"Before editing ask.py recency, cite which
   digest applies and one principle."*

Verifier catches stale Crush copies; it cannot prove an LLM read the file.

## Record block discipline

After a verified fix, `convmem record --relates-to <real obs or dec id>` must
separate:

- **Summary:** what changed (one sentence)
- **Rationale:** repro → cause → fix → verification

Do not conflate "we deployed builder-reference" with "agents cite it in UI" —
the latter requires manual soak (see README soak table).

## `convmem doctor` check inventory

[`doctor.py`](../../doctor.py) reuses brief probes — treat as the bench checklist:

| Check | What it validates |
|-------|-------------------|
| `config` | `~/.config/convmem/config.toml` readable |
| Ollama / embed model | nomic-embed-text reachable |
| Chroma | collection count, path exists |
| MCP registration | cursor/crush entries (when probed) |
| Watch RSS | daemon memory ceiling |
| DeepSeek key | distill path (when configured) |

If doctor fails, stop — debugging ask/search while embed is down produces
false negatives (empty results look like ranking bugs).

Run: `convmem doctor` (exit 0 required before ask/search per protocol).

## `list_unresolved` and OPEN_STATUSES

[`unresolved.py`](../../unresolved.py) collects observations where
`evidence_boost` status is in `OPEN_STATUSES`:

- `unresolved`
- `failed_check`
- `failed_verification`

Sorted by severity (boost) then ledger_id. Domain/site filters apply **after**
open detection — wrong filter looks like "no bugs."

```bash
convmem unresolved
convmem unresolved --site staging2.willowyhollow.com   # client lane only
```

For coordination work, run unresolved **without** `--site` first.

## MCP `brief()` gate repro

[`mcp_server.py`](../../mcp_server.py) blocks other MCP reads on alien cwd until
`brief()` succeeds once. Repro for "search_fast works but brief never ran":

1. Fresh MCP process on `~/Documents/...` cwd.
2. Call `search_fast` before `brief()` → expect blocked JSON.
3. Call `brief()` → then `search_fast` → expect hits.

Fix is protocol compliance, not search tuning — log as agent-habit obs, not
retrieval regression.

## Crush `ask` timeout repro

Symptom: `search_fast` returns in seconds; `ask` fails at ~15–120s.

**Minimize:**

```bash
convmem doctor
# MCP ask with short question and evidence on
```

Check `mcp.convmem.timeout` in `crush.json` (120s deployed). If synthesis
model is slow, reduce `_ASK_TOP_K` or add synthesis timeout handling in
[`ask.py`](../../ask.py) (`_ASK_SYNTHESIS_TIMEOUT = 45.0` for MCP).

Compare with shell: `convmem ask "short question"` — if shell passes and MCP
fails, surface adapter or timeout, not Chroma.

## Automated verification scripts (Zeller-style)

After builder-reference deploy:

```bash
bash scripts/deploy-builder-reference.sh
bash scripts/verify-builder-reference.sh      # sha256 + file presence
bash scripts/validate-builder-reference-surfaces.sh  # per-surface config
```

These scripts **verify the fix** for wiring — not agent citation behavior.
Exit 1 on FAIL; WARN on thin digests or missing Kiro CLI.

Log validation date in README when re-running after digest edits.

## `related()` for evidence chains

When an obs references `dec_prop_*`, walk chain:

```bash
convmem related dec_prop_20260629_054023_84ac
```

Use before filing a duplicate obs — the failure may already have a decision
child that supersedes the parent recommendation.

## Graded soak alignment

[`docs/inter-model/VERIFICATION-MATRIX.md`](../../docs/inter-model/VERIFICATION-MATRIX.md)
and `grade-continue-session.sh` encode surface expectations. A builder-reference
pass on Cursor does not imply Continue pass — separate repro per surface.

## Failure report template (paste into obs or PR)

```text
Symptom:
Repro (commands):
Expected:
Actual:
Delta (pass vs fail run):
Hypothesis:
Fix:
Verification (replay repro):
Ledger id (if recording):
```

Forces separation of symptom and fix — Zeller's core discipline.

## Builder-reference interactive soak (manual)

Prompt (all surfaces):

> I'm editing `ask.py` recency behavior. Before proposing changes, cite which
> builder-reference digest applies and one principle from it.

CLI validation (2026-07-01): Cursor/Kiro/Codex/Crush config **PASS** via
`validate-builder-reference-surfaces.sh`. Interactive citation **pending** —
update README soak table after live UI test.

## Scenario: digest deploy regression

**Symptom:** Crush shows old Ousterhout text without `mcp_server.py` gate section.

**Repro:**

```bash
cd ~/Projects/convmem
# edit ousterhout-builder-digest.md
bash scripts/deploy-builder-reference.sh
bash scripts/verify-builder-reference.sh
```

**Expected:** Crush sha256 match PASS for all three copies.

**If FAIL stale:** deploy did not run or wrong `rules` dir — check
`~/.config/crush/rules/` not project-local `.crush.json` override.

## Scenario: alien workspace false zero

**Symptom:** `brief()` reports `inventory.total: 0` on `~/Documents/...` cwd.

**Diagnosis:** `workspace_local` mode zeros global stats intentionally — read
`workspace_local_note` in JSON. Not a doctor failure.

**Verify:** `search_fast(workspace_hint.suggested_search_fast)` + local files —
not `inventory.total`.

## `propose_decision` / record pipeline debug

Legacy name `propose_decision`; current path `convmem record` +
`convmem record --approve-last`. If approval does not index:

1. Check pending queue file under `~/.local/share/convmem/`
2. Run approve command — indexing should follow automatically
3. `convmem search` for new `dec_prop_*` id — if missing, index lag not ranking

Separate indexing bugs from retrieval bugs before reading Manning digest.

## Watch daemon as background infection

High watch RSS fails doctor (`WATCH_RSS_PASS_KB`). Symptom: OOM or slow embed.
Repro: `convmem doctor` watch line; compare PID memory to threshold. Fix bench
before blaming Chroma corruption.

## Coordination obs worked example

Pilot log: 7 coordination unresolved during digest run 4. Triage one obs:

1. `convmem unresolved` — copy ledger_id
2. `convmem related <id>` — parent decisions
3. `convmem ask "what is the open issue for <short title>"` — evidence gather
4. Minimal repro (often one MCP call order)
5. Fix deploy/rules/code
6. `convmem record --relates-to <id>` after replay passes

Do not record "we read the digest" — record the **fix** with repro.

## Surface validation checklist (CLI)

```bash
bash scripts/validate-builder-reference-surfaces.sh
```

| Surface | CLI-validated (2026-07-01) |
|---------|----------------------------|
| Cursor | globs, alwaysApply false, byte-match example |
| Kiro | manual steering deployed (UI soak pending) |
| Codex | AGENTS pointer, codex-cli 0.142.4 |
| Crush | 3 global_context_paths, 120s timeout |

Interactive soak still required for citation behavior.

## `convmem doctor` one-liner for agents

Before any architecture edit session:

```bash
convmem doctor && convmem brief --stdout-only && convmem unresolved
```

If this sequence fails, the bug is infrastructure or config — not the code you
were about to edit. Zeller: fix the bench first.

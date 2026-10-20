# [Arc Codex #286] Kiro incremental Stage 1 packet — review only

**Author / recipient:** Codex Astra → Kiro, 2026-10-20 UTC (Oct 19 CDT).
**State:** `READY_FOR_KIRO_REVIEW`; **live execution: `NO-GO`**.
**Branch:** `docs/2026-10-20-issue-286-kiro-stage1-packet`.
**Authority:** Ryan requested read-only packet preparation, commit and explicit-refspec
push; no PR, config, watcher, index, recovery, or provider action. This is not a
bootstrap grant. Kiro reviews this exact committed revision; execution needs
Ryan's later **“go Stage 1”**, with the exact resources and scope below refreshed.

Ryan gets five ranked, exact-path candidates and a bounded spending proposal.
The smallest first experiment remains K1 plus one genuinely new Kiro session.
The five-source list is a priority cohort, not permission to bypass the original
two-source Stage 1. All five existing sources need paid bootstrap.

## 1. Decision and blocking findings

**Do not spend from this packet yet.** Four operational gates from Kiro's exact
review remain open: final source/grant bindings, a materialized live cohort
ledger, the Oct 13 pending transaction disposition, and a no-other-writer window.
Read-only preparation cannot honestly mark the latter three complete.

Two additional findings affect this packet:

1. **Bootstrap per-source accounting is shadowed by cohort accounting.** At the
   deployed revision, the bootstrap's outer `provider_http_accounting` installs
   `BootstrapOperationJournal.consume_provider_http_attempt`; Kiro's
   `_build_frontier_with_accounting` installs a new context with only the cohort
   callback. `llm.provider_http_accounting` replaces ContextVars rather than
   composing them. Paid transform attempts therefore reach the cohort callback,
   but not the outer bootstrap callback. The proposed 18-attempt K1 bootstrap
   limit and per-operation receipts cannot be treated as enforced/reconciled.
   The aggregate cohort cap still applies. **Separate implementation authority,
   hermetic proof of both caps, and exact-tip review are prerequisites**, not work
   authorized by this packet. Do not work around this by omitting the Kiro policy
   (that changes the transform contract), resetting counters, or enlarging a cap.
2. **The canary meter is an estimate, not Kiro paid-attempt accounting.** Its
   `Done. chunks_indexed` value comes from `IncrementalRunResult.chunks`, including
   reused chunks. Multiplying by two can overcount reuse; retry/failure attempts
   can be missed. Manual bootstrap is outside its watcher-journal input. Section 5
   specifies the accounting required before an operational Kiro canary.

The source-only callback experiment extracted the actual context-manager AST from
`llm.py` into an in-memory namespace: one inner marker produced **outer=0,
inner=1**, then restored the outer hook on exit. It imported no provider/store
module and made no HTTP or corpus call. This corroborates the static call-chain
finding; it is not an end-to-end bootstrap test.

## 2. Evidence and freshness

Runtime and fetched `origin/main`:
`686d50e8e671b773cacc44c14e70aa3cbd822d2e` (read-only runtime HEAD check).
`convmem doctor` exited 0 with warnings, including the still-pending Oct 13
transaction. `brief` and `unresolved` completed. No pytest, live bootstrap,
coordinator construction, index invocation, paid transform, or service
mutation was performed. Session orientation included read-only corpus search. The cohort parser was used only on bytes read from disk,
with Python bytecode writes disabled.

Read these historical documents at their pinned revisions; they are not all on
this branch's `origin/main` baseline:

- Codex's Kiro incremental design, especially §§9–10:
  `docs/plans/DESIGN-issue-286-kiro-incremental-indexing.md` on
  `origin/docs/2026-10-18-issue-286-kiro-incremental-design`,
  `f6a59f9856b6247647e4e598f62ea1c40a174c4a`.
- Kiro's implementation review (Stage 1 spending FAIL, code target `c432408`):
  `docs/inter-model/KIRO-2026-10-18-issue-286-kiro-incremental-exact-review.md` on
  `origin/kiro/2026-10-18-issue-286-kiro-incremental-exact-review`,
  `19901d8c5daf21260735d6144be780242a57a389`.
- The operational STATUS §6, Codex item 5, on
  `origin/docs/2026-10-12-issue-286-stage2-fixes-handoff`,
  `e1679e98b6b5396604edada4d79da8b09d16fc06`.
  Its Oct 19 live observations supersede the older STATUS text on main.

Use `git show <revision>:<path>` to read a pinned document without switching any
checkout. In the deployed source, the CX-A coordinator sidecar test and CX-B
Codex golden-descriptor test requested by Kiro are present; this planning session
inspected them but did not rerun or independently re-certify the implementation.

Observed live config: incremental `enabled=true`, `live_sources=[]`, **no Kiro
policy table**, shared `allow_full_rebuild=true`, Codex admission unchanged,
and **`mutation_proof_observer="shadow"`**. The latter is already enabled and
must not be described as still off. Summarize/distill both use
`deepseek-v4-flash`; embedding is `nomic-embed-text:latest`, 768 dimensions;
chunk size/overlap 60/10; min confidence 0.6. Any model transition requires a
fresh transform binding and packet; the separate proposed Luna pilot is not part
of this operation.

Watcher observed active/enabled, PID 2534672, started Oct 19 21:29:10 CDT;
effective MemoryMax=8 GiB and MemoryHigh=infinity. Configured index children have
12G memory limits. No writer window exists now. Reconcile runs every two minutes;
other installed timers include backup, audit, and cross-project digest. These
observations are an inventory input, not proof that all other writers are fenced.

The [machine-readable evidence](ASTRA-2026-10-20-issue-286-kiro-stage1-evidence.json)
contains the capture time, config/processed/journal hashes, all 28 eligible
processed-path rankings, five source/sidecar identities, and parser results.
It contains no transcript bodies and is **not** a runtime ledger or grant.

Evidence capture: `2026-10-20T03:11:07.946189+00:00`. Observed config SHA-256:
`f83aeec2587db08b672bb4bb53513a333560178a3e608fbceebe02146ba89d08`. This is the **pre-change** digest, not a
valid digest for a later bootstrap configuration.

## 3. Cohort: highest recent legacy exposure

Fixed window: **2026-10-19 03:05:17.189705Z → 2026-10-20 03:05:17.189705Z**.
For each non-excluded Kiro path in `processed.json`, rank by:

`priority = (2 × processed chunks) × watcher dispatches in 24 h × reach`

The dispatch count is the available proxy for recent debounced write frequency,
not a count of filesystem write syscalls or successful paid runs. It comes from
`journalctl --user -u convmem-watch.service` spawn lines within that fixed window.
Reach=1 requires the configured `~/.kiro/sessions` root, no processed exclusion,
and observed dispatch. Timestamped JSONL record counts corroborate activity;
they include tool/lifecycle records and are not multiplied into paid work.

There were 28 non-excluded processed Kiro paths, seven with dispatches in the
window. K1–K5 are the top five: scores 42, 28, 12, 8, 6, totaling **96 nominal
call-equivalents/day of exposure**. The two remaining active-window paths each
score 2; the other 21 score 0. This is a ranking, **not measured spending or a
savings forecast**: chunks grew during the window, writes coalesce, and runs can
skip/fail/retry. Re-rank before execution if the chosen sessions stop receiving
useful work. Cold five-chunk files do not outrank frequently written smaller ones.

All five paths are canonical, owned, readable regular files under the existing
watch root, non-excluded, with valid semantic sidecars. At capture, none had an
incremental state directory/checkpoint/transaction. Complete-prefix hashes equal
full-file hashes (no trailing partial line); the parser found only emitted
messages and intentionally skipped non-message records. The files were stable
across each read, not frozen against future writes.

### K1 — Kiro exact-review #286 incremental

- Exact source: `/home/lauer/.kiro/sessions/0fdb3f7faae1e6f9/sess_1195be52-6ab0-4008-8503-3645fa46bd94/messages.jsonl`
- Full file / complete-prefix SHA-256: `7676d5557986925a888ccd38278bd8c92936fb76f052c645a894e633c463bcee`
- Bytes / complete boundary: **481,907**; accepted messages: **141**;
  processed/current chunks: **3/3**.
- Frequency/reach: **7 dispatches/24 h × 1**;
  **392 timestamped raw records** in the window;
  priority **42**; legacy full re-index **6 nominal calls**.
- Sibling `session.json` SHA-256: `e05c1a1d0b836505a38de4208d3bdc347c492384827aa4f14b5cc9a8fb1312f6`.
  Semantic identity digest: `a211b841bcac8bca5706a3dec0e040626c5a89d6487ce903cd94e6ad47fe64a4`.
- Bootstrap: **6 nominal calls**;
  proposed source lifetime paid cap **18 actual attempts**.
  A small append costs about **2** nominal calls; adding **20** accepted
  messages crosses the next chunk boundary and normally costs **4** nominal calls.

### K2 — Debug Convmem Timeout Issue

- Exact source: `/home/lauer/.kiro/sessions/0fdb3f7faae1e6f9/sess_d6055dc4-fefe-4ce8-b49b-c660a9b1be5f/messages.jsonl`
- Full file / complete-prefix SHA-256: `25871092b76b5effbb3b01e2c02ab5d6a1e5845b09d8f7f6a5196aa1d14d9795`
- Bytes / complete boundary: **322,087**; accepted messages: **89**;
  processed/current chunks: **2/2**.
- Frequency/reach: **7 dispatches/24 h × 1**;
  **261 timestamped raw records** in the window;
  priority **28**; legacy full re-index **4 nominal calls**.
- Sibling `session.json` SHA-256: `15c21dcd35bfc1d6b69d469bc35fb42b471109ea837f73af657b07918420cd79`.
  Semantic identity digest: `819f1f17fffe787d3d8a8cc61da04b84946419cd94873a30ec5fa58ee8b90076`.
- Bootstrap: **4 nominal calls**;
  proposed source lifetime paid cap **12 actual attempts**.
  A small append costs about **2** nominal calls; adding **22** accepted
  messages crosses the next chunk boundary and normally costs **4** nominal calls.

### K3 — Review Kiro Checkpoint Session Digest Fix

- Exact source: `/home/lauer/.kiro/sessions/0fdb3f7faae1e6f9/sess_6c2e4d86-7609-4f6e-b3f5-e101b01d68c4/messages.jsonl`
- Full file / complete-prefix SHA-256: `bf81ed4c4abfe9e602f1a629520a9cd9a7729f4186453e223ee51b74dde1a066`
- Bytes / complete boundary: **298,511**; accepted messages: **68**;
  processed/current chunks: **2/2**.
- Frequency/reach: **3 dispatches/24 h × 1**;
  **191 timestamped raw records** in the window;
  priority **12**; legacy full re-index **4 nominal calls**.
- Sibling `session.json` SHA-256: `f8e3c28741219a3d8b83c20de5aa1c5a6c3e5dd04875a3ed41de4b643d82992f`.
  Semantic identity digest: `78087121dcae14e0439ee02f4f554bbbfb70d0af620e25503cce36457e0a5ce6`.
- Bootstrap: **4 nominal calls**;
  proposed source lifetime paid cap **12 actual attempts**.
  A small append costs about **2** nominal calls; adding **43** accepted
  messages crosses the next chunk boundary and normally costs **4** nominal calls.

### K4 — Automate ConvMem Doctor Refresh After Midnight

- Exact source: `/home/lauer/.kiro/sessions/0fdb3f7faae1e6f9/sess_c5d99720-bd85-449d-b27a-797ba8c81531/messages.jsonl`
- Full file / complete-prefix SHA-256: `b20eb70adb75b7ec2893f208ecd4a82a19be415075ce2ec7c376c54855832c1d`
- Bytes / complete boundary: **483,824**; accepted messages: **183**;
  processed/current chunks: **4/4**.
- Frequency/reach: **1 dispatches/24 h × 1**;
  **132 timestamped raw records** in the window;
  priority **8**; legacy full re-index **8 nominal calls**.
- Sibling `session.json` SHA-256: `ce79bd01d3eff6258f42bc4d772aed953010a2977d7f8b7cc8155962d0f951c5`.
  Semantic identity digest: `6993fb8c246c11b6850894d99ed47adb4e2b9cd95c93352c1514141f6ecdac27`.
- Bootstrap: **8 nominal calls**;
  proposed source lifetime paid cap **24 actual attempts**.
  A small append costs about **2** nominal calls; adding **28** accepted
  messages crosses the next chunk boundary and normally costs **4** nominal calls.

### K5 — Review FILE-STYLE Scope Boundary Rules

- Exact source: `/home/lauer/.kiro/sessions/cbc2d18059e50959/sess_c39d4797-cac2-4ec5-a1ea-16ffea15bd57/messages.jsonl`
- Full file / complete-prefix SHA-256: `c8833c4252b248a50456e12fab63566e3d3a88d222ada90d4338a4db9b192c0e`
- Bytes / complete boundary: **586,499**; accepted messages: **148**;
  processed/current chunks: **3/3**.
- Frequency/reach: **1 dispatches/24 h × 1**;
  **19 timestamped raw records** in the window;
  priority **6**; legacy full re-index **6 nominal calls**.
- Sibling `session.json` SHA-256: `d5bad6c26dcf0a0b0e38444251a1747520f1d8eabc3514bbeb8dbfcd121e7f83`.
  Semantic identity digest: `c0510d136f4f229acb39da54f12a13dce8425fa2a3327e31ed6182a7451f7fd8`.
- Bootstrap: **6 nominal calls**;
  proposed source lifetime paid cap **18 actual attempts**.
  A small append costs about **2** nominal calls; adding **13** accepted
  messages crosses the next chunk boundary and normally costs **4** nominal calls.

K2's current file hash differs from its processed-log key
`7a11f5c9a1ce47a0ab14e3a1fb67d707be7c51d2fb7bc24b3d2adca57ad47ed8`.
It has unindexed changes despite still having two chunks. Grant the current
complete prefix, never substitute the old processed hash. The other four file
hashes matched their processed keys at capture.

**Bootstrap rule:** existing processed entries are legacy evidence, not reusable
semantic-v2 prepared artifacts. All five require `scripts/bootstrap-incremental-jsonl.py`
(the Kiro-only command); ordinary `index --file` cannot silently adopt them.
K1 meets the design's existing-source limit of three chunks and is the first pilot.
The failed historical Kiro bootstrap source `sess_2628159e-d039-4646-a208-0a10a1b3e450`
is not in this cohort; its old grants must not be reused.

**New-source control:** the design also requires one dedicated native Kiro session
enrolled before its first index. This read-only session did not create one and
cannot invent its UUID/path/hash. Before the final execution grant, create it
under a separately authorized stopped-watcher window, identify its real
`messages.jsonl` and `session.json`, prove absence of prior processed/projection
lineage, and review an addendum binding it as N1. An already-indexed “recent”
session is not a substitute. N1 must be ≤60 accepted messages initially, one
chunk, two nominal paid calls, proposed six-attempt initial limit. N1 adds no
120-call cap replenishment.

The five-source config below is the requested priority-cohort proposal.
**Original Stage 1 enrolls only K1 and the later bound N1.** K2–K5 require accepted
pilot evidence plus Ryan's explicitly scoped expansion grant (or an explicitly
reviewed amendment of the original Stage 1). This packet does not silently rename
Stage 2 as Stage 1.

## 4. Exact proposed configuration, ledger, and bootstrap binding

### Post-bootstrap cohort configuration (proposal; do not apply)

Replace the existing `live_sources=[]` value in the existing
`[index.incremental_jsonl]` table with the following five entries for a later
explicitly granted whole-cohort operation. Do not create a duplicate parent table.
For the original pilot, that list instead contains only K1 plus the reviewed N1.
Keep other existing parent keys and Codex admission values unchanged.

```toml
live_sources = [
  "/home/lauer/.kiro/sessions/0fdb3f7faae1e6f9/sess_1195be52-6ab0-4008-8503-3645fa46bd94/messages.jsonl",
  "/home/lauer/.kiro/sessions/0fdb3f7faae1e6f9/sess_d6055dc4-fefe-4ce8-b49b-c660a9b1be5f/messages.jsonl",
  "/home/lauer/.kiro/sessions/0fdb3f7faae1e6f9/sess_6c2e4d86-7609-4f6e-b3f5-e101b01d68c4/messages.jsonl",
  "/home/lauer/.kiro/sessions/0fdb3f7faae1e6f9/sess_c5d99720-bd85-449d-b27a-797ba8c81531/messages.jsonl",
  "/home/lauer/.kiro/sessions/cbc2d18059e50959/sess_c39d4797-cac2-4ec5-a1ea-16ffea15bd57/messages.jsonl",
]

[index.incremental_jsonl.kiro_session]
max_transform_chunks_per_run = 4
max_source_bytes = 1048576
allow_full_rebuild = false
cohort_ledger_path = "/home/lauer/.local/share/convmem/incremental-jsonl/cohorts/kiro-stage1-2026-10-20.json"
cohort_max_paid_http_attempts = 120
cohort_operation_id = "kiro-stage1-2026-10-20-v1"
```

The four-chunk and 1 MiB limits are deliberately narrower than the design's
20-chunk/256 MiB defaults: they admit every measured bootstrap above (largest
file 586,499 bytes; largest bootstrap four chunks). They also allow up to four
uncached chunks per append run; exceeding either limit is a hold, not permission
to raise it. Kiro's explicit `allow_full_rebuild=false` overrides the current
shared true flag for admitted Kiro sources. Do not change the shared flag as
part of this packet.

### Bootstrap has a different configuration phase

The existing script requires `incremental.enabled=false` on entry, then overlays
`enabled=true`, exactly `[source]`, grant dimension, and `allow_full_rebuild=false`
in memory. It also requires the watcher **inactive AND disabled AND MainPID=0**.
Simply adding the post-bootstrap table to today's enabled live config will not
work. A later exact configuration proposal must name both phases:

1. With all writers fenced, use the shared config with `enabled=false`,
   `live_sources=[]`, and the complete Kiro policy table above retained as raw
   TOML. **Temporarily omit the entire `codex_rollout_admission` table** in this
   phase: leaving it present with `enabled=false` fails configuration parsing
   with `codex_admission_requires_enabled`. Preserve its exact current values
   for the later, separately bound post-bootstrap config (root
   `/home/lauer/.codex/sessions`, `admitted_after="2026-10-12T04:04:00Z"`,
   `max_transform_chunks_per_run=20`, `max_source_bytes=268435456`). On initial
   parse the unselected Kiro policy is dormant; the script's selected-source
   overlay activates it. This temporarily disables normal Codex incremental
   routing too, so **no ordinary index command may run in this phase**. Ryan's
   final exact config grant must explicitly include this temporary omission
   and restoration; a generic Kiro source-enrollment grant is insufficient.
2. For each separately granted bootstrap, derive the binding from that exact
   on-disk config **and the effective in-memory overlay**, using the corrected,
   reviewed runtime. Execute sequentially, never concurrently.
3. After the granted bootstrap phase and no pending transaction, restore the
   exact preserved Codex admission table and `enabled=true` in the reviewed
   post-bootstrap config, selecting only the grant-listed Kiro sources.
   Manual runs remain in the writer window. Restarting the watcher is a separate
   Stage 2 grant; this packet does not authorize it.

Do not copy the current config digest into a grant. Do not switch distill models,
revert shadow mode, or use a v1 descriptor to bypass the accounting finding.

### Durable cohort ledger: exact destination and initial content

The live destination proposed above does **not** exist as a result of this work.
The following is its reviewable initial content, not a claim of materialization:

```json
{
  "version": 1,
  "operation_id": "kiro-stage1-2026-10-20-v1",
  "reserved": 0,
  "consumed": 0,
  "max_paid_http_attempts": 120
}
```

After Kiro review and the exact operational grant, the executor must materialize
it with an owned non-symlink 0700 parent / 0600 file, file fsync, atomic publication,
and parent-directory fsync; capture its SHA-256 and validate its operation/cap
before any paid dispatch. Refuse unexpected existing contents rather than
resetting them. Register the JSON, sibling `kiro-stage1-2026-10-20.lock`, and
publication temp `kiro-stage1-2026-10-20.json.tmp` as exact mutable resources in
the grant/backup inventory. They are outside individual source-state directories;
the existing bootstrap receipt's `_mutation_inventory` does not enumerate this
cohort ledger, so the final packet needs explicit supplemental evidence.

Use one operation identity and cap for the complete canary, including bootstrap,
retry, failed HTTP attempts, recovery, and any authorized expansion. Charge
`consumed + reserved`; interrupted reservations remain charged. No refund,
zeroing, new identity, or increased configured ceiling is an implicit recovery
step. The implementation takes the ceiling from settings on each reservation,
so preserving the exact config is part of enforcing the reviewed total.

### Paid-call plan

At current content sizes: K1–K5 initial transforms **6+4+4+8+6 = 28** nominal
DeepSeek calls. Proposed per-source bootstrap hard limits are **18/12/12/24/18**
actual HTTP attempts (84 combined). These are proposed allocations, **not valid
hard limits on the current runtime**, because of the callback replacement in §1.
After correction, both the per-source journal and shared cohort must veto
before dispatch; verify no path can charge only one and evade the other.

For original Stage 1 (K1+N1), initial work is **8 nominal**, with a proposed K1 bootstrap limit of **18** and
an N1 initial allocation of **6**, all within the same **120** lifetime cohort cap. If all
five existing sources and N1 are later granted, initial work is **30 nominal**;
proposed initial allocations total **90**, leaving **30** attempts for appends
if those allocations were respected. Stop and report
INCONCLUSIVE if that remainder cannot finish the evidence requirements; do not
replenish it automatically.

An unchanged rerun or fully prepared replay must add **zero** paid attempts.
With 60/10 chunking, only the last partial chunk and newly exposed chunks normally
change: two nominal calls for a short append, four for the specific boundary
crossings listed above. At the configured four-chunk maximum, one append can
plan at most eight nominal calls, but retries can exceed eight actual attempts;
the **remaining cohort budget**, not nominal math, is the durable ceiling.
The normal new-source route also has no independent six-attempt N1 limit.
That six-attempt figure is a planning allocation, not a hard cap supplied by the
shown config. Kiro must either accept cohort-only enforcement for N1 or require
a separately reviewed pre-dispatch source limit before final grant; the initial
90/30 allocation is not an enforceable partition today.

Per-append actual usage is measured from before/after ledger totals in the
single-writer window. A per-append hard HTTP limit would require explicit
mechanism/review; the current config exposes no such independent field.

A full bootstrap grant is deliberately not minted while blockers remain. The
final packet must bind each source path, complete boundary/hash, sidecar semantic
identity, runtime SHA, post-overlay transform descriptor, on-disk config SHA,
768-dimensional collection/provider binding, fresh exact backup snapshot and
offsite copy, `max_chunks`, source cap, and operation identity. Proposed recovery
allowance is **one** invocation per source, with the original lifetime spend cap
retained; any additional retry/supersession needs a fresh reviewed disposition.
Retain source and cohort attempts together; exclude local Ollama embeds from
paid totals. Gratuity credits do not make DeepSeek HTTP attempts free for limits.

## 5. Canary guard accounting: required behavior, no edit made

The operational scratch files were located at:
`/tmp/claude-1000/-home-lauer-Projects-convmem/4199516e-e787-4f9f-b671-3f42ce73a4ce/scratchpad/canary2/`.

Read revisions: `measure.py` SHA-256
`ab52257a74bdbe17ac4784eb105a93ac944bab3cbd13f4aad26263637d4a3b89`;
`guard24.sh` SHA-256
`45854c34691dbec295699befcceb986a649afe50e256e4250453b103e12573f8`.
The existing guard's window starts `2026-10-19 12:02:40` local time, lasts 24 h,
and uses a 3,000-call estimate. Its sampled latest report showed ~638 total
(526 new-route, 112 legacy), with Kiro still legacy and no stop condition.
That historical guard ceiling does not authorize 3,000 Kiro calls.

`family()` already recognizes Kiro, but `new_runs` treats any successful run
without a legacy marker as new-route. It is not proof of incremental admission.
The coordinator's structured `incremental_codex_admitted_run` event is explicitly
Codex-only; do not require a nonexistent Kiro event or classify by basename
(`messages.jsonl` is shared by every session).

Required accounting contract for a separately authorized guard update:

- Identify selected Kiro runs by **exact canonical source path**, operation id,
  expected config, and checkpoint/receipt outcome. A selected path emitting a
  legacy `[index] ... (N msgs, M chunks)` marker is a stop, even if cheap.
- Kiro cohort spend is the absolute **ledger `consumed+reserved`** for this
  operation, including manual bootstrap before watcher start, failed runs, and
  crash-ambiguous reservations. For the report's since-window delta, subtract a
  recorded ledger baseline; for enforcement always use the absolute total. Never
  reset the total on watcher restart or journal rollover.
- Count completed committed, unchanged, refused, failed, and in-progress Kiro
  runs separately. Do not interpret an unfinished run as zero spend. Missing,
  corrupt, mismatched, decreasing, or unreadable ledger state means STOP/UNKNOWN,
  not zero. Require `0 <= consumed+reserved <= 120` and matching configured cap/id.
- Replace the selected Kiro component in the overall guard estimate with its
  ledger total/delta as appropriate; **do not add it twice** to the old
  `2*done_chunks` estimate. Keep unselected Kiro/Cursor legacy estimates separate.
  Continue to label non-Kiro totals estimates until independently measured.
- Report `bootstrap_paid`, `append_paid`, `retry/recovery_paid` using reconciled
  per-operation receipts and sequential ledger snapshots. The cohort JSON has
  aggregate counters and a last event, not a full per-source event history; it
  cannot alone reconstruct those categories after concurrent writers.
- For nominal savings evidence use transformed versus reused chunk counts from
  supported receipts/cache lineage, and a provider-free full-file parse at the
  same committed prefix. `chunks_indexed` is coverage, not transform work.
- Keep the durable cap as the pre-dispatch enforcement. A 120-second poll can
  report/stop expansion but cannot replace it. No automatic cap extension at a
  24-hour boundary, crash, or new guard invocation.

Future hermetic meter acceptance examples: an unchanged mature source adds zero;
a three-chunk source reusing two adds two nominal calls, not six; two failed HTTP
attempts still add two actual attempts; a crash reservation remains charged;
manual bootstrap before T0 is included in the lifetime total; restart neither
forgives nor double-counts; missing ledger and selected-source legacy both stop.
No guard modification or guard invocation was performed here.

## 6. Oct 13 wedge: no safe irrelevance claim yet

Source:
`/home/lauer/.codex/sessions/2026/10/13/rollout-2026-10-13T17-07-28-01a1374e-6a94-71c1-8e8d-fc2c30c4ec9c.jsonl`.
Source-state directory:
`/home/lauer/.local/share/convmem/incremental-jsonl/0d50863041f0fcd95dc7497d140dd7dceca1babc631838f3ef6fd548db922137`.
Transaction **`46313d437ae4446282a752270770c614`** is **version 1, APPLYING**.

Observed evidence:

- `transaction.json` SHA-256:
  `a0530661c920c17ff22679a43cd94b80e10c97dd9f872a6da47fbf622d4fa7c4`.
  Its bound rollback hash is
  `33ab1c3ba1f7462b326bdfc3e71b7768232f924e4c913f5a78579d4b1851c56a`.
- **`rollback.json` is absent.**
  **`snapshots/46313d437ae4446282a752270770c614` is absent.** Two prepared JSON
  artifacts remain, but are not substitutes for rollback authority or snapshot.
- `retry_state.json` SHA-256:
  `101fc9cee7650568aa29adf13179c68d47f90eed000852972eeea4921be6b90e`;
  error `recovery_unproven`, attempts_on_prefix=3, source_consecutive=2.
- Existing checkpoint is version 1, 13 accepted records, boundary 1,995,036 bytes;
  pending transaction boundary is 6,079,972 bytes. Checkpoint SHA-256:
  `bab59aa6d987690d92e3424a30ab46f306831b97ec9e70fd3bcf2ba11da5d705`.

Kiro tied this to Stage 1 because both adapters mutate the same Chroma collections,
processed projection, export, and dedupe surfaces under shared writer gates.
A source-scoped lock separates coordinator instances, but an APPLYING transaction
with missing recovery authority leaves a potentially torn shared-store baseline.
Kiro's review explicitly left the transaction with its owner and demanded a
no-other-writer packet. A stopped process does not prove its writes are complete.

Current `_roll_forward` first refuses v1 transactions under a semantic-v2
coordinator (`v1 transaction requires original runtime`). Even under a compatible
v1 path, absent bound rollback authority and snapshot prevent proven replay.
`watch --clear-quarantine` would clear a retry/circuit hold, **not repair any of
this**. Do not clear it, delete the transaction, fabricate rollback data, or point
a current runner at it to see what happens.

**Smallest safe resolution to investigate next (separate authority):** recover
only this source's original, hash-matching rollback and exact snapshot from
retained backups/evidence into isolated scratch; identify its authoring runtime;
prove a source-scoped recovery/conversion and non-source preservation there;
then have Kiro review an exact per-source repair packet before Ryan grants any
live repair. Restoring an old whole-corpus backup or merely replaying under the
new runtime is not a minimal repair. If original authority cannot be recovered,
use the already-planned real-data converter disposition; do not manufacture a
journal. This packet neither authorizes that work nor claims it will succeed.

An alternative irrelevance proof would need Kiro to accept verified source-row,
export, processed, and dedupe ownership/disjointness; no active or scheduled
replayer; stable non-source before/after baselines; preserved immutable wedge
evidence; and an explicit grant that keeps the source held throughout Kiro work.
The v1 missing-authority state and today's active writers prevent that proof
here. Therefore **wedge gate remains FAIL/UNRESOLVED**, not waived because it is
Codex rather than Kiro.

A second retained transaction exists for excluded historical Kiro source
`sess_2628159e-d039-4646-a208-0a10a1b3e450`: version 1, `transform_failed`, transaction
`18d83bf3246c4c19b823e2cd950fe8c0`. It is outside this cohort. Inventory and preserve
it when establishing “no pending transaction”; require an explicit accepted
non-interaction disposition or resolution rather than claiming the global
transaction census is empty. Do not reuse its prior bootstrap/successor grant.

## 7. Preconditions, stop conditions, and rollback limits

These are obligations for the later executor; none is permission to act now.

### Before Ryan's final execution decision

1. Kiro reviews this exact packet and rules on the accounting finding, original
   two-source scope versus five-source expansion, wedge disposition, and guard
   contract. Any code correction follows its own implementation/review/merge/
   deployment authority. Rebind this packet to the resulting runtime.
2. Complete the N1 source addendum if following original Stage 1; refresh all
   selected hashes, accepted counts, exclusions, prefix and sidecar identity,
   source ownership/symlink checks, pending-state census, and exact configuration.
   Do not freeze a source merely by writing its hash in a document.
3. Obtain fresh complete-data local and offsite backups covering source+sidecar,
   Chroma collections/vectors, export, processed/dedupe/failure ledgers, all source
   checkpoints/prepared/snapshots/transactions, cohort accounting, and config.
   Revalidate exact snapshot ids, common tree/copy lineage, timestamp and coverage
   immediately before the operation. Doctor reported local
   `18cb57f144633643615cf46dfaf024c3c4bc857f2093f134a3e726c46db57204`
   and offsite
   `79b21ce255da0f833a573ec83ec521b7036ec06ffabd0fbae125bdbfacf6b7f1`
   as covering the day; this session did not independently verify their contents
   or bind them to a grant. They are evidence leads, not evergreen backup authority.
4. Bind the exact writer window and operations in Ryan's “go Stage 1”: watcher
   disable/stop and drain, timer/service pause list, ordinary CLI/MCP/manual writers,
   reconcile/refine/purge/digest work, end conditions, and who owns restoration.
   Watcher being inactive alone does not fence manual indexers or a scheduled
   reconciler. Coordinate with the existing canary-guard owner so its polling does
   not race the controlled stop or classify an intentional pause as a new failure.
   Read-only packet preparation grants none of those controls.
5. Materialize and validate the live cohort ledger, final source grants, and
   supplemental ledger mutation inventory after approval. Require no pending
   selected-source transaction and no unresolved shared-store transaction hazard.
   The current two retained transactions must have a reviewed disposition first.

### Manual Stage 1 sequence after all gates are satisfied

Hold transcript writers during hash-bound bootstrap; source locks block competing
indexers, not Kiro's own appends. Bootstrap K1 once, validate coverage and original
retrieval, then prove unchanged zero-paid rerun. Admit N1 before its first index
and validate initial/unchanged behavior. Release only the intended transcript
producer to add meaningful content, hold it again for each deterministic check,
and test the chunk-boundary append plus stable-history reuse. Never fabricate
messages into a user's transcript or induce live crashes. Keep source locks
through admission/transform and shared writer locks only around appropriate store
work; no provider call inside a Chroma write scope. Record sequential ledger
before/after values and receipts at every step.

Proposed numeric operating limits for Kiro review: **60 minutes** for the manual
window; **15 minutes** per completed run and accepted-prefix lag; **2 GiB process
RSS** for each single-source worker (small ≤1 MiB inputs); **30 seconds** maximum
mixed-collection visibility during commit; **5 minutes** for a separately granted
recovery to reach a proven state. These are proposed stop thresholds, not measured
performance claims or new systemd settings. Observe without killing a writer
inside APPLYING: stop further dispatch, preserve journals, and follow the reviewed
recovery path. If visibility/lag cannot be measured, mark acceptance INCONCLUSIVE.

Watcher behavior is a later grant. Settings are parsed from the watcher's startup
config dict on each event; the file is not hot-reloaded. Newly enrolled sources
need a separately authorized restart. `session.json` events forward to the
selected sibling transcript only. Watch roots stay unchanged; unselected sources
remain legacy. Stage 2 needs its own 24-hour window, at least ten completed append
runs, one mature source, one restart, and one compatible non-transform runtime
transition **without pending transactions**, within the reviewed remaining budget.
Insufficient workload or budget means INCONCLUSIVE, not automatic expansion.

### Stop and hold

Stop new dispatch on any cap exhaustion/mismatch/unreadable ledger, uncharged
attempt, source/sidecar/config/runtime/model/backup drift, unexpected writer,
selected-source legacy route, missing history or unexplained raw-line coverage,
identity/frontier/recovery refusal, newly pending transaction, native fault/OOM,
quarantine, repeated sidecar failure, or operating-limit breach. Explain all
holds. Reconcile actual attempts including failed and crash-ambiguous requests.
Check retrieval of older and appended turns and non-source vectors/rows; a cheap
run or successful exit alone is not acceptance.

### Rollback limits

Disabling enrollment/config does not reverse paid calls, partial projection
writes, or a committed semantic-v2 migration. Removing `live_sources` and
restarting the watcher can re-enable legacy full re-indexing; it is not safe
containment by itself. Keep the selected paths/writers held until disposition.
Do not reset the cohort ledger, delete pending state, garbage-collect prepared
artifacts, run a v1 converter, or restore shared files wholesale. Preserve the
original recovery authority. Any whole-store rollback risks other sources and
requires its own exact restore grant. Source-scoped rollback/replay is permitted
only with verified retained authority, compatible runtime, lifetime budget,
non-source invariance evidence, and Ryan's reviewed scope.

## 8. Verification of this planning artifact

- `git diff --check` passed. The diff is documentation plus one JSON evidence
  artifact; no code/config/runtime/guard changes are included.
- All five source and sidecar hashes were re-read and matched the evidence;
  ownership, regular-file type, canonical path/no symlink components, and lack
  of processed exclusions were checked. All source-state directories were absent.
- Arithmetic checked: 14 chunks, 28 nominal bootstrap calls, 84 proposed
  per-source bootstrap attempts, and 96 ranking call-equivalents in the fixed
  window. These checks do not turn estimates into measured paid work.
- The proposed TOML and JSON parse; sources, cap, operation id and ledger path
  agree. All five fit the proposed chunk/byte limits. The live ledger remains
  absent. New packet/STATUS/LATEST links resolve.
- The actual `incremental_jsonl_settings` parser accepted the proposed normal
  table and the disabled-bootstrap/per-source-overlay sequence **in memory**.
  It rejected disabled bootstrap with the live Codex table retained, then
  accepted it when that table was omitted as specified in §4. No config was
  written. No coordinator/store/provider was constructed for this check.
- The actual accounting context function's in-memory nested-callback probe
  corroborated the source-cap finding (outer callback zero; inner callback one).
  Runtime call sites: `scripts/bootstrap-incremental-jsonl.py:547`,
  `incremental_jsonl.py:753`, `llm.py:65`; scope is deployed baseline `686d50e`.
- Implementation tests, paid canary evidence, backup-content validation, live
  recovery, and Kiro's independent packet review remain unperformed here.

## 9. Kiro handoff and acceptance request

Review this packet's commit on
`docs/2026-10-20-issue-286-kiro-stage1-packet`, against deployed baseline `686d50e`.
Please issue separate verdicts for **packet accuracy/completeness** and **Stage 1
spending readiness**. Confirm the callback/cap finding from the call chain; review
the five-source ranking, proposed 120-attempt envelope, N1 addendum requirement,
ledger materialization procedure, missing wedge authority, and guard accounting.
Do not execute the packet or infer a spend grant from a review PASS.

Next route: Kiro packet review → Ryan decisions on prerequisites/scope → separately
authorized correction or recovery work as needed → refreshed exact packet → Ryan's
“go Stage 1”. No PR was requested. No Track A index command is run here because
Ryan explicitly prohibited index actions; the watcher may capture the chat under
its existing policy. No record block or new operational log is produced.

I finished: [Arc Codex] read-only Stage 1 packet preparation.
Next step: Kiro reviews this exact packet; live execution stays NO-GO.
Next lane: Kiro, then Ryan for the remaining grants.
See my work: `docs/inter-model/ASTRA-2026-10-20-issue-286-kiro-stage1-packet.md`.

**TL;DR:** [Arc Codex] Five exact sessions rank highest for recent legacy exposure
and need 28 nominal bootstrap calls. Proposed cohort cap: 120 actual paid attempts.
The bootstrap hook composition, missing Oct 13 recovery authority, new-source
binding, materialized ledger, guard accounting, and writer window still block
spending. This packet authorizes no execution.

<!-- src: ./ASTRA-2026-10-20-issue-286-kiro-stage1-evidence.json — read-only source and config capture -->
<!-- src: ../../scripts/bootstrap-incremental-jsonl.py, ../../bootstrap_safety.py, ../../incremental_jsonl.py, ../../llm.py, ../../incremental_jsonl_cohort_budget.py — deployed accounting and recovery contracts -->
<!-- ref: ../plans/STATUS-codex-jsonl-production-integration.md, ./LATEST.md — next-lane routing -->

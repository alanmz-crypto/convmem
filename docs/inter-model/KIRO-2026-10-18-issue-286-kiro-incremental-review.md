# [Arc Codex #286] Kiro review — Kiro session incremental indexing

**Reviewer:** Kiro, 2026-10-18. **Design under review:**
`docs/plans/DESIGN-issue-286-kiro-incremental-indexing.md` at `f6a59f9` on
`origin/docs/2026-10-18-issue-286-kiro-incremental-design`.
**Baseline verified against:** `origin/main` `07117ed`
(PR #388 time-based admission, #399 semantic v2, #402 rebuild-when-allowed,
#396 Kiro exact-path recovery parity — all merged).
**Scope:** review-only. No implementation; new branch from `origin/main`; no PR.

**Verdict: PASS-with-conditions** for implementation (later Execute grant).

## Consequence for Ryan

Codex proposes to bring Kiro sessions onto the same incremental v2 route Codex
already uses, by **exact-source enrollment** (not inferred birth time), a small
**paid bootstrap** of existing sessions (~36 provider calls for the recent
ten-source cohort; ~84 for all 18 non-excluded indexed sessions), and a staged
canary. Normal Kiro rebuilds stay **off** even though the shared
`allow_full_rebuild` is currently `true` for Codex. The headline trade-off,
stated plainly in the design and which I confirm is the right call: **every new
Kiro session must be manually enrolled before its first index, or it falls to the
legacy full-re-index route.** That is acceptable for a bounded first rollout; it
is not a complete answer to the Canary-2 burn (~186 legacy paid calls / 24 h,
Cursor 29 runs + Kiro 23 runs) on its own.

## Verification I performed

I checked the design's load-bearing code claims against baseline `07117ed`:

- **v2 is Codex-only today (§2, §4) — CONFIRMED.** `incremental_jsonl.py:639`:
  `self.transform_v2 = bool(self.codex_admitted_live)`. Kiro cannot reach v2
  without the exact change the design proposes (an explicit selected-format
  capability replacing the `codex_admitted_live` condition). This is the
  design's central technical move and the baseline matches its premise.
- **session.json is hashed in full (§4 sidecar concern) — CONFIRMED.**
  `_revalidate_live_prefix` computes `digest = _sha(sibling.read_bytes())` over
  the entire sidecar and raises `source_identity_changed` on any difference.
  Kiro stores mutable UI fields (`lastModifiedAt`, title, status) there, so the
  design's claim that "an unrelated sidecar change during paid work can refuse
  the run" is real, and its `kiro-complete-prefix-v2` semantic-digest fix targets
  the actual code path (capture + `_revalidate_live_prefix`).
- **Bootstrap computes its binding independently (§3, §5) — CONFIRMED.**
  `scripts/bootstrap-incremental-jsonl.py:_effective_binding` resolves provider/
  model/dimension independently of the coordinator, so the design's insistence
  that "the bootstrap script, grant validator, supersession checks, and
  coordinator must use the same descriptor builder" is a real correctness
  requirement, not a theoretical one.
- **Checkpoint migration is hermetic-only (§5) — CONFIRMED.**
  `incremental_checkpoint_migration.py` calls `require_hermetic_migration_context()`
  which raises `migration_requires_hermetic_root`. The design correctly treats it
  as not a live tool and refuses live v1 conversion.
- **Codex admission is identity-based, not mtime (§2) — CONFIRMED** against
  `incremental_jsonl_codex_admission.py` (UUIDv7 time + filename time + in-file
  session identity). This is why the design cannot clone it for Kiro: Kiro parent
  IDs are UUIDv4 (design: 678/678), with no comparable birth proof.
- **Commit/recovery seams (§5, §8) — CONFIRMED** the shared production-boundary
  recovery (PR #396) and the lock order (source → global writer → export) the
  design preserves exist as described.

I did not re-run the live inventory (678 files / 18 indexed / 10 recent cohort,
etc.); those are the design's read-only estimates and it labels them as such.

## Ruling on the six requested areas

### (1) Exact-source admission vs time-based: PASS — exact-source is correct now

**Is manual enrollment of every new session acceptable for the burn goal?** Yes,
for this slice, with eyes open. The design is honest that exact-source "reduces
repeated work for its cohort, not all future Kiro traffic automatically," and
Stage 3 requires reporting "residual legacy Kiro and Cursor paid work so partial
enrollment is visible." The burn goal is not met by this slice alone — it is a
*bounded, reversible* first step whose coverage gap is explicit and measured.
That is the right way to make progress against 186 calls/24 h without wiring
ordinary watcher events to spending authority (option C, correctly rejected).

**What evidence would justify time-based admission (option B)?** The design's bar
is correct and I adopt it as the condition: a *validated Kiro birth-identity
contract*. Concretely, before any time-based cutoff is designed, Codex must show:
(a) a stable, forgery/copy-resistant session-birth identifier — Kiro UUIDv4
parents are **not** it, and `session.json:createdAt` is copy/restore-mutable, and
mtime/ctime/watcher-first-seen/`lastModifiedAt` are explicitly not birth proof;
(b) defined copy/restore handling (a restored transcript must not be admitted as
"new" and must not skip bootstrap classification); (c) durable enrollment that
survives before any legacy index can win the race; and (d) measured false-admit /
false-skip rates against a labeled corpus. Absent (a)–(d), exact-source stays.
**Condition C-KI1 (binding):** time-based admission is out of scope for this arc
until a separate design establishes (a)–(d); this slice must not add any
time-derived selection path, even disabled.

### (2) Move of the Kiro route to v2 semantic fingerprints (§4), incl. sidecar: PASS

The separation of concerns is exactly right: **source selection**, **transform
compatibility**, **resource policy**, **recovery authority** kept as four distinct
axes. Replacing the Codex-only v2 condition with an explicit selected-format
capability (admitted Codex OR selected Kiro → v2), *without* setting
`codex_admitted_live` for Kiro or running Codex identity checks against it, is the
minimal correct change and is testable in isolation as the design requires.

The **sidecar contract (`kiro-complete-prefix-v2`)** is the subtle, load-bearing
part and the design gets it right:

- Semantic digest over *effective fields consumed by canonical messages/
  provenance* (session ID + selected workspace dir), with raw sidecar bytes/digest
  preserved as evidence. `id` must equal the full `sess_<uuid>` parent name (the
  observed schema), with **no** snapshot directory-name fallback and no provider
  calls on malformed/mismatched metadata.
- Title/status/`lastModifiedAt`-only changes proceed zero-transform **only** when
  effective fields are identical; session/workspace identity changes refuse even
  on the fast unchanged path. This directly fixes the real
  `_revalidate_live_prefix` full-byte-hash refusal I confirmed above, *without*
  the lazy fix of "just keep the raw digest" (which the design explicitly rejects
  as incomplete) and *without* allowing an expensive automatic rebuild to paper
  over noisy metadata.

**Condition C-KI2 (binding):** the design states the digest must be compared "during
capture, before apply, on replay, and against the checkpoint even for an unchanged
JSONL prefix." The implementation and tests must prove the checkpoint-comparison
path (unchanged prefix, changed effective field) actually refuses — this is the
case that leaves reused historical rows carrying obsolete provenance if it is
missed, and it is the easiest one to under-test.

**Condition C-KI3 (binding):** the Kiro adapter-contract version must gate Kiro-only
semantic changes; enrolling Kiro must **not** bump a shared epoch and invalidate
healthy Codex caches. Pin a regression test asserting Codex v2 cache keys and
full-rebuild behavior are byte-unchanged by this slice (the design calls for this;
make it a gate).

### (3) Bootstrap of existing sessions and spending bounds (§5–§6): PASS

The classification matrix is complete and conservative, and the arithmetic checks
out against the stated chunk formula `C(N)=1+ceil(max(0,N-60)/50)` with paid work
`2·C` (summary + distillation per chunk; Ollama embeddings cap-exempt):

- 10 recent sources: 18 chunks → **36 nominal**; proposed hard ceiling **108**
  actual paid HTTP attempts (6·C). ✔ consistent.
- all 18: 42 chunks → **84 nominal**; **252** ceiling. ✔ consistent.
- The 495 excluded paths are preserved; the 678-file / 513-processed populations
  are explicitly **not** targets. ✔ scope is bounded.

The important correctness properties are all present: the hard cap counts **actual
provider HTTP attempts durably before dispatch** (not successful summaries, not
watcher invocations); v1 checkpoints refuse `migration_required` and are left
intact (and the surveyed cohort has none, so live v1 conversion is not a
dependency); legacy-indexed-no-checkpoint uses the existing exact-source bootstrap
updated to bind v2, without manufacturing a checkpoint from `processed.json` or
importing arbitrary Chroma rows as prepared artifacts; and existing serving state
remains until the governed replacement commits.

**Condition C-KI4 (binding):** the pre-dispatch HTTP-attempt reservation must be
durable and crash-conservative (count crash-ambiguous reservations against the
cap). §10's cohort-ledger design covers this; it must land **before** Stage 1, and
"an operator spreadsheet is not a hard cap" must be honored literally — no bootstrap
runs against a soft/advisory counter.

### (4) Watcher interaction, safety, recovery, rollback (§7–§8): PASS

- Watcher stays scheduler-only; ingest chooses the route; PR #397 child
  `--now` behavior preserved so a watcher child cannot defer to its own parent.
  Sidecar create/modify/move/delete maps to the sibling `messages.jsonl`
  **only for selected Kiro paths**; the sidecar is never indexed as a transcript
  and watch roots are not broadened. ✔
- The `ingest.py:_index_one_file` unchanged-hash early return (confirmed in the
  baseline) is correctly identified as the shortcut that must be bypassed **for
  selected Kiro only**, while retaining exclusion and other policy checks, and
  **not** via `force_reindex` (which the live route forbids). ✔
- Rollback is correctly defined as **hold affected paths + preserve evidence**,
  explicitly *not* removing paths from `live_sources` or flipping incremental off
  (either of which would silently route back to legacy). Returning a migrated
  source to legacy requires an explicit lineage + paid-rebuild decision. This is
  the single most important safety property in §8 and it is correct.
- The design neither clears nor repairs the unrelated Codex `recovery_unproven`
  pending transaction, and makes a shared-runtime deploy/bootstrap window NO-GO
  until the operator establishes no unresolved writer/recovery state can race.
  Good — this is the live wedged transaction `46313d43…` doctor still reports.
- `watch --clear-quarantine <path>` clears both watcher state and incremental
  retry holds and must be used only under an exact recovery decision, never
  `--clear-quarantine-all`. Correct and matches the live remedy string.

**Condition C-KI5 (binding):** the "woken by prefix change" vs "terminal refusal"
distinction (§7) must be tested — a prefix change must not forgive a terminal
refusal or a recovery-authority failure, and a woken Kiro operation must still
pass durable retry/recovery gates and never discard its journal. This is where a
subtle regression could silently re-enable spending on a held source.

### (5) Verification and staged canary gates (§9–§10): PASS

The seven verification families (§9) are comprehensive and target the real risk
surfaces — routing/authority, semantic compatibility, prefix/sidecar behavior,
budget boundaries (exact N=0/1/60/61/110/111 and 20/21 planned chunks), bootstrap/
recovery with crash injection at every durability point, concurrency/watcher
double-pay prevention, and coverage/value (canonical accepted-message/range
parity against full parsing, not just row counts). The instruction to redirect
synthesis-failure logs/sidecars before imports — "do not repeat the earlier test
leak into live `synthesis_failures.jsonl`" — is a good, specific guardrail.

The staged gates are correctly ordered and each demands its own evidence and Ryan
authority:

- **Stage 0** hermetic proof → **Stage 1** one existing + one new source (≤3
  chunks, ≤18 paid attempts; durable cohort cap **120** actual paid attempts for
  the entire canary; ≥24 h, ≥10 completed appends, one mature multi-chunk session,
  one watcher restart, one compatible non-transform runtime transition) →
  **Stage 2** ten-source cohort (refresh inventory, 36 nominal / 108 max,
  sequential in a no-other-writer window) → **Stage 3** steady exact-source.
- Canary PASS criteria are the right ones: selected runs never use legacy; no
  bootstrap/rebuild from watcher events; unchanged runs and prepared-artifact
  replay make zero transform calls; **a mature source demonstrates actual
  historical reuse below the provider-free full-file counterfactual**; HTTP totals
  reconcile with the durable budget with no Ollama mis-counting; recovery/
  mixed-collection-visibility measured against numeric limits. "A passing cost
  chart cannot override these [safety] gates." ✔

The design is admirably disciplined about **not promising a savings percentage**:
it refuses to derive a Kiro savings figure or payback date from the aggregate 186,
notes a one-chunk conversation may save zero on append, and requires the
counterfactual be a *provider-free* full-file chunk count rather than a second paid
legacy transform. This is exactly right and I want it preserved verbatim into the
VERIFY section.

**Condition C-KI6 (binding):** the cohort-ledger budget-lock protocol (§10 Stage 1)
must be implemented and tested as specified — serialize+fsync each reservation
under a short budget lock held *while holding the source lock*, release the budget
lock **before** the request, and **never** acquire it from inside a Chroma write
scope. This lock-ordering rule is the kind of detail that, if violated, deadlocks
or lets two children double-pay one source; it needs explicit concurrent-source and
crash tests, "not just a sum of success events."

### (6) Cursor applicability (§11): PASS — "yes, with adapter work" is correct

The design correctly answers *not* by adding `jsonl_cursor` to an allowlist.
I confirmed the baseline gap: `adapters/kiro_session_jsonl.py` has complete-prefix
parsing / raw-line coverage / byte ranges, while Cursor's `adapters/jsonl_chat.py`
is whole-file-only and absent from `incremental_jsonl_formats.py`. So Cursor needs
a real complete-prefix adapter (accepted-message byte ranges, raw-line
dispositions, boundary/hash, identity) with proven whole-parse/prefix parity before
it can reuse this architecture. The design is right that Cursor has no Kiro-style
sidecar dependency (so Kiro metadata checks must **not** be imposed), has no
reviewed creation-time proof (so start with exact paths), and that "Kiro evidence
cannot sign off Cursor automatically." Cursor is correctly left as a later,
separately scoped and separately tested rollout — not bundled into this slice.

## Are the five load-bearing decisions sound? (§12)

Yes to all five: (1) exact-path enrollment over inferred birth time — correct given
UUIDv4 parents; (2) v2 + versioned bootstrap binding as one coherent change —
necessary because the bootstrap script binds independently; (3) semantic sidecar
continuity — fixes a real full-byte-hash refusal without over-rebuilding;
(4) Kiro-specific refusal of automatic rebuild even when the shared flag is true —
prevents a code deploy or metadata change from spending on full history;
(5) bounded active-cohort bootstrap + canary — reversible, measured, scoped.

The two acknowledged trade-offs are the right ones to accept: incomplete unattended
coverage (new sessions stay legacy until enrolled) and paying once to regenerate
legacy output whose prepared-work provenance is unavailable. The design explicitly
refuses the tempting shortcut — "avoiding that payment by inventing cache
compatibility is not acceptable" — which is the correct and safe posture.

## Conditions summary (all must hold for the Execute PR to pass Kiro)

- **C-KI1** — no time-based/time-derived selection path in this slice (even
  disabled); option B requires a separate design proving a validated birth-identity
  contract (forgery/copy-resistant id, copy/restore handling, durable
  pre-index enrollment, measured false-admit/skip rates).
- **C-KI2** — prove the checkpoint-comparison refusal for an unchanged JSONL prefix
  with a changed effective sidecar field (session ID / workspace).
- **C-KI3** — Kiro adapter-contract version gates Kiro-only semantic changes; pin a
  regression test asserting Codex v2 cache keys and full-rebuild behavior are
  unchanged by enrolling Kiro.
- **C-KI4** — durable, crash-conservative pre-dispatch HTTP-attempt reservation
  lands before Stage 1; no bootstrap runs against a soft counter.
- **C-KI5** — test that a prefix change does not forgive a terminal refusal or
  recovery-authority failure; woken operations still pass durable gates and keep
  their journal.
- **C-KI6** — implement and test the cohort-ledger budget-lock ordering exactly
  (budget lock inside source lock, released before the request, never inside a
  Chroma write scope), with concurrent-source and crash tests.

These bind the implementer to discipline the design already describes; none require
a redesign. Hence PASS-with-conditions.

## What this review does NOT grant

- Not an implementation grant (that is Ryan's, after execution planning).
- Not a live-selection or spending grant; `live_sources` stays empty until a
  separate exact packet with the no-other-writer window.
- Not permission to enroll time-based admission or to roll out Cursor.
- Does not clear or repair the pending Codex `recovery_unproven` transaction
  `46313d43…`; the design correctly leaves it with its existing owner.
- Does not accept any claim of a specific savings percentage or payback date.

---

I finished: Kiro review of the Kiro incremental-indexing design (`f6a59f9`).
Next step:  Ryan decides direction; execution planning specifies exact tasks/tests;
            Cursor implements after the Execute grant under conditions C-KI1..C-KI6.
Next lane:  Ryan (direction), then Cursor (Execute).
See my work: `docs/inter-model/KIRO-2026-10-18-issue-286-kiro-incremental-review.md`

<!-- src: ../plans/DESIGN-issue-286-kiro-incremental-indexing.md — f6a59f9 on origin/docs/2026-10-18-issue-286-kiro-incremental-design, the design under review -->
<!-- src: ../../incremental_jsonl.py, ../../incremental_jsonl_codex_admission.py, ../../scripts/bootstrap-incremental-jsonl.py, ../../incremental_checkpoint_migration.py, ../../ingest.py, ../../adapters/kiro_session_jsonl.py, ../../adapters/jsonl_chat.py — baseline 07117ed seams verified during review -->
<!-- ref: ../plans/STATUS-codex-jsonl-production-integration.md — Arc Codex routing and future implementation evidence -->

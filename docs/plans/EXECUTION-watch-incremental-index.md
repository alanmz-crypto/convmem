# EXECUTION — Codex JSONL transform reuse, proposed slices

**Arc: Trapdoor Hunt** · **Issue:** [#286](https://github.com/alanmz-crypto/convmem/issues/286) · **State:** DRAFT FOR KIRO REVIEW; NOT AUTHORIZED · **Date:** 2026-09-17

Companion: [ARCHITECTURE-watch-incremental-index.md](ARCHITECTURE-watch-incremental-index.md).
These are future, bounded implementation tasks for a separate Ryan Execute
decision. No task below is permission to run against production.

## 1. Scope and dependencies

The proposed outcome is default-off transform reuse for **new, isolated**
Codex history/rollout JSONL sources with a valid checkpoint. Each slice
retains full-prefix source verification. Previously indexed Codex sources
remain on the legacy route until the adoption proof in S4 passes or Ryan
authorizes a measured rebuild. Tail-only source I/O is not promised.

| Slice | Proposed future deliverable | Exit evidence | Gate |
|---|---|---|---|
| S0 — contract inventory | Pin current-main Kiro and Codex parser, chunk, ID, provenance, dedupe, writer, and isolation behavior as fixed oracles. Carry Claude 3's completed, revision-paired memory result with its stated limits; do not rerun it for this correction. | Code-derived invariant map, focused parity fixtures, unchanged Kiro baseline. | Kiro reviews design first; no runtime change. |
| S1 — Codex prefix adapters | Add separate complete-prefix views for history and rollout, including raw line ranges/outcomes and legacy message parity. No coordinator routing. | Full/partial/malformed-line and rotation fixtures; old `parse()` behavior unchanged. | Cursor after Execute. |
| S2 — shared state contract | Version format eligibility, source IDs, fingerprints, complete keep-set generation, prepared replay, and physical projection-ID accounting without changing the Kiro route or default-off gate. | Existing Kiro hermetic suite plus fault/replay and source-scope tests on both collections. | Cursor after S1 review. |
| S3 — isolated fresh-source route | Permit only positively eligible Codex formats under the existing disabled flag and `CONVMEM_INCREMENTAL_ROOT` isolation boundary; run append, rewrite, and crash fixtures. | Zero historical transform calls on verified append; complete-generation parity against clean rebuild; no live access. | Cursor after S2 review. |
| S4 — existing-source adoption | Attempt a no-call adoption only if the architecture §6 proof is met. Otherwise keep refusal and deliver an explicit, costed rebuild proposal for Ryan. | Exact row/ID/provenance/coverage proof, negative fixtures, replay proof, call counters. | **Separate** design/Execute choice; S3 may finish without S4. |
| S5 — tail-only I/O | Separate source-authority architecture and watcher/ingest routing review if Ryan wants O(tail) reads. | Proof of append-only authority or documented weaker guarantee; bytes-read measurements. | Outside this plan and #286's first acceptance claim. |

S0–S3 do not include watcher, service, configuration, memory-cap, retry,
timeout, cooldown, exclusion, or production-source changes. S4 cannot be
folded into S3 merely to make the feature useful on live files: it changes
the authority of preexisting rows and needs its own proof. S5 cannot be
silently claimed by S3: `watch.py` and `ingest.py` still hash full files before
the coordinator.

## 2. Proposed adversarial test matrix

All tests use temporary files, an isolated mutable root, real temporary
Chroma only where needed, fake providers, network denial, and deterministic
fault hooks. No live Codex files, Ollama, paid API, watch service, or corpus
write is part of verification. Compare semantic source coverage and both
collections with a clean rebuild oracle; compare historical model-call counts
and bytes read separately.

| Case | Constructed attack | Required oracle |
|---|---|---|
| A1 | Append one complete record to a large history and rollout fixture, including append at exactly a chunk boundary and one record before/after it. | All old stable artifacts reused; only affected seam/new windows transformed; complete manifest equals clean rebuild; provider-call counters and bytes read reported separately. |
| A2 | Partial final JSON object, then complete it in a later write; include final line without newline. | Boundary stops at prior newline; cursor/checkpoint never skips the completed record; raw line range is included exactly once after completion. |
| A3 | Blank, ignored, malformed complete, invalid UTF-8, and metadata-only rollout lines. | New view and legacy parser agree where legacy has defined behavior; every complete raw line has an outcome; ambiguity refuses rather than declaring coverage. |
| A4 | Replace file with same size and matching last 4 KiB; separately rewrite an interior byte on the same inode; truncate then regrow past old size. | Identity or full prior-prefix hash rejects reuse; no wrong-offset message, stale keep set, or checkpoint advance. |
| A5 | Mutate the selected prefix while preparing, after prepared fsync, during Chroma writes, and before processed publication. | No commit for a changed selected prefix; rollback or validated retry restores both collections/sidecars; no silent coverage loss. |
| A6 | Non-step-aligned prior final window and append spanning multiple new windows; include repeated text and exact-dedupe suppression. | Absolute offsets, stable IDs/provenance for unchanged chunks, new IDs for changed seam, and exact/semantic dedupe parity. |
| A7 | Crash after prepared publish, first summary upsert, unit upsert, each prune, checkpoint publish, export/dedupe, and processed publish. | Valid prepared output is replayed with zero new transform calls after first write; invalid/missing cache rolls back or refuses; final state converges to one complete generation. |
| A8 | Old seam produces fewer units, a new unit gets a provenance-derived physical projection ID, and an unrelated source shares Chroma collections. | Complete physical keep set removes only superseded source rows, preserves every valid historical/new row and unrelated source; both collections and export agree. |
| A9 | Change parser contract, chunk size/overlap, prompt, model, embed dimension, provenance/ID contract, and implementation revision one at a time. | Each relevant change invalidates cache/checkpoint reuse or refuses; no stale output is presented as current. |
| A10 | Existing source has processed entry alone, partial Chroma rows, dedupe-suppressed unit, missing summary, ambiguous provenance, or corrupt cache. | No automatic adoption. Any claimed zero-call class has a complete row-to-input proof and exact replay; otherwise `bootstrap_required` persists. |
| A11 | Run with flag absent/false, wrong format, forced/supersede reindex, missing isolated root, or path outside granted root. | Existing path or fail-closed refusal as specified; no newly created state and no Kiro behavior change. |
| A12 | Simulate concurrent index attempt and watcher-style repeated invocation on one isolated source. | Source lock serializes state; one generation commits; second run is unchanged/replay, not a competing transform. |

Claude 3 completed a paired hermetic, sampled-RSS comparison of pre-#305
`5c103aa` and post-#305 `ef4a7dd`. At 20,000 synthetic corpus units,
exposure-probe growth changed from +527.5 to +2.6 MiB for a small trigger
and +510.4 to +3.0 MiB for a larger trigger; at 5,000 units with a small
trigger it changed from +43.5 to −2.4 MiB. This supports only that #305
removed roughly 0.5 GiB of the targeted 20,000-unit probe spike. The run
used fake providers, synthetic data, only two corpus sizes, a 6 GiB address-space
ceiling because real Chroma reserves more than 2 GiB virtually, and
real-Chroma upsert seeding. No harness artifact was committed. It neither
reproduced the historical ~12.5 GiB OOM nor measured the live corpus; do
not calculate a remaining OOM “gap” or close #268 from it. No further
measurement is part of this plan update. The 900-second child timeout
bounds a hang's duration but cannot prevent an earlier OOM.

## 3. Review and acceptance gates

1. **Architecture review:** Kiro reviews the post-evidence commit of both
   documents by exact SHA, superseding any review begun at `131ab425`,
   writes a PASS/FAIL with any required corrections, and checks the scope
   boundary against Arc Codex P2. A PASS is not Execute authorization.
2. **Ryan decision:** Ryan chooses whether S0–S3 may proceed, whether S4 is
   deferred, and whether full-prefix verification is an acceptable first
   product outcome. The grant must name target slices and resources.
3. **Future implementation:** Cursor implements only granted slices. Each
   slice has focused hermetic oracles; shared coordinator changes must keep
   the existing Kiro route byte/semantic-equivalent and default-off.
4. **Future verification:** Check source-coverage, replay, pruning,
   provenance, isolation, and transform-call oracles before any production
   consideration. Any live indexing or activation is a later, separate
   authorization.

The implementation acceptance claim for S0–S3 is narrow: in an isolated
fixture with a valid checkpoint and unchanged verified prefix, a small Codex
append reuses stable historical transforms without losing complete-line
coverage or changing unrelated/Kiro behavior. It does **not** mean existing
production sources are adopted, source reads are O(tail), or watch memory is
bounded below the cgroup cap.

## 4. Open decisions for Kiro and Ryan

- **Prefix cost:** Is full-prefix verification with transform reuse sufficient
  for #286's first Execute, given unchanged full-file hashing upstream?
- **Coverage contract:** For malformed complete lines and invalid UTF-8,
  should parity with legacy skip behavior be retained with explicit skip
  outcomes, or should the new route refuse? The answer must be per format.
- **Projection manifest:** Does current writer API expose every physical ID
  after provenance collision handling and dedupe, or does S2 need a narrow
  return-contract change before pruning can be proved safe?
- **Adoption:** Which existing-source class, if any, can satisfy zero-call
  adoption? What one-time provider budget and source set would a fallback
  rebuild require? Neither is presumed approved.
- **Memory:** Does the narrow ~0.5 GiB targeted-probe reduction at 20,000
  synthetic units affect the priority of a separate #268 investigation?
  This result does not quantify a remaining OOM gap.
- **Tail I/O:** Is a trusted writer/mutation journal available? Without it,
  do not trade full-prefix authority for a matching-tail heuristic under this
  Execute plan.

## 5. Kiro review handoff

**Target:** current `origin/main` `ef4a7dd972435de1fbb684cd3aba43076b8232f6`
plus this planning branch's two documents. Read the historical
`92395e9:docs/plans/DESIGN-watch-incremental-index.md` as contrast, then
`watch.py`, `ingest.py`, both Codex adapters, `incremental_jsonl.py`, and
`ingest_dedupe.py` at the target revision. Claude 2's advisory is in the
2026-09-17 local Claude transcript; its assertions are incorporated here
with the per-chunk `accepted_rows` correction. Claude 3's completed paired
hermetic measurement and its limits are recorded above; there is no
committed harness artifact. Pin the new branch tip, not ancestor `131ab425`.

**Requested verdict:** PASS or FAIL on whether S0–S3 can safely become a
bounded future Execute brief, with explicit review of matching-tail rotation,
full-prefix authority, complete keep sets/physical IDs, replay after partial
publication, existing-source refusal/adoption, and default-off isolation.
Please identify any assumption that needs a proof before implementation.
Return the review to Ryan; stop before Cursor assignment, PR creation,
production indexing, or activation.

**TL;DR:** [Arc Trapdoor Hunt] S0–S3 propose safe, isolated Codex transform
reuse after Kiro review and a separate Ryan Execute grant. Existing-source
adoption and true tail-only I/O remain separately gated.

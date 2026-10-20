# [Arc Codex #286] Kiro review — Oct 13 wedge recovery-authority and per-source repair packet

**Reviewer:** Kiro (design review / sign-off lane; review-only, no implementation)
**Date:** 2026-10-20 UTC (Oct 19 CDT)
**Artifact under review:**
`docs/inter-model/CLAUDE-2026-10-20-issue-286-oct13-wedge-recovery-packet.md`
at commit `70adb23` on branch `docs/2026-10-20-issue-286-oct13-wedge-recovery`
(packet base `origin/main` `686d50e`).
**This review:** branch `kiro/2026-10-20-issue-286-oct13-wedge-review` from
`origin/main` `686d50e8e671b773cacc44c14e70aa3cbd822d2e`; own detached worktree;
explicit-refspec push; no PR.
**Scope:** review-only. Authorizes **no** scratch restore, live repair, journal
archive/delete, quarantine clear, config change, bootstrap, provider call, or
runtime promotion. I did not touch `.worktrees/runtime-main` or any live config.
I read code via `git show <rev>:<path>` only; I ran no `convmem` command that
writes incremental state (doctor/brief/unresolved and ledger reads only).

---

## Consequence first (for Ryan)

Claude's packet turns the Oct 13 wedge from "recovery authority missing, torn
store feared" into "recovery authority **found byte-exact in restic**, and the
live store for this one source **already equals** the rollback's before-image."
If the packet is right, the wedge is now a **journal-only orphan**: an APPLYING
`transaction.json` with no live rollback file behind it, left when something
completed a rollback on Oct 17 and then — 22 seconds later — recreated a
byte-identical `transaction.json` that nobody can attribute.

**My verdict, three parts as asked:**

- **(a) Evidence + no-op claim: PASS on everything checkable without opening
  Chroma; the no-op claim is NOT YET PROVEN for the two surfaces that matter
  most (HNSW vectors + non-source invariance).** The hash lineage, the restic
  retention, the authoring-runtime attribution, and the "live = before-image"
  metadata comparison are sound and I independently confirmed the load-bearing
  code claims. But "no-op" cannot be asserted until the scratch proof actually
  reads vectors. The packet says this itself; I am holding it to it.
- **(b) Which runtime runs the scratch proof: `3e705e4` is correct, and I
  confirmed *why* in code.** It is the only one of the three candidates that
  both (i) does not refuse v1 and (ii) verifies non-source against a **freshly
  computed** digest rather than the obsolete Oct 13 stored digest. `8a7cdab`
  would refuse-or-fail on today's store; `main` (`686d50e`) refuses v1 by design.
- **(c) The unknown writer DOES block Stage 1's no-other-writer condition.**
  It is not clearable by argument. A completed rollback that a code path cannot
  produce, followed by an unattributable byte-identical journal re-creation into
  live incremental state, is exactly the "a stopped process does not prove its
  writes are complete" failure Astra §6 flagged — now worse, because the writer
  is *active and unknown*, not merely stopped. I specify below what evidence
  would clear it.

**Bottom line:** I accept the recovery *direction* (R1) and the *scratch-restore
+ scratch-proof* as the correct next step, which Ryan can grant as a read-only /
isolated-scratch action with low risk. I do **not** clear the live-disposition
step or the Stage 1 no-other-writer gate until the scratch proof passes
*including vectors* and the unknown Oct 17 writer is explained or structurally
fenced.

---

## Code claims I independently verified (at the packet's pinned revisions)

I grounded the packet's runtime reasoning against `git show` at `8a7cdab`,
`3e705e4`, and `686d50e` (main). All load-bearing claims confirmed:

1. **Main refuses v1; `3e705e4` and `8a7cdab` do not.**
   `686d50e:incremental_jsonl.py:2685` carries
   `"recovery_unproven", "v1 transaction requires original runtime"`. That string
   is **absent** from both `3e705e4` and `8a7cdab`. So the packet's claim that
   "current `main` refuses v1 by design" and that an older runtime is required to
   drive the recovery is accurate.

2. **The non-source digest oracle differs exactly as the packet says.**
   - `8a7cdab:incremental_jsonl.py` `_restore_replay_before_images` verifies with
     `self._verify_non_source_collections(rollback.get("non_source_collections") or {})`
     — i.e. against the **stored Oct 13 digest**. On today's mutated store that
     comparison can only refuse or fail. This is why `8a7cdab` cannot be the
     scratch runtime.
   - `3e705e4:incremental_jsonl.py:2284-2290` computes
     `attempt_non_source = self._non_source_collection_digest()` **first**, then
     restores before-images, then
     `self._verify_non_source_collections(attempt_non_source)`. The oracle is a
     fresh self-consistent snapshot, so the check proves the *restore itself* is
     a no-op for non-source rows at proof time — which is the right property for
     a scratch no-op proof. **Caveat (see gap G-b below):** because the oracle is
     captured *inside* the same locked restore, it proves "restore did not change
     non-source rows," not "today's non-source state equals the Oct 13
     before-image." Those are different claims; the acceptance list must not
     conflate them.

3. **`_cleanup` ordering matches the Oct 17 forensic timeline.**
   `3e705e4:incremental_jsonl.py:2099-2112`: `_cleanup` unlinks `transaction`
   then `rollback` (one `transaction_cleanup` transition), then empties and
   `rmdir`s the snapshot dir (`snapshot_cleanup`). This matches the observed
   Oct 17 00:24:22 `snapshots/` removal and the completed-rollback hypothesis.

4. **No recovery code path re-creates `transaction.json`.** Every
   `transaction.json` writer in `3e705e4:incremental_jsonl.py` is `_write_transaction`
   (lines 2174, 2781, 2816, 2832), all on the **forward** PREPARING/APPLYING
   path of a *new* run — never in `_restore_replay_before_images` or `_cleanup`.
   The only other writers in the tree are `bootstrap_supersession.py` and
   `scripts/bootstrap-incremental-jsonl.py` (Kiro-bootstrap-only). So the
   byte-identical 00:24:44 re-creation **cannot** be produced by the rollback
   path. The packet's "unidentified writer" is a genuine code-level anomaly, not
   a misread. This is the single most important corroboration in my review: it
   converts the mystery from "probably a race we didn't trace" into "no in-tree
   recovery path does this," which is why I treat it as a hard gate (c).

5. **Live state corroborates the timeline arithmetic.** The live `convmem doctor`
   WARN for tx `46313d43…` reports `phase=APPLYING age=255549s` = **71.0 h**,
   which lands exactly on Oct 17 00:24 CDT from the Oct 19 23:24 CDT capture.
   `code=recovery_unproven` matches `retry_state.json`. The branch diff is
   docs-only (one file, +292), consistent with the packet's "no live writes"
   assertion.

I did **not** re-run the packet's restic `dump | sha256sum` lineage, its
SQLite-`mode=ro` Chroma metadata comparison, or its transcript attribution. Those
are read-only forensics I accept on the packet's authority given the internal
consistency above and the matching live doctor state. If Ryan wants them
independently reproduced before the scratch grant, that is a reasonable ask (it
is all read-only), but I do not consider it necessary to accept the *direction*.

---

## (a) The evidence and the no-op claim

**PASS on the recovered-authority and live-equals-before-image evidence.**

- The dual-repository retention (local `ca2a6f04`…`495c2d65`, offsite `1d4a9ff5`),
  all four hashing identically, with the Oct 17 snapshot taken 6 minutes before
  the loss, is strong. The `rollback.json` `33ab1c3b…` = transaction's bound
  `rollback_authority_sha256`, and snapshot `ba6f350a…` = `prefix_sha256` =
  live-source prefix, is a clean three-way identity. The "reproducible from the
  live source's first 6,079,972 bytes, same inode, same hash" cross-check is a
  good independent confirmation that the snapshot is the real prefix.
- The §5 metadata comparison (summaries, units, export payloads, processed,
  checkpoint, prepared, dedupe) all equal to the rollback before-image is a
  thorough plain-file/SQLite audit and I accept it as evidence that **no partial
  apply of the pending 35-message generation is visible on those surfaces.**

**The "no-op" claim is NOT YET PROVEN. Two explicit gaps, both named by the
packet, that the acceptance list must close:**

- **G-a — HNSW vectors unread.** §5 marks embedding vectors "not read (HNSW)."
  A rollback restores vectors too; the whole corruption class this arc worries
  about (Chroma heap corruption history, noted in the packet's own R1-A caveat)
  lives in the vector segment, not the SQLite metadata. "Live = before-image" is
  unproven precisely where it is most expensive to be wrong. The scratch proof's
  acceptance (ii) already requires "source rows, **including embedding vectors**,
  byte/hash-equal before and after." Good — but that is an *equal before/after
  the scratch restore* check. It must also include a **today-vs-Oct-13 vector
  comparison** for the source rows, or state honestly that it only proves
  "restore is idempotent in scratch," not "the live vectors already match the
  before-image." These are different guarantees (see G-b).

- **G-b — "restore is a no-op in scratch" ≠ "live already equals before-image."**
  This is the subtle correctness point in the whole packet. The `3e705e4`
  rollback verifies non-source against a *fresh* digest captured inside the same
  locked operation (confirmed in code, item 2 above). That proves the restore
  does not perturb non-source rows **in the scratch environment seeded from a
  current snapshot**. It does **not** prove that the *live* store today equals the
  Oct 13 before-image — the §5 metadata comparison is what argues that for
  metadata, and nothing yet argues it for vectors or for a true non-source
  before/after. The packet's language ("prove that the rollback is a no-op") is
  slightly too strong: the scratch run proves **restore idempotence on a seeded
  copy**; the "live already equals before-image" claim rests on §5 (metadata,
  proven) **plus** a vector comparison (not yet done). I want the acceptance list
  to separate these two propositions explicitly so the eventual proof does not
  overclaim.

**Net:** evidence of recovered authority = PASS. "Journal-only orphan" framing =
accepted *for metadata surfaces*. "No-op / live equals before-image" = **hold
until the scratch proof reads vectors and the acceptance list distinguishes
restore-idempotence from live-equivalence.**

---

## (b) Which runtime should run the scratch proof

**`3e705e4` is correct. Confirmed in code, with one constraint.**

The candidate set is `8a7cdab` (author), `3e705e4`, and `686d50e` (main):

- **`686d50e` (main) — rejected by its own guard.** `_roll_forward` refuses v1
  with `v1 transaction requires original runtime` (line 2685). It cannot drive
  this recovery without disabling the guard, which I will not endorse.
- **`8a7cdab` (author) — rejected on correctness.** Its
  `_restore_replay_before_images` verifies non-source against the **stored Oct 13
  digest** (`rollback.get("non_source_collections")`). Against a scratch store
  seeded from today's snapshot that digest will not match, so the author runtime
  can only refuse or fail. (It is also the runtime whose live Oct 13 attempt
  already died in `_verify_non_source_collections` → Chroma `InternalError`, per
  the packet's `/tmp/enso-session-index-retry.txt` trace.) Using the *authoring*
  runtime is intuitively appealing but is the wrong instinct here.
- **`3e705e4` — correct.** It does not refuse v1, and it computes the non-source
  oracle fresh inside the locked restore, so the proof is self-consistent against
  the scratch store rather than against an obsolete baseline.

**Constraint C-run1:** pin the exact `3e705e4` blob of `incremental_jsonl.py`
(and its imported modules) for the scratch run and record its SHA in the proof
evidence. "Runtime `3e705e4`" must mean that exact tree, run from an isolated
`HOME`/config with network denied and no provider key — matching §6 step 2's
own isolation requirements. Do not run `3e705e4` from a dirty working tree.

**Constraint C-run2 (the stop condition is right — keep it hard).** §6 step 2
says: if the `3e705e4` run chooses `replay_forward` and commits the 35-message
generation instead of rolling back, **stop and report**. I confirmed in code
that `_roll_forward` at `3e705e4` *can* take the forward branch (the `try`
block builds/commits a generation when there is no `roll_refusal`), so this is a
real fork, not hypothetical. Making "forward commit in the scratch proof" a hard
stop is correct and I require it: the proof exists to show a **no-op rollback**,
not to perform a (different, forward) disposition. That answers the packet's §8
Q2 — **stop**, do not accept a forward commit from the proof run.

---

## (c) Does the unknown writer block Stage 1's no-other-writer condition?

**Yes. Hard block. This is the finding I weight most heavily.**

The packet documents, and I confirmed structurally, that:

1. Some process completed a rollback on Oct 17 00:23–00:24 that matches the
   `3e705e4` `rolled_back` path (checkpoint + prepared rewritten byte-identical
   at 00:23:09; `snapshots/` removed at 00:24:22).
2. **22 seconds later** (00:24:44) a byte-identical APPLYING `transaction.json`
   reappeared.
3. **No in-tree recovery path writes that file.** I verified every
   `transaction.json` writer at `3e705e4`: all are `_write_transaction` on the
   forward run path; `_cleanup`/`_restore_replay_before_images` only *unlink* it.
   The bootstrap writers are Kiro-only and were not running.
4. The packet could not attribute either write to any systemd unit, watcher
   spawn (watcher started 01:12:58, after the fact), shell history, or any
   Codex/Claude/Kiro/Copilot/Cursor transcript in the window.

This is **exactly** the condition Astra §6 and my own prior review (C4
quiescence gate) said must be closed: "a stopped process does not prove its
writes are complete," and "the converter must verify no transaction/rollback of
any phase under the writer locks immediately before publish." Here we have the
stronger, worse case — not a stopped writer, but an **active unidentified writer**
that demonstrably reached live incremental state and left a journal behind. If
we cannot say what wrote it, we cannot promise it will not write again *during*
the live repair, which is the precise risk the no-other-writer gate exists to
exclude.

**So:** Stage 1's no-other-writer precondition remains **FAIL/UNRESOLVED**, and
this packet does not clear it. The scratch restore + scratch proof (steps 1–2)
can proceed under a Ryan grant without resolving this, because they touch no
live state. The **live disposition (step 3, either R1-A or R1-B) must not be
granted** until the writer is explained or structurally fenced.

### What evidence would clear it

Any one of the following, in order of preference:

- **E1 (best) — attribute the writer.** Identify the exact process/command that
  wrote `transaction.json` at Oct 17 00:24:44. Candidate sources not yet
  exhausted by the packet: audit/`auditd` or `fanotify` records if present;
  `atime`/`ctime` and the file's creating-process via any BPF/`fs` logging that
  was active; the `3e705e4`-era watcher's own structured logs *before* 01:12:58
  in case an earlier short-lived invocation existed; any `systemd-run --scope`
  transient unit journald entries (not only persistent units); cron/at;
  `~/.local/state` or editor-driven file touches. The packet checked transcripts
  and persistent units; it did not report checking a filesystem-audit trail. If
  none exists, say so — that itself is evidence (E2 becomes mandatory).

- **E2 (acceptable fence) — structural owner-only fence + audit on every
  state-dir write.** Astra §6 and the packet both propose this. Concretely:
  (i) an owner-only advisory lock on the source-state directory that any writer
  (coordinator, bootstrap, recovery) must hold, with the holder's PID/exe
  recorded; (ii) an append-only audit event emitted on **every** mutation of
  `transaction.json`/`rollback.json`/`snapshots/` with pid/exe/revision, so a
  future unattributed write is caught in the act rather than reconstructed from
  mtimes days later. This is net-new hardening and must be designed, reviewed,
  and implemented (Cursor, under a separate grant) — it is **not** work this
  packet or the scratch proof performs. Until (ii) exists, "no other writer" is
  asserted, not enforced.

- **E3 (minimum to *proceed to scratch only*) — bounded live-quiescence
  attestation.** For the scratch grant specifically, confirm the source-state
  dir has had **no mtime change** since the capture and that the watcher is
  stopped+disabled+MainPID=0 for the scratch window. This does not clear E1/E2;
  it only bounds risk for the read-only scratch step. The live step still needs
  E1 or E2.

### On §8 Q4 and Q5

- **Q4 (is 00:24:44 a hard Stage 1 blocker?): yes, hard — not "acceptable with
  monitoring" until E1 or E2.** Monitoring-after-the-fact is what we already
  have, and it is how we found the anomaly 3 days late. A fence that *prevents or
  catches in-flight* (E2) is the acceptable substitute for attribution (E1);
  passive monitoring alone is not.
- **Q5 (is §6 step 2 (i)–(v) sufficient, or also reproduce the re-creation?):**
  (i)–(v) are sufficient **for the no-op proof itself**, with the G-a/G-b
  corrections (vectors read; restore-idempotence vs live-equivalence
  distinguished). A **hermetic replay of the Oct 17 sequence to reproduce the
  re-creation is NOT required for the scratch proof**, and I would not gate the
  no-op proof on it. But reproducing (or failing to reproduce) the re-creation
  **is** the natural experiment for E1 — if a hermetic replay of the `3e705e4`
  recovery never recreates `transaction.json` (which the code says it won't),
  that strengthens "the writer was external," pointing the investigation away
  from the coordinator and toward E1's filesystem-audit angle or E2's fence.
  So: not a gate on the no-op proof; yes, a useful input to clearing (c).

---

## R1-A vs R1-B for the live step (§8 Q3)

**My ruling: R1-B (minimal-mutation archive-move) is preferable to R1-A, but
neither is grantable until (c) is cleared, and R1-B needs one guard.**

- The packet asks whether archive-moving the orphan `transaction.json` after a
  no-op proof "counts as deleting a journal." **It does not** — moving a journal
  into a copy-first, SHA-manifested 0700 archive, leaving Chroma/export/processed
  untouched, is a *disposition*, not fabrication or destruction. It is the
  cleaner analogue of what the completed Oct 17 rollback already did (minus the
  mysterious re-creation). I agree with Claude's framing.
- **Why R1-B over R1-A:** R1-A re-places the authority and runs real Chroma
  upserts of identical rows on an engine with a documented heap-corruption
  history — i.e. it performs the exact kind of vector-segment write this arc is
  nervous about, to achieve a state the proof already shows is a no-op. R1-B
  achieves the same end state (orphan journal closed, v1 checkpoint retained)
  with no Chroma write. Prefer the path that does not touch the vector engine
  when the proof says the write is redundant.
- **Guard on R1-B (R1-B-g):** R1-B is only sound *if* the no-op proof passed
  **including vectors** (G-a). If vectors are the one surface where live ≠
  before-image, then R1-B's "leave Chroma untouched" would strand a real
  discrepancy. So: R1-B is authorized **only** on a vector-inclusive PASS; if the
  vector comparison shows any live-vs-before-image delta for the source rows,
  escalate — that is no longer a journal-only orphan and needs a fresh ruling
  (it would reopen the torn-store premise for the vector segment specifically).
- Clearing the retry hold must be part of the **same** live grant (not a
  separate `watch --clear-quarantine`, which would clear state without closing
  the journal). Do not clear quarantine as a shortcut at any earlier step.

---

## Folding in my Stage 1 C1/C2 (from the 2026-10-17 transform-compat review)

The prompt asks me to fold in C1/C2. Those conditions were about the
**transform-compatibility converter**, a different (forward re-admission) path.
Their relevance here is at the boundary where this wedge hands off to §6 step 4
(re-admission of the v1 checkpoint to semantic-v2):

- **C1 (contract-inventory check must fail closed on template/settings drift,
  hashing actual bytes not labels):** This wedge's recovery deliberately does
  **not** re-transform — R1 keeps the v1 checkpoint and spends zero paid calls.
  Good: it does not touch the fingerprint surface C1 guards. But §6 step 4 (the
  later converter / full-rebuild re-admission) **does**, and C1 still applies
  there in full. Flag for the eventual re-admission packet: the v1 checkpoint
  recovered here must pass the fail-closed contract-inventory check before any
  semantic-v2 re-key, and its legacy fingerprint must be recomputed from the
  authoring runtime's effective settings (the `8a7cdab` identity is known, which
  helps). Do **not** let the wedge recovery's success be read as clearing C1 for
  re-admission — they are separate gates.

- **C2 (must not hash any module wholesale into the runtime key):** Directly
  relevant to *why this wedge exists at all*. The Oct 13 author `8a7cdab`'s
  non-source verification is pinned to a store-state digest, and the broader
  arc's over-invalidation (the `cpu_tripwire.py`-via-lazy-import closure I
  confirmed at `9ef4ecd`) is the class of fragility that made these transactions
  deploy-brittle. The wedge recovery itself does not re-introduce wholesale
  hashing, so C2 is **not violated** by R1. But the lesson stands for E2's fence
  design: the audit/fence must key on **stable identity** (source path, tx id,
  pid/exe), not on a content-manifest that a routine deploy perturbs — otherwise
  the fence inherits the same over-invalidation that produced the wedge.

Neither C1 nor C2 is *satisfied or cleared* by this packet; both are **carried
forward** to the re-admission (step 4) and fence (E2) work respectively. The
wedge recovery (R1 steps 1–3) does not depend on them.

---

## Answers to the packet's §8 questions (consolidated)

1. **Accept R1 as the per-source disposition?** Direction: **yes**. Scratch
   restore + scratch proof: grantable now (read-only / isolated). Live step:
   **held** on (c) + vector-inclusive proof.
2. **If the scratch run picks `replay_forward`, stop or accept?** **Stop** (hard).
   Confirmed the fork exists in code; the proof must demonstrate rollback no-op,
   not perform a forward commit.
3. **R1-A vs R1-B for the live step?** **R1-B** (archive-move is disposition, not
   deletion), guarded by a vector-inclusive PASS (R1-B-g). R1-A only if a reason
   to re-run the code path live emerges; it writes vectors needlessly.
4. **Is 00:24:44 re-creation a hard Stage 1 blocker?** **Yes, hard.** Clear via
   E1 (attribute) or E2 (owner-lock + per-write audit); passive monitoring is not
   sufficient.
5. **Is §6 step 2 (i)–(v) sufficient, or also hermetic Oct 17 replay?** (i)–(v)
   sufficient for the no-op proof **with** G-a (read vectors) and G-b
   (distinguish restore-idempotence from live-equivalence). Hermetic replay is
   **not** required for the proof but is a useful experiment toward clearing (c).

---

## Overall verdict

**PASS with conditions on the recovery direction and the scratch step;
HOLD on the live disposition and on Stage 1's no-other-writer gate.**

Grantable now (low risk, read-only / isolated scratch), under C-run1/C-run2:
- restic restore of the two authority files into fresh 0700 scratch (never in
  place), hash-verified against `33ab1c3b…`/`ba6f350a…` and cross-checked offsite;
- the `3e705e4` scratch no-op proof, with acceptance (i)–(v) **amended** to read
  vectors (G-a) and to separate restore-idempotence from live-equivalence (G-b),
  and with "forward commit → stop" as a hard condition.

Held (not grantable from this packet):
- the live disposition (R1-B preferred, guarded; R1-A discouraged) — blocked on
  (c);
- Stage 1 no-other-writer — **FAIL/UNRESOLVED** until E1 or E2;
- the `restic tag --add hold-issue-286-wedge` hygiene — correctly Ryan-gated;
  I endorse doing it (it protects the only two copies) but it is a repo-metadata
  mutation outside review scope.

Carried forward (not cleared here): C1/C2 to the step-4 re-admission and the E2
fence design; the second retained transaction (Kiro `sess_2628159e…`,
`transform_failed`) still needs its own disposition.

**Separation held:** this review grants nothing. Scratch restore, scratch proof,
live repair, journal archive, quarantine clear, hold-tagging, and re-admission
each remain separate, Ryan-gated actions.

---

## Forward announcement

I finished: Kiro review of the Oct 13 wedge recovery-authority + per-source
repair packet — verdicts (a) evidence/no-op, (b) runtime, (c) unknown writer,
plus R1-A/R1-B ruling and C1/C2 fold-in.
Next step:  Ryan decides whether to grant (1) the read-only scratch restore and
(2) the `3e705e4` scratch no-op proof (acceptance amended per G-a/G-b); the live
step and Stage 1 no-other-writer stay blocked on clearing the unknown writer
(E1 attribute, or E2 owner-lock + per-write audit).
Next lane:  Ryan (scratch grant); then Claude/Codex execute the scratch proof;
Cursor for the E2 fence if that route is chosen; Kiro re-review before any live
disposition.
See my work:
`docs/inter-model/KIRO-2026-10-20-issue-286-oct13-wedge-recovery-review.md`
on branch `kiro/2026-10-20-issue-286-oct13-wedge-review`.

## TL;DR

- **(a) Evidence PASS; "no-op" NOT YET PROVEN.** Recovered authority
  (`33ab1c3b…`/`ba6f350a…`) and "live metadata = before-image" are sound and I
  confirmed the load-bearing code claims. But vectors are unread (G-a) and the
  packet conflates "restore is idempotent in scratch" with "live already equals
  before-image" (G-b) — the acceptance list must read vectors and separate those
  two claims.
- **(b) Runtime `3e705e4` is correct** — confirmed in code: main refuses v1,
  `8a7cdab` verifies non-source against the obsolete stored digest, `3e705e4`
  uses a fresh self-consistent oracle. Pin the exact blob, isolated HOME, network
  denied; forward-commit in the proof is a hard stop.
- **(c) The unknown Oct 17 00:24:44 writer is a HARD Stage 1 blocker.** No
  in-tree recovery path recreates `transaction.json` (verified), so an
  unattributed active writer reached live state. No-other-writer stays
  FAIL/UNRESOLVED; clear via E1 (attribute the writer) or E2 (owner-lock +
  per-write audit) — passive monitoring is not enough.
- **Scratch restore + proof: grantable now (read-only/isolated). Live
  disposition (R1-B preferred over R1-A, vector-guarded): held.** C1/C2 carry
  forward to re-admission and fence design; nothing here is granted.

<!-- src: ./CLAUDE-2026-10-20-issue-286-oct13-wedge-recovery-packet.md (branch docs/2026-10-20-issue-286-oct13-wedge-recovery, 70adb23) — packet under review -->
<!-- src: ./ASTRA-2026-10-20-issue-286-kiro-stage1-packet.md — Stage 1 §6 wedge gate this review builds on -->
<!-- src: ./KIRO-2026-10-17-issue-286-transform-compatibility-review.md — my C1/C2 conditions folded in here -->
<!-- src: ../../incremental_jsonl.py at 8a7cdab / 3e705e4 / 686d50e — v1 refusal, non-source digest oracle, _cleanup ordering, transaction writers verified via git show -->
<!-- ref: ../plans/STATUS-codex-jsonl-production-integration.md — arc brief; not updated by this read-only review -->

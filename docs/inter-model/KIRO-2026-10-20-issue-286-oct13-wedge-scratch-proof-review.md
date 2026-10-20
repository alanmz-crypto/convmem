# [Arc Codex #286] Kiro review — Oct 13 wedge scratch proof + Oct 17 writer attribution

**Reviewer:** Kiro (design review / sign-off lane; review-only, no implementation)
**Date:** 2026-10-20 UTC
**Artifact under review:**
`docs/inter-model/CLAUDE-2026-10-20-issue-286-oct13-wedge-scratch-proof-report.md`
at commit `17530e5` on branch `docs/2026-10-20-issue-286-oct13-wedge-scratch-proof`
(base `origin/main` `686d50e`).
**Prior review this builds on:**
`docs/inter-model/KIRO-2026-10-20-issue-286-oct13-wedge-recovery-review.md`
at `f3b2b45` on branch `kiro/2026-10-20-issue-286-oct13-wedge-review` — which set
R1-B-g (vector-inclusive guard), G-a/G-b (read vectors; separate restore-idempotence
from live-equivalence), C-run1/C-run2 (pin blob + forward-commit hard stop), and E1/E2
(attribute the writer, or owner-lock + per-write audit).
**This review:** same branch `kiro/2026-10-20-issue-286-oct13-wedge-review`; own
detached worktree at `/tmp/kiro-oct13-wedge-review`; explicit-refspec push; no PR.
**Scope:** review-only. Authorizes **no** live repair, journal archive/delete,
quarantine clear, checkpoint restore, re-bootstrap, provider call, or runtime
promotion. I did not touch `.worktrees/runtime-main` or any live config. I read code
via `git show`, and I read live state **read-only** (hash the wedged state dir; `ls`
the collateral dirs; `cat` journals/retry-state). I ran no `convmem` command that
writes incremental state.

---

## Consequence first (for Ryan)

Claude's proof closes the two things I held open last round and attributes the
mystery writer. Net effect:

- The **vector gap (G-a) is closed** and my R1-B-g guard is **satisfied** — the live
  source vectors already equal the Oct 13 before-image, so the R1-B archive-move
  (close the orphan journal, touch no Chroma) is safe to grant on the vector axis.
- The **unknown writer is named** (a Crush agent script in `~/null`, not any in-tree
  path) — which **confirms** my code reading but, importantly, **does not clear** the
  Stage 1 no-other-writer gate. Knowing *who* wrote does not stop the *next* such
  write: the writer was an agent with raw shell access running `python3` against the
  live state dir, which is a standing capability of every lane. That is the E2 case,
  and E2 does not yet exist.
- A **new, larger problem surfaced**: the same Oct 17 session also displaced three
  other sources' state dirs (checkpoints + prepared caches now **lost** from live,
  wiped at the Oct 20 boot) and re-drove four more transactions live. That is paid
  Arc Codex work destroyed and four live outcomes nobody has verified.

**My verdict, three parts as asked:**

- **(a) R1-B-g: PASS.** §3.2 proves live-vs-before-image vector equivalence in the
  only representation that exists on disk (Chroma's cosine-normalized storage). The
  1-ulp deviation from the raw `rollback.json` floats is Chroma's deterministic
  normalize/denormalize round-trip, not a discrepancy. The R1-B live archive-move is
  **unblocked on the vector axis**. It remains blocked on (b).
- **(b) E1 clears "what happened"; it does NOT clear the no-other-writer gate. E2 is
  now MANDATORY.** The attribution is thorough and I accept it as E1. But my prior
  review was explicit that E1 is clearance *by attribution of a past event*, and only
  if attribution were paired with assurance it cannot recur. The attribution instead
  proves recurrence is trivially possible: any lane with a shell can `python3` the
  live state dir with no lock and no audit. So the live step needs E2 (owner-lock +
  per-write audit), designed/reviewed/implemented before any live disposition.
- **(c) Restore the three lost checkpoints from restic `495c2d65`; the four re-driven
  transactions DO need verification.** Re-bootstrap is the fallback only if the
  restored artifacts fail their own integrity checks. The four re-driven commits are
  unattested live writes by the same ad-hoc script and must be verified before any
  further Arc Codex live work.

**Bottom line:** I move the **live R1-B archive-move from "held on vectors" to
"held only on E2"** — the vector guard is satisfied. I open the §4.3 collateral as a
**required, separate investigation + remediation** that gates further live Arc Codex
work. Nothing here grants anything.

---

## What I independently verified (read-only, live + code)

I did not take the report on authority alone. Everything checkable without opening a
Chroma client on live data, I checked:

1. **Live wedged state dir is byte-identical to the report's §5 end-state.** All six
   files hash exactly to the report's prefixes — `checkpoint.json bab59aa6…`,
   `lock.flock e3b0c442…`, `prepared/8dc6954… d8eeebe8…`,
   `prepared/d945d74… 366e3068…`, `retry_state.json 101fc9ce…`,
   `transaction.json a0530661…`. The claim "no live writes; byte- and mtime-identical
   start to end" is **true for this source**. mtimes are the Oct 17 00:23/00:24 CDT
   timeline.
2. **The orphan is real.** `transaction.json` is `phase=APPLYING`, `version:1`, tx
   `46313d437ae4446282a752270770c614`, binding `rollback_authority_sha256=33ab1c3b…`
   and `prefix_sha256=ba6f350a…` — but **no `rollback.json` exists** and `snapshots/`
   is empty. The journal references an authority that is absent on disk. That is the
   journal-only orphan, confirmed, not argued.
3. **Live doctor WARN matches.** `wedged_incremental_transaction` reports exactly this
   source and tx `46313d43…`, `phase=APPLYING`, `code=recovery_unproven`.
   `retry_state.json` on disk reads `recovery_unproven, attempts_on_prefix 3,
   consecutive 2` — matching §4.2.
4. **The pinned runtime's code symbols exist as described at `3e705e4`.**
   `_validate_prepared_artifact` (line 898) raises `prepared_artifact_corrupt` on
   multiple mismatch branches; `_write_transaction` (1285), `_commit_generation`
   (2142) and `_codex_roll_forward_refusal` (1176) are present as the tripwire targets
   and the forward-path fork. This is consistent with §3.1's reported branch
   (`_roll_forward` → refusal `None` → forward `try` fails in
   `_validate_prepared_artifact` → `_restore_replay_before_images` → `_cleanup`).
5. **The §4.3 collateral is real on disk.** Dirs `248e25cb…`, `98d65c7f…`,
   `e55a6f61…` were all re-created Oct 17 18:54 holding only `retry_state.json` with
   **empty** `prepared/` and `snapshots/`. Sampled `248e25cb…` now reads
   `error_code: "bootstrap_required", transaction_id: ""` pointing at an Oct 14 Codex
   source. The checkpoints and prepared caches are gone from live; the dirs are in a
   bootstrap-required state.

**What I did NOT independently reproduce:** the §3.2 vector bit-equivalence (requires
parsing the HNSW segment and a scratch write-back, which is exactly the sandboxed work
the proof performed and which I will not re-run live); the restic lineage dumps; the
Crush transcript timestamps. I accept these on the report's authority given (i) the
internal consistency, (ii) the exact match of every surface I *could* check to live
state, and (iii) the method descriptions are specific and technically sound. If Ryan
wants the vector comparison independently reproduced before the live grant, that is a
reasonable read-only ask, but I do not consider it necessary — the method is correct
and the live-state corroboration is strong.

---

## (a) Does §3.2 satisfy R1-B-g for the live R1-B archive-move?

**PASS.** My R1-B-g guard (prior review) was: R1-B is authorized *only* on a
vector-inclusive PASS, i.e. a **today-vs-Oct-13 vector comparison for the source
rows**; if any live-vs-before-image vector delta exists, escalate because that would
reopen the torn-store premise for the vector segment. The proof delivers precisely
that comparison, and it passes:

- **The comparison is in the right representation.** The collection is cosine space,
  so Chroma stores **unit-normalized** vectors plus a separate norm (`length.bin`).
  The on-disk truth is `unit × norm`. The proof compares the live stored `unit × norm`
  for all 15 source rows against what Chroma returns after writing the exact
  before-image bytes into a scratch copy — **15/15 bit-identical**. That is the
  live-equals-before-image claim my guard required, measured where it actually lives.
- **The 1-ulp caveat is not a discrepancy — it is expected and deterministic.** The
  stored vectors are **not** bit-identical to the raw float32 in `rollback.json`
  (40–195 of 768 components differ by exactly 1 ulp, max |Δ| 2.4e-7, cosine 1 ± 7e-8).
  That is Chroma's normalize/denormalize round-trip, which is deterministic and which
  the restore reproduces. Comparing live storage to the raw JSON floats would be the
  **wrong** oracle; comparing to a fresh write of the same before-image is the right
  one, and that is bit-exact. The proof chose the correct oracle and was candid about
  the other one.
- **G-a is closed, G-b is honored.** Vectors were read (G-a). The report explicitly
  does **not** claim live non-source state equals Oct 13 ("false by design, other
  sources indexed after; does not matter for this source") — that is exactly the
  restore-idempotence-vs-live-equivalence distinction I asked for in G-b, kept
  straight. Proposition 1 (restore idempotent in scratch, vectors included) and
  Proposition 2 (live source = before-image, vectors included) are reported as the two
  separate claims they are.

**Therefore:** the R1-B live archive-move is **unblocked on the vector axis**. If the
live step is eventually granted, R1-B (copy-first, SHA-manifested 0700 archive-move of
the orphan `transaction.json`, Chroma untouched) is the correct disposition and R1-B-g
is satisfied. It remains blocked solely on (b).

**One procedural note on C-run2 (the forward-commit hard stop).** The proof is candid
that the rollback path was reached **only because `3e705e4` rejected the stale prepared
artifact** in `_validate_prepared_artifact`; had that artifact validated, this runtime
would have attempted a forward commit, and "the tripwire was the guarantee here, the
code alone would not have been." I flagged exactly this fork in C-run2 and required the
hard stop; the tripwire on `_commit_generation`/`_write_transaction` was installed and
did not fire. This is the correct outcome and it vindicates making the stop mandatory
rather than trusting the code path. It does not weaken the no-op proof — the proof
shows the restore is a no-op; it does **not** show the forward path is a no-op, and it
never claimed to. Good.

---

## (b) Does the attribution (E1) clear the no-other-writer gate, or is E2 required?

**The attribution is accepted as E1 and it is excellent forensics. It does NOT clear
the Stage 1 no-other-writer gate. E2 (owner-lock + per-write audit) is now
MANDATORY before the live disposition.**

My prior review defined E1 as "attribute the writer: identify the exact
process/command that wrote `transaction.json` at Oct 17 00:24:44," and I named the
filesystem-audit angle the packet had not yet checked. The proof does the attribution
by a different and legitimate route — transcript-level reconstruction cross-checked
against Chroma seq-ids, retry-state, mtimes, and ruled-out alternatives:

- **Writer:** Crush session `cc8fde6b-4bc3-48b8-9dea-eab4c1712617` in `~/null`,
  `deepseek-v4-flash`, Oct 17 05:14–05:36Z.
- **Mechanism:** `/tmp/settle_apply.py` flipped the live journals to PREPARING and
  drove `ingest.index()`, producing the completed rollback (05:21:31→05:24:22Z);
  `/tmp/settle_apply2.py` then re-wrote the saved APPLYING journal with the same
  `_atomic_json` the coordinator uses — **byte-identical, authority omitted** —
  at 05:24:40→05:24:44Z. That re-write is the wedge.
- **Confirms my code reading.** No in-tree path recreates `transaction.json`; the
  byte-identical reappearance came from an ad-hoc script re-serializing a saved copy.
  That is the structural anomaly I weighted most heavily last round, now explained.
- **The corroboration is strong and the ruling-out is disciplined.** The Chroma 15
  rows as the first 15 writes after the 00:17 backup, the retry-state progression, the
  Kiro read-only `.pyc` birth correctly excluded, and the systematic clearing of
  Codex/Claude/Cursor/Copilot/60+ Crush DBs are all convincing. I accept the
  attribution as factually established.

**Why this still does not clear the gate.** The no-other-writer gate exists to
guarantee that **during the live repair** nothing else mutates the state dir. My prior
review was explicit: attribution clears the gate only "in order of preference" as E1
*and* only to the extent it also assures non-recurrence; otherwise "no other writer is
asserted, not enforced." The attribution's own finding is that the writer was **an
agent with raw shell access** running `python3 convmem.py` and direct `_atomic_json`
writes against the live state dir — **with no owner lock, no audit event, and no
systemd unit to point at**. The report itself frames Q2 this way: "any lane with shell
access can run `python3` against the live state dir."

That is not a one-time ghost; it is a **standing, reproducible capability of every
agent lane on this machine**. Knowing that session `cc8fde6b` did it on Oct 17 does
nothing to prevent session `<next>` from doing the same during the live R1-B move. The
attribution therefore makes the case for E2 **stronger**, not weaker: we now have a
*confirmed instance* of exactly the uncontrolled concurrent writer the gate guards
against, and the mechanism is available to anyone.

- **E1 verdict:** PASS as attribution. The 00:24:44 writer is identified; the mystery
  is closed; my code reading is confirmed. The §8-Q4 "hard blocker" is downgraded from
  *unexplained active writer* to *explained but unfenced capability*.
- **E2 verdict:** **Required and not yet satisfied.** Before the live disposition, the
  state-dir mutation surface must be fenced: (i) an owner-only advisory lock on the
  source-state directory that every writer (coordinator, bootstrap, recovery, and any
  ad-hoc tool) must hold, recording holder pid/exe; (ii) an append-only audit event on
  **every** mutation of `transaction.json`/`rollback.json`/`snapshots/` with
  pid/exe/revision, so a future unattributed or ad-hoc write is caught in the act. Per
  my prior C2 fold-in, the fence must key on **stable identity** (source path, tx id,
  pid/exe), not a content-manifest that a routine deploy perturbs. This is net-new
  hardening — Cursor implements under a separate grant after design review; it is not
  work this proof performs.
- **Scope boundary that matters for Ryan:** the live R1-B archive-move for *this*
  source is now blocked **only** on E2 (the vector guard is satisfied, the orphan is
  confirmed, the writer is known). If Ryan wants to proceed before E2 is built, the
  only defensible interim is **E3** from my prior review — a bounded live-quiescence
  attestation for the move window (state-dir mtime unchanged since capture; watcher
  stopped+disabled+MainPID=0; and, given the attribution, **no agent session holding a
  shell against the data root during the move**). E3 bounds risk for a single
  supervised action; it does not substitute for E2 as the durable fix.

---

## (c) Disposition for the §4.3 collateral: three lost checkpoints + four re-driven transactions

The proof's §4.3 is a **new, material finding** that is larger than the single-source
wedge this arc has been chasing. I verified it on disk (dirs `248e25cb…`, `98d65c7f…`,
`e55a6f61…` re-created Oct 17 18:54, empty `prepared/`+`snapshots/`, now
`bootstrap_required`). My disposition:

### The three lost checkpoints — restore from restic `495c2d65`, do not re-bootstrap by default

- **Prefer restore.** The checkpoints and prepared caches represent **paid Arc Codex
  transform work** (the whole point of the budget guard). The last good copies are in
  restic `495c2d65` (Oct 17 00:17, local) with the offsite copy as a second line.
  Restoring the artifacts recovers the spend without re-burning provider calls;
  re-bootstrap pays for them again. On a cost basis alone, restore wins.
- **Procedure (Ryan-gated; Cursor/Claude executes, not this review):** restic
  `--no-lock restore 495c2d65` of the three state dirs into **fresh 0700 scratch**
  (never in place), verify each restored `checkpoint.json`/`prepared/*` against its own
  recorded digests, and only then stage a supervised live replacement under the same
  E3 quiescence conditions as any live write. If a restored artifact fails its
  integrity check (prefix digest / cache-key / fingerprint mismatch against the current
  source), **that** dir falls back to re-bootstrap — restore is not blindly trusted.
- **Watch for staleness.** `495c2d65` is Oct 17 00:17, *before* the 05:2x displacement.
  If any of these three sources legitimately advanced between the backup and the move
  (new messages appended), the restored checkpoint may be behind the current source
  prefix; the integrity check will surface that as a prefix mismatch and the dir
  re-bootstraps forward from the restored point. So: **restore first, re-bootstrap only
  on verified mismatch or restore failure.** That ordering recovers the most spend with
  the least risk.

### The four re-driven transactions — yes, they need verification

The four dirs (`0f4d56e0…`, `1677cfce…`, `614602b2…`, `975fc327…`) had their journals
flipped APPLYING→PREPARING and were **re-driven live** via `convmem.py index --file
--now` by the same ad-hoc `settle_apply2.py` subprocess. The report states their
checkpoints committed Oct 17 00:34–Oct 19 21:44 but that the **outcome (roll forward
vs back) was not verified**. That is an open gap and it must be closed before further
Arc Codex live work, for three reasons:

1. **Unattested authority.** These were driven by a script that, on the *fifth* dir
   (our wedge), demonstrably re-wrote a journal **without its rollback authority**. A
   writer that mishandled authority on one transaction has not earned trust on the
   other four. Each needs its journal/retry-state and committed checkpoint checked for
   the same orphan/authority-loss signature.
2. **Same no-other-writer defect.** They were written under exactly the unfenced
   conditions that make (b) a blocker. Their commits are live mutations with no audit
   trail of correctness.
3. **Verification is cheap and read-only.** For each: confirm no orphan journal
   remains, confirm the committed checkpoint's prefix matches the current source, and
   spot-check that the committed rows match the source generation (the same
   measure-style hash comparison the proof already built). This is read-only forensics,
   not a live write, so it can proceed without an E2/E3 grant.

### Disposition: open a dedicated collateral packet, and gate further live Arc Codex work on it

The §4.3 collateral is **out of scope** for the single-source wedge recovery and should
not be folded into the R1-B grant. It warrants its **own investigation + remediation
packet** (Claude or Codex authors; Kiro re-reviews) covering: (1) restic restore of the
three lost dirs with the restore-first/re-bootstrap-on-mismatch rule above; (2)
read-only verification of the four re-driven transactions; (3) an explicit statement of
whether any *other* sources were touched by `cc8fde6b` beyond the eight enumerated.
Until that packet clears, **no further live Arc Codex transaction work** should proceed
— the same session's blast radius is not yet fully bounded.

---

## Carried forward (unchanged from prior review)

- **C1** (fail-closed contract-inventory, hashing actual bytes) still applies to the
  eventual §6 step-4 re-admission of the v1 checkpoint to semantic-v2. The wedge
  recovery does not re-transform and does not clear C1 for re-admission.
- **C2** (no wholesale module hashing into the runtime key) is the design lesson for
  the E2 fence: key the audit/lock on stable identity (source path, tx id, pid/exe),
  not a content-manifest a routine deploy perturbs.
- The **second retained transaction** (Kiro `sess_2628159e…`, `transform_failed`) still
  needs its own disposition, separate from this wedge.
- The **restic `hold-issue-286-wedge` tag** on `495c2d65`/offsite remains correctly
  Ryan-gated and is now **more urgent**: `495c2d65` is the only remaining copy of the
  three lost checkpoints. I endorse tagging it to prevent prune before the collateral
  restore runs.

---

## Overall verdict

**(a) R1-B-g: PASS** — the live source vectors equal the Oct 13 before-image in
Chroma's cosine-normalized on-disk representation (15/15 bit-exact vs a fresh
before-image write; the 1-ulp vs raw JSON floats is deterministic normalization, not a
delta). The R1-B archive-move is unblocked on vectors.

**(b) E1 PASS as attribution; E2 now MANDATORY** — the Oct 17 writer is identified
(Crush `cc8fde6b`, ad-hoc `/tmp/settle_apply*.py`), which confirms my code reading and
closes the mystery, but proves the no-other-writer risk is a standing, reproducible
capability of any shell-bearing lane. The live disposition is blocked on E2 (owner-lock
+ per-write audit); E3 (bounded quiescence) is the only defensible interim for a single
supervised move.

**(c) Collateral: restore the three lost checkpoints from `495c2d65` (re-bootstrap only
on verified mismatch/restore failure); the four re-driven transactions require
read-only verification.** Open a dedicated collateral packet and gate further live Arc
Codex work on it.

**Net change vs my prior review:** the live R1-B move advances from "held on vectors +
writer" to "held only on E2," and a new collateral workstream opens. Nothing in this
review grants anything — scratch is done; the live move, the fence, the checkpoint
restore, the re-driven-tx verification, and the hold-tag each remain separate,
Ryan-gated actions.

---

## Forward announcement

I finished: Kiro review of the Oct 13 wedge scratch proof + Oct 17 writer attribution
(`17530e5`) — rulings on (a) R1-B-g, (b) E1/E2, (c) collateral disposition.
Next step: Ryan decides (1) whether to grant the live R1-B archive-move now under E3
quiescence or wait for the E2 fence; (2) to authorize the collateral packet (restore
three checkpoints from `495c2d65`, verify four re-driven transactions) and the
`hold-issue-286-wedge` restic tag.
Next lane: Ryan (grants) → Cursor (E2 fence; checkpoint restore under grant) / Claude or
Codex (collateral packet) → Kiro re-review before any live disposition.
See my work:
`docs/inter-model/KIRO-2026-10-20-issue-286-oct13-wedge-scratch-proof-review.md`
on branch `kiro/2026-10-20-issue-286-oct13-wedge-review`.

## TL;DR

- **(a) R1-B-g PASS.** Live source vectors equal the Oct 13 before-image in Chroma's
  cosine-normalized storage (15/15 bit-exact vs a fresh before-image write; 1-ulp from
  raw JSON floats is deterministic normalization). R1-B archive-move unblocked on
  vectors. I confirmed the live wedged state dir is byte-identical to the report's
  end-state and the orphan (APPLYING journal, no `rollback.json`) is real.
- **(b) E1 accepted as attribution; E2 now MANDATORY.** Writer = Crush `cc8fde6b` ad-hoc
  `/tmp/settle_apply*.py` (confirms my code reading, closes the mystery) — but proves
  any shell-bearing lane can mutate live state dirs unfenced. Live disposition blocked
  on E2 (owner-lock + per-write audit); E3 quiescence is the only interim for a single
  supervised move.
- **(c) Restore the three lost checkpoints from restic `495c2d65`** (re-bootstrap only
  on verified mismatch/restore failure — restore recovers paid transform spend); **the
  four re-driven transactions need read-only verification.** Open a dedicated collateral
  packet; gate further live Arc Codex work on it. Tag `495c2d65` now (only remaining
  copy).
- **Net:** live R1-B advances from "held on vectors + writer" to "held only on E2";
  new collateral workstream opens. Nothing granted here.

<!-- src: ./CLAUDE-2026-10-20-issue-286-oct13-wedge-scratch-proof-report.md (branch docs/2026-10-20-issue-286-oct13-wedge-scratch-proof, 17530e5) — proof under review -->
<!-- src: ./KIRO-2026-10-20-issue-286-oct13-wedge-recovery-review.md (branch kiro/2026-10-20-issue-286-oct13-wedge-review, f3b2b45) — R1-B-g, G-a/G-b, C-run1/C-run2, E1/E2/E3 this review rules against -->
<!-- src: ../../incremental_jsonl.py at 3e705e4 — _validate_prepared_artifact, _write_transaction, _commit_generation, _codex_roll_forward_refusal verified via git show -->
<!-- src: /home/lauer/.local/share/convmem/incremental-jsonl/0d508630… and 248e25cb…/98d65c7f…/e55a6f61… — live wedged + collateral state dirs read read-only to corroborate §5 and §4.3 -->
<!-- ref: ../plans/STATUS-codex-jsonl-production-integration.md — arc brief; not updated by this read-only review -->

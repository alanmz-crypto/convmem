# Backup + Neutral decision memos (Cursor + ChatGPT) — salvage 2026-07-24

**Who:** Cursor (WS-main-cursor) assembled Cursor Track memos; ChatGPT Cloud
returned a counter-memo from research pack PR #114.  
**What:** Owner decision inputs for (1) complete-data backup close and
(2) Neutral / observation ledger-first appetite — **not** Architecture #115.  
**When:** After #114 merged; before Copilot exact-SHA audit of `492e6e7` and
before Ryan records Yes/No/Not-yet.  
**Why:** These lived only in chat; salvaged so one workspace can take over.  
**How:** Ryan decides the forks below; Copilot/Codex/Cursor follow ownership
lanes. **Does not authorize** live Restic rollout, Office coding, Neutral
extraction, or shadow hooks.

Related already on GitHub:

- Research pack (merged): [#114](https://github.com/alanmz-crypto/convmem/pull/114)
- Backup Copilot audit contract + attachments: pack under
  `docs/inter-model/research-pack-2026-07-24-backup-neutral/`
- Impl tip to audit: `492e6e7` on `fix/2026-07-23-complete-data-backup`
- Shadow Ledger Architecture (separate arc): draft [#115](https://github.com/alanmz-crypto/convmem/pull/115)

---

## Open owner forks (Ryan)

| Fork | Cursor memo | ChatGPT memo | Status |
|---|---|---|---|
| Track 1 consistency bar | **(A)** crash-consistent Restic + documented reconcile/reindex; write-gate wiring unverified ⇒ quiescence premature | Copilot **FAIL** unless five-part Universal Tier-1 proof (census, participation, safe boundary, adversarial concurrency, isolated restore) | **LOCKED Hybrid (Ryan 2026-07-24)** — Copilot scores A + reports Five-part; see [`COPILOT-2026-07-24-complete-data-backup-hybrid-bar.md`](COPILOT-2026-07-24-complete-data-backup-hybrid-bar.md) |
| Track 1 trigger | Hybrid: write-gated + daily ensure timer | Hybrid **contingent on** proven consistency protocol | Agree hybrid intent; disagree when timer counts toward RPO |
| Track 1 offsite | Fix tag-blind false-green; accept tag-presence as freshness bar (defer full remote restore) | Destination-proven, cost-tiered (lineage every copy; periodic isolated restore) | Agree false-green is real; depth of bar undecided |
| Track 2 appetite | Priority call; ship bucket A; use friction + retrieval postmortem; Not-yet OK with portable contracts | Record **Yes — Scope C** direction only → Phase 0 research (not migration); Gate 0 structure≠instantiation; active-policy index theater for Office v0 | Soft fork; compatible if Yes≠cutover auth |

Cross-arc (both agree): Track 1 proceeds without Track 2 answer; no Neutral
generalization inside the backup PR. Future Yes on ledger-first makes
reconcile≈replay cheaper — notice later, do not gate Track 1.

---

## Track 1 — Cursor memo (compressed)

1. **Consistency → (A)** crash-consistent + reconcile/reindex on restore. Not B
   (global quiescence) while write-gate call-site wiring is unverified; not C
   (same enumeration debt). Smallest verify: restore-from-mid-write in existing
   restore drill; assert drift **detected and reported**, then post-reconcile
   consistent. Premise: Chroma rebuildable from ledger — nail any
   non-reconstructable Chroma-unique state before trusting A.
2. **Trigger → both** write-gated + daily ensure (calendar RPO + heartbeat).
3. **Offsite →** post-sync check expected tags (`convmem-chroma` +
   `convmem-data-v1`) present; fail loud. Defer full offsite restore every cycle
   explicitly.
4. **Copilot blocking:** reconcile proven; ledger/sidecar restore asserted;
   legacy chroma tags still restore; consumers tested on `convmem-data-v1`; no
   Neutral creep; offsite tag check in PR or tracked follow-up.
5. **Rollout after Copilot PASS:** exact-SHA in audit doc → manual snapshot →
   doctor → scratch restore+reconcile → day of triggers → spot-check offsite +
   USB → docs → recurring drill → keep legacy tags a few cycles.

---

## Track 1 — ChatGPT memo (compressed)

- Pack set audit **policy**; did not claim `492e6e7` already failed — Copilot
  must re-check against the **actual diff**.
- Observations Chroma-first / weak export durability; decisions stronger but
  narrow; governed lock ≠ backup barrier; expanding coverage changes failure
  mode to silent-wrong mixed snapshots.
- Recommend hybrid trigger only after consistency protocol; Universal Tier-1
  families (shared lock / service pause / FS-native) without prescribing one.
- Silent-inconsistency threat model: many pairs restore-blocking today because
  no complete canonical observation ledger.
- Offsite: separate execution vs protection vs restore-assurance statuses.
- Next: Copilot exact-SHA → if FAIL, Codex consistency plan → Ryan picks
  mechanism → Cursor implements → re-audit.

---

## Track 2 — Cursor memo (compressed)

- Yes/No/Not-yet is **priority**, not more code-reading. Ship bucket A
  (secrets/logging/reranker) regardless; use friction + stale negative-existence
  retrieval postmortem as evidence.
- Gate 0 needs a concrete workflow card (artifact, people, steps, evidence it
  already happens) — structure alone is false readiness.
- Premature abstraction: two implementations is a thin base; hash discipline
  must allow legitimate domain divergence; audit other Neutral gates for
  Gate-0-style abstract criteria.

---

## Track 2 — ChatGPT memo (compressed)

- Recommend **Yes — Scope C** as **direction only** (ConvMem needs observation
  ledger-first on its own merits) → authorizes Phase 0 **research**, not
  migration, Neutral extraction, Office-driven refactor, or shared package.
- Gate 0: structurally specified, **not instantiated** (real artifact, people,
  sanitized request, revision, Ryan auth still missing).
- Active-policy index for Office v0 = architecture theater without named
  consumer/query.
- Improved Neutral coherence bar: authority/cutover, identity/revision,
  durable append, deterministic replay (ordered-log vs commutative stated),
  projection only with named consumer, portable duplicate tests before extract.
- Disagreements called out: lock≠backup consistency; observation/decision gap
  not “small”; full-root coverage incomplete without consistency; timer≠RPO
  alone; hermetic tests≠safety PASS.

---

## Suggested next actions (not authorized by this doc)

1. ~~Ryan locks Track 1 consistency bar~~ → **Hybrid locked** 2026-07-24.
2. Copilot audits `492e6e7` against Hybrid brief + base audit contract.
3. Ryan records Track 2 appetite (Yes-Scope-C direction / Not-yet / No).
4. Keep Shadow Ledger [#115](https://github.com/alanmz-crypto/convmem/pull/115)
   HITL on its own lane — do not fold Neutral Office work into it.

## TL;DR

Cursor and ChatGPT agree on hybrid trigger intent, offsite false-green risk,
separate tracks, and Gate 0 not execution-ready; they disagree on whether
`492e6e7` can pass with crash-consistent+reconcile (A) or must FAIL without
Universal Tier-1 five-part proof — Ryan must lock that bar before Copilot close.

# Cursor handoff — JudgeBench T2/T3/T4/T5 (Tier 5–8 escalation)

**Who/What:** Crush (lane) writing the routing handoff from Crush/DeepSeek V4 Flash to
the Cursor implementation lane for the JudgeBench Tier 5–8 escalation wall.
**When:** 2026-08-09, after G1 (architecture locked) + G2 (execution approved) + Kiro
PASS (MEDIUM complexity, no mandatory Cursor gate but Cursor is the designated
implementation lane).
**Why:** The tier-1 Flash slices (S1, S3–S9) landed on `main` and are green; the
remaining T2b/T3/T4b/T5 are **Tier 5–8, OFF-LIMITS to Flash/Crush** per
`EXECUTION-judgebench-flash-slices.md`. Ryan routed to Cursor.
**Branches:** author on `fix/2026-08-09-judgebench-arch-lock-chroma-rebuild` (already on
origin, contains the G1+ G2 approval commits) or a fresh `feat/…` branch you open.

---

## Authorized scope (G2, 2026-08-09)

Implement **T2, T3, T4, T5** from `docs/plans/EXECUTION-judgebench.md`. T6 remains
structure-only (E2E skeleton already landed via S1/S2); **no gold values** until G3.

**Do NOT touch:** `ask.py`, live judging, Chroma in the semantic path, gold authoring,
judge selection, J2/J3. (OFF-LIMITS per flash-brief §4.)

---

## Current landing state on `main` (verify with git, do not assume)

- `eval_judgebench/` present: `contracts.py`, `contract_validate.py`, `rubric.py`,
  `rubric_validate.py`, `__init__.py`, `identity_registry.py` (S7 stub).
- `eval_corpus/fixtures/judgebench/` present: `identity-registry-v1.json`,
  `semantic-v1/{manifest.json,cases.jsonl,gold.jsonl,rubrics/synthesis-grounded-v1.json}`.
- `tests/test_judgebench_{contracts,rubric,no_chroma}.py` — **29/29 pass**.
- `eval_provenance.py` present (has `classify`, `context_changed`, `fixture_hash`,
  `model_context`, `ollama_version`, `model_digest_and_quant`).
- **`eval_model_identity.py` does NOT exist** (T2 target).

---

## Tasks

### T2 — `eval_model_identity.py` + classify (Tier 5, OWNER Cursor)
- **Extend** the S7 stub `eval_judgebench/identity_registry.py` OR add
  `eval_model_identity.py` that implements `classify_independence(judge, under_test)`
  returning `self | same_family | cross_family | unknown | not_applicable`.
- **Rules (locked invariants):** different quants of same base = `self`; different known
  lineages same family = `same_family`; both families known and unequal = `cross_family`;
  unprovable = `unknown` (**fail-closed** for canonical calibration/baseline/update);
  `not_applicable` = human-curated candidate. **No substring guessing.** Serving-provider
  diversity alone never proves `cross_family`. `unknown` cannot be promoted by user.
- **S7 stub must drop its** `classify_independence` → `NotImplementedError`; lift the
  OFF-LIMITS docstring once implemented.
- **Gate:** `cross_family` enforcement; `unknown` fail-closed preflight; existing
  `not_applicable` preserved; unit tests.

### T3 — `eval_provenance.py` comparison-signature expansion (Tier 5–8)
- Build the canonical **comparison signature** over: evaluation surface; case/fixture/
  gold hashes; semantic-contract+rubric+schema+prompt hashes; identity-policy version +
  resolved identity records; judge role/lineage/revision/digest/quant; under-test model
  provenance; independence class; decoding params; model-serving runtime version;
  metric-policy version; E2E retrieval-corpus fingerprint.
- Signature change → `needs_rebaseline`/`incomparable` **before** score comparison.
- **Gate:** deltas detect evidence-id or judge-pin changes (this is VERIFY CHK-004).

### T4 — JudgeBench offline runner + semantic-v1 orchestration (Tier 5–7)
- Runner loads frozen case → J0 (MechanicalGrade, deterministic) → J1 (semantic judge)
  → compares to locked gold. **Chroma prohibited** in the semantic path (assert with the
  S8 no-chroma guard).
- Pinned judge per run (invariant 6); default temp 0; no majority vote; single call per
  case. Provider failure → `provider_error`/`not_run`, never semantic FAIL (invariant 5).
- **Gate:** runner dry-run with empty corpus (VERIFY CHK-007); corrupt/absent gold,
  Chroma stopped — inputs unchanged.

### T5 — Legacy `eval_judge.py` shim (Tier 6–8)
- Keep 1–5 score path **only** under explicit `--legacy` flag / legacy result type.
- Legacy output must be byte-compatible; **must not** emit v1 provenance or update v1
  baselines (VERIFY CHK-005, CHK-006). Mark clearly as legacy.

---

## Hard stops / do not cross

- **G3** (Ryan gold/split lock) — do **not** author semantic case content or E2E gold
  values; T6 scaffold is structure-only.
- **G4** (judge selection) — do **not** choose/bless a judge model; that is Ryan after
  calibration experiments.
- No J2/J3, no live `ask.py` integration, no Chroma in the semantic path.

---

## Acceptance / verify

- New/updated unit tests green; run:
  `~/miniforge3/envs/convmem/bin/python -m pytest tests/test_judgebench_contracts.py tests/test_judgebench_rubric.py tests/test_judgebench_no_chroma.py -q`
  plus new identity/provenance/runner tests.
- Do not regress the 29 existing tests.
- VERIFY CHK-004..008 become satisfiable (they were PENDING behind the escalation wall;
  this handoff removes that blocker for 004–008 as tasks land).
- Pylint gate: no new/increased findings (repo convention).

## Merge/PR

- Push branch immediately after each commit (remote-is-backup rule).
- On completion: offer a PR title/body with consequence-first shape per AGENTS.md; do not
  create the PR unless Ryan explicitly asks.

**Branch discipline:** `convmem work start feat|fix …` before first tracked edit; never
commit to `main`; push with explicit refspec.

**Merge reading:** [`ARCHITECTURE-judgebench.md`](../plans/ARCHITECTURE-judgebench.md) ·
[`EXECUTION-judgebench.md`](../plans/EXECUTION-judgebench.md) ·
[`EXECUTION-judgebench-flash-slices.md`](../plans/EXECUTION-judgebench-flash-slices.md) ·
[`VERIFY-judgebench.md`](../plans/VERIFY-judgebench.md).

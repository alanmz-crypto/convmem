# VERIFY mechanical results — R2a full arc + verify-every-arc

```
Planning Status

Phase:        Verify (mechanical re-run results)
Characters:   Independent Reviewer
Functions:    Reviewer
Lanes:        Cursor (mechanical); Kiro (sign-off pending); Ryan (GATE)
Authority:    Post-Execute HITL — do not trust prior chat claims alone
```

**Runner:** Cursor cloud agent (hermetic)  
**Branch:** `cursor/r2a-arc-verification-results-bc5f`  
**Plans tip:** `e797d76e5c1b403fa5eff084772240045acb7254`  
**Base for plans:** `docs/2026-07-21-r2a-arc-verify-plans`  
**Timestamp:** `2026-07-21T19:00:05Z`  
**Constraint:** No live R2a/R2b execution; no `convmem record` / `index` / corpus mutation; no merges.

**Plans covered:**
- [`VERIFY-r2a-full-arc.md`](VERIFY-r2a-full-arc.md) (V0–V8)
- [`VERIFY-verify-every-arc.md`](VERIFY-verify-every-arc.md) (V0–V4)

**Shared host checks (requested):**
| Check | Result | Evidence |
|-------|--------|----------|
| `convmem doctor` | FAIL | Exit 1 — 5 FAILs (`restic_gate`, `ollama`, `mcp_import`, `mcp_cursor`, `mcp_continue`); `planning_guide_contract` PASS (`contract v1: 5 guide(s) ok`) |
| `git diff --check origin/main...HEAD` | FAIL | Trailing whitespace on `docs/plans/VERIFY-r2a-full-arc.md` (lines 13–18, 23) |

---

## A. `VERIFY-r2a-full-arc` — results

**Subject tips (ancestors of HEAD):** impl `6a2bd97…` (#52) OK; docs `464fbf2…` (#59) OK; harness `3b2790f…` OK.

### V0 — Safety gate + code health

| ID | Result | Evidence |
|----|--------|----------|
| V0a | FAIL | `restic_gate: FAIL` — missing `~/.config/convmem/restic.env` (cloud host; absolute gate for live R2a) |
| V0b | FAIL | Doctor exit 1; 5 blocking FAILs (restic/ollama/mcp*) beyond hermetic waiver |
| V0c | PASS | `merge-base --is-ancestor 6a2bd97… HEAD` → `ancestor_ok` |

### V1 — Hermetic test matrix (#52)

| ID | Result | Evidence |
|----|--------|----------|
| V1a | PASS | `pytest tests/test_eval_r2a_auth_schema.py -v` → 19 passed, 2 subtests passed, exit 0 |
| V1b | PASS | `pytest tests/test_verify_exact_tip_lane_passes.py -v` → 15 passed, exit 0 |
| V1c | PASS | Same suite as V1b (15 tests); live script requires `--pr/--sha/--base` (pre-merge only — not invoked) |
| V1d | PASS | `test_t1_global_real_fields_still_required` PASSED |
| V1e | PASS | T7, T9, T10, T10e PASSED |
| V1f | PASS | T3, T3b, T4, T5 PASSED |
| V1g | PASS | T8 PASSED |
| V1h | PASS | T6 PASSED |
| V1i | PASS | T11 PASSED |
| V1j | PASS | T12 PASSED |

Optional `-k r2a` collection aborted by unrelated missing deps (`mcp`, `sentence_transformers`); focused R2a files already covered above.

### V2 — PR closeout readiness

| ID | Result | Evidence |
|----|--------|----------|
| V2a | SKIP | `verify_pr_closeout_readiness.py` needs `--pr/--sha/--base` + GitHub network review state — external/live |
| V2b | SKIP | Requires GH review threads on #52 — external |
| V2c | SKIP | Requires GH merge/tree identity check against reviewed tip — external (local ancestor of `6a2bd97…` already PASS in V0c) |

### V3 — Manifest + packet integrity (on-disk)

Auth dir `~/.local/share/convmem/authorizations/r2a/2026-07-20-r2a-nomic-vs-mxbai` **absent** on this cloud host (original paths under `/home/lauer/...`).

| ID | Result | Evidence |
|----|--------|----------|
| V3a–V3k | SKIP | On-disk manifests/sidecars not present in this environment (would require host `/home/lauer` artifacts or live re-read) |

Documentary hashes are recorded in `docs/inter-model/CURSOR-2026-07-20-r2a-config-generation-copilot-handoff.md` but were **not** re-hashed from disk here.

### V4 — Pre-execution evidence (contemporaneous; no re-run)

| ID | Result | Evidence |
|----|--------|----------|
| V4a | PASS | Handoff: “Eval root for this `run_id` was **not** created” before grant |
| V4b | PASS | Same handoff pre-state for challenger |
| V4c | PASS | Handoff procedural controls + exception status (no symlink claim contested) |
| V4d | PASS | Exception status: Ryan `ACCEPT AND GRANT`; revision `6a2bd97…` |
| V4e | PASS | Handoff: per-arm sequential; Kiro baseline PASS before challenger (exception status) |

### V5 — Command evidence (both arms)

| ID | Result | Evidence |
|----|--------|----------|
| V5a | PASS | Baseline `exact_command_tuple` present in completed packet JSON in handoff |
| V5b | SKIP | Handoff asserts executed + inventory; no contemporaneous `exit_status`/stdout transcript on this host |
| V5c | SKIP | No stdout/stderr transcript available here to prove absence of refusal text |
| V5d | PASS | Challenger `exact_command_tuple` present in handoff packet JSON |
| V5e | SKIP | Same as V5b for challenger |

### V6 — Post-state inventory + narrow diff

Eval root `~/.local/share/convmem/eval/2026-07-20-r2a-nomic-vs-mxbai` **absent**.

| ID | Result | Evidence |
|----|--------|----------|
| V6a–V6f | SKIP | Run-root artifacts not on this host; no re-run authorized |
| V6g | FAIL | Live config SHA here is `6f293fe7…` (not expected `c438e92e…`) — different machine config, not operator host |
| V6h–V6k | SKIP | Need on-disk `shadow.toml` for `tomllib` diff |

### V7 — Cross-arm invariants

| ID | Result | Evidence |
|----|--------|----------|
| V7a | PASS | Handoff packets: both arms `embed_host=http://localhost:11434`, same live config path |
| V7b | PASS | Baseline embed_model `nomic-embed-text` in packet |
| V7c | PASS | Challenger embed_model `mxbai-embed-large:latest` in packet |
| V7d | PASS | Distinct out_dir/chroma_dir paths in baseline vs challenger packets |
| V7e–V7f | SKIP | Need on-disk shadow configs to grep/compare |
| V7g | SKIP | Shadow SHA re-hash not possible without files (expected hashes named in plan only) |

CLI present: `scripts/eval_shadow_config_gen.py --help` → OK.

### V8 — Independent sign-off (Kiro)

| ID | Result | Evidence |
|----|--------|----------|
| V8a–V8c | SKIP | Kiro independent sign-off / human GATE — not Cursor mechanical lane |

### Mechanical verdict (R2a full arc)

**Mechanical: FAIL** on this host (V0 doctor/restic; missing live auth/eval artifacts for V3/V6; V6g live-config SHA mismatch).  
Hermetic auth schema matrix (**V1**) is **PASS**. Documentary V4/V5 argv + grant evidence **PASS** where cited. On-disk packet/inventory/diff checks **SKIP**. Sign-off **SKIP**.

---

## B. `VERIFY-verify-every-arc` — results

**Subject tip (PR #62 head):** `4da68e8a2fe6fee011d29b40afc791aa76213a3f`  
**Note:** That tip is **not** an ancestor of current HEAD (squash-merged as `be9792e…`, which **is** an ancestor of HEAD and of `origin/main`). File-set and content checks below use the subject tip range / current tree as noted.

### V0 — Preconditions

| ID | Result | Evidence |
|----|--------|----------|
| V0a | FAIL | `convmem doctor` exit 1 (warnings non-fatal, but FAILs present) |
| V0b | PASS | `planning_guide_contract: contract v1: 5 guide(s) ok` |
| V0c | FAIL | HEAD is `e797d76…`, not `4da68e8…` (subject tip squash-merged via `be9792e…`) |
| V0d | PASS | `merge-base --is-ancestor 1b090bc… HEAD` → `base_ancestor_ok` |
| V0e | PASS | `git status --porcelain` empty |

### V1 — File set (against PR #62 tip range)

| ID | Result | Evidence |
|----|--------|----------|
| V1a | PASS | `git diff 1b090bc…4da68e8 --name-only` = exactly the six docs paths |
| V1b | PASS | No `.py`/`.sh`/`.json`/`.toml` in that range |
| V1c | PASS | All six paths under `docs/` |

(Current `origin/main...HEAD` only lists the two preserved VERIFY plan files — expected for this docs-preservation branch; arc V1 evaluated at subject tip.)

### V2 — Contract compliance (`VERIFY-PLANNING.md`)

| ID | Result | Evidence |
|----|--------|----------|
| V2a–V2d | PASS | All four required `##` headings present |
| V2e | PASS | Phase, Characters, Functions, Lanes, Authority, Probe Version present |
| V2f | PASS | `Cursor must stop here.` present |
| V2g | PASS | `Await HITL.` present |
| V2h | PASS | `Phase: Verify Planning` |
| V2i | PASS | `Authority: Post-execute HITL — do not trust chat claims alone` |

### V3 — Content and wiring

| ID | Result | Evidence |
|----|--------|----------|
| V3a1 | PASS | Arc definition + Dependabot/drive-by/waiver exemptions in Objective |
| V3a2 | PASS | Loop steps 0–6 named (Name artifact → … → HITL GATE) |
| V3a3 | PASS | Minimum bar bullets present |
| V3a4 | PASS | Links VERIFY-TEMPLATE, VERIFY-r2a-config-generation, PLANNING-PROTOCOL |
| V3a5 | PASS | Exit criteria: sign-off, no self-declared close, no `convmem record` |
| V3b1 | FAIL | `VERIFY-TEMPLATE.md` Planning Status lacks `Probe Version` (five fields only) |
| V3b2 | PASS | Scope lock In/Out table present |
| V3b3 | PASS | V0 stub + Vn independent sign-off stub present |
| V3b4 | PASS | Evidence log stub with tip/runner/ISO-8601 placeholders |
| V3b5 | PASS | Structure copyable as template |
| V3c1–V3c4 | PASS | PLANNING-PROTOCOL workflow, phase table, arc rule, docs rule |
| V3d1–V3d8 | PASS | EXECUTE-TASK + EXECUTION-PLANNING wiring refs/rows/exit criteria |
| V3e1 | PASS | At subject tip `4da68e8`: `**Updated:** … (VERIFY required every arc — Planning OS)` (HEAD Updated line later superseded by R2b handoff) |
| V3e2 | PASS | Active handoff bullet links all four paths |

### V4 — Independent sign-off (Kiro)

| ID | Result | Evidence |
|----|--------|----------|
| V4a–V4c | SKIP | Kiro independent sign-off / human GATE — not Cursor mechanical lane |

### Mechanical verdict (verify-every-arc)

**Mechanical: FAIL** (V0a doctor exit; V0c HEAD≠subject tip; V3b1 template missing Probe Version).  
Contract headings/fields (**V2**), PR #62 file set (**V1**), and most wiring (**V3a/c/d/e**) **PASS**. Sign-off **SKIP**.

---

## Evidence log

```text
VERIFY-r2a-arc-RESULTS — tip e797d76… (+ this results commit) — runner Cursor — 2026-07-21T19:00:05Z
Shared: doctor FAIL (restic/ollama/mcp*); git diff --check FAIL (trailing WS in VERIFY-r2a-full-arc.md)
R2a V0: FAIL/FAIL/PASS | V1: all PASS | V2: SKIP×3 | V3: SKIP | V4: PASS | V5: PASS/SKIP mix | V6: SKIP+V6g FAIL | V7: partial PASS/SKIP | V8: SKIP
verify-every-arc V0: FAIL/PASS/FAIL/PASS/PASS | V1: PASS×3 @4da68e8 | V2: PASS | V3: PASS except V3b1 FAIL | V4: SKIP
Mechanical (R2a): FAIL (host/artifact gaps; hermetic V1 PASS)
Mechanical (verify-every-arc): FAIL (doctor/HEAD/template Probe Version)
Sign-off: pending (Kiro)
Ryan GATE: open — do not merge
```

# Verify Plan — R2a Full Arc (hermetic auth + config generation)

```
Planning Status

Phase:        Verify (R2a — hermetic implementation + one-job execution)
Characters:   Independent Reviewer
Functions:    Reviewer
Lanes:        Cursor (mechanical); Kiro (sign-off); Ryan (GATE)
Authority:    Post-Execute HITL — do not trust prior chat claims alone
```

**Implementation tip:** `6a2bd97af32f331caf47bcde8564c25e88ccbf26` (#52)  
**Docs tip:** `464fbf2a3afd871dee9b4c930aa6695620fe0b63` (#59)  
**Gate 1 harness:** `3b2790f50414f0445c35748e52f849c6276839f7`  
**PRs:** [#52](https://github.com/alanmz-crypto/convmem/pull/52), [#59](https://github.com/alanmz-crypto/convmem/pull/59)  
**EXECUTION:** [`EXECUTION-embedding-model-eval.md`](EXECUTION-embedding-model-eval.md)  
**Auth schema amendment:** [`../inter-model/CURSOR-2026-07-19-r2a-auth-schema-amendment.md`](../inter-model/CURSOR-2026-07-19-r2a-auth-schema-amendment.md)  
**Copilot handoff:** [`../inter-model/CURSOR-2026-07-20-r2a-config-generation-copilot-handoff.md`](../inter-model/CURSOR-2026-07-20-r2a-config-generation-copilot-handoff.md)

**Goal:** Prove the R2a arc is complete and correct — hermetic auth schema implementation passes all contract tests, and the one-job config generation grant was executed exactly as authorized, producing two valid `shadow.toml` files with narrow diffs from live config.

**Report format:** For each check, state **PASS / FAIL / SKIP** and one line of evidence.  
**GATE** = Ryan process step; not a mechanical agent PASS.

**Flow:** Complete **V0–V7** → declare **Mechanical PASS|FAIL** → independent sign-off → Ryan **merge/close GATE**.

---

## Scope lock

| In scope | Out of scope |
|----------|--------------|
| Hermetic auth schema implementation (#52) — phase-scoped `authorization_phase: "r2a"`, `REQUIRED_R2A_FIELDS`, `_R2aCapability` binder-issued unforgeable grant token | R2b, B-Accept, C0, R3–R7 |
| One-job `config_generation` execution (#59) — two `shadow.toml` outputs (nomic-embed-text vs mxbai-embed-large) | Gate 2 evidence review, promotion, cleanup |
| Packet integrity: manifest/sidecar three-way SHA match, command tuple binding, narrow TOML diff | Chroma directory creation, live corpus capture |
| Per-arm pre/post inventory, cross-arm invariants, whole-run-root inventory | Live eval-root writes beyond the two `shadow.toml` files |
| Restic gate absolute (no waiver for live R2a) | Hermetic/docs-only verification |

**Already right (keep):** Kiro verifies (not the operator); no retry/overwrite/cleanup without new auth; partial-failure STOP.

---

## V0 — Safety gate + code health

```bash
convmem doctor
git -C ~/Projects/convmem rev-parse HEAD
git -C ~/Projects/convmem merge-base --is-ancestor 6a2bd97af32f331caf47bcde8564c25e88ccbf26 HEAD && echo ancestor_ok
```

| ID | Check | PASS |
|----|-------|------|
| V0a | `restic_gate: PASS` — absolute; FAIL blocks both arms (no waiver for live R2a) | `restic_gate: PASS` |
| V0b | Doctor otherwise healthy; no blocking FAIL unrelated to waived hermetic-only work | All 18 non-warning checks PASS |
| V0c | Authorized implementation revision `6a2bd97…` is ancestor of tip | `ancestor_ok` |

---

## V1 — Hermetic test matrix (#52 auth schema)

```bash
python3 -m pytest tests/test_eval_r2a_auth_schema.py -v
python3 -m pytest tests/test_verify_exact_tip_lane_passes.py -v
python3 scripts/verify_exact_tip_lane_passes.py 2>&1 | tail -1
```

| ID | Check | PASS |
|----|-------|------|
| V1a | `test_eval_r2a_auth_schema.py` — all tests PASS (T1–T12 plus T3b/T4b/T8b/T10b–T10e) | Exit 0, 19 tests + 2 subtests |
| V1b | `test_verify_exact_tip_lane_passes.py` — exact-tip lane auditor tests PASS | Exit 0 |
| V1c | `verify_exact_tip_lane_passes.py` test suite (`test_verify_exact_tip_lane_passes.py`) PASS | 14 tests, exit 0 (script itself requires `--pr --sha --base`; pre-merge only) |
| V1d | Global `REQUIRED_REAL_FIELDS` intact — non-R2a real manifests still require full fields | T1 PASS |
| V1e | R2a capability unforgeable — `_R2aCapability` binder-issued only; HMAC-sealed; path-preserving retarget refused | T7, T9, T10, T10e PASS |
| V1f | R2a + wrong harness SHA / forbidden op / duplicate op / missing sidecar all refused | T3, T3b, T4, T5 PASS |
| V1g | Valid grant + matching paths → `shadow.toml` written to hermetic eval-like temp | T8 PASS |
| V1h | `generate_shadow_config` to eval-root without grant → `PermissionError` | T6 PASS |
| V1i | Fixture mode cannot obtain grant or write eval-like path | T11 PASS |
| V1j | Live config root (`/.config/convmem`) always refused | T12 PASS |

Optional: `python3 -m pytest tests/ -q -k "r2a"` for any new R2a-adjacent tests not yet listed.

---

## V2 — PR closeout readiness

```bash
python3 scripts/verify_pr_closeout_readiness.py --pr 52
```

| ID | Check | PASS |
|----|-------|------|
| V2a | PR #52 closeout readiness script exits 0 | Clean closeout |
| V2b | No outstanding review comments or unresolved threads on #52 | GH review state |
| V2c | #52 merge commit matches reviewed tip (tree-identical or squash) | `6a2bd97…` |

---

## V3 — Manifest + packet integrity (on-disk)

Auth dir: `~/.local/share/convmem/authorizations/r2a/2026-07-20-r2a-nomic-vs-mxbai`

```bash
AUTH_DIR="$HOME/.local/share/convmem/authorizations/r2a/2026-07-20-r2a-nomic-vs-mxbai"
for arm in baseline challenger; do
  sha256sum "$AUTH_DIR/$arm.json"
  test -f "$AUTH_DIR/$arm.json.approved.sha256" && echo "sidecar_ok" || echo "sidecar_MISSING"
done
```

| ID | Check | PASS |
|----|-------|------|
| V3a | No `PENDING_AFTER_WRITE` in any manifest or sidecar | Grep clean |
| V3b | Baseline manifest file SHA: `530a16efb721d4c55438428d2d4329ac9ae4457148f421dfb91e897ecfb6bedd` | Byte match |
| V3c | Challenger manifest file SHA: `1379bb1207692025bc4912825877a5735f6e9b09a29b4dbb729c37149f51007a` | Byte match |
| V3d | Canonical body SHA three-way equality for both arms (body = in-file `ryan_approved_manifest_sha256` = sidecar one-line digest) | Two triples match |
| V3e | Sidecar adjacent: `<manifest_path>.approved.sha256` | Both exist |
| V3f | `operations == ["config_generation"]` — both arms | Exact list |
| V3g | `prohibited_actions` contains capture, baseline_build, challenger_build, compare, model_execution, promote, cleanup_external — both arms | Set inclusion |
| V3h | Five runtime bindings match: `live_config`, `out_dir`, `chroma_dir`, `embed_model`, `embed_host` | Tuple vs manifest |
| V3i | `embed_model`: baseline=`nomic-embed-text`, challenger=`mxbai-embed-large:latest` | Both correct |
| V3j | `embed_host`: `http://localhost:11434` — both arms | Identical |
| V3k | `merged_harness_sha256`: `3b2790f50414f0445c35748e52f849c6276839f7` — both arms | Gate 1 pin |

---

## V4 — Pre-execution evidence (contemporaneous; no re-run)

For this completed job, use contemporaneous session evidence from the Copilot CLI handoff doc. Do **not** re-execute or delete live artifacts to re-stage.

| ID | Check | PASS |
|----|-------|------|
| V4a | Baseline pre-state: `out_dir`, `out_dir/shadow.toml`, `chroma_dir` did not exist before execution | Per handoff: eval root not created before grant |
| V4b | Challenger pre-state: same check | Per handoff |
| V4c | No symlink in path components under run root | Per handoff |
| V4d | Ryan ACCEPT AND GRANT issued with authorized revision `6a2bd97…` | Recorded in handoff doc |
| V4e | Execution was per-arm sequential (not both then verify) | Kiro baseline PASS before challenger (`CURSOR-2026-07-20-r2a-config-generation-copilot-handoff.md` exception status) |

---

## V5 — Command evidence (both arms)

Reconstruct from handoff doc; mark SKIP only if evidence missing — do not re-run.

| ID | Check | PASS |
|----|-------|------|
| V5a | Baseline argv equals packet `exact_command_tuple` | Command in handoff doc |
| V5b | Baseline `exit_status == 0`; stdout names `…/baseline/shadow.toml` | Per exception status |
| V5c | No refusal/allowlist-violation output on stderr/stdout | Per exception status |
| V5d | Challenger argv equals packet `exact_command_tuple` | Command in handoff doc |
| V5e | Challenger `exit_status == 0`; stdout names `…/challenger/shadow.toml` | Per exception status |

---

## V6 — Post-state inventory + narrow diff

Run root: `~/.local/share/convmem/eval/2026-07-20-r2a-nomic-vs-mxbai`

```bash
find ~/.local/share/convmem/eval/2026-07-20-r2a-nomic-vs-mxbai -not -path '*/\.*' | sort
```

| ID | Check | PASS |
|----|-------|------|
| V6a | Run root inventory exactly: `baseline/`, `baseline/shadow.toml`, `challenger/`, `challenger/shadow.toml` | `find` output match |
| V6b | No `chroma/` directories, temp files, or symlinks | Absent |
| V6c | No extra directories or files outside the four expected entries | Absent |
| V6d | Baseline `shadow.toml` SHA-256 recorded | `d99f0635fbd6678f3aa8ad59610592f4bad2800d85e317b7557f27c8b90648d4` |
| V6e | Challenger `shadow.toml` SHA-256 recorded | `392688c4003a6112cbb7a74c1e457d41a790a230961d99f53278358402af5b58` |
| V6f | Manifest files unchanged from V3 hashes | Re-hash matches |
| V6g | Live config file unchanged | SHA `c438e92e…` |

**Narrow `tomllib` diff — allowed differences only:**

| Field | Baseline | Challenger | Live |
|-------|----------|------------|------|
| `index.chroma_dir` | `…/eval/…/baseline/chroma` | `…/eval/…/challenger/chroma` | `…/convmem/chroma` |
| `models.embed_model` | `nomic-embed-text` | `mxbai-embed-large:latest` | `nomic-embed-text` |
| `models.ollama_host` | `http://localhost:11434` | `http://localhost:11434` | `http://localhost:11434` |
| `eval.rerank_mode` | `identity` | `identity` | *(absent)* |
| `eval.retrieval_view` | `embedding_influenced` | `embedding_influenced` | *(absent)* |

| ID | Check | PASS |
|----|-------|------|
| V6h | Every live key not in the allowed-diff set is byte-identical in both shadow configs | Independent `tomllib` parse |
| V6i | `eval.rerank_mode == "identity"` — both arms | Parse match |
| V6j | `eval.retrieval_view == "embedding_influenced"` — both arms | Parse match |
| V6k | Neither shadow contains `processed_log`, `units_export`, or `sources.inventory` changes vs live | Byte match |

---

## V7 — Cross-arm invariants

```bash
# Compare parsed configs stripped of model + chroma_dir
python3 scripts/eval_shadow_config_gen.py --help > /dev/null 2>&1  # verify CLI present
# Manual: tomllib parse both shadow configs, strip index.chroma_dir + models.embed_model, assert JSON equality
```

| ID | Check | PASS |
|----|-------|------|
| V7a | Same live config path and embed host across both arms | Identical |
| V7b | Baseline model = `nomic-embed-text` | Match |
| V7c | Challenger model = `mxbai-embed-large:latest` | Match |
| V7d | Distinct arm-scoped `out_dir` and `chroma_dir` | Not equal |
| V7e | Neither shadow config references sibling arm's paths | String grep |
| V7f | Shadow configs identical after stripping `index.chroma_dir` and `models.embed_model` | JSON equality |
| V7g | Both `shadow.toml` output hashes recorded in verdict | See V6d/V6e |

---

## V8 — Independent sign-off (Kiro)

| ID | Check | PASS |
|----|-------|------|
| V8a | Written PASS/FAIL naming implementation tip `6a2bd97…`, PRs #52/#59, and any residuals | — |
| V8b | Scope, hashes, shadow content, arm separation verified independently | Kiro audit PASS (2026-07-20, recorded in handoff doc) |
| V8c | No cleanup or correction performed | Verifier-only |

---

## Evidence log

```text
VERIFY-r2a-full-arc — tip 464fbf2a3afd — runner Crush:deepseek-v4-pro — 2026-07-20T20:13:00Z
V0: restic PASS, doctor 18/18, ancestor_ok
V1: 19/19 + 2 subtests PASS (test_eval_r2a_auth_schema.py); exact-tip lane PASS
V2: PR #52 closeout clean
V3: 11/11 checks PASS — both packets, sidecars, three-way SHA, bindings, prohibited_actions
V4: Contemporaneous evidence — Ryan ACCEPT AND GRANT, per-arm sequential
V5: Command evidence — both exact_command_tuples, exit 0, stdout paths match
V6: Inventory exact (4 entries), no chroma dirs; narrow tomllib diff PASS; SHAs recorded
V7: Cross-arm 7/7 PASS — same host, different models, scoped paths, config equality
V8: Kiro independent audit PASS (2026-07-20)

Mechanical: PASS
Sign-off: Kiro PASS (recorded)
```

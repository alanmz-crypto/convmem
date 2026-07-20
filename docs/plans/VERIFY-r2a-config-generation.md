# Verify Plan — R2a config_generation (one-job)

```
Planning Status

Phase:        Verify (R2a config_generation — live one-job + future grants)
Characters:   Independent Reviewer
Functions:    Reviewer
Lanes:        Cursor (mechanical evidence); Kiro (per-arm + final verdict); Ryan (grant + merge GATE)
Authority:    Post-Execute HITL — do not trust prior chat claims alone
```

**Authorized revision (impl):** `6a2bd97af32f331caf47bcde8564c25e88ccbf26` (#52)  
**Docs tip (handoff):** `464fbf2a3afd871dee9b4c930aa6695620fe0b63` (#59)  
**Gate 1 harness:** `3b2790f50414f0445c35748e52f849c6276839f7`  
**Run ID:** `2026-07-20-r2a-nomic-vs-mxbai`  
**Run root:** `/home/lauer/.local/share/convmem/eval/2026-07-20-r2a-nomic-vs-mxbai`  
**Auth dir:** `/home/lauer/.local/share/convmem/authorizations/r2a/2026-07-20-r2a-nomic-vs-mxbai`  
**Handoff:** [`../inter-model/CURSOR-2026-07-20-r2a-config-generation-copilot-handoff.md`](../inter-model/CURSOR-2026-07-20-r2a-config-generation-copilot-handoff.md)  
**EXECUTION context:** [`EXECUTION-embedding-model-eval.md`](EXECUTION-embedding-model-eval.md)

**Goal:** Prove a live R2a `config_generation` grant was (or will be) followed exactly — packet integrity, no overwrite, per-arm stop gates, command exit evidence, narrow TOML semantics, whole-run-root inventory, cross-arm invariants.

**Report format:** For each check, state **PASS / FAIL / SKIP** and one line of evidence.  
**GATE** = Ryan process step (merge / new grant); not a mechanical agent PASS.

**Flow (future grants — binding):** V0 → V1 → V2 → V3 → V4 (Kiro baseline) → **STOP unless PASS** → V5 → V6 → V7.  
**Flow (this completed job — evidence):** Re-run V0 (doctor/restic), V1 (packets on disk), V4/V6 post-state + narrow diff + cross-arm, V7. For V2/V3/V5 pre-exec and argv capture: use **contemporaneous session evidence** only; do **not** re-execute without a **new** Ryan grant.

---

## Scope lock

| In scope | Out of scope |
|----------|--------------|
| One-job R2a `config_generation` (create `out_dir` + `shadow.toml`; bind `chroma_dir` path) | Creating `chroma/` directories |
| Packet + sidecar three-way digest equality | R2b, B-Accept, C0, R3–R7 |
| Per-arm pre-state STOP; command evidence; narrow `tomllib` diff | Gate 2, promotion, cleanup |
| Whole run-root inventory; cross-arm invariants; Kiro verdict | Live Chroma store byte-identity (unless separately frozen) |
| Absolute `restic_gate: PASS` before live eval-root writes | Hermetic/docs waiver for live R2a |

**Already right (keep):** Kiro verifies (not the operator); no retry/overwrite/cleanup without new auth; partial-failure STOP.

---

## Expected packet identities (this run)

| Arm | Manifest file SHA-256 | Body digest (= in-file = sidecar) |
|-----|----------------------|-----------------------------------|
| baseline | `530a16efb721d4c55438428d2d4329ac9ae4457148f421dfb91e897ecfb6bedd` | `2bbb591ac9876319c7a59a050b9385528cda5c544afb21708ef67523b9f6078e` |
| challenger | `1379bb1207692025bc4912825877a5735f6e9b09a29b4dbb729c37149f51007a` | `563599d67513d864423c2f72c0947d18a6baacc7f034c6cf209b991e4734d1fa` |

| Arm | Model | `out_dir` | `chroma_dir` (bind only) |
|-----|-------|-----------|---------------------------|
| baseline | `nomic-embed-text` | `…/eval/…/baseline` | `…/eval/…/baseline/chroma` |
| challenger | `mxbai-embed-large:latest` | `…/eval/…/challenger` | `…/eval/…/challenger/chroma` |

Live config: `/home/lauer/.config/convmem/config.toml`  
Embed host: `http://localhost:11434`  
Working directory for commands: `/home/lauer/Projects/convmem`

---

## Eight mandatory rules (corrections)

1. **Restic absolute:** `convmem doctor` must report `restic_gate: PASS`. FAIL blocks both arms. No documentation/hermetic waiver applies to live eval-root R2a.
2. **Pre-existing-target STOP:** Before each arm, `out_dir`, `out_dir/shadow.toml`, and `chroma_dir` must not exist; no symlink in any path component under the run root; resolved paths must equal packet paths. Pre-existing → **STOP** (implementation uses `mkdir(exist_ok=True)` and `os.replace` — overwrite is not refused).
3. **Per-arm verify immediately:** Baseline packet+pre → execute once → Kiro baseline PASS → only then challenger pre → execute → Kiro challenger → cross-arm. Never execute both then verify once.
4. **Packet integrity:** No `PENDING_AFTER_WRITE`; `manifest_file_sha256` = file bytes; canonical body SHA = `approved_manifest_body_sha256` = `ryan_approved_manifest_sha256` = adjacent `<manifest>.approved.sha256` contents; `operations` exactly `["config_generation"]`; `prohibited_actions` is a list including capture, builds, compare, model execution, promote, cleanup; five runtime bindings match the command tuple; `authorized_revision` = `6a2bd97…`; Ryan grant quotes/incorporates both final packet identities.
5. **Command evidence:** cwd, exact argv vector (not a reconstructed shell string), start/finish timestamps, exit status, stdout, stderr, resulting `shadow.toml` SHA-256. PASS requires exit `0`, stdout naming the exact authorized `shadow.toml`, and no refusal/allowlist-violation output. Exit `1` may leave a file — existence alone ≠ success.
6. **Narrow R2a semantic diff:** Kiro parses live + shadow with `tomllib`. Allowed differences only:

   | Field | Expected |
   |-------|----------|
   | `index.chroma_dir` | Exact arm-bound future Chroma path |
   | `models.embed_model` | Exact packet model |
   | `models.ollama_host` | Exact packet host |
   | `eval.rerank_mode` | `identity` |
   | `eval.retrieval_view` | `embedding_influenced` |

   Every other live value must remain semantically identical. Do **not** accept the generator’s general allowlist (it also permits `processed_log` / `units_export` / `sources.inventory`).
7. **Whole-run-root inventory:** Final contents of the run root must be exactly:

   ```text
   baseline/
   baseline/shadow.toml
   challenger/
   challenger/shadow.toml
   ```

   No `chroma/` dirs, temps, symlinks, or extras. Live config file hash unchanged. Manifests and sidecars unchanged from approved packet values. Do **not** claim live Chroma store byte-identical unless separately frozen.
8. **Cross-arm invariants:** Same live config and embed host; baseline model `nomic-embed-text`; challenger `mxbai-embed-large:latest`; distinct arm-scoped `out_dir`/`chroma_dir`; neither shadow references the sibling; parsed configs identical except model + arm Chroma path; both output hashes in Kiro’s verdict.

---

## V0 — Safety gate

```bash
convmem doctor
# Must show restic_gate: PASS — FAIL blocks both arms (no waiver for live R2a)
git -C ~/Projects/convmem rev-parse HEAD
git -C ~/Projects/convmem merge-base --is-ancestor 6a2bd97af32f331caf47bcde8564c25e88ccbf26 HEAD && echo ancestor_ok
```

| ID | Check | PASS |
|----|-------|------|
| V0a | `restic_gate: PASS` | Absolute; FAIL stops |
| V0b | Doctor otherwise healthy enough to proceed | No blocking FAIL unrelated to waived hermetic-only work |
| V0c | Authorized revision on `main` ancestry | `6a2bd97…` is ancestor of tip |

---

## V1 — Grant integrity

For **each** arm packet (baseline, challenger):

| ID | Check | PASS |
|----|-------|------|
| V1a | No field contains `PENDING_AFTER_WRITE` | Grep packets/manifests |
| V1b | `manifest_file_sha256` = SHA-256 of file bytes at `manifest_path` | `sha256sum` |
| V1c | Canonical body SHA (exclude `ryan_approved_manifest_sha256`) equals packet `approved_manifest_body_sha256`, in-file field, and sidecar one-line digest | `eval_corpus.run_manifest.canonical_manifest_body_sha256` + read sidecar |
| V1d | Sidecar path is exactly `<manifest_path>.approved.sha256` (adjacent) | Path check |
| V1e | `operations == ["config_generation"]` | Exact list |
| V1f | `prohibited_actions` is a list containing capture, baseline_build, challenger_build, compare, model_execution, promote, cleanup_external | Set inclusion |
| V1g | Five bindings equal command tuple: `live_config`, `out_dir`, `chroma_dir`, `embed_model`, `embed_host` | Tuple vs manifest/paths |
| V1h | `authorized_revision` = `6a2bd97af32f331caf47bcde8564c25e88ccbf26` | Exact |
| V1i | Ryan grant quotes/incorporates both final packet identities (file and/or body hashes) | Grant text / chat |

Optional hermetic: `pytest -q tests/test_eval_r2a_auth_schema.py` (schema code still green; does not authorize live writes).

---

## V2 — Baseline pre-state

| ID | Check | PASS |
|----|-------|------|
| V2a | Baseline `out_dir` does not exist | `test ! -e` |
| V2b | Baseline `out_dir/shadow.toml` does not exist | `test ! -e` |
| V2c | Baseline `chroma_dir` does not exist | `test ! -e` |
| V2d | No symlink in path components under run root (create run root parents only if grant allows; else require absent) | `find -type l` empty under run root if present |
| V2e | `realpath` of packet paths equals packet string bindings | Resolve match |

Pre-existing target → **STOP**. Do not proceed to V3.

**This completed job:** record PASS/FAIL from contemporaneous pre-inventory (session showed run root absent before first command). Do not delete live artifacts to re-stage V2.

---

## V3 — Baseline execution

Record evidence pack:

- `working_directory`
- `argv` as JSON array (exact vector)
- `t_start`, `t_finish` (ISO-8601)
- `exit_status`
- `stdout` (full)
- `stderr` (full)
- `shadow_toml_sha256` after success

| ID | Check | PASS |
|----|-------|------|
| V3a | argv equals packet `exact_command_tuple` | Byte-identical args |
| V3b | `exit_status == 0` | Required |
| V3c | stdout names exact authorized `…/baseline/shadow.toml` | Path match |
| V3d | No refusal / allowlist-violation text on stderr/stdout | Grep |
| V3e | Resulting file SHA recorded | `sha256sum` |

**This completed job:** reconstruct from session logs if argv/timestamps were not filed; mark SKIP only if evidence truly missing — do not re-run.

---

## V4 — Baseline verification (Kiro)

After baseline only (challenger must not have run yet on a future grant):

| ID | Check | PASS |
|----|-------|------|
| V4a | Inventory under run root is only `baseline/` + `baseline/shadow.toml` | `find` |
| V4b | No `baseline/chroma`; no temps; no symlinks | `find` |
| V4c | Narrow `tomllib` diff vs live config (rule 6) | Independent parse |
| V4d | `shadow.toml` SHA recorded in evidence | Hash |
| V4e | Manifests/sidecars unchanged vs V1 | Re-hash |

Kiro **PASS** required before V5. Kiro performs **no** cleanup or correction.

---

## V5 — Challenger pre-state and execution

Only after V4 Kiro **PASS**:

1. Repeat V2 checks for challenger paths (**STOP** if any exist).
2. Repeat V3 evidence pack for challenger `exact_command_tuple`.

| ID | Check | PASS |
|----|-------|------|
| V5a | Challenger pre-state (V2a–e for challenger) | STOP on fail |
| V5b | Challenger execution evidence (V3a–e for challenger) | Exit 0 + stdout path |

---

## V6 — Challenger verification + cross-arm

| ID | Check | PASS |
|----|-------|------|
| V6a | Challenger narrow `tomllib` diff (rule 6) | Independent parse |
| V6b | Final run-root inventory exactly four entries (rule 7) | `find` sort |
| V6c | No `challenger/chroma`; no temps; no symlinks | `find` |
| V6d | Live config file SHA unchanged vs pre-grant snapshot | `sha256sum` |
| V6e | Auth manifests + sidecars unchanged vs V1 | Re-hash |
| V6f | Same `live_config` and embed host both arms | Compare |
| V6g | Models exactly nomic vs mxbai | Compare |
| V6h | Distinct arm-scoped dirs; no sibling path refs in either shadow | Grep paths |
| V6i | Parsed shadows identical except model + chroma_dir | Diff |
| V6j | Both output SHA-256 values recorded | Evidence |

Do **not** claim live Chroma store byte-identical unless a freeze was authorized separately.

---

## V7 — Kiro verdict

Written **PASS** or **FAIL** must name:

- Both packet identities (file SHA and/or body digest)
- Both `shadow.toml` SHA-256 values
- Authorized revision `6a2bd97…`
- Any residual / unexpected artifacts
- Explicit statement: no cleanup or correction performed

| ID | Check | PASS |
|----|-------|------|
| V7a | Structured verdict present | Written block |
| V7b | Names packet + output hashes + revision | All present |

---

## Final expected filesystem (post both arms)

```text
/home/lauer/.local/share/convmem/eval/2026-07-20-r2a-nomic-vs-mxbai/
  baseline/
    shadow.toml
  challenger/
    shadow.toml
```

Auth dir (outside eval; unchanged after grant):

```text
…/authorizations/r2a/2026-07-20-r2a-nomic-vs-mxbai/
  baseline.json
  baseline.json.approved.sha256
  challenger.json
  challenger.json.approved.sha256
```

---

## Mechanical vs sign-off

1. Cursor/operator fills V0–V6 evidence tables (or SKIP with reason for non-replayable pre-exec steps on the completed job).
2. Kiro issues V4 (baseline) and V7 (final) — for a future grant, V4 is a hard gate before challenger.
3. Ryan **GATE:** merge this VERIFY docs PR; authorize any new live R2a job only under this sequence.

**Partial failure:** STOP; preserve inventories and evidence; no retry/overwrite/cleanup without new Ryan authorization.

---

## Evidence log (fill on re-verify)

```text
VERIFY-r2a-config-generation — tip <sha> — runner <lane> — <ISO-8601>
V0: …
V1: …
V2: … (or SKIP — contemporaneous …)
V3: …
V4: …
V5: …
V6: …
V7: Kiro PASS|FAIL — packet baseline=… challenger=… shadow baseline=… challenger=… revision=6a2bd97…
```

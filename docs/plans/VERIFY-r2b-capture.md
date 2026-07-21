# Verify Plan — R2b capture + corpus package

```
Planning Status

Phase:        Verify (R2b capture)
Characters:   Independent Reviewer
Functions:    Reviewer
Lanes:        Cursor (mechanical evidence); Kiro (sign-off); Ryan (GATE + grant)
Authority:    Post-Execute HITL — do not trust prior chat claims alone
```

**EXECUTION:** [`EXECUTION-2026-07-20-r2b-capture.md`](EXECUTION-2026-07-20-r2b-capture.md)  
**Parent runbook:** [`EXECUTION-embedding-model-eval.md`](EXECUTION-embedding-model-eval.md)  
**CLI:** `scripts/eval_corpus_capture.py` → `eval_corpus.capture.run_capture`  
**Binder:** `bind_capture` / `assert_capture_authorized` — runtime fields exactly  
`CAPTURE_FIELDS = {export, processed, capture_dir, chroma_dir}`  
**Gate 1 harness pin:** `3b2790f50414f0445c35748e52f849c6276839f7`  
**Auth files root (convention):** `~/.local/share/convmem/authorizations/r2b/<run_id>/`  
**Eval capture root (convention):** `~/.local/share/convmem/eval/<run_id>/capture/` (exact paths = grant)  
**Working directory for commands:** `/home/lauer/Projects/convmem`

**Goal:** Prove one Ryan-granted real-mode `capture` produced the immutable capture products under the packet-bound `capture_dir`, with Chroma required, without B-Accept / Gate 2 creep.

**Report format:** For each check, **PASS / FAIL / SKIP** + one line of evidence.  
**GATE** = Ryan process step (grant / merge / close); not a mechanical agent PASS.

**Status:** Checks filled (T1). **Live R2b capture not authorized** until Ryan posts T2 grant. Do not run V2–V5 against disk until after grant + T3 manifests.

**Flow (after grant):** V0 → V1 → V2 → V3 → V4 → V5 (Kiro) → Ryan GATE.

---

## Scope lock

| In scope | Out of scope |
|----------|--------------|
| One real-mode `capture` via approved manifest + adjacent `.approved.sha256` | `--authorize-fixture` as a substitute for live grant |
| Packet-bound `export`, `processed`, `capture_dir`, `chroma_dir` | B-Accept, adjudication edits to spot-check, C0, R3–R7 |
| Capture products listed under **Expected artifacts** | Gate 2, promotion, cleanup, R8 |
| Absolute `restic_gate: PASS` before eval-root writes | Overwrite of pre-existing `capture_dir` without new auth |
| Canonical overlap policy (40/30/30) as implemented | Claiming live prod Chroma byte-freeze unless separately authorized |

---

## Open decision (block T3 until Ryan picks)

Real `execution_mode=real` manifests (non-R2a) must include every `REQUIRED_REAL_FIELDS` entry — including `corpus_package_sha256` and `unit_corpus_fingerprint` — **before** capture runs, but capture **produces** those digests.

| Option | Meaning |
|--------|---------|
| **A — Phase-scoped R2b schema** | Code change: `authorization_phase: "r2b"` with capture-only required fields (like R2a). Preferred for honesty. |
| **B — Grant placeholders** | Ryan-approved pre-image digests / sentinel values bound in the manifest; VERIFY records them; post-capture digests must be recorded separately and must not silently rewrite the approved manifest. |

T2 grant text must name **A or B**. T3 must not invent a third path.

---

## Expected artifacts (under packet `capture_dir`)

Write-once completion products from `run_capture` (names fixed by code):

| Path | Role |
|------|------|
| `knowledge_units.jsonl` | Copied export |
| `processed.json` | Copied processed (if source existed) |
| `chroma_extract.json` | Collection metadata + id list + sqlite SHA |
| `chroma_documents.json` | Extracted documents slice |
| `corpus_package.jsonl` | Deduped package bytes |
| `corpus_package_manifest.json` | Package manifest (fingerprint, sha, counts) |
| `overlap_validation.json` | Stratified overlap result |
| `historical_spot_check.json` | Immutable spot-check plan (**must not be edited by adjudicate**) |
| `capture_report.json` | Status, input SHAs, `package_sha256`, `unit_corpus_fingerprint`, `overlap_overall`, `corpus_accepted` |

`capture_report.status` success values: `CAPTURE_COMPLETE` (or grant-documented `UNRESOLVED` if Ryan accepts under-quota overlap). `FAILED` → VERIFY FAIL.  
`corpus_accepted` must remain `false` after R2b (B-Accept is a later arc).

---

## Exact command shape (fill paths from grant)

```bash
cd /home/lauer/Projects/convmem
python3 scripts/eval_corpus_capture.py \
  --run-manifest <auth>/capture.json \
  --export <packet export> \
  --processed <packet processed> \
  --capture-dir <packet capture_dir> \
  --chroma-dir <packet chroma_dir>
```

No `--authorize-fixture` on the live grant path.

---

## Mandatory rules

1. **Restic absolute:** `convmem doctor` → `restic_gate: PASS`. FAIL blocks capture. No hermetic/docs waiver for live eval-root R2b.
2. **Pre-existing-target STOP:** Before execute, `capture_dir` must not exist (or must be Ryan-authorized empty with no completion products). No symlinks under the eval run root. Resolved paths must equal packet paths. Capture uses write-once products — pre-existing completion files → **STOP**.
3. **Single shot:** One argv execution per grant. No retry/overwrite/cleanup without **new** Ryan authorization. Preserve evidence on FAIL.
4. **Packet integrity:** No `PENDING_AFTER_WRITE`; file SHA; three-way body digest = in-file `ryan_approved_manifest_sha256` = adjacent sidecar; `operations` allowlist includes `capture` and matches grant (no silent extras like `promote`); `prohibited_actions` is a **list** including at least `promote`, `cleanup_external`, and non-granted build/compare/model_execution ops; four `CAPTURE_FIELDS` bindings match argv; `merged_harness_sha256` = Gate 1 pin; grant quotes packet identity + authorized revision.
5. **Command evidence:** cwd, exact argv vector, start/finish ISO timestamps, exit status, full stdout/stderr, SHA-256 of `capture_report.json` + `corpus_package.jsonl` + `historical_spot_check.json`. PASS needs exit `0`, stdout JSON with `package_sha256` / fingerprint fields, no `Refusing capture:` on stderr.
6. **Chroma required:** Packet and argv both bind `chroma_dir`; capture must have performed chroma extract (`capture_report.chroma_extract` true / extract files present).
7. **Whole `capture_dir` inventory:** Final tree must match **Expected artifacts** (plus empty dirs only if grant allows). No unexpected paths; no temps left; no symlinks.
8. **Spot-check immutability:** `historical_spot_check.json` byte-identical from post-capture to Kiro sign-off; adjudicate must not have run.
9. **Live config / prod export:** Hash of packet `export` and `processed` sources at pre-capture recorded; post-capture sources may differ (live corpus moves) — VERIFY records pre-hashes from `capture_report` input SHA fields and does **not** require post-run source freeze unless Ryan grants a freeze.

---

## V0 — Safety gate

```bash
convmem doctor   # require [PASS] restic_gate
git -C ~/Projects/convmem rev-parse HEAD
# authorized_revision from grant must be ancestor of tip
```

| ID | Check | PASS |
|----|-------|------|
| V0a | `restic_gate: PASS` | Absolute |
| V0b | Grant names `authorized_revision`; tip has that commit as ancestor | |
| V0c | Option A or B from **Open decision** named in grant | |

---

## V1 — Grant + packet integrity

| ID | Check | PASS |
|----|-------|------|
| V1a | No `PENDING_AFTER_WRITE` in packet or manifest | |
| V1b | `manifest_file_sha256` = SHA-256 of file bytes at `manifest_path` | |
| V1c | Canonical body SHA (exclude `ryan_approved_manifest_sha256`) = packet body field = in-file field = sidecar one-line digest | |
| V1d | Sidecar path is exactly `<manifest>.approved.sha256` | |
| V1e | Schema valid under chosen option A (r2b phase) or B (full `REQUIRED_REAL_FIELDS` + documented placeholders) | |
| V1f | `operations` matches grant and includes `capture` | |
| V1g | `prohibited_actions` is a list; includes `promote`, `cleanup_external` | |
| V1h | `paths` supplies `export`, `processed`, `capture_dir`, `chroma_dir` matching argv | |
| V1i | `merged_harness_sha256` = `3b2790f50414f0445c35748e52f849c6276839f7` | |
| V1j | Ryan grant quotes packet file and/or body hash + revision + option A/B | |

---

## V2 — Pre-state STOP

| ID | Check | PASS |
|----|-------|------|
| V2a | `capture_dir` does not exist OR is empty with Ryan empty-dir authorization | STOP otherwise |
| V2b | None of the **Expected artifacts** exist at `capture_dir` | |
| V2c | No symlinks under eval run root | `find -type l` empty |
| V2d | `realpath` of packet paths equals packet strings | |

---

## V3 — Execution evidence

| ID | Check | PASS |
|----|-------|------|
| V3a | argv equals grant `exact_command_tuple` | |
| V3b | `exit_status == 0` | |
| V3c | stdout is JSON including `package_sha256`, `unit_corpus_fingerprint`, `capture_dir` | |
| V3d | stderr has no `Refusing capture:` | |
| V3e | Evidence pack filed (cwd, argv JSON, timestamps, exit, stdout, stderr, artifact SHAs) | |

---

## V4 — Artifacts + report semantics

| ID | Check | PASS |
|----|-------|------|
| V4a | All **Expected artifacts** present under `capture_dir` | |
| V4b | Inventory has no unexpected files/dirs (list in evidence) | |
| V4c | `capture_report.status` is `CAPTURE_COMPLETE` (or grant-allowed `UNRESOLVED`) | |
| V4d | `capture_report.corpus_accepted` is `false` | |
| V4e | `capture_report.package_sha256` equals SHA-256 of `corpus_package.jsonl` bytes **or** equals package manifest field per code contract (record which) | |
| V4f | `overlap_validation.json` `overall` consistent with report `overlap_overall` | |
| V4g | `historical_spot_check.json` present; SHA recorded | |
| V4h | Manifests/sidecars under `authorizations/` unchanged vs V1 | |
| V4i | No adjudicate outputs (`corpus_acceptance.json` absent) | |

---

## V5 — Independent sign-off (Kiro)

| ID | Check | PASS |
|----|-------|------|
| V5a | Written PASS/FAIL naming packet hashes, `package_sha256`, `unit_corpus_fingerprint`, `historical_spot_check` SHA, authorized revision | |
| V5b | Explicit: no cleanup/correction performed by verifier | |
| V5c | Spot-check file hash matches V4g | |

---

## Evidence log

```text
VERIFY-r2b-capture — tip <sha> — runner <lane> — <ISO-8601>
V0: …
V1: …
V2: …
V3: …
V4: …
V5: …
Mechanical: PASS|FAIL|NOT_RUN (awaiting grant)
Sign-off: …
Open decision: A|B|unset
```

---

## Soft-close / arc close

Blocked until: Ryan T2 grant → T3 manifests → T4 capture → mechanical V0–V4 recorded → V5 sign-off → Ryan GATE.  
Planning-only merge of this VERIFY fill does **not** authorize capture.

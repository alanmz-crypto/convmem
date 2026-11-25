# Claude → Codex handoff: adversarial review of the embedding-identity change (2026-11-24)

**Arc: none (ad-hoc).** `docs/inter-model/LATEST.md` and `STATUS-*.md` were intentionally not changed.

**Date:** 2026-11-24
**Author:** Claude (implementation)
**For:** Codex (adversarial review, read-only)
**Authorization:** Ryan, 2026-11-24, in chat ("create a prompt and handoff to have Codex do an adversarial review").

## Resume state

| Field | Value |
|-------|--------|
| **State** | `IN_PROGRESS` (implementation done; independent review outstanding) |
| **Branch** | `fix/2026-11-24-chroma-collection-embed-identity` |
| **Code under review** | `73e072b` (later commits on the branch are docs and bookkeeping only: this handoff and its manifest line) |
| **Push status** | pushed to origin |
| **PR** | not opened |
| **Ryan GATE** | Ryan decides the PR after this review. Nothing here authorizes a merge. |
| **Track A ingest** | not performed |

## What was built (so you know what to attack)

Issue: normal `ChromaStore` collection creation never recorded which embedding model made the vectors, so `convmem doctor` WARNed on every session and a model change could not be detected. Issue text: `/home/lauer/Projects/convmem/Issues/chroma-collections-missing-embedding-identity.md` (untracked in the shared checkout; read it by absolute path, do not touch that checkout). Items 1–4 are covered:

1. **Record at creation** (`chroma_store.py:31,136,319`; `chroma_write_store.py:632,705`). `ChromaStore` takes an optional `embed_model`; the production factory passes `cfg["models"]["embed_model"]`. Both collections go through one `_collection` path. Chroma ignores metadata on an *existing* collection, so only newly created collections are stamped.
2. **Attest legacy collections without editing them** (`chroma_embed_attestation.py`). A sidecar file beside the Chroma directory (`<chroma_dir name>.embed-attestation.json`) binds collection UUID + Chroma's own dimension + an operator-claimed model. It is written only after a re-embedding spot check on a restic restore copy. Dry run unless `--write`.
3. **Doctor semantics** (`chroma_embed_identity.py`, `doctor.py:1679`, `chroma_readonly.py:422`). Judges both collections read-only (SQLite `mode=ro`, no client). `[index] require_embed_identity = true` turns the unattested WARN into a FAIL; default off.
4. **Bookkeeping**: SHADOW writer inventory coordinates, repository-knowledge manifest, R2B inventory regeneration, one hardcoded coordinate in `tests/test_shadow_writer_gate_c3.py`.

Diff: `git fetch origin fix/2026-11-24-chroma-collection-embed-identity && git diff origin/main...origin/fix/2026-11-24-chroma-collection-embed-identity --stat` (15 files, about +2100/−94 at `73e072b`). Commits: `git log origin/main..73e072b --oneline`.

## Claims to falsify (my claims, not established facts)

- **C1.** No new code path modifies an existing collection's metadata or vectors (production write path, doctor, attestation tool).
- **C2.** `create_collections=False` and the recovery session still never create a collection; the new `embed_model` argument cannot change that.
- **C3.** Doctor returns PASS for a collection only if (a) it records a model equal to the configured model (and any recorded dimension equals Chroma's), or (b) it records none and a sidecar entry matches its UUID, its Chroma-recorded dimension and the configured model.
- **C4.** On the live store the default doctor verdict stays WARN. A new FAIL appears only with the strict switch, a corrupt sidecar, or a model/dimension contradiction.
- **C5.** The attestation tool never writes to the live Chroma directory, never opens a client on a path that overlaps or shares files with it, and writes the sidecar only if every requested collection passes.
- **C6.** A model other than the one claimed cannot pass the spot check (cosine ≥ 0.99, default sample 50, minimum 10).
- **C7.** Each new guard is covered by a test that fails when the guard is removed, and every new test is hermetic (nothing opens the live store).
- **C8.** The bookkeeping diffs are mechanical: SHADOW inventory = coordinates only; manifest = one hash refresh plus `unrelated` classifications for new files; R2B = `code_revision`, `inventory_digest`, `route_id`/`entrypoint`/`shadow_inventory_ref` for the one moved site.

## Where I suspect weakness (attack here first, then beyond)

1. **Trust model of the sidecar.** It is an unauthenticated operator claim; anyone able to write the data directory can forge a PASS. Is binding to UUID + dimension enough? Is a forged or stale sidecar distinguishable from a real one? Should it carry a hash of the evidence or the model digest? Compare with CG2's D0 attestation (`cg2_legacy_vector_attestation.py`, `cg2_rollback_baseline.py:427-554`, profile `LEGACY_EXACT_VECTOR_UNKNOWN_MODEL_V1`): is this a second, weaker authority for the same fact? I did not check whether a ratified CG2 chain exists for the live store.
2. **Spot-check power.** 50 of N documents, snapshot-time only. Can a mixed-model collection (some vectors from another model, or written after the snapshot) pass? Quantify. Is 0.99 justified given Ollama non-determinism, and is the failure direction always "refuse"?
3. **Text equality.** The spot check assumes the stored `document` is exactly the text that was embedded. I verified that only for `ingest.py` (summary → `summary`; unit → `summary + " " + keywords` stored as `doc`). I did not verify `observe.py`, `inter_model_index.py`, `propose_decision.py`, `repository_knowledge_index.py`, or older writers. Which can produce a document that differs from the embedded text, and what does the tool do then (false refusal vs false acceptance)?
4. **Model identity is a name, not a digest** (`nomic-embed-text:latest`). A moved `:latest` tag is invisible to doctor. Is that acceptable for "fail closed"?
5. **Doctor aggregation and exit behaviour.** `DoctorCheck(ok, status)` mapping; "WARN:" prefix duplication in aggregated detail; read errors on the second collection; behaviour when `conversation_summaries` exists but `knowledge_units` does not; anything that parses doctor output (scripts gating under `set -e`, e.g. `scripts/cross-project-digest.sh`, `Issues/weekly-digest-blocked-by-doctor-fail.md`).
6. **Regression of exact-metadata assumptions.** Does any code, recovery path, CG2 baseline comparison or test assert that a freshly created collection's metadata equals exactly `{"hnsw:space": "cosine"}`, so that a newly stamped collection would now mismatch (for example a restore, rebuild or rollback comparing against a fresh store)? `git grep` for it; I believe not, but I did not prove it.
7. **Creators I left alone.** `open_chroma_for_read` (default `create_collections=True`, no cfg) and `refine.py:628` can still create an unmarked collection in an empty directory. With the strict switch on, is that fail-closed enough or a hole?
8. **Attestation tool mechanics.** Race windows between the overlap/inode check and `open_chroma_for_verify`; symlink and bind-mount cases beyond the SQLite inode check (`_shares_storage`); `_existing_evidence` re-reads the sidecar without the validator; fsync of the file but not the directory; sidecar file mode; behaviour with a 6.5 GB store (`collection_ids` loads every id); partial failure between collections.
9. **Governance.** I regenerated the R2B inventory myself (as #419 did), but the repo's rule is that the author of a writer-code change does not attest it. Independently regenerate and compare (see "What I need back", item 2).
10. **Test quality.** Tests that mirror the implementation instead of constraining behaviour; assertions that pass for the wrong reason; places where a hermetic fixture hides a real-store difference (the live store has 768-dimension vectors and a 6.5 GB SQLite file; my tests use 8- and 16-dimension scratch stores).

## Known gaps I am disclosing (do not spend time rediscovering these)

- The attestation tool has **never been run** against a real restic restore or a real embedding service; tests use a deterministic fake embedder.
- The live store was read once, read-only through the doctor access path: both collections exist, 768 dimensions, metadata `{'hnsw:space': 'cosine'}`, no sidecar.
- CI launcher (`tests/_safe_harbor_t3_worker.py run-ci`, pinned restic 0.19.0, Python 3.11 locally, CI is 3.12): 5 failed / 3922 passed. One is in the bare-pytest baseline (`test_golden_questions`). Four are restic `lchown … invalid argument` failures on this machine (`/tmp` is owned by `nobody`) in `tests/test_backup_workflows.py` and `tests/test_restic_offsite.py`. I did **not** run `origin/main` under the launcher, so "environmental" is an attribution, not a proof.
- Bare-pytest full suite: same 265 failures as `origin/main` with the same command, none new (baseline is ephemeral; regenerate it on `origin/main` if you want to compare).
- `doctor.py` is being edited by another agent in the shared checkout (uncommitted, invisible to me). None of the pushed doctor-arc branches touch `doctor.py`; the R2B inventory and manifest will conflict with some of them whoever lands second.
- Intermediate commits leave bookkeeping tests red until later commits; squash-merge makes that moot.

## Rules for the reviewer

- **Read-only on this branch.** Do not push, force-push, open a PR, or merge. Try fixes only in a scratch clone.
- **Do not touch `~/Projects/convmem`** (the shared checkout has another agent's uncommitted changes).
- **Do not open the live Chroma directory** (`~/.local/share/convmem/chroma`) with any client, and do not write anywhere under `~/.local/share/convmem`. Use `tmp_path`-style scratch stores.
- **Never read or print** `~/.claude.json`, `~/.codex/config.toml`, `~/.kiro/settings/mcp.json`, `~/.claude/settings.json`, or any env file holding API keys.
- Do not call the convmem `ask` tool. Do not edit `LATEST.md` or `STATUS-*.md`.

## How to run things

```bash
git fetch origin fix/2026-11-24-chroma-collection-embed-identity
git switch --detach 73e072b          # or a scratch clone
tmp=$(mktemp -d)
sed "s|~/.local/share/convmem|$tmp/nodata|g" config.example.toml > "$tmp/config.toml"
env -i HOME="$tmp/home" PATH=/usr/local/bin:/usr/bin:/bin LANG=C.UTF-8 TMPDIR="$tmp" \
  CONVMEM_CONFIG="$tmp/config.toml" PYTHONDONTWRITEBYTECODE=1 ANONYMIZED_TELEMETRY=False \
  ~/miniforge3/envs/convmem/bin/python -m pytest -q -p no:cacheprovider \
  tests/test_chroma_store_embed_identity.py tests/test_chroma_production_embed_identity.py \
  tests/test_chroma_embed_identity.py tests/test_chroma_embed_attestation.py
```

Expected: 112 passed. The bookkeeping tests are `tests/test_r2b_v2_corrective_viii.py`, `tests/test_r2b_v2_implementation_revision.py`, `tests/test_repository_knowledge_committed_manifest.py`, `tests/test_shadow_writer_coverage_scan.py`, `tests/test_shadow_writer_gate_c3.py` and `tests/test_file_generation_read_path_inventory.py`; run them in the same environment. Interpreter: Python 3.11 locally with chromadb 1.5.9.

## What I need back

1. **Findings**, ranked Critical / High / Medium / Low, each with `file:line`, a reproduction (a failing test or a command against a scratch store), and whether it is observed or inferred. Lead with anything that would block a PR.
2. **R2B attestation (a required statement):** regenerate the inventory yourself into a scratch path (`from eval_corpus.r2b_v2.coverage.inventory import build_static_route_inventory`), compare with `docs/plans/R2B-V2-WRITER-COVERAGE-INVENTORY.json`, and state `MATCH` or `DIFFERS` and whether the diff against `origin/main` is only the fields listed in C8.
3. **A verdict on C1–C8:** `AGREE / DISAGREE / CANNOT VERIFY`, one line of evidence each.
4. **Answers to suspicion items 1, 2, 6 and 7** in particular, even if the answer is "no problem found", with how you looked.
5. **A recommendation:** ship as is, ship after named changes, or rework; and whether the sidecar design should proceed or be replaced by extending CG2.

Report as plain text in your reply. Ryan files it; do not commit it to this branch.

## Prompt Ryan can paste into Codex

```text
Do an adversarial, read-only review of an unmerged change in the convmem repo. Assume the author is wrong until the code shows otherwise; do not rely on the author's summary.

Branch: fix/2026-11-24-chroma-collection-embed-identity (pushed). Code under review: commit 73e072b.
Setup: git fetch origin fix/2026-11-24-chroma-collection-embed-identity && git switch --detach 73e072b   (or use a scratch clone)
Read first: docs/inter-model/CLAUDE-2026-11-24-chroma-embed-identity-codex-adversarial-review-handoff.md (claims C1–C8, suspected weak points 1–10, disclosed gaps, rules, how to run, report format).
Issue being fixed (read it by absolute path only; do not modify that checkout): /home/lauer/Projects/convmem/Issues/chroma-collections-missing-embedding-identity.md
Diff: git diff origin/main...origin/fix/2026-11-24-chroma-collection-embed-identity

Tasks:
1. Read the diff and the new modules in full (chroma_embed_identity.py, chroma_embed_attestation.py) plus the edits to chroma_store.py, chroma_write_store.py, doctor.py, chroma_readonly.py.
2. Try to falsify C1–C8 with real experiments on scratch Chroma stores (tmp dirs only). Write failing tests where you can.
3. Work the suspicion list, especially items 1 (sidecar trust vs CG2), 2 (spot-check power), 6 (code that assumes metadata is exactly {"hnsw:space": "cosine"}) and 7 (creators left unmarked).
4. Independently regenerate the R2B inventory into a scratch path and say MATCH or DIFFERS; confirm the diff is only the fields named in C8.
5. Give a ranked findings list, an AGREE/DISAGREE/CANNOT VERIFY line per claim, and a recommendation (ship / ship after changes / rework / replace the sidecar with CG2).

Rules: read-only on the branch (no push, PR, merge or force-push); do not touch ~/Projects/convmem; never open the live Chroma directory (~/.local/share/convmem/chroma) or write under ~/.local/share/convmem; never read or print ~/.claude.json, ~/.codex/config.toml, ~/.kiro/settings/mcp.json, ~/.claude/settings.json or env files with API keys; do not call the convmem ask tool; do not edit LATEST.md or STATUS files. Put the report in your reply, not in the repo.
```

---

## Review round 1 outcome (appended after the Codex review; the text above is the record of what was reviewed at 73e072b)

Codex recommended **rework before a PR**. It reproduced eight problems, answered the suspicion items, and independently attested the R2B regeneration at bea21a2 (`MATCH`, digest `7d306fe3…`). Disposition of each finding:

| Codex finding | Disposition |
|---|---|
| High: a new collection can be stamped with the wrong model (embed, config reload, writer open) | **Fixed in two steps; the first was not enough.** 332591f tagged vectors (`llm.ollama_embed` returns a list that remembers its model) and refused a *creating* write of a vector made by another model. Preparing round 2 I found that did not cover real writers: they read before they write (the dedupe query and `get_unit` run on the writer store), a read creates the collection already stamped with the live config, and the later `add_unit` then saw an existing collection and accepted the model-A vector (reproduced). 48f6891 compares the *first vector* with what the collection records (or would be stamped with), at `add_unit`/`update_unit` and in `_native`. Only a first write is judged; once a collection holds vectors, a mismatch is left to doctor. |
| High: strict legacy PASS survives replacing every vector | **Not closed, hardened.** A sidecar is a point-in-time claim about a restore copy; it cannot prove the vectors are unchanged. Hardening: evidence is mandatory and validated, doctor reports "sampled k of N", and strict accepts only a full check (`--sample-size all`). Ryan decided to keep the sidecar as the strict authority rather than extend CG2 D0. |
| High: non-finite vectors or threshold publish a result | **Fixed** (2f247c0). NaN, infinity, zero vectors and non-finite or out-of-range thresholds are errors; NaN/Infinity literals in the sidecar are refused. |
| High: an error in one collection erases a FAIL in the other | **Fixed** (2f247c0). Each collection is judged on its own; unreadable is WARN (FAIL when strict); a non-UTF-8 sidecar is an attestation error; empty metadata on a collection that holds vectors is unproven, not ignored. |
| High: C5 live-directory isolation | **Fixed for what was observed.** The sidecar path is made absolute (`"."` can no longer land inside live); the copy is compared file by file (device and inode), symlinks in the copy are refused, an uninspectable directory refuses the copy, the check repeats before each collection's client opens, and a collection requested by name must exist. **Residual:** a local actor swapping files between the last check and the client open; no shared-segment write was observed by Codex or me. |
| Medium: PASS without a configured model or a comparable dimension | **Fixed.** No configured model is WARN (FAIL when strict); the sidecar needs a known Chroma dimension. A stamped collection with no vectors yet and a recorded dimension still passes, deliberately (nothing to contradict). |
| Medium: read or refine jobs create unmarked collections first | **Not changed.** Only affects brand-new empty stores (the live collections exist). Doctor now says an empty unmarked collection can be dropped so the next write stamps it. Making `open_chroma_for_read` and `refine.py:628` get-only changes first-run behaviour of the serving path and belongs in its own PR. |
| Medium: two attestations can lose an entry | **Fixed.** Exclusive lock, re-read under it, parent directory fsync. |
| Low: whitespace in the model name FAILs an unchanged config | **Fixed.** Both ends use `normalize_embed_model`. |

Claim verdicts after the fixes: C1 and C2 stand. C3, C4 and C5 now hold as corrected above. **C6 stays false as an absolute:** a sample can miss a minority of foreign rows (pinned by `test_a_full_check_catches_foreign_vectors_a_sample_can_miss`); the full-census option and the strict rule are the mitigation. C7: Codex found the sampled-id completeness guard had no test; it has one, and 29 guards across the new code were mutation-checked. C8 correction: the manifest change is four refreshed hashes (`chroma_store.py`, `chroma_write_store.py`, `config.example.toml`, `tests/test_shadow_writer_gate_c3.py`) and seven new `unrelated` classifications (including this document), not one hash and six files.

Also recorded from the review: a ratified owner-scoped CG2 D0 chain exists under the machine's file_generations root (captured 2026-08-29, both collections, historical model explicitly UNKNOWN). Nobody compared its roots with today's live store. It matters for any later move from the sidecar to a CG2 extension.

**Operating rule (Ryan's decision):** attest with `--sample-size all`, then set `[index] require_embed_identity = true`. Strict mode enforces the full-census part itself.

**Still open for Ryan:** (1) whether writes into an already-stamped collection with another model's vector should be refused (today only creation is); (2) the serving-read and `refine` creators, as a follow-up PR.

Verification recorded at 332591f/9fae6c9 (superseded by the round 2 section below): full suite 213 failed / 3533 passed / 52 errors with the same 265 failing ids as the baseline and none new. **R2B has been regenerated since Codex attested it, so it needs a fresh independent attestation at the final tip.**

---

## Round 2 review brief (written after round 1 was addressed)

You may be a fresh reviewer. Everything above is context and history; this section says what to do now. Round 1 found real defects, so assume round 2 can too: I already found two of my own while preparing it (below), which is evidence that my self-checks are not enough.

### Resume state (round 2)

| Field | Value |
|-------|--------|
| **State** | `IN_PROGRESS`: round-1 findings addressed, independent re-review outstanding |
| **Branch** | `fix/2026-11-24-chroma-collection-embed-identity` (pushed) |
| **Base** | `origin/main` = `f10d67d` (unchanged). In a clone, `origin/main` can be stale; fetch it from the source worktree's remote-tracking ref and check it reads `f10d67d`. |
| **Code under review** | `6910a49`; later commits on the branch are docs only (this section) |
| **Delta since round 1** | `73e072b..6910a49`: `2f247c0` harden identity and attestation, `332591f` stamp guard, `9fae6c9` strict needs a full check, `48f6891` stamp guard covers read-before-write writers, `8d672e6` RecursionError, `6910a49` reverts the one-line `ingest.py` change |
| **Expected counts** | identity and store suites **201 passed, 1 xfailed** (the xfail is deliberate, see C11); the nine governed-inventory suites **84 passed**, none skipped |
| **Full suite** | at `6910a49`, from a scratch clone: 213 failed / 3545 passed / 69 skipped / 1 xfailed / 52 errors, the **same 265 failing ids as the baseline on `origin/main`, none new** (the failures are pre-existing; see "Known flaky tests") |
| **PR** | not opened; Ryan gates it. Nothing here authorizes a merge. |

### What changed since you (or round 1) looked

- `chroma_embed_identity.py`: each collection judged on its own with a broad safety net; configured model normalised and required; evidence mandatory and validated; strict accepts only a full-census attestation; `RecursionError` from a deeply nested sidecar is an unusable sidecar (FAIL), not an escape.
- `chroma_embed_attestation.py`: non-finite and zero vectors, thresholds validated; whole-tree device/inode comparison, symlinks refused, fail-closed on unreadable directories, re-checked before each client opens; exclusive lock, re-read under it, directory fsync; random recorded seed; `--sample-size all`; a collection requested by name must exist.
- `llm.py`: `ollama_embed` returns `EmbeddingVector`, a `list` that remembers its model. `chroma_store.py`: `ChromaStore._require_vectors_match_first_write` compares the first vector of a collection with what it records (or would be stamped with) at `add_unit`, `update_unit` and in `_native`; looked up once per store session. `ingest.py` is **unchanged**: a one-line fix (stop copying the conversation-summary vector with `list()` at line 1130, which drops the tag) broke three baseline-hash pins in the incremental-JSONL canary tests, so I reverted it in `6910a49`; a strict xfail records the gap.
- Bookkeeping: manifest hashes refreshed for `chroma_store.py`, `chroma_write_store.py`, `config.example.toml` and `tests/test_shadow_writer_gate_c3.py`, plus seven new `unrelated` classifications; SHADOW inventory coordinates only; **R2B regenerated again** (`code_revision` is content-derived: any edit to the identity modules changes it).

### Decisions already taken (do not re-argue unless you find a defect that undermines them)

1. The sidecar stays the strict authority for legacy collections; CG2 D0 is not extended in this change. Strict mode requires an attestation that checked every row.
2. Only a collection's **first** vector is judged. Refusing a mismatched write into a collection that already holds vectors is a policy call left open (it would stall indexing after a config model change).
3. `open_chroma_for_read` and `refine.py:628` can still create unmarked collections on a brand-new store; follow-up PR.
4. The conversation-summary vector reaches the store untagged on the `ingest.py` path, so that collection's first write is not checked (unit vectors keep their tag). Closing it means editing `ingest.py`, whose hash `tests/test_incremental_jsonl_canary_baseline.py`, `..._p2_corrective.py` and `..._p2_runtime_readiness.py` pin; those pins record a reviewed refresh for every past change, so re-pinning is Ryan's call, not part of this change.

### Claims to falsify

- **C9.** No path through `ChromaStore` stores a vector tagged with model X as the first vector of a collection that records (or would be stamped with) model Y. Include read-first writers, `restore_source_rows`, and any code that reaches `_collection(...).upsert` directly.
- **C10.** No legitimate production write is newly refused. Find any real flow where the model passed to `ollama_embed` legitimately differs from `[models] embed_model` in the config the writer loads (CLI overrides, per-source models, recovery, the incremental path).
- **C11.** The tag reaches the store on the real writer paths. I only grepped for `list(`/`float(` copies: found `ingest.py:1130` (summary vector; **not fixed**, see decision 4, pinned by a strict xfail) and `incremental_jsonl.py:1591,1604` (off by default, persists vectors, not changed). There are 15 `ollama_embed` call sites outside tests and scripts; trace them end to end. A lost tag fails open.
- **C12.** `EmbeddingVector` is a plain list to every consumer. I checked JSON, numpy, pickle and deepcopy (tag kept) and slicing and `list()` (tag dropped, by design). Look for `type(x) is list` checks, Chroma validation paths, multiprocessing.
- **C13.** `check_embed_identity` never raises, and never returns PASS while any collection has a definite FAIL, for any collection metadata or sidecar bytes. Fuzz it. Doctor's two `except` blocks still turn any escape into WARN.
- **C14.** Every sidecar the tool writes parses and (with a full check) passes strict. I ran 60 randomized attestations including threshold edges, unicode and newline notes, with no failure; look for edges I did not.
- **C15.** Concurrent attestations never lose an entry. The committed test nests two calls in one process; I probed two real processes ad hoc (both entries survived), not committed.
- **C16.** Copy isolation holds against hardlinks, symlinks, directory swaps and a copy that appears valid after the first check. Also consider the opposite error: the tool refuses *any* symlink in the copy; does a real restic restore of a chroma directory ever contain one?
- **C17.** The bookkeeping is mechanical. R2B diff against `origin/main`: `code_revision` (top level and 39 routes), `inventory_digest`, and `route_id`/`entrypoint`/`shadow_inventory_ref` for the one moved site. Manifest: four refreshed hashes (listed above) and seven new `unrelated` entries. `ingest.py` must be byte-identical to `origin/main`. SHADOW inventory: coordinates only.

### Where I suspect weakness (attack here first, then beyond)

1. **What strict PASS means.** A full-census attestation covers the rows in the restore copy at snapshot time. Rows written after it are unverified (they rely on production using the configured model), and rows replaced after it are not detected. Is "full census at snapshot plus the configured model" an honest fail-closed state, or does the doctor detail overstate it?
2. **Model names are strings.** The tag, stamp and config compare normalised names. `nomic-embed-text` and `nomic-embed-text:latest` are different strings. Which direction can that go wrong (false refusal, false accept) in real configs?
3. **"First write" is `count() == 0`.** A collection emptied by deletes and rewritten under another model passes; one created empty by a read and stamped from a stale config is judged against that stamp. Is count the right proxy? Race with another process writing between the check and the write?
4. **The check reads outside the write guard.** It calls `client.get_collection` and `count()` before a guarded native write. Any interaction with `ChromaWriteGuard`, `_reload_client`, `ChromaStaleSystemError`, or the shared HNSW loading state?
5. **The per-session cache** (`_first_write_checked`): thread-safety, and whether a store reused across a config reload keeps a stale verdict.
6. **Broad `except Exception`** per collection in `check_embed_identity`: does it swallow something that should surface (a programming error reported as "cannot read collection metadata")?
7. **Sidecar location and lock file.** The sidecar and `.lock` sit beside the Chroma directory, outside it. Permissions, a world-writable parent, a pre-existing symlink at the sidecar path (the tool opens the lock with `O_CREAT` and replaces the sidecar with `os.replace`).
8. **Tests that pass for the wrong reason.** Round 1 found a shared fixture whose empty evidence made malformed-input cases pass vacuously, and a guard with no test. I mutation-checked 35 guards this round (and 12 in the first build), but my mutations are my own idea of what matters. Find a guard whose removal no test notices.

### Known flaky tests (do not chase these)

The full-suite diff at `48f6891` showed five failures outside the baseline. Three were the `ingest.py` change (reverted). Two are not mine: `tests/test_openclaw_watch_coverage.py::IsolatedWatchCoverageTests::test_real_watch_subprocess_and_public_query_reproduce_across_data_roots` fails about half the time on pure `origin/main` (2 of 4 runs, no changes of mine), and `tests/test_issue_286_scoped_proof_shadow.py::test_c_sh3_cc2_raw_collection_handle_bypass_unqualified` failed once inside the full run on `httpx.ConnectError: Temporary failure in name resolution` and passes in isolation on both `main` and this branch.

### What I already probed myself

Found and fixed before this review: the stamp guard missed the read-before-write flow (reproduced with `get_unit` then `add_unit`; fixed in `48f6891`), and a deeply nested sidecar raised `RecursionError` through doctor's check (fixed in `8d672e6`). Probed and unchanged: pickle/deepcopy keep the tag; a real two-process race keeps both entries; 60 randomized sidecars round-trip.

### Disclosed gaps (do not spend time rediscovering these)

- The attestation tool has never run against a real restic restore or a real Ollama; the identity checks have only run on scratch stores. Nothing here may open the live store.
- A sample cannot rule out a minority of foreign rows (pinned by a test; the full check is the mitigation). Model identity is a name, not a digest. A ratified CG2 D0 chain exists on the machine (captured 2026-08-29, historical model UNKNOWN) and was never compared with today's live store.
- Unmarked collections can still be created by `open_chroma_for_read` and `refine.py:628` (decision 3). `incremental_jsonl.py` drops the tag (C11).
- Intermediate commits are not individually green on the governed-inventory suites (R2B is regenerated at the end of several commits); judge the tip. Squash-merge makes this moot.
- Python 3.11 locally against 3.12 in CI. `doctor.py` is concurrently edited, uncommitted, by another agent in the shared checkout, and was not changed in this round.

### Rules, commands, report format

Same rules as "Rules for the reviewer" above (read-only on the branch; scratch clone only; never the live Chroma directory; never the client config or env files named there; no `ask`; no `LATEST.md`/`STATUS-*.md`). Commands as in "How to run things", with these changes: the code is `6910a49` (the branch tip is a docs-only commit after it), and the expected results are 201 passed and 1 xfailed for the four identity and store files and 84 passed for `tests/test_r2b_v2_corrective_viii.py`, `tests/test_r2b_v2_implementation_revision.py`, `tests/test_r2b_v2_coverage.py`, `tests/test_repository_knowledge_committed_manifest.py`, `tests/test_repository_knowledge_scope.py`, `tests/test_shadow_writer_coverage_scan.py`, `tests/test_shadow_writer_gate_c3.py`, `tests/test_file_generation_read_path_inventory.py` and `tests/test_t3_residual_closure.py`.

Return, as plain text in your reply: (1) findings ranked Critical / High / Medium / Low, each with `file:line`, a reproduction and observed-or-inferred; (2) the **R2B attestation**, regenerated independently into a scratch path, stating `MATCH` or `DIFFERS` and whether the diff against `origin/main` is only the fields in C17, and the digest you computed; (3) `AGREE / DISAGREE / CANNOT VERIFY` for C9 to C17 with one line of evidence each; (4) direct answers to suspicion items 1, 2, 3 and 8 even if the answer is "no problem found", with how you looked; (5) a recommendation: ship, ship after named changes, or rework, and whether strict-with-sidecar is an acceptable fail-closed state.

### Prompt Ryan can paste into Codex (round 2)

```text
You are a reviewer for an unmerged change in the convmem repo. This is round 2: an earlier review found real defects and I fixed them; assume more remain. Be adversarial toward my work, and trust nothing I say until the code shows it.

Get the code without touching anyone's checkout (never work in or modify ~/Projects/convmem):
  scratch=$(mktemp -d)
  git clone /home/lauer/.local/share/convmem/worktrees/fix-2026-11-24-chroma-collection-embed-identity "$scratch/repo" && cd "$scratch/repo"
  git fetch /home/lauer/.local/share/convmem/worktrees/fix-2026-11-24-chroma-collection-embed-identity refs/remotes/origin/main:refs/remotes/origin/main
  git rev-parse origin/main        # must read f10d67d...
  git log --oneline origin/main..HEAD   # the code is 6910a49; the tip is a docs-only commit after it
(If that path is unreadable, clone the GitHub remote with GIT_SSH_COMMAND='ssh -F /dev/null' and switch to origin/fix/2026-11-24-chroma-collection-embed-identity.)

Read, in your clone, docs/inter-model/CLAUDE-2026-11-24-chroma-embed-identity-codex-adversarial-review-handoff.md. The "Round 2 review brief" section (the last one) is your task: claims C9 to C17, eight suspicion items, decisions already taken, disclosed gaps, expected test counts and the exact report format. The sections above it are history. The original issue is at /home/lauer/Projects/convmem/Issues/chroma-collections-missing-embedding-identity.md if you need it (read-only).

Then: read the whole diff (git diff origin/main...HEAD), the two new modules in full, and the edits to chroma_store.py, llm.py and chroma_write_store.py (ingest.py is deliberately unchanged). Run the tests with the hermetic command in the handoff. Try to break each claim with real experiments on throwaway Chroma stores in temp dirs; a failing test or a short reproduction beats prose. Trace the real writer paths for the model tag (claim C11). Independently regenerate the R2B inventory and say MATCH or DIFFERS.

Hard rules: read-only on the branch (no commit, push, force-push, PR or merge; try fixes only in your scratch clone). Never open the live Chroma directory (~/.local/share/convmem/chroma) with any client or write anywhere under ~/.local/share/convmem; use temp-dir stores only. Never read or print ~/.claude.json, ~/.codex/config.toml, ~/.kiro/settings/mcp.json, ~/.claude/settings.json or any env file holding API keys. Do not call the convmem ask tool. Do not edit LATEST.md or any STATUS file.

Return the report in your reply (not in the repo) in the five-part format at the end of the Round 2 brief. If you find nothing in an area, say what you tried so I can judge how hard you looked.
```

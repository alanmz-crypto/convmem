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

---

## Review round 2 outcome (appended after the second Codex review; text above is the record of what was reviewed at 6910a49)

Codex recommended **rework** again. It independently attested R2B (`MATCH`, digest `22254ee8…`; diff against `origin/main` only the C17 fields; `ingest.py` blob identical to `main`), and confirmed C12, C15 and C17. It disagreed with C9, C10, C11, C13, C14 and C16. Disposition of every finding (fixes are in `777596e` and `ae5971c`):

| Codex finding | Disposition |
|---|---|
| High: a check can succeed before any vector is stored (a no-op `update_unit`, or a first write that fails, populated the cache, so a later foreign `add_unit` passed) | **Fixed.** Nothing is remembered from a check. `ChromaStore` remembers a collection only after an `add`/`upsert` of vectors succeeded; a delete or a client reload forgets it. |
| High: some routes skip the check on an already-stamped empty collection | **Fixed for `ChromaStore`:** the check judges every store, including `create_collections=False` and model-less ones. **Not changed, by design:** `restore_source_rows` restores rows read from the same collection (no new model enters). **Not fixed:** `FileGenerationStore.stage_rows` writes raw rows with no check; it is reached only from CG2 rehearsal, rollback-baseline and cutover code, which the repo documents as not production-wired. It belongs to CG2 activation. |
| High: a full census fails on 34,000 rows (`too many SQL variables`) | **Fixed.** Reads are batched (500) with completeness checked across batches. Verified on a real 34,000-row scratch collection (full census completes; the unbatched `get` fails exactly as reported). |
| High: doctor can PASS the wrong physical collection (same name in another Chroma database) | **Fixed.** The five identity read helpers are bound to the default tenant and database. A schema with no `databases` table is read as before (my first version broke six `watch_oom` tests that use hand-made SQLite fixtures; the consumer-suite run caught it before it was pushed). |
| High: sidecar numeric overflow escapes the checker and becomes a WARN | **Fixed** in three layers (`_score`, the `read_attestations` wrapper, the checker's safety net) and by a test that mutates every sidecar field to hostile values. Removing one layer alone is invisible by design; all three removed is caught. |
| Medium: doctor advises dropping a collection that has data | **Fixed.** The advice appears only after the rows are counted and found to be zero. |
| Medium: the attester can write a sidecar its own reader rejects (cosine underflow to 1.17; a year-900 timestamp) | **Fixed.** Cosine normalises with `hypot` and refuses anything outside [-1, 1]; the final payload is validated with the reader before it replaces the file. |
| Medium: an alias-only config change (`name` versus `name:latest`) refuses a legitimate first write | **Fixed.** A bare name means `:latest`; any other tag stays distinct. Doctor compares the same way. **Residual:** a mutable tag that keeps its spelling after its artifact changes is still accepted (names are not digests). |
| Medium (inferred): the isolation scan misses live-side links, and the directory can change between the last check and the client opening | **Mitigated.** The live side follows links (with a cycle guard) and the copy is re-checked immediately before the client opens. **Residual:** a swap after the last check cannot be excluded; no write through shared storage was observed. |

Suspicion items: **1** the attested detail now says what the census was (restore copy at attestation time, rows sampled, minimum cosine, threshold); a current live row count is not compared. **3** the cache semantics are fixed as above. **4** a test now holds two writers inside the read-merge-replace (the earlier nested-call test could not), and the lock open refuses a symlink; with the lock disabled, that test fails. **8** removing the lock had left every test green; that is closed, and every round-2 guard was mutation-checked (20 more guards, each disabled in turn and caught by a test aimed at it).

Claim verdicts after the fixes: C9, C13 and C14 now hold for the cases Codex reproduced. **C10** holds for the alias case; I found no ordinary per-source model override. **C11 stands as disclosed:** the tag is lost on the `ingest.py` summary path (pinned by a strict xfail), `incremental_jsonl.py` persistence, `shadow_replay.py:234` and `eval_corpus/embed_adapters.py:52` (administrative or evaluation tools, not changed). **C16 is not absolute:** the residual above.

What strict PASS means, stated narrowly (Codex's recommendation, which I accept): *a full re-embedding of a restore copy, at the time and threshold shown, reproduced the stored vectors of that copy.* It does not certify present live-vector identity; rows added or replaced after the census are unverified.

**Still open for Ryan:** (1) re-pin and fix the `ingest.py` summary-vector copy (decision 4 above); (2) whether to refuse writes of a differently tagged vector into a collection that already holds vectors; (3) the serving-read and `refine` creators; (4) the CG2 `stage_rows` route at CG2 activation.

Full suite at `ae5971c`, from a scratch clone of the pushed commit: 213 failed / 3572 passed / 69 skipped / 1 xfailed / 52 errors, the **same 265 failing ids as the baseline on `origin/main`, none new**.

---

## Round 3 review brief (written after round 2 was addressed)

You may be a fresh reviewer. Everything above is context; this section is your task. Two rounds each found real defects, and in both rounds some were defects in my own fixes from the round before (round 2 found that my round-1 stamp guard still missed real writers and that a "fixed" cache was set before anything was stored). So do not assume the round-2 fixes are right: they are the least-reviewed code on this branch.

### Resume state (round 3)

| Field | Value |
|-------|--------|
| **State** | `IN_PROGRESS`: round-2 findings addressed, independent re-review outstanding |
| **Branch** | `fix/2026-11-24-chroma-collection-embed-identity` (pushed) |
| **Base** | `origin/main` = `f10d67d` (unchanged). In a clone `origin/main` can be stale: fetch it from the source worktree's remote-tracking ref and check it reads `f10d67d`. |
| **Code under review** | `ae5971c`; later commits are docs only (this section) |
| **Delta since round 2** | `6910a49..ae5971c`: `777596e` closes the round-2 findings, `ae5971c` restricts the serving-database filter to schemas that have databases |
| **Expected counts** | `tests/test_chroma_store_embed_identity.py`, `test_chroma_production_embed_identity.py`, `test_chroma_embed_identity.py`, `test_chroma_embed_attestation.py`: **228 passed, 1 xfailed** (the xfail is deliberate); the nine governed-inventory files (`test_r2b_v2_corrective_viii`, `test_r2b_v2_implementation_revision`, `test_r2b_v2_coverage`, `test_repository_knowledge_committed_manifest`, `test_repository_knowledge_scope`, `test_shadow_writer_coverage_scan`, `test_shadow_writer_gate_c3`, `test_file_generation_read_path_inventory`, `test_t3_residual_closure`): **84 passed** on a clean tree |
| **Full suite** | at `ae5971c`, from a scratch clone: 213 failed / 3572 passed / 69 skipped / 1 xfailed / 52 errors, the **same 265 failing ids as the baseline on `origin/main`, none new** |
| **PR** | not opened; Ryan gates it. Nothing here authorizes a merge. |

### What changed since round 2 (read these first)

- **New `chroma_embed_first_write.py`** (called from `ChromaStore._require_vectors_match_first_write`): `require_first_vector_matches(store, name, embeddings)`. Looks the collection up; if absent, compares tagged vectors with what the store would stamp; if it exists and `count() == 0`, compares with the collection's recorded stamp; if it holds vectors, returns (not a first write). Judges every store, including `create_collections=False` and model-less ones.
- **`chroma_store.py`**: `store.published_collections` is filled by `_note_write` only after a native `add`/`upsert` with vectors succeeded, emptied for a collection on a native `delete`, and cleared on `_reload_client`. New `same_embed_model(a, b)`: names equal after stripping a trailing `:latest`. The first-write method now delegates to the new module (the file was over the 1000-line pylint cap).
- **`chroma_readonly.py`**: `collection_config_metadata`, `collection_ids`, `collection_count`, `collection_uuid`, `collection_dimension` restrict to the default tenant and database through `_serving_database(conn)`, which returns no restriction when the schema has no `databases` table or no `collections.database_id`. **Sibling helpers in the same file still select by name only** (see suspicion R3-3).
- **`chroma_embed_identity.py`**: doctor compares models with `same_embed_model`; `row_count` verified before the "can be dropped" advice; overflow handled in `_score`, in a `read_attestations` wrapper that raises only `AttestationError`, and by a broad net in `check_embed_identity`; the attested detail names the restore copy, rows sampled, min cosine and threshold.
- **`chroma_embed_attestation.py`**: reads in batches of 500 (`READ_BATCH`) with completeness checked per batch; cosine normalises with `hypot`; the live side of the isolation scan follows links with a cycle guard; `before_open` re-checks right before the client opens; the lock opens with `O_NOFOLLOW`; the merged payload is parsed by the reader before `os.replace`.
- Bookkeeping: manifest hashes refreshed for four files (`chroma_store.py`, `chroma_write_store.py`, `config.example.toml`, `tests/test_shadow_writer_gate_c3.py`) and eight new `unrelated` classifications (the seven earlier ones plus `chroma_embed_first_write.py`); **R2B regenerated again**; `ingest.py` is byte-identical to `origin/main`.

### Decisions already taken (do not re-argue unless you find a defect that undermines them)

1. The sidecar stays the strict authority; strict needs a full-census attestation; strict PASS means *a full re-embedding of a restore copy, at the time and threshold shown, reproduced that copy's vectors*. It does not certify present live vectors.
2. Only a collection's **first** vector is judged. Refusing a mismatched write into a collection that already holds vectors is an open policy call.
3. Left for follow-up PRs: `open_chroma_for_read` and `refine.py:628` creating unmarked collections on a brand-new store; the `ingest.py` summary-vector tag loss (editing `ingest.py` breaks three pinned baseline hashes, so a reviewed re-pin is Ryan's call; a strict xfail records the gap); `FileGenerationStore.stage_rows` (raw rows, no check; reached only from CG2 rehearsal, rollback-baseline and cutover code, which the repo documents as not production-wired).

### Claims to falsify

- **C18.** Nothing short of a vector actually being stored waives the first-vector check, through every `ChromaStore` method. Try failures after the native write but before `_note_write`, the write-guard path versus the unguarded path, `update` that changes an existing row, `restore_source_rows`, direct `_native` calls, and the production wrapper `_IndexWriteGuardedChromaStore`.
- **C19.** No legitimate production write is newly refused. The `:latest` equivalence is the only name normalisation; look for real spellings it does not cover (namespaced names, case) and for any flow where the embedding model legitimately differs from the stamp.
- **C20.** The five bound helpers return the serving collection's facts and nothing else, and no consumer is harmed. The test files that import them (23, including the identity ones) have 71 failures, all in the pre-change baseline and none new; I ran them after the change. Check every production caller of each helper.
- **C21.** `check_embed_identity` never raises and never returns PASS while any collection has a definite FAIL, for any collection metadata, sidecar bytes, database layout or exception from a helper. Fuzz it beyond my list (`None`, `True`, strings, containers, `10**400`, `-10**400`, `2**63`, `0`, `-1`, `1.5`).
- **C22.** Every sidecar the tool publishes passes the reader, and nothing the reader would reject is ever published.
- **C23.** A full census is correct and practical at 34,000 rows. I verified correctness and speed of the read side on a real 34,000-row scratch collection (about 0.3 s, embedding excluded). I did not measure a real embedding provider.
- **C24.** Copy isolation: hardlinks, symlinks (both sides), link cycles, directory swaps, and the interval between the last check and the client open. Residual I accept: a swap after the last check.
- **C25.** The lock serialises writers across threads and processes, refuses a symlink at the lock path, and leaves the sidecar and lock owner-only.
- **C26.** Bookkeeping is mechanical. R2B against `origin/main`: `code_revision` (top level and 39 routes), `inventory_digest`, and `route_id`/`entrypoint`/`shadow_inventory_ref` for the one moved site. Manifest: the four hashes and eight classifications above. SHADOW inventory: coordinates only. `ingest.py` identical to `main`.

### Where I suspect weakness (attack here first, then beyond)

1. **R3-1: the published-collections state machine.** It is per store instance and updated after the write. What about a second session or process that fills the collection between the check and the write, a store reused across a config reload, or a write that publishes but raises before `_note_write` (I believe that fails safe)? Does the guard path (`write_guard.native_write`) ever reload the client such that stale state matters?
2. **R3-2: name equivalence.** Only a trailing `:latest` is stripped. What do real Ollama names look like in this repo's configs and in the live sidecar, and which direction can it go wrong?
3. **R3-3: sibling helpers.** I bound five helpers to the serving database. `iter_collection_metadata_rows`, `unit_document_text`, `collection_inventory_snapshot`, `count_for_source_path`, `ids_for_source_path` and others in `chroma_readonly.py` still select by name alone. Do any of them feed a verdict, and should the binding be applied everywhere? Is the `1 = 1` fallback for schemas without `databases` a hole?
4. **R3-4: the prescribed operation may not be practical.** Measured read-only on this machine, nothing written: the live collections hold **116,661** rows (`knowledge_units`) and **6,182** (`conversation_summaries`), both 768-dim, both unmarked, no sidecar; the store is 6.9 GB. A local Ollama embedding takes a median of about 5 ms for a short text and 14 ms for 120 words (my first timing was invalid: identical prompts are cached), so a full census is roughly 20 to 60 minutes of embedding. Time is not the obstacle; robustness is. `chroma_embed_attestation.py:210` calls the embedder bare, so any error escapes `main` as a raw traceback (a test text of about 600 words got HTTP 500 from Ollama, probably over the model's context window; real writers truncate before embedding, so stored documents probably fit), with no progress output, retry or resume. And the pass criterion is `min cosine >= 0.99` over every row, so one row whose stored document differs from the text that was embedded fails the whole run. I have not run a census, or even a sample, on real data. Judge whether strict mode is reachable and what is the minimum that would make it so.
5. **R3-5: "verified empty".** The drop advice needs `collection_count == 0` from the read-only SQLite. Evidence I gathered: the count equals the client's while a store is open, and after deleting every row it is 0 while the recorded dimension stays set (so such a collection never gets the advice). Is there a state where the count is 0 but vectors exist (unflushed log, other segment)?
6. **R3-6: overstatement.** Read the doctor detail strings and the docstrings as an operator would. Does anything still imply the live vectors are certified?
7. **R3-7: tests that pass for the wrong reason.** Each round found a guard no test noticed (round 1: the sampled-id completeness guard; round 2: the exclusive lock). I mutation-checked 20 further guards this round, each caught by a test aimed at it, and three redundant layers (sidecar overflow) only together. Find a guard whose removal nothing notices, including the cache clears on `delete` and `_reload_client` (the reload clear is untested).
8. **R3-8: broad exception handling.** `check_embed_identity` catches `Exception` per collection and around the sidecar read. Does it hide a programming error as a WARN where it should fail loudly?

### Evidence I gathered myself (so you can check it, not trust it)

Probes, not committed: the 34,000-row census (unbatched `get` fails with `too many SQL variables`, batched completes); the two-database repro (before the filter the strict verdict was PASS for the wrong database, after it FAIL); the count/dimension behaviour above; pickle and deepcopy keep the model tag while slicing and `list()` drop it. Full suite results and the pre-existing flaky tests are listed under "Known flaky tests" above (the watch coverage test fails about half the time on pure `origin/main`).

### Disclosed gaps (do not spend time rediscovering these)

- The attestation tool has never run against a real restic restore or a real Ollama; nothing here may open the live store. A model name is a string, not a digest. A sample cannot rule out a minority of foreign rows (the full check is the mitigation). A ratified CG2 D0 chain exists on the machine (2026-08-29, historical model UNKNOWN) and was never compared with today's live store.
- Tag losses: `ingest.py` summary path, `incremental_jsonl.py` persistence, `shadow_replay.py:234`, `eval_corpus/embed_adapters.py:52`.
- Intermediate commits are not individually green on the governed-inventory suites; judge the tip. Python 3.11 locally against 3.12 in CI. `doctor.py` is concurrently edited, uncommitted, by another agent in the shared checkout and was not changed in rounds 2 or 3.

### Rules, commands, report format

Same rules as "Rules for the reviewer" above. Commands as in "How to run things", with the code at `ae5971c`. The identity and governed suites are the files named in the round 2 brief plus `tests/test_chroma_embed_identity.py` etc. as in "How to run things".

Return, as plain text in your reply: (1) findings ranked Critical / High / Medium / Low, each with `file:line`, a reproduction and observed-or-inferred; (2) the **R2B attestation**, regenerated independently into a scratch path, stating `MATCH` or `DIFFERS`, whether the diff against `origin/main` is only the C26 fields, and the digest you computed; (3) `AGREE / DISAGREE / CANNOT VERIFY` for C18 to C26 with one line of evidence each; (4) direct answers to R3-1, R3-3, R3-4 and R3-7 even if the answer is "no problem found", with how you looked; (5) a recommendation: ship, ship after named changes, or rework; whether strict-with-sidecar is now an acceptable fail-closed gate; and whether a fourth round is worth the cost.

### Prompt Ryan can paste into Codex (round 3)

```text
You are a reviewer for an unmerged change in the convmem repo. This is round 3. Two earlier reviews found real defects, and some were in my own fixes from the previous round, so the round-2 fixes are the least-reviewed code here: assume more remain, be adversarial toward my work, and trust nothing I say until the code shows it.

Get the code without touching anyone's checkout (never work in or modify ~/Projects/convmem):
  scratch=$(mktemp -d)
  git clone /home/lauer/.local/share/convmem/worktrees/fix-2026-11-24-chroma-collection-embed-identity "$scratch/repo" && cd "$scratch/repo"
  git fetch /home/lauer/.local/share/convmem/worktrees/fix-2026-11-24-chroma-collection-embed-identity refs/remotes/origin/main:refs/remotes/origin/main
  git rev-parse origin/main        # must read f10d67d...
  git log --oneline origin/main..HEAD   # the code under review is ae5971c; the tip is a docs-only commit after it
(If that path is unreadable, clone the GitHub remote with GIT_SSH_COMMAND='ssh -F /dev/null' and switch to origin/fix/2026-11-24-chroma-collection-embed-identity.)

Read, in your clone, docs/inter-model/CLAUDE-2026-11-24-chroma-embed-identity-codex-adversarial-review-handoff.md. The "Round 3 review brief" section (the last one) is your task: what changed since round 2, claims C18 to C26, eight suspicion items, decisions already taken, disclosed gaps, expected test counts and the exact report format. The sections above it are history, including what rounds 1 and 2 found. The original issue is at /home/lauer/Projects/convmem/Issues/chroma-collections-missing-embedding-identity.md if you need it (read-only).

Then: read the delta first (git diff 6910a49..HEAD), then the whole diff against origin/main, the three new modules in full (chroma_embed_identity.py, chroma_embed_attestation.py, chroma_embed_first_write.py), and the edits to chroma_store.py, chroma_readonly.py, llm.py and chroma_write_store.py (ingest.py is deliberately unchanged). Run the tests with the hermetic command in the handoff. Try to break each claim with real experiments on throwaway Chroma stores in temp dirs; a failing test or a short reproduction beats prose. Use the call graph to check every production caller of the helpers I changed. Independently regenerate the R2B inventory and say MATCH or DIFFERS, with the digest you computed.

Hard rules: read-only on the branch (no commit, push, force-push, PR or merge; try fixes only in your scratch clone). Never open the live Chroma directory (~/.local/share/convmem/chroma) with any client or write anywhere under ~/.local/share/convmem; use temp-dir stores only. Never read or print ~/.claude.json, ~/.codex/config.toml, ~/.kiro/settings/mcp.json, ~/.claude/settings.json or any env file holding API keys. Do not call the convmem ask tool. Do not edit LATEST.md or any STATUS file.

Return the report in your reply (not in the repo) in the five-part format at the end of the Round 3 brief. If you find nothing in an area, say what you tried so I can judge how hard you looked.
```

---

## Review round 3 outcome (appended after the third Codex review; text above is the record of what was reviewed at ae5971c)

Codex recommended **rework** a third time and a focused fourth review. It independently attested R2B (`MATCH`, digest `5c846359…`; diff against `origin/main` only the C26 fields; `ingest.py` blob identical to `main`) and confirmed C22 and C26. It disagreed with C18 to C21, C23, C24 and C25. It also confirmed that the original 34,000-row census, the six parser escapes and the same-session first-write failures were fixed. Disposition of every finding (fixes in `cf71b20`):

| Codex finding | Disposition |
|---|---|
| High: a second store can waive the first-vector check (store A published, store B emptied the collection, A then accepted a foreign first vector; a post-delete bookkeeping failure did the same inside one store) | **Fixed by removing the mechanism.** The "published" flag and the bookkeeping that set it are gone. Only a collection's *recorded model* is cached (it never changes). Whether the collection is empty is read at the moment a vector conflicts with that model, never remembered. |
| High: a damaged catalog (databases table renamed, `collections.database_id` kept) made strict doctor PASS the wrong database's collection | **Fixed.** A catalog with one of the two but not the other is refused (`sqlite3.DatabaseError`, which doctor reports as unreadable: WARN, FAIL under strict). Only a schema with neither is read unrestricted. A second tenant's `default_database` is distinguished by a test. |
| High: strict could call populated storage empty (rows present, metadata and dimension cleared gave a WARN; a relabelled segment made the filtered count 0 and doctor advised dropping) | **Fixed.** Emptiness is decided from every trace of a row (distinct ids in every segment whatever its scope label, plus the pending log); a collection with rows but no metadata is unproven (strict FAIL), not "empty". |
| Medium: the census published a passing cosine for sub-threshold vectors (`[1,0]` vs `[5e-324, 5e-324]` measured 1.0) | **Fixed.** Vectors are scaled by their largest component before normalising. |
| Medium: contradictory evidence passed strict (mean 0.0 with min 1.0 for one row) | **Fixed.** A mean below the minimum, or different from it for a single row, is not an attestation. |
| Medium: namespace and case forms of a legitimate model name (`library/nomic-embed-text:latest`, `NOMIC-EMBED-TEXT`) refused a first write | **Fixed.** Names compare as Ollama identifies them. **Residual:** a mutable tag that keeps its spelling after its artifact changes is still accepted (names are not digests). |
| Medium: a dry run created `-wal`/`-shm` files beside a WAL-mode live database | **Mitigated, not eliminated.** Reproduced only on a store switched to WAL; the live store and any store Chroma 1.5.9 writes use a rollback journal (header bytes `0101`, checked read-only). The tool now refuses a WAL-mode live database from its file header, before any SQLite open. Doctor's own reads of a WAL store are unchanged. |
| Medium: a late provider failure discarded the census with a raw `HTTPError` and no row | **Fixed.** Rows are read, embedded and scored one batch at a time; a failing embedding is retried twice with backoff, then the run is refused naming the collection and row; progress is reported. Memory no longer grows with the collection. **Not done:** resume after failure. |
| Medium: a direct `_native(..., embeddings=<numpy array>)` stored the row then raised | **Fixed** by removing the bookkeeping (see first row). |
| Low: an existing lock file kept mode 0644 | **Fixed.** The lock is narrowed to owner-only after it is opened. |
| Part 2c: sibling read helpers (`collection_inventory_snapshot`, `ids_for_source_path`, `unit_document_text`, `collection_count`, and the iterator) mixed in another database's rows | **Fixed.** Every name-selected query in `chroma_readonly.py` is bound to the serving database; each of the six is mutation-tested on its own. I reproduced the leak (a foreign `superseded` flag turned the serving row "historical"; a source present only in the other database returned an id). |
| Part 2e: removing only the tenant predicate, or the `_reload_client` cache clear, left every test green | **Fixed.** A second-tenant test and a reload test now fail without them. In total 25 round-3 guards were mutation-checked; **five of them survived the first sweep, i.e. no test noticed their removal** (four of the six scoped queries, and the "every segment" half of the emptiness check, masked by the log evidence). Each has a test now and is caught. |
| C24: the isolation scan recorded files only, so a shared empty directory was outside the proof | **Fixed.** Directories count too. **Residual I accept:** a swap after the last check cannot be excluded. |
| Part 2 (broad handler): a programming error in a collection was labelled "cannot read collection metadata" | **Fixed.** The detail now names the exception class. |

Accepted and unchanged: `restore_source_rows` (restores rows read from the same collection) and `FileGenerationStore.stage_rows` (CG2 rehearsal, rollback-baseline and cutover code only, not production-wired). Codex accepted the bounded exclusions and noted `restore_source_rows` does not verify the origin of its input.

**What is still unverified:** the attestation tool has never run against a real restic restore and a real corpus. The live collections hold 116,661 and 6,182 rows; per-row embedding time is about 5 to 14 ms, so a full census is roughly 20 to 60 minutes if every row re-embeds. Whether `min cosine >= 0.99` holds across all of them (one row whose stored document differs from the embedded text fails the whole run) is unknown until a dry run on a real restore copy. That needs Ryan's go-ahead (a restic restore of about 7 GB into scratch and local Ollama calls); nothing opens or writes the live store.

Full suite at `cf71b20`, from a scratch clone of the pushed commit: 213 failed / 3602 passed / 69 skipped / 1 xfailed / 52 errors, the **same 265 failing ids as the baseline on `origin/main`, none new**.

---

## Round 4 review brief (focused; written after round 3 was addressed)

Codex's recommendation was one *focused* fourth review: rerun its counterexamples, check a second tenant, and verify the operator failure path. A broad pass over unchanged bookkeeping adds little. So this brief is deliberately narrow. The code under review is `cf71b20`; later commits are docs only. Base `origin/main` = `f10d67d` (fetch it from the source worktree's remote-tracking ref; a fresh clone's copy can be stale). `git diff ae5971c..cf71b20` is the delta (11 files, about 800 added lines; 10 files outside `docs/`).

**Expected results** (hermetic environment as in "How to run things"): `tests/test_chroma_store_embed_identity.py`, `test_chroma_production_embed_identity.py`, `test_chroma_embed_identity.py`, `test_chroma_embed_attestation.py` and the new `test_chroma_embed_attestation_census.py`: **258 passed, 1 xfailed** (the xfail is the known `ingest.py` summary-vector gap). The nine governed-inventory files named earlier: **84 passed** on a clean tree. Manifest: four refreshed hashes and **nine** new `unrelated` classifications (the census test file is the ninth).

### Part 1: rerun your own counterexamples (report FIXED / STILL REPRODUCES / FIXED DIFFERENTLY with a command or test)

1. Store A publishes, store B (even through `_IndexWriteGuardedChromaStore` and the index lock, guard on and off) deletes the last row, then A adds a foreign first vector. Also the injected failure after a successful native delete.
2. The two-database fixture with `databases` renamed while `collections.database_id` is kept; and a second *tenant* with its own `default_database`.
3. Populated storage with the dimension cleared and (a) metadata cleared, (b) segment scope damaged: doctor must not say PASS, must not advise dropping, and under strict must FAIL.
4. `[1,0]` vs `[5e-324, 5e-324]`; the one-row `mean_cosine = 0.0` evidence; `library/nomic-embed-text:latest` and `NOMIC-EMBED-TEXT` through the real writer.
5. A dry attestation of a copy whose live side is WAL mode; and a provider that fails on call 33,999 of 34,000 (does the message name the collection and row?).
6. A direct `_native(..., 'upsert', embeddings=np.array(...))`; a pre-existing 0644 lock file; the shared empty segment directory.
7. The sibling helpers you named (`collection_inventory_snapshot`, `ids_for_source_path`): the same-row-id-in-two-databases case.

### Part 2: attack the new code (where I am least sure)

- **R4-1 `chroma_embed_first_write.py` as redesigned.** It caches only a collection's recorded model (`store.recorded_stamps`, cleared on `_reload_client`) and reads `count()` fresh only when a vector conflicts with that model. Find a way the cached model goes stale (a collection dropped and recreated with another model while a store lives: note that doctor's own advice is to drop an empty unmarked collection), a path that never reaches the check, or a conflict that is wrongly allowed or refused. The check is still advisory across processes; production sessions hold the index write lock.
- **R4-2 `_canonical_embed_model`.** Hostile and odd inputs (empty segments, repeated colons, a port in the registry part, trailing slashes, unicode case folding). Any pair that compares equal but is not one Ollama model, or the reverse.
- **R4-3 `_serving_database` and the scoping of every query in `chroma_readonly.py`.** Does each helper call it before it queries? Is there any query that still selects a collection by name alone, anywhere in the repo (not just this file)? The "neither table nor column" fallback reads unrestricted; is that safe for every consumer?
- **R4-4 `collection_row_evidence`.** The log is retained after deletes, so it can only make the advice more conservative; is there a state where it returns 0 yet rows exist?
- **R4-5 the census as an operator would run it.** Streaming, retry (2 retries, backoff 0.5 s doubling, applied to every exception including a permanent one such as an over-long text), progress every 2,000 rows, no resume. Read `main()` and the error paths. Is a failed 40-minute run diagnosable and cheap to repeat? Does anything still raise a raw traceback?
- **R4-6 tests that pass for the wrong reason.** Every round found at least one, and this round's sweep found five, each seen only after I mutation-tested every bound query individually. Pick guards I did not mutate (the retry classification, the `journal_mode_is_wal` header read, the moved test file's fixture import) and remove them.

### Decisions already taken (unchanged)

The sidecar stays the strict authority; a strict PASS means "a full re-embedding of a restore copy, at the time and threshold shown, reproduced that copy's vectors", not that live vectors are certified; only a collection's first vector is judged; left for follow-ups: `open_chroma_for_read` and `refine.py:628` creating unmarked collections, the `ingest.py` summary-vector tag loss (a re-pin of three baseline hashes is Ryan's call), `FileGenerationStore.stage_rows`. Known flaky tests are listed under "Known flaky tests" above.

### Return, as plain text

(1) a re-verification table for Part 1; (2) new findings ranked Critical / High / Medium / Low with `file:line`, a reproduction and observed-or-inferred; (3) the R2B attestation regenerated independently (`MATCH` or `DIFFERS`, the digest you computed, and whether the diff against `origin/main` is only the same fields as before); (4) direct answers to R4-1, R4-3, R4-5 and R4-6 even if "nothing found", with how you looked; (5) a recommendation: ship, ship after named changes, or rework, whether strict-with-sidecar is now an acceptable fail-closed gate, and whether a fifth round is worth the cost. Rules as before: read-only on the branch, never the live Chroma directory, never the client config or env files, no `ask`, no `LATEST.md` or `STATUS`.

---

## Decisions recorded and the first run on a real restore (appended after round 3; docs only)

**Decisions (Ryan chose the defaults):** the `ingest.py` summary-vector tag loss is deferred to a separate PR (it needs a reviewed re-pin of three baseline hashes); refusing a mismatched write into a collection that already holds vectors is deferred (a policy change that needs an explicit re-embed flow); `open_chroma_for_read` and `refine.py:628` creating unmarked collections is a follow-up PR; `FileGenerationStore.stage_rows` is handled at CG2 activation.

**First dry run against a real restic restore (read-only; nothing written to the live store; no `--write`).** The newest valid snapshot (`c078eb68…`, 2026-11-24, profile `complete-data-v2`) covers the whole 43 GB data root, so only its `chroma` directory (6.9 GB) was restored into a scratch directory with the repo's own credential loading and runner. Restic exited 1 because of two `lchown ... invalid argument` messages on the parent directories `/home` and `/home/lauer/.local` (the sandbox's ownership quirk); nothing else failed, the restored tree has the same 12 files and the same `chroma.sqlite3` size as the live directory, and it contains **no symlinks**. The real CLI (`chroma_embed_attestation.py --sample-size 2000 --seed 1`, real Ollama `nomic-embed-text:latest`) then reported:

| collection | rows checked | population in the restore | min cosine | mean cosine |
|---|---|---|---|---|
| `knowledge_units` | 2,000 | 116,622 | 0.999995 | 1.0 |
| `conversation_summaries` | 2,000 | 6,180 | 1.0 | 1.0 |

It took 31 seconds for the 4,000 embeddings (about 8 ms per row including overhead), so a full census of about 122,800 rows should take roughly 16 minutes. The live store has since gained rows (116,661 and 6,182), which a restore-copy census does not cover; the doctor detail says so ("restore copy at attestation time"). **Not yet known:** whether every row reproduces. A 2,000-row sample cannot rule out a minority of rows whose stored document is not the exact text that was embedded, and one such row fails a full census. The next step is a full-census dry run (still no `--write`); `--write` and flipping `require_embed_identity` are separate operator decisions.

---

## Full-census dry run on the real restore (appended; docs only, read-only, no `--write`)

Run through the real CLI path (`chroma_embed_attestation.py --restore-copy <restored chroma> --sample-size all`, real Ollama `nomic-embed-text:latest`) against the restored snapshot `c078eb68…` (2026-11-24). To get per-row evidence in a single pass I wrapped the tool's own `_embed_row` and `cosine` with recorders that delegate to the real functions and note each row's id, document length and score (a failing row would have been recorded and skipped; none failed). The CLI returned exit code 0.

| collection | rows checked (all) | failed | min cosine | rows below 0.9999 | median |
|---|---|---|---|---|---|
| `knowledge_units` | 116,622 | 0 | 0.999991 | 0 | 1.000000 |
| `conversation_summaries` | 6,180 | 0 | 0.999997 | 0 | 1.000000 |

Elapsed 670 s for 122,802 rows (about 180 rows per second), so a full census is about 11 minutes. The lowest-scoring rows are ordinary short documents scoring 0.99999, i.e. float rounding, not mismatches. Nothing was created beside the live store (no sidecar, no lock). **Consequence:** the worry that one unreproducible row would make strict mode unreachable did not materialise on this corpus at snapshot time. The live store has since gained rows (116,661 and 6,182 against the 116,622 and 6,180 checked); the doctor detail says the census covers a restore copy "at attestation time". The remaining steps are operator decisions, none taken: re-run with `--write` (it re-embeds, about 11 minutes, and writes `chroma.embed-attestation.json` and a `.lock` beside the live Chroma directory), confirm `convmem doctor` reports `attested legacy`, then set `[index] require_embed_identity = true`. A fresher snapshot would narrow the gap between census and live store.

---

## Review round 4 outcome (appended after the fourth Codex review; text above is the record of what was reviewed at cf71b20)

Codex recommended **ship after changes** and a focused fifth round, and said strict-with-sidecar was not yet an acceptable fail-closed gate: it produced a sidecar that strict doctor accepted as a 12/12 census while the same restore held a thirteenth, nonmatching row. It independently attested R2B (`MATCH`, digest `8b8a5cd0…`; diff against `origin/main` only the usual fields; `ingest.py` blob identical) and confirmed every round-3 counterexample as fixed. Disposition of each finding (fixes in `eb420d1`):

| Codex finding | Disposition |
|---|---|
| High: a full census omitted a pending vector. Ids were listed from SQLite before the client opened the restore; a log record Chroma only replays on open was never scored, so a 12-row census was published for a 13-row collection | **Fixed, and reproduced first** with a genuine `embeddings_queue` record above `max_seq_id` (SQLite saw 2 rows, the opened client 3). The rows to check are now listed by the opened collection, must equal its count, and a census that scored a different set refuses. A run stops at the first row under the threshold and names it. |
| High: the cached recorded model went stale (another session dropped and recreated the collection, or changed its stamp in place with the same UUID) | **Fixed by deleting the cache.** The recorded model is read fresh at every write and again inside the write guard, after it may have reloaded the client. Tests: replacement, in-place `modify`, a no-op that had cached "none", and a replacement made as the write guard is entered (a stub guard; the real guard's on/off modes are covered by your Part 1 rerun, not by a committed test). |
| High: distinct Ollama models compared equal (`library/acme/model` vs `acme/model`; `x:` and `/x` vs `x`) | **Fixed.** New `chroma_embed_model_names.py` parses `[host/][namespace/]model[:tag]` with Ollama's defaults and compares components; malformed names equal only themselves. |
| Medium: the legacy fallback combined two collections of one name into one strict PASS | **Fixed.** A name matching more than one collection is refused. |
| Medium: damage to a segment's collection reference restored the unsafe "can be dropped" advice | **Fixed.** "Empty" requires both segments accounted for and no segment belonging to no collection; each trigger has its own test, plus a positive control that a genuinely empty collection still gets the advice. |
| Medium: a header with format bytes `01 02` opened as WAL and the dry run created `-wal`/`-shm` | **Fixed.** Only `01 01` after the SQLite magic is read; anything else is refused before SQLite is opened. |
| Medium: a `#` in a directory name truncated the read-only URI, dropped `mode=ro` and created a sibling file | **Fixed** in `_connect_readonly` (percent-encoded). **Not changed:** about fourteen other modules build the same unescaped URI (the write guard, restore drill, file-generation validator, eval capture, adapters); a follow-up. |
| Medium: census failures lost their diagnostics (wrong-sized vector, an orthogonal row on call 3 of 34,000, a malformed SQLite file escaping as a raw traceback) | **Fixed.** Scoring failures name the collection and row; the run stops at the first failing row; storage and I/O errors end the command as a refusal. |
| Low: a lock-permission failure leaked a descriptor | **Fixed.** The descriptor is closed on every path once opened. |
| R4-3: other modules still select a collection by name alone (`chroma_write_guard.py`, `eval_corpus/capture.py`, `scripts/chroma_orphan_inventory.py`, `file_generation_validate.py`) | **Accepted as a follow-up, not fixed here.** They are separate consumers, not the doctor verdict; two sit in governed or `eval_corpus/` files that need Ryan's approval. Listed under the follow-up PRs. |
| R4-6: three behaviour-changing mutations survived (retry scope, backoff sequence, WAL header bytes) | **Fixed.** Tests now pin retry on any exception, the 0.5 s then 1.0 s delays, and each header-byte combination. Round-4 sweep: 21 guards mutation-checked; one survived outright (a four-part name collapsing to its bare model) and one was "caught" only by an unrelated test that counted every open descriptor and was therefore flaky. Both are fixed (the descriptor test now looks only at the lock file). The commit message for `eb420d1` says "21 more guards plus the three that survived"; this paragraph is the accurate record. |

**Behaviour changes to know about:** a failing census now stops at the first failing row instead of reporting a minimum over all rows, so the operator no longer sees a distribution when it fails (rerun with a lower `--threshold` to look further); the read helpers raise on an ambiguous or inconsistent catalog instead of reading it.

**Real-corpus rerun with the rewritten census (read-only, no `--write`).** The same real restic restore of today's snapshot `3e257900…` (it matches the live store exactly: 116,661 and 6,182 rows, same collection UUIDs), real Ollama `nomic-embed-text:latest`, through the real CLI with `--sample-size all` and per-row recorders wrapped around `_embed_row` and `cosine`: **122,843 of 122,843 rows reproduce, none failed, none below 0.9999; minimum cosine 0.999991 (`knowledge_units`) and 0.999999 (`conversation_summaries`); exit code 0; 635 s.** It also shows the new row listing through the opened collection works at this store's scale. Nothing was created beside the live store.

Full suite at `eb420d1`, from a scratch clone of the pushed commit: 213 failed / 3639 passed / 69 skipped / 1 xfailed / 52 errors, the **same 265 failing ids as the baseline on `origin/main`, none new**.

---

## Round 5 review brief (focused; written after round 4 was addressed)

Round 4 found that the newest code was still wrong in places its tests could not see, so this round is again narrow. The code under review is `eb420d1`; later commits are docs only. Base `origin/main` = `f10d67d` (fetch it from the source worktree's remote-tracking ref; a fresh clone's copy can be stale). `git diff cf71b20..eb420d1` is the delta (14 files, about 950 added lines; 12 files outside `docs/`). **Trail (the code graph) is available: use it where it helps, e.g. for callers and blast radius.**

**Expected results** (hermetic environment as in "How to run things"): `tests/test_chroma_store_embed_identity.py`, `test_chroma_production_embed_identity.py`, `test_chroma_embed_identity.py`, `test_chroma_readonly_scope.py`, `test_chroma_embed_attestation.py` and `test_chroma_embed_attestation_census.py`: **295 passed, 1 xfailed** (the xfail is the known `ingest.py` gap). The nine governed-inventory files named earlier: **84 passed** on a clean tree. Manifest: four refreshed hashes and **eleven** new `unrelated` classifications.

### Part 1: rerun your own counterexamples (FIXED / STILL REPRODUCES / FIXED DIFFERENTLY, with a command or test)

1. The 12-plus-one pending-log fixture (your decisive acceptance test): the first census must discover and reject the foreign vector and leave the prior sidecar untouched; and the same fixture with a *matching* pending vector must count 13.
2. Replacement of the collection by another session, the same-UUID `modify`, and the no-op that cached "none", with the write guard on and off.
3. `library/acme/model` vs `acme/model`; `x:` and `/x` vs `x`; `K` vs `k`; distinct registry ports; the real inter-model writer and a genuine 10/10 sidecar with the cross-registry name configured.
4. The legacy fixture with two `knowledge_units` rows; the segment-reference loss with the queue cleared; the `01 02` header; the `restore#1` directory; the wrong-sized vector, the orthogonal row on call 3, the malformed SQLite file, the lock-permission failure.

### Part 2: attack the new code

- **R5-1 `chroma_embed_model_names.py`.** Compare its grammar with Ollama's real parser (a digest suffix `@sha256:…`, `hf.co/user/model:tag`, tag and component character sets, uppercase hosts, a host without a dot, an IPv6 or bracketed host). Any pair that compares equal but is not one model, or a legitimate name that is now refused.
- **R5-2 enumeration through the opened collection.** `spot_check` lists ids with `collection.get(include=[])` and compares with `count()`. Read it against Chroma's behaviour on a large collection (116,661 and 6,182 rows on the real store): memory, time, a limit on `get` without ids, replay of the log mutating the restore copy. Does opening the copy with a client change anything an attestation then relies on?
- **R5-3 `_serving_database(conn, name)`.** It now runs an extra COUNT per helper call and refuses an ambiguous name. Is it called before every query in every helper? Any TOCTOU between the count and the query that matters?
- **R5-4 `may_create_wal_files`.** Only `01 01` after the magic is accepted. What does that do to a rollback-journal database with a hot `-journal` beside it, a database being written while the header is read, or a header-only file? (The live directory also holds an old `chroma.sqlite3-journal.bak-…` file, which is a backup, not a hot journal.)
- **R5-5 the fail-fast census.** It stops at the first row under the threshold. Is anything lost that an operator needs? Are the error paths now all refusals and never tracebacks, including a failure inside the embedding provider that is not an `Exception` subclass (`KeyboardInterrupt` should still interrupt)?
- **R5-6 tests that pass for the wrong reason.** Every round found at least one. Remove guards I did NOT mutate (for example the `count != 2` vs orphan split, `fail_below`, `READ_BATCH`, the moved test file's fixture import in `tests/test_chroma_readonly_scope.py`) and tell me whether a test notices.

### Decisions already taken (unchanged), known flaky tests, hard rules

The sidecar stays the strict authority; a strict PASS means "a full re-embedding of a restore copy, at the time and threshold shown, reproduced that copy's vectors"; only a first vector is judged; deferred to follow-up PRs: `open_chroma_for_read` and `refine.py:628` creating unmarked collections, the `ingest.py` summary-vector tag loss, refusing a mismatched write into a collection that holds vectors, `FileGenerationStore.stage_rows` and `restore_source_rows`, and the other name-only collection queries and unescaped URIs. Known flaky tests are under "Known flaky tests". Rules as before: read-only on the branch, never the live Chroma directory, never `~/.config/convmem/restic.env` or any client config, no `ask`, no `LATEST.md` or `STATUS`.

### Return, as plain text

(1) a re-verification table for Part 1; (2) new findings ranked Critical / High / Medium / Low with `file:line`, a reproduction and observed-or-inferred; (3) the R2B attestation regenerated independently (`MATCH` or `DIFFERS`, the digest, and whether the diff against `origin/main` is only the usual fields); (4) direct answers to R5-1, R5-2, R5-5 and R5-6 even if "nothing found", with how you looked; (5) a recommendation: ship, ship after named changes, or rework; whether strict-with-sidecar is now an acceptable fail-closed gate; and whether a sixth round is worth the cost.

---

## Review round 5 outcome (appended after the fifth Codex review; text above is the record of what was reviewed at eb420d1)

**The report reached me truncated:** it ends in the middle of the R5-1 answer. Items R5-2 to R5-6 and the closing recommendation were not received, so they are **not addressed here**; the round-6 prompt asks for them again. What I did receive: the 12-plus-one pending-log defect is fixed (Codex's decisive test), every round-4 counterexample but the Kelvin sign is fixed, and R2B matches (`MATCH`, digest `eb353ecb…`; the diff against `origin/main` is only the usual fields; manifest = four refreshed hashes and eleven new `unrelated` classifications; `ingest.py` blob identical). Codex's verdict was **ship after changes**, with strict-with-sidecar still able to return a false PASS through identity binding. Disposition of the seven findings (fixes in `7a2b7c0`):

| Codex finding | Disposition |
|---|---|
| High: a census could score one collection and publish the result under another's UUID (the UUID was checked through SQLite, the client then opened the path, and the directory was rotated in between) | **Fixed.** `spot_check` compares the opened collection's id with the one it was asked to attest and scores nothing otherwise. The test rotates the restore directory after the UUID check. |
| High: strict doctor passed during a replacement even though both complete states fail (UUID, dimension and metadata were read through separate connections) | **Fixed.** `collection_identity_facts` reads them in one read transaction, and the ambiguity count shares its snapshot. A test shows a writer trying to replace the collection mid-read is refused while the read lock is held. |
| Medium: normal doctor reads of a WAL store created `-wal`/`-shm`, and a switch to WAL after the single header check was missed | **Fixed at the boundary.** The refusal is now in `_connect_readonly`, which every reader passes through, and it runs at each connection. **Residual:** the microseconds between the header read and SQLite opening the file. |
| Medium: model parsing both accepted and refused wrongly (the Kelvin sign folded into `k`; a leading underscore refused) | **Fixed by porting Ollama's own parser** (`types/model/name.go`, fetched and quoted, not inferred): ASCII only, leading underscore valid, no dot in a namespace, scheme ignored, host 350 and other parts 80 characters, `x:`, digests and four-part names invalid, malformed names equal only themselves. |
| Medium: a stored row whose segment no longer exists counted as no row, restoring the unsafe "can be dropped" advice | **Fixed.** Such a row is unaccounted evidence, like a missing or orphan segment. |
| Medium: configuration and Chroma errors escaped `main()` as tracebacks | **Fixed.** A missing or malformed configuration and any Chroma error end the command as a refusal naming the cause; `spot_check` translates Chroma's own errors for library callers. |
| Low: the new in-guard refusal left a mutation intent with no matching completion | **Fixed.** The check is inside the failure handler, so the session sees a failed mutation. |
| R5-1 grammar: dotted namespaces, over-long components, scheme-qualified aliases, underscore-leading tags, colon-containing hosts | **Covered by the port** above, case by case. |

Mutation sweep for round 5: 15 guards, 13 caught on the first pass; two were not (a dotted namespace was undetectable because my test pair differed either way, and the Chroma-error handling existed in two layers so removing either was hidden by the other). Each layer now has its own test and all 3 reruns are caught. (The commit message for `7a2b7c0` says "14 guards, then 3 more"; this is the accurate count.) Also fixed along the way: a missing database stays "unreadable", not "empty", so strict still fails it.

**Real-store checks with this code (read-only; nothing written or created beside the live store):** doctor's read of the live store gives the same verdict as before (both collections 768-dim, unmarked, no sidecar; WARN by default, FAIL under strict) in 0.00 s, and the full-census dry run reproduces all 122,843 rows of today's restore: none failed, none below 0.9999, minimum cosine 0.999991 and 0.999998, exit 0, 669 s. Full suite at `7a2b7c0`: 213 failed / 3668 passed / 69 skipped / 1 xfailed / 52 errors, the **same 265 failing ids as the baseline, none new**.

---

## Round 6 review brief (focused; written after round 5 was addressed)

The code under review is `7a2b7c0`; later commits are docs only. Base `origin/main` = `f10d67d` (fetch it from the source worktree's remote-tracking ref). `git diff eb420d1..7a2b7c0` is the delta (10 files outside `docs/`, about 470 added lines). **Trail (the code graph) is available: use it for callers and blast radius.**

**Please first re-send what was cut off:** your round-5 answers to R5-2 (enumeration through the opened collection at 116,661 rows), R5-3 (`_serving_database`), R5-4 (`may_create_wal_files` and a hot journal), R5-5 (the fail-fast census), R5-6 (mutations that survive), and your closing recommendation. If you did not write them, answer them now against `7a2b7c0`.

**Expected results:** the six identity files (`tests/test_chroma_store_embed_identity.py`, `test_chroma_production_embed_identity.py`, `test_chroma_embed_identity.py`, `test_chroma_readonly_scope.py`, `test_chroma_embed_attestation.py`, `test_chroma_embed_attestation_census.py`): **324 passed, 1 xfailed**. The nine governed-inventory files: **84 passed** on a clean tree. Manifest: four refreshed hashes and **eleven** new `unrelated` classifications.

### Part 1: rerun your round-5 counterexamples (FIXED / STILL REPRODUCES / FIXED DIFFERENTLY, with a command or test)

1. The restore path rotated between the SQLite UUID check and the client open (restore A nonmatching, restore B a different UUID with matching rows).
2. Strict doctor with a same-dimension unmarked replacement scheduled right after the UUID read.
3. A WAL-mode stand-in: `check_embed_identity` and a dry attestation, including the switch to WAL right after a header check.
4. `K` (U+212A) against `k`; `_model` against `_model:latest`; a genuine 10/10 sidecar with `K` configured.
5. The stored row whose `segment_id` points at a missing segment, with the queue cleared.
6. A missing `--config`, malformed TOML, and a restore whose collection-configuration JSON Chroma cannot deserialize.
7. A refusal inside the write guard seen through a recording session (before / after callbacks paired).

### Part 2: attack the new code

- **R6-1 `collection_identity_facts`.** It opens one connection, runs `BEGIN`, and reads everything under a held read lock. What does that do to the live writers (a writer waiting for the exclusive lock, a reader's default busy timeout, a long transaction on a 6.7 GB database), and can it return stale facts or deadlock with Chroma's own connection?
- **R6-2 the connector refusal.** `_connect_readonly` now refuses anything that is not verifiably `01 01` after the SQLite magic, for every reader. Use Trail to list every consumer of `chroma_readonly` and every other module that reads a Chroma SQLite file. Is there a legitimate reader that now breaks?
- **R6-3 `chroma_embed_model_names.py` against Ollama's parser** (source quoted in the commit message and the doc): `ParseNameBare` order of splitting, the `!MISSING!` sentinel, a scheme on a two-part name, a host without a dot, a bracketed IPv6 host, case folding of non-ASCII.
- **R6-4 the UUID binding.** `str(collection.id)` against the live UUID: is the type and format always comparable? Can the opened handle still change after the comparison (the client holds it for the whole census)?
- **R6-5 error boundaries.** `ChromaError` is the only Chroma exception caught. Is there a Chroma, `pyo3` or Rust-panic failure on a damaged restore that still escapes `main()`, or a failure in the provider that is not an `Exception`?
- **R6-6 tests that pass for the wrong reason.** Every round found at least one. Remove guards I did NOT mutate (the `segments != 2` versus `orphan_segments` split now that there is a third trigger, `READ_BATCH`, the `fail_below` pass-through, the descriptor-closing structure of `_sidecar_lock`, `_normalized` stripping) and tell me whether a test notices.

### Decisions already taken (unchanged), known flaky tests, hard rules

The sidecar stays the strict authority; a strict PASS means "a full re-embedding of a restore copy, at the time and threshold shown, reproduced that copy's vectors"; only a first vector is judged; deferred to follow-up PRs: `open_chroma_for_read` and `refine.py:628`, the `ingest.py` summary-vector tag loss, refusing a mismatched write into a collection that holds vectors, `FileGenerationStore.stage_rows` and `restore_source_rows`, and the other name-only collection queries and unescaped URIs in other modules. Known flaky tests are under "Known flaky tests". Rules as before: read-only on the branch, never the live Chroma directory, never `~/.config/convmem/restic.env` or any client config, no `ask`, no `LATEST.md` or `STATUS`.

### Return, as plain text

(1) a re-verification table for Part 1; (2) new findings ranked Critical / High / Medium / Low with `file:line`, a reproduction and observed-or-inferred; (3) the R2B attestation regenerated independently (`MATCH` or `DIFFERS`, the digest, and whether the diff against `origin/main` is only the usual fields); (4) direct answers to R5-2 to R5-6 (if not already sent) and to R6-1, R6-2 and R6-6 even if "nothing found", with how you looked; (5) a recommendation: ship, ship after named changes, or rework; whether strict-with-sidecar is now an acceptable fail-closed gate; and whether a seventh round is worth the cost.

---

## Review round 6 outcome (appended after the sixth Codex review; text above is the record of what was reviewed at 7a2b7c0)

Codex recommended **rework the shared SQLite reader before shipping** and said strict-with-sidecar was not yet an acceptable fail-closed gate. It answered R5-2 to R5-6 (resent), attested R2B (`MATCH`, digest `893cffc5…`; only the usual fields differ; manifest = four hashes and eleven classifications; `ingest.py` identical), and confirmed all seven round-5 counterexamples as fixed for the cases originally reproduced. Its first acceptance test, which I adopted: every ordinary reader must preserve another connection's OS lock. Disposition (fixes in `cf147db`):

| Codex finding | Disposition |
|---|---|
| **Critical (mine, introduced in round 5):** the WAL header probe I put in the shared connector used an ordinary `open()` and `close()` on `chroma.sqlite3`. On POSIX, closing any descriptor for a file cancels every lock the process holds on it, so a doctor read could drop another transaction's lock (reproduced: a connection still reporting `in_transaction` let a second process take the exclusive lock) | **Fixed.** The connector no longer touches the file except through SQLite. The pre-flight `may_create_wal_files` reads the header in a child process and is used only by the attestation command (as before round 5). Reproduced first, then a test for each of 13 readers run in a fresh process: with the raw open put back, 12 of them fail. |
| High: doctor's PASS could describe no committed state (units and summaries read in separate transactions; a commit swapped their stamps in between) | **Fixed.** `collection_identity_facts_many` reads both through one connection in one transaction; a failure reading one collection is returned for that collection and cannot hide the other's. |
| High: a stable UUID, count and id set did not make a stable census (a second writer repaired a row not yet read and broke one already scored; 501/501 was published) | **Fixed.** The census fingerprints the copy (row count, sequence numbers, log sequence) after listing and again after scoring, repeats the id listing, and refuses with "changed while it was being checked". The fingerprint and the listing each have a test that fails without it. **Condition:** the restore copy must be private; the message says so. |
| Medium: the connector broke healthy WAL readers (the keyword fallback raised) and still left the no-creation promise incomplete | **Fixed by removing the connector refusal.** Readers read a WAL store again (as before this branch). The promise is made only by the attestation command: a pre-flight, then one read of the live catalog in one transaction (it no longer reopens it per fact). **Residual:** a switch to WAL between the pre-flight and that single read can still create `-wal`/`-shm`. |
| Medium: malformed inputs still escaped as tracebacks (`models = ["k"]`; a catalog dimension `'unknown'`) | **Fixed.** A configuration whose `models` is not a table, and a malformed dimension, are refusals. |
| R5-3: the ambiguity count and its query could race in the single-collection helpers | **Fixed.** The connector opens a read transaction for every reader, so they share a snapshot (a test shows a writer cannot commit between them). |
| R5-4 / R6-5: a hot rollback journal passes the header check; a provider `SystemExit(0)` returned success; a Rust panic would escape | A hot journal: SQLite refuses recovery on the read-only connection and the CLI returns 2 (Codex observed this; nothing to change). **Fixed:** a provider `SystemExit` is a failed row; a native `PanicException` is a refusal. **Not changed, by design:** other `BaseException` subclasses from a provider still escape, so `KeyboardInterrupt` still interrupts. |
| R5-6 / R6-6: guards whose removal nothing noticed (final scored-id coverage, `READ_BATCH` set to 1,000,000, the segment-count check, a descriptor leak on `flock` failure) | **Fixed.** Each now has a test: coverage by a patched sampler, the batch limit by a real 34,000-row store, the segment count by an *empty* collection missing its vector segment (the old fixture let a stored row stand in), the leak by a failing `flock`. |

Mutation sweep for round 6: 14 guards, 3 first undetected (the id re-listing, redundant with the fingerprint; the configuration check, redundant with an exception handler; and the segment-count test), each now caught by its own test.

**What is not fixed, and why.** (1) A process that has Chroma open on a database and also reads it through Python's `sqlite3` can still disturb Chroma's locks when that connection closes: they are different SQLite library instances that do not coordinate their POSIX locks. This predates the branch (`chroma_readonly` has always opened and closed its own connection); it is the reason the lock tests run in a fresh process. A safer reader design (for example never reading a store a live client holds open) is a decision for Ryan. (2) The WAL residual above. (3) A failed census still yields the first failing row, not a complete score distribution.

**Real-store checks with this code (read-only, nothing created beside the live store).** Doctor's read of the live store is unchanged (both collections 768-dim, unmarked, no sidecar; WARN by default, FAIL under strict) in 0.01 s. The full-census dry run reproduces all 122,843 rows of today's restore: none failed, none below 0.9999, minimum cosine 0.999991 and 0.999998, exit 0, 663 s, with the new fingerprint check on and no false refusal. Full suite at `cf147db`: 214 failed / 3696 passed / 69 skipped / 1 xfailed / 52 errors, which is the 265 baseline ids plus one failure of the known-flaky `test_real_watch_subprocess_and_public_query_reproduce_across_data_roots` (it passed 4 of 5 reruns on this commit; the failing run took 37 s, the same signature as on pure `origin/main`).

---

## Round 7 review brief (focused; written after round 6 was addressed)

The code under review is `cf147db`; later commits are docs only. Base `origin/main` = `f10d67d` (fetch it from the source worktree's remote-tracking ref). `git diff 7a2b7c0..cf147db` is the delta (6 files outside `docs/`, about 565 added lines). **Trail (the code graph) is available: use it for callers and blast radius.**

**Expected results:** the six identity files (`tests/test_chroma_store_embed_identity.py`, `test_chroma_production_embed_identity.py`, `test_chroma_embed_identity.py`, `test_chroma_readonly_scope.py`, `test_chroma_embed_attestation.py`, `test_chroma_embed_attestation_census.py`): **353 passed, 1 xfailed**. The nine governed-inventory files: **84 passed** on a clean tree. Manifest: four refreshed hashes and **eleven** new `unrelated` classifications (unchanged this round).

### Part 1: rerun your round-6 counterexamples (FIXED / STILL REPRODUCES / FIXED DIFFERENTLY, with a command or test)

1. Your first acceptance test: hold a read transaction in one connection and ask another process for an exclusive lock after each ordinary reader runs (`may_create_wal_files`, every `collection_*` helper, `iter_collection_metadata_rows`, `unit_document_text`, `check_embed_identity`). Run it in a process that has never loaded Chroma.
2. The atomic two-collection stamp swap: does strict doctor still pass across the commit?
3. The same-UUID, two-batch census: a second writer repairs a row not yet read and breaks one already scored.
4. A WAL stand-in: stationary, and switched after the pre-flight; readers (the keyword fallback) on a WAL store.
5. `models = ["k"]`, a catalog dimension `'unknown'`, a provider raising `SystemExit(0)`.

### Part 2: attack the new code

- **R7-1 `collection_change_fingerprint`.** It claims any change to a collection changes (rows, newest sequence, sum of sequences, newest log sequence). Is that true of Chroma 1.5.9? Try an `update` of an existing vector, a delete and re-add of the same id, a metadata-only change, a write whose effect reaches the HNSW index but not SQLite's `embeddings.seq_id`, and a second writer in another process. Any change it misses is a false PASS.
- **R7-2 `may_create_wal_files` in a child process.** It runs `sys.executable -I -S -c`. What happens under a sandbox that forbids subprocesses, a frozen interpreter, a very slow filesystem or the 30 s timeout? It returns "unsafe" on any failure, so is the attestation command unusable somewhere it should work?
- **R7-3 transaction scope.** Every reader now `BEGIN`s on connect. `iter_collection_metadata_rows` is a generator that holds its read lock while a consumer iterates. List consumers that pause mid-iteration or hold a reader open across slow work, and say what that does to writers.
- **R7-4 the pre-existing lock hazard** (Python's `sqlite3` closing a connection in a process where Chroma's embedded SQLite also has the file open). Use Trail to list readers that can run in a process holding a Chroma client on the live store (the MCP server, the watcher, `query`). Is there a safe design, and is the hazard worse than before this branch?
- **R7-5 provider `BaseException`s.** Only `SystemExit` is converted. Is anything else a provider can raise that ends a run with success or an unhelpful traceback?
- **R7-6 tests that pass for the wrong reason.** Every round found at least one. Remove guards I did NOT mutate (the `'missing'` branch of the header probe, the queue component of the fingerprint, the `FileNotFoundError` branch of `_judge_facts`, the `row_evidence` is-None path, the `sorted(...)` in the fingerprint comparison) and tell me whether a test notices.

### Decisions already taken (unchanged), known flaky tests, hard rules

The sidecar stays the strict authority; a strict PASS means "a full re-embedding of a *private* restore copy, at the time and threshold shown, reproduced that copy's vectors"; only a first vector is judged; deferred to follow-up PRs: `open_chroma_for_read` and `refine.py:628`, the `ingest.py` summary-vector tag loss, refusing a mismatched write into a collection that holds vectors, `FileGenerationStore.stage_rows` and `restore_source_rows`, the other name-only collection queries and unescaped URIs in other modules. Known flaky tests are under "Known flaky tests". Rules as before: read-only on the branch, never the live Chroma directory, never `~/.config/convmem/restic.env` or any client config, no `ask`, no `LATEST.md` or `STATUS`.

### Return, as plain text

(1) a re-verification table for Part 1; (2) new findings ranked Critical / High / Medium / Low with `file:line`, a reproduction and observed-or-inferred; (3) the R2B attestation regenerated independently (`MATCH` or `DIFFERS`, the digest, and whether the diff against `origin/main` is only the usual fields); (4) direct answers to R7-1, R7-2, R7-4 and R7-6 even if "nothing found", with how you looked; (5) a recommendation: ship, ship after named changes, or rework; whether strict-with-sidecar is now an acceptable fail-closed gate; and whether an eighth round is worth the cost.

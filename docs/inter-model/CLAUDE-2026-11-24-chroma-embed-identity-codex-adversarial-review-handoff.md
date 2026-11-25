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

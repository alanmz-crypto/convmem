# ARCHITECTURE — OpenClaw maintenance watch coverage

**Arc: OpenClaw Watch Coverage** · **State: DRAFT FOR KIRO REVIEW** ·
**Date: 2026-09-21** · **Baseline: `5ab03a37559a93f1b51932c57a2a2a783da3354b`**

This design covers only ConvMem watching and indexing safe repository knowledge
needed to maintain the ConvMem + OpenClaw integration. It does not implement or
change the OpenClaw reader, strict runtime, connector, authority model, live
OpenClaw configuration, or the Kiro-approved T0–T5 plan at
`cd9d2698b7423f907b552bc9118a0af523018ca9`.

This document is not an Execute grant. Kiro must review the exact planning tip;
Ryan must separately authorize implementation and any live configuration or
watch-service restart.

## 1. Product outcome

A future maintainer can ask ConvMem how the combined system is designed,
operated, tested, repaired, or safely changed and retrieve the relevant current
repository evidence without Ryan remembering which folders to attach.

Coverage means all four conditions hold:

1. the reviewed scope inventory classifies the complete declared repository
   surface;
2. only exact, safe, committed bytes are eligible;
3. a watch/reconciliation event sends those bytes through the ordinary
   `convmem index --file` ingest path and makes them retrievable with source and
   provenance metadata; and
4. indexing changes only derived retrieval state, never proposals, approvals,
   ledger authority, capture receipts, strict publication, or durable admission.

Merely observing a directory is not coverage. At the baseline, active
`docs/inter-model/*.md` files are indexable, while ordinary plans, Python,
tests, JSON Schema, JavaScript/MJS, TOML, and shell/text fixtures are not.

## 2. Frozen decisions

### 2.1 Closed allowlist, not extension admission

The canonical scope is
`config/repository-knowledge/openclaw-watch-scope-v1.json`, validated against
`config/repository-knowledge/openclaw-watch-scope-v1.schema.json`. Each active
entry contains:

- an exact repository-relative regular-file path;
- SHA-256 of the committed bytes;
- content class and parser mode;
- adapter contract version and expected `source_type`;
- required/reviewed state, owner, freshness role, and retrieval needles; and
- a sensitivity policy chosen from a closed enum.

No glob, recursive include, suffix-only admission, or directory membership can
make a file indexable. A new file is excluded until a reviewed manifest revision
names its exact path and hash. Exclusions override entries.

The v1 manifest declares the repository root (`.`) as its single **coverage
root**. Every Git-tracked path in the checkout must be classified as `include`,
`exclude`, or `unrelated`, with a reason. The validator fails on an unclassified file, a
duplicate path, a missing required file, a hash mismatch, a symlink, a path
escape, or a case-fold collision. This drift check is how future additions are
forced back through review.

The manifest is control state and is not indexed as project knowledge. Its
schema and the human-readable architecture/status/runbook are eligible.

### 2.2 Git-clean byte authority

An included file is eligible only when all of these are true in the configured
repository root:

1. root and manifest resolve without symlinks or traversal;
2. the file is Git tracked at current `HEAD`;
3. the working-tree and index bytes for that path equal `HEAD`;
4. SHA-256 of the file equals the manifest entry; and
5. the manifest itself is tracked, clean, schema-valid, and belongs to the same
   checkout.

Edits made before a commit therefore fail closed. The edit that updates the file
and its manifest produces a manifest event. Because Git commit itself need not
change file mtime, the watcher retains a dirty-manifest retry and polls only
manifest identity every 30 seconds until the new manifest and files are clean at
`HEAD`; it then reconciles the complete accepted set. Startup performs the same
check. This does not poll or parse unlisted repository content.

The provenance source identity is the canonical repository path plus the
repo-relative path, byte SHA-256, Git commit, manifest SHA-256, and adapter
contract version. A worktree copy, detached review bundle, `/tmp` file, or
identical file under another root is a different and ineligible source.

### 2.3 One repository adapter with content-specific chunkers

Add `adapters/repository_knowledge.py`. Detection returns
`repository_knowledge_v1` only after the allowlist and byte-authority checks
pass. Existing transcript and SQLite detectors do not run as a fallback for a
path under the configured repository-knowledge root; an unlisted path there is
rejected. This prevents watching the repository root from accidentally
admitting a transcript-shaped fixture or database through another adapter.

The adapter supports only these declared content classes:

| Class | Accepted suffixes | Chunk contract |
|---|---|---|
| `markdown` | `.md` | document title plus deterministic heading sections; split oversized sections by bounded line windows |
| `python` | `.py` | module preamble plus deterministic top-level AST definition spans; bounded line windows for residual text |
| `javascript` | `.js`, `.mjs` | deterministic bounded line windows with import/export/function headings as labels; no execution |
| `json` | `.json` | strict UTF-8 and JSON parse; deterministic JSON-pointer groups, preserving original source text in the provider payload |
| `toml` | `.toml` | strict UTF-8 and `tomllib` parse; deterministic table spans |
| `text` | `.txt`, `.sh` | deterministic bounded line windows; shell is never executed |

V1 constants are: at most 2 MiB per included file, 512 included files, 2,048
total classification entries, 64 MiB aggregate included bytes, 6,000 characters
per chunk, 120 lines per fallback window, 20 overlapping lines, and 256 chunks
per file. These are code constants asserted by schema/tests, not tunable
manifest values. Every class has strict UTF-8 and parser-version constants.
Binary bytes, invalid UTF-8, parse errors for structured classes, NULs, and
resource-limit excesses refuse the entire file. No LLM summarizes source code.
The retrieval document contains the repo-relative path, chunk label, line or
pointer locator, and bounded exact content. The provenance provider payload
contains the exact chunk content and byte/hash locators.

### 2.4 Dedicated documentary indexing path

Add `repository_knowledge_index.py` and route
`repository_knowledge_v1` through it from `ingest.py`. It packages each chunk as
an `explanation` knowledge unit with:

- `tool=repository-knowledge`;
- `source_type=repository_knowledge_v1`;
- `domain=coding.tooling`;
- `author_model=repository-file`;
- exact path, Git revision, manifest revision, byte hash, content class,
  locator, and adapter version; and
- provenance `transformer_class=packaging`, `producer_class=external`, and
  `producer_assurance=claimed`.

Unit IDs are content addressed from the source identity, locator, chunk hash,
and adapter version. Reindexing changed committed bytes writes the complete new
set and then uses the existing source-scoped snapshot/prune path to remove only
stale rows after source revalidation. Unchanged chunks retain IDs. Other source
rows remain untouched. No conversation summary is created.

Document text is never parsed as a ConvMem record, proposal, decision, capture
receipt, approval, governance intent, or publication command. Decision-shaped
IDs and words such as “approved” remain inert content. The adapter has no import
or call path to `propose_decision`, governed add/apply, recovery, capture, strict
publication, or private authority writers.

### 2.5 Watch routing and reconciliation

Extend `[watch]` with a closed list:

```toml
repository_knowledge_manifests = [
  "/ABSOLUTE/REPO/config/repository-knowledge/openclaw-watch-scope-v1.json",
]
```

Each manifest supplies its repository root relative to its own checked-in
location; live configuration does not duplicate an allowlist. Watch attaches a
dedicated recursive repository handler to that root. That handler places every
event through the repository allowlist before format detection and never falls
back to transcript/SQLite adapters. Existing configured watch roots retain a
separate generic handler and their current behavior; an overlapping legacy root
may still index a file under its existing source contract, but that result does
not count as OpenClaw repository coverage. Only an eligible exact file or the
manifest itself enters the repository debounce scheduler.

On watch startup and after a debounced manifest event,
`repository_knowledge_sync.py` validates the whole manifest and compares its
entries with a dedicated derived state file in the ConvMem data directory. It
dispatches each new or changed eligible file as a child process using the same
public `convmem index --file ABS_PATH` command, existing child timeout/memory
scope, processed-log rules, Chroma writer guard, source lock, and failure
behavior. It never calls an adapter-to-store shortcut. A file event uses the
same dispatch after revalidating the manifest.

Sync is bounded by the frozen v1 limits above, at most four configured
manifests, a 30-second manifest-identity retry interval, and one child at a
time. Any manifest or byte-authority failure blocks that repository sync; it
does not partially accept an unreviewed revision. Failed entries remain pending
for a later startup or manifest event.

### 2.6 Change, removal, and supersession

An updated path must carry its new hash in the same clean commit. Successful
reindexing publishes new units and prunes the snapshotted stale source rows only
after all new units and processed state pass existing revalidation.

A removed or renamed entry requires a manifest `retire` record containing the
old exact path, prior file hash, prior manifest hash, and replacement path or
reason. Reconciliation uses the existing authorized Chroma writer to mark all
active `repository_knowledge_v1` units for that exact source as superseded, then
records the retirement in derived sync state. It refuses rows of any other
source type or a mismatched prior identity. The operation is idempotent and
retries until no active matching rows remain. A missing file without a matching
retirement record fails the coverage gate and leaves the previous units active
with a reported stale-source error; it is never silently forgotten.

`retire` changes only derived documentary units. It cannot touch ledger rows,
proposals, receipts, authority roots, publication state, or other sources.

## 3. Required inventory

The v1 manifest must classify and include every existing reviewed tracked file
needed for these categories. Exact future T0–T5 paths are declared
`required_when_present`; they remain ineligible until a clean reviewed commit
adds the file and its exact hash.

1. **Architecture and plans:** the Kiro-approved OpenClaw architecture and
   execution plans, this arc's architecture/execution/status/verify surfaces,
   the bounded actualization brief if it lands, and current OpenClaw STATUS or
   runbook material.
2. **Operation and maintenance source:** OpenClaw reader modules after they
   land; `convmem.py`, `config.py`, `watch.py`, `ingest.py`,
   `source_reconciler.py`, adapter detection, documentary adapter/indexer, and
   the exact provenance/governed-writer helpers necessary to understand the
   non-bypass boundary.
3. **Tests and fixtures:** the exact OpenClaw reader tests and strict fixtures
   after they land, plus focused watch, provenance, writer-gate, and repository
   knowledge acceptance tests.
4. **Schemas and interfaces:** OpenClaw Gate B/Gate C schemas and connector
   manifests after they land, the repository-scope schema, and exact CLI/MCP
   interface definitions used by the combined system.
5. **OpenClaw integration:** the connector package/plugin manifest, JS/MJS
   implementation/tests, and safe operator docs after they land.
6. **Safe configuration knowledge:** `config.example.toml`,
   `config/agent-protocol.md`, and reviewed examples containing no live values.
7. **Execution and operations:** acceptance, recovery, Git hygiene,
   always-available fallback, model workflow, verification, watch, and
   operational documents directly needed for this system.
8. **Troubleshooting:** parser detection, event debounce, child containment,
   exclusion, reconciliation, provenance, proposal/approval separation, common
   refusals, and coverage-drift repair.

The implementation inventory must list the exact paths rather than referring
to this prose. It must distinguish current, historical, and future-when-present
material so retrieval does not present a superseded review as current guidance.

## 4. Mandatory exclusions

Before opening content, reject:

- credentials, `.env*`, tokens, cookies, private keys, auth stores, password
  files, real provider settings, or credential-bearing output;
- production authority roots, grounding/citation/issuer stores, governance
  intents, capture receipts, approvals, recovery evidence, or private grants;
- Chroma, SQLite and WAL/SHM files, live corpora/exports, processed state,
  transcript/session stores, OpenClaw memory/workspaces, or mutable user data;
- `.git`, caches, virtual environments, `node_modules`, build/dist/temp output,
  locks, sockets, PIDs, service state, and editor state;
- generated bundles, manifests, reports, screenshots, logs, copied runtime
  trees, compiled/minified output, and duplicate worktree/review copies; and
- unrelated arcs, client/site material, historical debates, vendored
  dependencies, and all files outside the exact manifest.

Synthetic fixtures are allowed only by exact path/hash and must be labeled
`synthetic`. Safe configuration examples use the strictest sensitivity policy:
the validator rejects credential filenames, private-key markers, and non-
placeholder assignments to credential-shaped keys. Source-code entries still
reject private-key material but may contain credential field names as code.

## 5. Threat model and trust boundary

The attacker may add or rename a file, craft a supported suffix, place a
symlink inside an allowed directory, alter a file after validation, copy the
repo into another worktree, embed instructions or decision-shaped records,
exhaust chunk/file limits, or trigger many watch events. The attacker may not
modify a reviewed commit and its manifest without producing a different Git
and manifest identity.

Controls are exact path/hash admission, Git-clean revalidation immediately
before and after parsing, strict parser/resource limits, no execution, one-child
serialization, existing process containment, source locks, source-scoped
replacement, and documentary provenance. If any identity changes before
publication, the file is refused and processed state does not advance.

The watch manifest grants retrieval eligibility only. It grants no edit,
runtime import, proposal, approval, admission, authority, publication,
promotion, or OpenClaw activation permission.

## 6. Acceptance contract

All acceptance runs use a disposable repository and ConvMem data root,
synthetic nonsecret content, fake deterministic embeddings, network denial,
and the real watch child/ingest/writer boundaries. No live config, corpus,
OpenClaw profile, credential, provider, model, or service is touched.

### Positive proof

1. Start with the synthetic relevant folder absent from
   `repository_knowledge_manifests`; prove a unique nonce is absent from normal
   retrieval.
2. Add the exact manifest path to isolated watch config and start the watcher.
   Startup reconciliation must dispatch every eligible committed file once.
3. Require retrievable examples for architecture Markdown, Python source,
   Python test/fixture text, JSON Schema, JavaScript/MJS, safe TOML, and
   operational Markdown. Each result must expose exact path, Git commit, file
   hash, manifest hash, adapter/source type, locator, and valid provenance.
4. Commit a changed eligible file and matching manifest hash. The manifest
   event must cause current text to replace the old active source generation;
   the old text cannot remain as an unlabeled current duplicate.
5. Add a new relevant folder containing an exact admitted file in a clean
   commit and update the manifest/config as applicable. Prove one debounced
   event, one `index --file` child dispatch, and retrieval by nonce and natural
   maintenance question.
6. Repeat from a second fresh data root and require the same inventory,
   identities, units, and retrieval needles.

### Negative and non-bypass proof

Seed unique synthetic markers for every exclusion class, plus dirty tracked
file, untracked file, unreviewed new file, hash mismatch, symlink, traversal,
case collision, duplicate worktree, unsupported/invalid content, resource
limit, and transcript-shaped fixture. None may parse, dispatch, or retrieve.

Before and after the positive run, independently snapshot and hash the proposal
queue/event log, approved-decision file, ledger authority, strict authority and
publication roots, governance intent, capture receipt state, and other durable
approval surfaces. They must be byte-identical. Expected mutations are limited
to the isolated derived Chroma/index, processed/reconciliation/sync state, and
test evidence.

Document content that imitates an approval, proposal, governed decision,
capture receipt, or promotion instruction must remain ordinary documentary
text. Tests must prove no call to `record`, proposal apply/approve, governed
add, recovery, capture, publication, or a private writer.

## 7. Operational activation boundary

Implementation completion does not activate live watching. After code review
and merge, a separate Ryan grant must name:

- the exact absolute manifest path;
- the exact live config key/value;
- the checkout/root and branch policy (normally clean `main`);
- resource limits;
- the watch service to restart; and
- rollback values.

Activation must back up the live config, validate the clean manifest, capture
pre-state, apply only that key, restart the named watcher, observe startup sync,
run the safe retrieval needles, prove governance hashes unchanged, and restore
the prior value on failure. It must never add an OpenClaw user profile,
workspace, auth store, memory, transcript, or live database.

## 8. Non-goals and hard stops

- no changes to Kiro-approved OpenClaw T0–T5 architecture or acceptance;
- no OpenClaw reader/runtime/connector implementation in this arc;
- no broad generic repository parser or automatic suffix admission;
- no indexing of dirty/untracked bytes, live configuration, secrets, authority,
  live corpora, sessions, caches, generated output, or unrelated material;
- no live config edit, service restart, corpus mutation, or activation during
  planning/review;
- no claim that folder observation alone is coverage; and
- no claim of complete coverage while a required current file is absent,
  unclassified, hash-mismatched, unsupported, stale, or unretrievable.

Stop for Codex/Kiro if implementation needs a new content class, writer route,
authority change, retirement policy, source identity, parser behavior, or
activation surface. Cursor must not invent those decisions.

## 9. Review request

Kiro should independently inspect the exact planning tip and issue PASS or
FAIL on: closed inventory completeness; Git-clean byte authority; generic-
detector shadowing; parser/resource bounds; source-scoped update/retirement;
provenance strength; proposal/approval/authority non-bypass; isolated positive
and negative acceptance; and separation from OpenClaw T0–T5 and live
activation. Kiro PASS is design approval only and does not authorize Execute.

**TL;DR [Arc OpenClaw Watch Coverage]:** Use a reviewed, hash-pinned exact-file
manifest and Git-clean reconciliation to index safe ConvMem + OpenClaw
maintenance knowledge through normal `index --file` ingest. Reject everything
else before parsing, preserve documentary provenance, prove retrieval and
governance non-bypass in isolation, and keep live activation separately gated.

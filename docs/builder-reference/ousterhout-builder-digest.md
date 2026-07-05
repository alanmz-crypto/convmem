# Ousterhout - builder digest (convmem)

**Source:** *A Philosophy of Software Design* (2nd ed.) · Chapters 4-9, pp. 34-92;
Chapter 10 (Define Errors Out Of Existence), pp. 95-109; Chapter 17
(Consistency), pp. 164-168

**Read when:** editing `convmem.py`, `brief.py`, `mcp_server.py`, the CLI
surface, protocol generation, module boundaries, ask() timeout/fallback
design, partial-synthesis vs raw-fallback decisions, multi-surface protocol
consistency, or any code that is starting to look like a pass-through layer.

## Principles

- Complexity is the thing to fight first. Working code is necessary, but it is
  not the same as good design.
- Deep modules are the ideal. A deep module offers a lot of behavior through a
  narrow interface, while hiding the ugly details behind that interface.
- Shallow modules are expensive. They add surface area, documentation burden,
  and cognitive load without buying much capability.
- Strategic programming beats tactical programming. Spend a little extra time
  to improve the design now, because the long-term cost of tactical shortcuts
  compounds.
- Information hiding is a design tool, not a slogan. If a detail matters only
  inside one module, keep it inside that module.
- General-purpose modules tend to be deeper because they can absorb special
  cases instead of forcing them into the surface API.
- Push specialization upward or downward. Shared mechanisms should stay
  general; case-specific behavior belongs in the layer that actually needs it.
- Pull unavoidable complexity downward if it removes complexity from the
  higher-level interface and makes the overall system easier to use.
- Split code only when the split removes real complexity. Separating code just
  to be “clean” can make the design shallower.
- Defining errors out of existence is better than documenting them later. If a
  failure mode can be removed by design, remove it.
- **Exception handling is one of the worst sources of complexity** (Ch. 10). The
  best exception is the one that never needs to be thrown. The second best is
  the one that is masked at a low level so callers never see it.
- **Aggregate exception handling.** Rather than catching the same error in many
  places, handle it once at the top of the call chain. This turns exception
  handling into a deep mechanism: narrow interface (one handler), broad
  behavior (covers all callers).
- **Crashing can be a valid design choice.** If a failure indicates a bug,
  crashing is simpler and more honest than attempting error recovery that will
  probably be wrong (Ch. 10, out-of-memory example).
- **Design it twice** (Ch. 11). Your first design for any non-trivial module is
  unlikely to be the best one. Compare at least two approaches before committing.
- **Consistency creates cognitive leverage** (Ch. 17). When similar things are
  done in similar ways, developers can transfer knowledge from one part of the
  system to another without studying each case in detail.
- **Consistency has three enforcement tiers:** documentation, automated
  checkers (lint, fitness functions), and design conventions that make
  violations structurally impossible. Automated enforcement is the most
  reliable.
- **Don't change existing conventions.** A "better idea" that breaks consistency
  is almost never worth the cost (Ch. 17, p. 167). The value of predictability
  across the codebase exceeds the marginal improvement of the new approach.
- **Comments, names, and consistency are part of design quality.** They are not
  polish added after the fact.

## What to look for in convmem

- If a function has to explain itself in code comments before you can use it,
  the interface is probably too shallow.
- If a CLI flag exists only because another internal API was awkward, that is
  a sign the abstraction boundary is in the wrong place.
- If an implementation detail leaks into `brief`, `search`, or `record`, the
  user contract is getting coupled to storage or orchestration details.
- If a command is mostly forwarding arguments to another command, the layer is
  redundant and probably needs to disappear or absorb more behavior.
- If a new feature adds a second way to express the same idea, ask whether the
  two paths are really different or just duplicated surface area.

## Design moves that matter

- Prefer one deep orchestration function to several shallow wrappers.
- Keep validation close to the place where the invariant matters, not out in a
  distant caller that has to guess what the callee needs.
- Put knowledge in the narrowest module that needs it. For convmem, that often
  means the extraction/indexing code or the protocol generator, not the top
  level entrypoint.
- If a command needs many knobs, consider whether the knobs belong to the
  caller or whether the command should split into a simpler command plus a
  separate advanced path.
- If a helper becomes a dumping ground for ad hoc cases, that helper has become
  a shallow module.

## Convmem-specific examples

- `mcp_server.py` should not become the place where convmem policy is invented.
  It should load a thin instruction set and delegate to deeper modules.
- `scripts/generate-agent-protocol.sh` is valuable because it keeps the protocol
  SSoT in one place and emits the surface variants. That is a deep move.
- The builder-reference digests are another deep move: instead of repeating
  architecture lore in each surface config, the configs point to a narrower
  curated source.
- A good `search` path should hide the vector-store and retrieval plumbing from
  the caller. The caller should ask a question, not reconstruct the pipeline.
- A good `record` path should hide ledger mechanics from the session author.
  The author should describe the decision and rationale, not the storage shape.

## Module-level heuristics

- If a module is hard to explain in one paragraph, check whether it is doing
  too many jobs.
- If a module is easy to explain but hard to use, check whether it is shallow.
- If a module needs several call-site-specific exceptions, consider pushing the
  specialization somewhere else.
- If a module exists only to convert between two similar interfaces, ask whether
  one layer can be removed.
- If two modules share a hidden dependency, that is usually a signal that the
  abstraction boundary is wrong.

## How agents should use it

- Before editing protocol or orchestration code, read this digest and look for
  places where the current change would widen a surface unnecessarily.
- When you see a new helper, ask whether it increases depth or simply adds
  another pass-through hop.
- When you see a new config file, ask whether it is encoding policy that should
  instead live in the code or in a smaller rule file.
- When you see repeated code across agent surfaces, prefer a generator or a
  shared digest rather than copy-paste.

## convmem Hooks

- `brief`, `search`, `ask`, and `record` should each do one thing and expose a
  small surface.
- `mcp_server.py` should stay thin. If it starts embedding policy, retrieval,
  or report logic, that is a sign the module boundary is wrong.
- The CLI should not mirror internal storage structure. The user should not
  need to know how Chroma, summaries, or watch state are laid out to use the
  tool.
- Generated protocol files are a better fit for shared rules than repeated
  hand-edited blocks in many places.
- `doctor -> brief -> unresolved` is a design decision as much as a workflow
  rule: it prevents avoidable failures up front.
- Keep builder-reference digests separate from protocol rules. The rules should
  point at the digests, not absorb them.
- A deep helper like `evidence.py` or `search_fast.py` is better than a chain
  of wrappers that merely rename the same operation across layers.
- For repo maintenance, use the digest to check whether a proposed change makes
  the builder surface easier to reason about, not just easier to type.

## Anti-patterns for Agents

- Do not add a new CLI flag if the same behavior can be expressed by a helper
  that already exists.
- Do not stuff retrieval logic into the MCP entrypoint just because the call
  site is convenient.
- Do not create separate code paths for “same thing, different surface” unless
  the surfaces genuinely differ.
- Do not expose low-level corpus or vector-store details in user-facing
  commands unless the detail is part of the user contract.
- Do not make the surface more complicated just to preserve a local shortcut.
  If the shortcut is good, it belongs deeper down.
- Do not convert a deep module into a thin wrapper just so the call graph looks
  flatter.
- Do not bury ask() synthesis failures in a silent fallback without a way for
  the caller to detect degradation. If you define the error away, make sure the
  degraded path is observable (Ch. 10, exception masking caveat).
- Do not hand-edit generated protocol files for one surface. The inconsistency
  between surfaces will compound faster than the convenience gain (Ch. 17,
  "don't change existing conventions").
- Do not add a second way to express the same concept across agent surfaces.
  If Crush and Cursor need different phrasings, the generator should emit both
  from one SSoT — not two hand-edited rule files drifting apart.

## Worked example: adding a Typer command

Suppose you want `convmem unresolved --json` for machine-readable triage output.

**Leaky design (avoid):**

- Add `--json` flag on the Typer command in `convmem.py`.
- Inline `json.dumps()` over raw observation dicts in the command handler.
- Duplicate field-selection logic that `unresolved.py` already knows.
- Force MCP and shell callers to understand ledger field names.

**Deep design (prefer):**

- Add `render_unresolved_json(observations: list[dict]) -> str` in
  [`unresolved.py`](../../unresolved.py) next to the existing text renderer.
- Keep `convmem.py` as a one-line delegate: parse flags, call
  `list_unresolved(...)`, pass result to the renderer.
- If MCP needs the same shape later, expose a thin tool that calls the same
  renderer — one implementation, two surfaces.

The test: can you describe the new behavior in one sentence without naming
Chroma, Typer, or JSON? "Return open observations as a stable JSON list." If
yes, the interface is probably deep enough.

## Named modules in this repo

| Module | Depth | Why |
|--------|-------|-----|
| [`evidence.py`](../../evidence.py) | Deep | Hides ledger graph boosts, recency decay, and dedupe behind `apply_evidence_rerank()` |
| [`ask.py`](../../ask.py) | Deep | Owns retrieval + synthesis orchestration; callers pass a question |
| [`brief.py`](../../brief.py) | Deep | Gathers corpus snapshot, staleness, projects — one `gather_brief_data()` |
| [`chroma_store.py`](../../chroma_store.py) | Deep | Vector ops + metadata; query layer does not touch raw Chroma APIs |
| [`mcp_server.py`](../../mcp_server.py) | Should stay thin | Loads MCP slice, registers tools, delegates to `ask` / `brief` / `query` |
| [`convmem.py`](../../convmem.py) | Risk zone | Typer shell — grows fast; resist embedding policy here |

When editing, ask: "Am I making a deep module deeper, or making the shell
shallower by pushing logic down?"

## Before/after: `unresolved --json` (hypothetical)

**Before (shallow):** six call sites format observations differently; agents
parse inconsistent text; MCP tool reinvents the list.

**After (deep):** one canonical JSON schema from `unresolved.py`; text and JSON
are views over the same list; verifier script can assert schema stability.

## Protocol generation as information hiding

[`scripts/generate-agent-protocol.sh`](../../scripts/generate-agent-protocol.sh)
reads [`config/agent-protocol.md`](../../config/agent-protocol.md) and emits
Cursor `.mdc`, Kiro steering, Codex `AGENTS.md`, Crush rules. Surfaces never
edit ritual text by hand — they consume slices. That is Ousterhout's "general
module absorbs special cases": one SSoT, many outputs.

This is also Ousterhout's **consistency** principle (Ch. 17) applied at the
protocol level. The generator enforces consistency across five surfaces by
making drift structurally impossible — the same class of mechanism as
automated style checkers, but for agent behavior instead of code formatting.

Builder-reference deploy follows the same pattern: digests live in
`docs/builder-reference/`; surfaces get pointers or copies via
[`scripts/deploy-builder-reference.sh`](../../scripts/deploy-builder-reference.sh).
The deploy scripts are the enforcement tier: if a surface digest is stale, the
verifier fails, not just a style warning.

## When to split vs when to merge

Split when two subsystems have different change rates or different failure modes
(ingest vs query). Merge when a split only renames calls without hiding
complexity. `cross_project_digest.py` calling `ask()` is correct depth — digest
formatting is separate from RAG, but it should not reimplement retrieval.

## Comments and names as design signals

If you need a comment like "must run after doctor because brief assumes Chroma
is up," that invariant belongs in `doctor.py` or the brief gather path — not
in every agent rule file. Generated protocol text should state the ritual once;
builder digests state the *why* once.

## `mcp_server.py`: define errors out of existence

[`mcp_server.py`](../../mcp_server.py) implements `_blocked_until_brief_json()` for
`workspace_local` and system-runbook cwd modes. Instead of letting agents list
directories and invent project state, MCP tools return a JSON error until
`brief()` runs once in-process (`_mcp_brief_called`).

That is Ousterhout's "define errors out of existence" (Ch. 10): the failure mode "agent
guessed cwd context" is removed by gating reads. Do not duplicate this policy in
every tool handler — centralize the gate, as the chapter recommends aggregating
exception handling in one place.

### ask() timeout as error definition

The partial-synthesis-vs-raw-fallback design is an errors-out-of-existence
problem:

- **Throw the error:** if synthesis times out (>45s), return an error to the
  caller. Clean, honest, but the caller (agent) gets nothing and may hallucinate.
- **Define it away:** fall back to raw search results when synthesis fails.
  The caller gets a degraded answer instead of no answer. This is exception
  masking — the error is handled at a low level so higher levels need not be
  aware (Ch. 10, p. 102).
- **Promote and reuse:** if synthesis failures are common enough to justify a
  retry or fallback mechanism, make that mechanism the standard path and use
  it for other recovery cases too. This mirrors the RAMCloud example (Ch. 10,
  p. 107) where crash recovery became the universal mechanism.

**Applied 2026-07-05 (P1c Phase 1):** `generate_stream()` + partial fallback.
Callers distinguish three states via response fields:

- **Full synthesis** — normal answer, no flags.
- **`synthesis_interrupted: true`** — partial tokens before timeout; answer
  ends with `[Synthesis interrupted …]`; not counted by doctor synthesis gate.
- **`synthesis_failed: true`** — empty buffer; citation-only fallback (prior
  behavior); logged to `synthesis_failures.jsonl`; doctor gate >=3/week.

This is promote-and-reuse, not silent masking: agents can recognize degraded
state without parsing prose. See
[`notes/suggested-application-of-builder-material.md`](notes/suggested-application-of-builder-material.md)
§ Partial synthesis on timeout.

Prior design (pre-2026-07-05) masked the error (returns raw context only).
That path remains the empty-buffer worst case.

MCP `instructions=` load from [`config/agent-protocol-mcp.txt`](../../config/agent-protocol-mcp.txt)
when generated; the inline `_INSTRUCTIONS` fallback in `mcp_server.py` should
stay short. Long policy belongs in `agent-protocol.md`, not duplicated in Python
string literals.

## `brief.py`: gather vs render

[`brief.py`](../../brief.py) separates **data gathering** (`gather_brief_data`,
`gather_brief_payload`) from **rendering** (`render_brief_markdown`,
`write_brief`). CLI `convmem brief` and MCP `brief()` share the gather path;
only output destination differs (stdout vs JSON).

If you add a new brief field (e.g. builder-reference deploy status), add it once
in gather — not in Cursor rules, Crush ritual, and brief template separately.

## `convmem record`: thin write path

Recording flows through Typer in `convmem.py` into ledger write helpers — agents
never get MCP write tools. The user contract is flags (`--relates-to`,
`--summary`, `--rationale`, `--author`); storage shape stays internal.

When adding record validation (e.g. reject fake `--relates-to` slugs), validate
in the ledger module, not in each agent surface's instructions.

## Ingest vs query boundary

[`ingest.py`](../../ingest.py) and adapters (`adapters/sqlite_chat.py`, etc.)
change slowly and fail differently from [`query.py`](../../query.py) /
[`ask.py`](../../ask.py). Keep ingest adapters from importing ask/brief — one-way
dependency: ingest → Chroma → query.

Watch daemon ([`watch.py`](../../watch.py) if present) debounces file changes;
query layer should not assume synchronous index freshness. That invariant
belongs in brief staleness alarms, not in search error messages.

## Builder-reference module boundary

These digests are **not** corpus units and **not** protocol ritual. They sit in
`docs/builder-reference/` with their own deploy/verify scripts:

- [`scripts/verify-builder-reference.sh`](../../scripts/verify-builder-reference.sh) — sha256 + paths
- [`scripts/validate-builder-reference-surfaces.sh`](../../scripts/validate-builder-reference-surfaces.sh) — per-surface config depth

Keeping verification out of `convmem doctor` (for now) preserves doctor as
infra health; builder-reference is agent wiring health — related but separate.

## Checklist before merging a convmem PR

1. Did the change widen a public API without hiding complexity?
2. Could the same behavior live in an existing deep module?
3. Did you add a second path to express one idea (shell vs MCP vs generated rule)?
4. Will `generate-agent-protocol.sh` need a regen, or only builder-reference deploy?
5. Can an agent describe the feature without Chroma/Typer jargon?

If any answer signals leakage, refactor before adding docs.

## Scenario walkthrough: new MCP tool

Suppose you add MCP `unresolved()` read-only tool.

**Wrong path:** copy `list_unresolved` loop into `mcp_server.py` with JSON
formatting inline — doubles ledger logic, breaks when `unresolved.py` adds
severity sort.

**Right path:**

1. `unresolved.py`: add `unresolved_payload(store, site=..., domain=...) -> dict`
   returning `{count, items: [...]}`.
2. `mcp_server.py`: register `@mcp.tool` calling that function — ~10 lines.
3. Shell CLI: call same payload, render text or `--json` from one schema.
4. `generate-agent-protocol.sh`: one line in Tier B if agents must know the tool.

**Depth test:** MCP handler readable without scrolling; all ledger rules in
`unresolved.py`; tests target payload function not MCP wire format.

## Scenario walkthrough: protocol drift

Symptom: Cursor rule says `brief()` first; Crush rule still mentions old tool
name. Root cause: hand-edited surface file instead of regen.

**Fix:** edit [`config/agent-protocol.md`](../../config/agent-protocol.md) only;
run `bash scripts/deploy-agent-protocol.sh` (includes builder-reference phase).
Never patch `~/.cursor/rules/convmem.mdc` by hand for ritual text.

Builder-reference pointers are separate deploy — do not merge digests into
`agent-protocol.md` (keeps protocol lean per Ousterhout).

## `chroma_store.py` as storage deep module

Callers pass text + metadata; `ChromaStore` owns collection names, upsert keys,
and `query_units` distance→score mapping. Query layer should not open Chroma
client directly except through store — prevents duplicate connection logic and
readonly/write mode mistakes ([`chroma_readonly.py`](../../chroma_readonly.py)).

## Complexity budget for `convmem.py`

The Typer app registers dozens of commands. Acceptable growth: new **command
registration** only. Unacceptable: business logic blocks inside `@app.command`
handlers longer than ~15 lines. Refactor threshold: second `if` branch on the same
storage detail in the shell file.

## Joining builder-reference with session ritual

Tier A ritual (`doctor → brief → unresolved`) lives in protocol rules.
Builder-reference is **scoped guidance** for architecture edits — loaded via
Cursor globs when cwd is `~/Projects/convmem`, Crush `global_context_paths`,
or Kiro manual steering.

An agent can complete ritual correctly and still ship a shallow module split.
Ritual answers "is the corpus healthy?"; Ousterhout digest answers "is this
diff the right shape?" Use both — neither replaces the other.

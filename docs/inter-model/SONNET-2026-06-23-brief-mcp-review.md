# Sonnet cloud review — brief MCP + per-project rollup

## Verdict: PASS WITH NOTES

## Findings (ranked)

1. **The named failing example is closed, with an honest caveat already in the bundle itself.** LIVE-RESULTS shows the vague "where left off willowyhollow-dev" `ask` failing thin without project context, then `gather_brief_payload(project="willowyhollow-dev")` returning a populated row (53 units, `AGENTS.md` path, 3 recent titles, a working `entry_search`). That's the actual fix to the gap I named two rounds ago. Good.

2. **`resolve_project_from_path` has a real, demonstrable false-negative class: anything outside `GitClones|Projects|WordPress` and outside a Cursor `projects/home-lauer-*` directory returns `None` silently.** Concrete case from the code itself: `~/.local/share/convmem/` paths, `~/Downloads/`, or any ad-hoc clone outside the three named roots produce no slug and the source is dropped from every project row — not mis-attributed, just invisible. Given `WordPress` is one of three roots, I'd also ask whether `pavlomassage.com`'s repo lives under one of these three names; if it's cloned somewhere else, it gets the same silent drop. Not a bug in the code as written — a real limitation the code can't see past, and worth Ryan confirming repo locations against this list once.

3. **False positive is narrower but real: `_REPO_ROOT_NAMES` substring match (`needle = f"/{root}/"`) means any path containing `/Projects/` as a substring of a longer segment name would not collide** (it requires exact path-boundary slashes), but two *different* root families both named, say, `wp-sec-agent` under both `GitClones/wp-sec-agent` and `Projects/wp-sec-agent` would silently merge into one slug bucket — `by_slug` keys purely on `slug`, not `(root, slug)`. Low-probability given Ryan's naming habits, but the merge would be silent, not erroring.

4. **Double-counting is structurally avoided, not just hoped-for.** Inventory rows and Chroma metadata rows write into *different* fields on the same bucket (`indexed_sources` from inventory only, `knowledge_units` from Chroma only) — they don't both increment the same counter. That's correct as written; I don't see a path to inflated numbers here.

5. **`entry_search` as `"{slug} handoff next steps"` is a reasonable default but will sometimes literally fail** — search_fast is semantic, and "handoff next steps" is exactly the kind of meta-phrase that may not appear in any actual unit's content (units are about *what happened*, not about being a handoff). A slightly better default, costing nothing extra: `"{slug} {most_recent_recent_unit_title}"` when `recent_unit_titles` is non-empty, falling back to the current phrase only when it's empty. Minor, not blocking.

6. **Test coverage gap, named honestly:** no test exercises `resolve_project_from_path` returning `None` (the unmatched-path case from finding #2), and no test exercises the cross-root slug collision from finding #3. The existing three path tests are good but only cover the success path.

## Boundary check (MCP read-only)

- Confirmed by direct read of `mcp_server.py`: 6 tools total (`brief`, `search_fast`, `search`, `ask`, `related`, `stats`). No `propose_decision`, no `add`, no write call anywhere in `brief()`'s body — it's a json.dumps wrapper over a payload function that itself only reads (`load_config`, `collection_metadata_rows`, `_load_inventory_records`, `subprocess.run` against `systemctl`/`pgrep`/`/proc`). No filesystem writes, no Chroma writes, in the entire diff.
- The MCP server's own docstring/instructions now state the boundary explicitly to any agent reading tool descriptions: *"Read-only: no propose_decision or add on MCP — durable writes are CLI + signer only."* That's the right place to say it — visible to every cold agent, not buried in a doc they might skip.
- `coordination.mcp_writes: false` is also stated as a literal payload field, so any agent parsing `brief()`'s JSON sees the boundary as data, not just prose. I like this — it's checkable by code, not just by a human reading a docstring.
- I did not find any erosion of the CLI-only `propose_decision` boundary anywhere in this change. This passes the constraint from the README and from your message.

## One follow-up (single highest-leverage item)

**Confirm Ryan's actual repo root locations against `_REPO_ROOT_NAMES = ("GitClones", "Projects", "WordPress")` once, by hand, before trusting the project list as complete.** Everything else in this review is a refinement; this one is a coverage question with a real, silent failure mode (finding #2) and a five-minute check (`ls ~/GitClones ~/Projects` and confirm nothing relevant lives elsewhere). If a repo Ryan actually works in isn't under one of these three names, `brief(project=...)` for that repo will return an empty row with no error — which is exactly the kind of silent gap this whole effort was meant to close.

---

## Answers to QUESTIONS.md

**1. Can `resolve_project_from_path` mis-map paths? Concrete examples.**
False negative: any path outside the three named roots and outside a Cursor `projects/home-lauer-*` dir returns `None` — e.g. `~/Downloads/export.jsonl` or a clone under `~/dev/` instead of `~/GitClones/`. False positive (narrow): two repos with the same basename under different roots (`GitClones/foo` and `Projects/foo`) merge into one slug bucket since `by_slug` keys on slug alone, not `(root, slug)`.

**2. Is merging inventory + Chroma units into one slug bucket correct, or can counts double-count?**
Correct as written. Inventory contributes only to `indexed_sources`; Chroma metadata contributes only to `knowledge_units`. Different counters, no overlap, no double-count path that I can find by tracing the code.

**3. Should `entry_search` be `{slug} handoff next steps` or something else?**
I'd prefer `{slug} {most_recent_unit_title}` when a recent title exists, falling back to the current phrase otherwise — semantic search works better against language that resembles actual unit content than against meta-vocabulary like "handoff." Not blocking; current default is a reasonable v1.

**4. Should each project row include last ledger decision id for that repo? How would you derive it without new schema?**
Yes, worth adding, and derivable without schema changes: filter `_recent_decisions()`'s existing Chroma scan by `site` or by checking if `source_path`/`relates_to` on the decision resolves to the same slug via the same `resolve_project_from_path` function already written. Since decisions are sparse relative to chat units, this is a cheap additional pass, not a new index.

**5. Is the `brief` JSON payload too large for typical MCP context? What fields would you drop or lazy-load?**
With `project=""` (no filter), payload includes up to 8 project rows each carrying 3 recent titles plus paths — likely a few KB, not large by MCP standards. I'd lazy-load `recent_unit_titles` and `formats` only when a specific `project` filter is passed (i.e., return slug/repo/counts/age for the unfiltered overview list, and only the richer per-project detail when `project` narrows to one match) — cheap to add, keeps the common "give me the lay of the land" call lighter.

**6. Is `with_tests` on MCP safe (runs unittest on host)? Should it default false and stay rare?**
Confirmed default is `False` in both `brief()`'s signature and the test mock. Agree it should stay rare and default-off — `_run_test_count()` runs the full suite via subprocess with a 120s timeout, which is a meaningfully heavier and slower call than every other MCP tool in this file; fine as an opt-in, wrong as a default.

**7. Does `coordination` block belong in every brief call or a separate tool?**
Every call — it's small (four short fields) and it's precisely the boundary-stating data a cold agent needs on its *first* call, not a second round-trip. Splitting it into a separate tool risks an agent never calling it and never learning the write boundary.

**8. Does this change accidentally encourage agents to treat brief as writable truth?**
No — I traced every line of `brief()`'s body and `gather_brief_payload`/`gather_brief_data`; there is no write call anywhere in this path. The tool docstring and the `coordination.mcp_writes: false` field both state the boundary as a property an agent can check, not just infer.

**9. Confirm: no MCP write path is correct. What should agents do when they want to record "left off"?**
Confirmed correct, and I'd actively resist adding one — durable claims need the signer gate, and "convenient for an agent" was already rejected as a reason to erode that boundary in this same thread. What agents should do: surface the "left off here" content back to Ryan (or whichever human/Kiro session has shell access) to run `convmem propose_decision -i`, exactly as `gather_brief_payload`'s own `coordination.durable_writes` field already states: *"CLI only: propose_decision → signer approve → add --upsert."*

**10. Does `brief(project="willowyhollow-dev")` close Sonnet's named failing example in design, given 22d stale transcript?**
Yes, in design, and the live output supports it: the cold-pickup answer for that repo now includes repo path, `AGENTS.md` location, 3 recent unit titles, and a working search entry point — exactly the five things I listed as "the bar for we're there" two rounds ago, minus #5 (open the repo itself), which is outside brief's scope and correctly left to the agent's own shell/file tools once it has the repo path.

**11. What's the minimum second change if this ships as-is?**
Confirm and likely widen `_REPO_ROOT_NAMES` (or add a config-driven list) so repos outside the three hardcoded names aren't silently invisible — this is the single highest-leverage gap left, named in my one-follow-up above.

**12. What path patterns are untested?**
The `None`-return case (path matches none of the patterns) and the cross-root slug-collision case (same basename under two different roots). Both are real code paths with no assertion against them.

**13. What test would you add with highest value?**
A test asserting `resolve_project_from_path("/home/lauer/Downloads/random.jsonl") is None` — cheap, and it documents the actual boundary of what this function can see, which matters more than another success-path test given the existing three already cover the common cases well.

**14. PASS / PASS WITH NOTES / FAIL — one sentence why.**
PASS WITH NOTES: the read-only boundary is fully intact and verified by direct code trace, the named cold-pickup failure is closed in both design and live output, and the only real gaps (silent path-coverage limits outside three hardcoded root names, and a narrow cross-root slug-collision edge case) are refinements to ship alongside or immediately after, not reasons to block this change.

# Review questions (answer all)

## A. Project rollup

1. Can `resolve_project_from_path` mis-map paths? Give concrete false positive/negative examples from the code.
2. Is merging inventory + Chroma units into one slug bucket correct, or can counts double-count?
3. Should `entry_search` be `{slug} handoff next steps` or something else?
4. Should each project row include **last ledger decision id** for that repo? How would you derive it without new schema?

## B. MCP API

5. Is the `brief` JSON payload too large for typical MCP context? What fields would you drop or lazy-load?
6. Is `with_tests` on MCP safe (runs unittest on host)? Should it default false and stay rare?
7. Does `coordination` block belong in every brief call or a separate tool?

## C. Boundaries

8. Does this change accidentally encourage agents to treat brief as writable truth?
9. Confirm: **no MCP write path** is correct for durable memory. What should agents do when they want to record "left off"?

## D. Cold pickup (reason from LIVE-RESULTS.md)

10. Does `brief(project="willowyhollow-dev")` close Sonnet's named failing example **in design**, given 22d stale transcript?
11. What's the minimum **second** change if this ships as-is?

## E. Tests

12. What path patterns are untested?
13. What test would you add with highest value (describe; no need to implement)?

## Verdict

14. **PASS / PASS WITH NOTES / FAIL** — one sentence why.

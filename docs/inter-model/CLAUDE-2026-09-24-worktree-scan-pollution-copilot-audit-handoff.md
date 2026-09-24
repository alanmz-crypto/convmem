# Review Request: PR #334 — worktree/review-bundle scan pollution fix

**Date:** 2026-09-24
**Author:** Claude (Sonnet 5)
**For:** GitHub Copilot audit lane (safety/isolation review)
**Authorization:** Ryan, 2026-09-24 (verbal — "send it to review please")

---

## Resume state

| Field | Value |
|-------|--------|
| **State** | `BLOCKED_ON_RYAN` — pending Copilot audit-lane verdict; no implementation blocked |
| **Branch** | `fix/2026-09-24-worktree-scan-pollution-320-321` |
| **Tip SHA** | `a6171ab7f9b49dda5c363c312420861a8ea13120` |
| **Push status** | pushed to origin |
| **PR** | [`#334`](https://github.com/alanmz-crypto/convmem/pull/334) — open, mergeable, CI green, 0 reviews |
| **Ryan GATE** | Ryan decides merge after the audit-lane verdict |
| **Track A ingest** | pending at session close |

---

## What this is (not an implementation task)

This is a **review request**, not a build handoff. PR #334 was opened by a separate Claude Code session (not this one) on 2026-09-24. It is mechanically ready — all 6 CI checks pass, no merge conflicts — but has zero reviews. Ryan asked for this one specifically to be routed to formal review before merge, rather than merged on green CI alone.

**PR under review:** [`#334` — fix: stop repo-wide safety scans from failing on local scratch snapshots](https://github.com/alanmz-crypto/convmem/pull/334)

---

## Why the Copilot audit lane specifically

Per the HITL charter's role table, "Safety / isolation / code audit" routes to the **GitHub Copilot audit lane** as primary. This PR is in that category by content, not by size: it edits the **exclusion lists of three repo-wide safety scans** —

- `tests/test_shadow_writer_gate_c3.py`
- `tests/test_shadow_writer_coverage_scan.py`
- `tests/test_file_generation_read_path_inventory.py`

— adding `.worktrees/` and `review-bundles/` as skip-prefixes so gitignored local scratch directories stop tripping the same alarms a real legacy-write regression would. It also corrects two stale golden-eval expectations (Q08, Q10) unrelated to the scan change.

The risk category here is not "is the diff correct" (CI already confirms the stated tests pass) — it's "does this exclusion pattern stay narrow enough that a real legacy call inside a *tracked* path could never be swallowed by it." That's exactly the kind of check the requesting session can't fully certify of its own change, and exactly what an independent safety/isolation audit is for.

---

## What to check

1. **Exclusion-pattern precision.** Confirm `.worktrees/` and `review-bundles/` prefix matching in all three scans is anchored narrowly enough that no tracked, non-scratch path could ever match (e.g. no accidental substring match, no case where a legitimate future directory name could collide).
2. **The positive/negative controls the PR claims to add.** The PR body says controls were added "proving the exclusion can't blind the gate to a real legacy call in a tracked file." Verify those controls actually exercise that claim — i.e., a real legacy-write construct in a *tracked* (non-excluded) path still fails the scan post-change.
3. **The two golden-eval fixture changes (Q08, Q10).** Confirm these are genuinely stale-expectation corrections (system behavior changed and the test was wrong) rather than the test being loosened to match a regression. Q10 in particular changed from a hardcoded expected value to one derived from the checkout's own directory name — confirm that derivation can't be gamed or produce a false pass.
4. **Scope discipline.** The PR explicitly deferred the real Q02 ranking fix (issue #320) and a related pollution bug in `eval_corpus/r2b_v2` (filed as new issue #333) rather than bundling them in. Confirm nothing beyond the stated scope (scan exclusions + two eval fixture corrections) actually landed in the diff.
5. **General audit** — anything else that reads as weakening a safety/isolation control under cover of a "fix false failures" framing.

---

## What NOT to do

- No implementation edits — audit only; if changes are needed, issue findings and let Ryan route the fix.
- Do not merge PR #334 — Ryan decides after your verdict.
- Do not treat CI green as sufficient; the whole point of this routing is that CI passing does not establish the exclusion boundary is safe.

---

## Acceptance criteria

- [ ] Copilot audit lane issues a written verdict (PASS / PASS with findings / FAIL) on PR #334 at tip `a6171ab`
- [ ] Verdict explicitly addresses exclusion-pattern precision (item 1) and control sufficiency (item 2)
- [ ] Ryan decides merge/amend/drop based on the verdict

---

## Related files

| What | Path |
|------|------|
| PR under review | [`#334`](https://github.com/alanmz-crypto/convmem/pull/334) |
| Scans touched | `tests/test_shadow_writer_gate_c3.py`, `tests/test_shadow_writer_coverage_scan.py`, `tests/test_file_generation_read_path_inventory.py` |
| Golden eval fixtures touched | `tests/fixtures/golden_questions.jsonl`, `tests/test_eval_golden.py` |
| Related issues | #320 (partial — Q08/Q10 only), #321 (closed by this PR), #333 (filed, out of scope) |
| Governing charter for this routing | `TEAM-CHARTER-2026-07-06.md` §4 role table (Safety / isolation / code audit → GitHub Copilot audit lane) |

---

## Leaving / picking up checklist

**Author (leaving):**

- [x] This file committed on a pushed branch (this session's active branch)
- [ ] `LATEST.md` bullet at top with link and resume state
- [ ] `STATUS-*.md` Update Log line — not applicable, no active arc tracks this PR
- [x] Branch pushed (PR #334 itself already pushed by its originating session)

**Copilot audit lane (picking up):**

- [ ] Read this file before reviewing
- [ ] Audit PR #334 at tip `a6171ab7f9b49dda5c363c312420861a8ea13120`
- [ ] Issue written verdict; do not edit the PR directly unless Ryan separately requests it

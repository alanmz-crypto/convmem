# Review outputs (written 2026-10-31)

- `REVIEW.md` — verdict (revise before the pilot), highest-impact findings F01–F13, surviving claims, smallest workable architecture, human work that remains, corrections ready to apply.
- `CLAIM-RESULTS.csv` — 38 rows: the 26 checklist claims (C01–C26) and 12 added claims (A01–A12), each with verdict, confidence, baseline locator, source URL, retrieval date, supporting passage, qualification, smallest correction and test.
- `PILOT-GATES.md` — gates G0–G19 with prerequisites, input, expected output, pass/fail and the decision each resolves.
- `VERIFICATION-QUEUE.md` — V1–V18: evidence that could not be obtained and who can supply it.
- `evidence/SOURCE-PASSAGES.md` — verbatim passages from every source used, with retrieval method.
- `evidence/plaid_us_institution_coverage_2026-10-31.csv` — Plaid's full US directory as downloaded on 2026-10-31 (10,304 rows; generation stamp 2026-10-16T03:26:16.866Z, identical to the baseline's snapshot).
- `evidence/plaid-directory-extract-2026-10-31.csv` — the 19 rows whose names match the institutions in the plan.
- `FULL-REVIEW.md` — single-file bundle of all of the above in reading order (generated from the canonical files), for agents that want one path.
- `REVIEW-MANIFEST.json` — sizes and SHA-256 hashes of the files above.

Codex handoff notes: `docs/inter-model/CLAUDE-2026-10-31-arch-finance-adversarial-review-codex-handoff.md`.

`baseline/` is unchanged. The packet-level files (`REVIEW-STATE.json`, `REVIEW-BUNDLE-MANIFEST.json`, `review/README.txt`) were left untouched so that `VERIFY-BUNDLE.py` still passes; `review/README.txt` therefore still says no review has been performed, which is now outdated.

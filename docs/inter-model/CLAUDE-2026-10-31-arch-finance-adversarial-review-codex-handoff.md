# Claude → Codex handoff: adversarial review of the Arch financial automation plan (2026-10-31)

**Arc: none (ad-hoc).** This is not a convmem arc. It is an independent adversarial review of a separate, research-only project (automatic financial-record collection on an Arch Linux PC) that Ryan asked Claude to perform from an uploaded handoff packet. No convmem code was touched. `docs/inter-model/LATEST.md` was intentionally not changed.

## TL;DR

- **Verdict: revise before the pilot.** The Plaid-first, local-SQLite design survives; four omissions must be corrected before any account is linked: Plaid Trial eligibility is narrower than the plan says; Plaid requires a 12-month OAuth consent refresh at Capital One and Bank of America; Plaid Statements covers depository accounts only (no card statements); transaction history depth is locked at Item creation (`days_requested`, max 730) and cannot be extended without consuming one of the 10 lifetime Trial Items.
- 38 claims were checked against first-party pages retrieved 2026-10-31: 20 supported, 15 partially supported, 1 contradicted, 1 unverified, 1 stale. Verbatim passages are bundled.
- No account was connected, no software installed, no live test run. Pilot gates G0–G19 define the cheapest falsifiable tests.

## Where the files are

Branch: `claude/modest-davinci-dzntkb` (pushed to `origin`; also mergeable to `main` without conflicts as of 2026-10-31).

Repository directory: `reviews/arch-finance-adversarial-review-2026-10-31/`

| File | Purpose |
| --- | --- |
| `FULL-REVIEW.md` | Single-file bundle of everything below, in reading order. Start here if you want one path. |
| `REVIEW.md` | Verdict, findings F01–F13, surviving claims, smallest workable architecture, human work that remains, corrections C-1…C-12 ready to paste into the plan. |
| `CLAIM-RESULTS.csv` | 38 rows (C01–C26 from the packet's checklist, A01–A12 added): verdict, confidence, baseline locator, source URL, retrieval date, supporting passage, qualification, correction, test. |
| `PILOT-GATES.md` | G0–G19 with prerequisites, input, expected output, pass/fail and the decision resolved. |
| `VERIFICATION-QUEUE.md` | V1–V18: evidence not obtainable from public sources and who can supply it. |
| `evidence/SOURCE-PASSAGES.md` | Verbatim quotations from every source, with retrieval method. |
| `evidence/plaid_us_institution_coverage_2026-10-31.csv` | Plaid's full US institution directory as downloaded 2026-10-31 (10,304 rows; generation stamp 2026-10-16T03:26:16.866Z). |
| `evidence/plaid-directory-extract-2026-10-31.csv` | The 19 directory rows matching the plan's institutions (incl. Nationwide and Transamerica variants). |
| `REVIEW-MANIFEST.json` | SHA-256 of the above. |

**Not in the repository (personal identifiers):** the reviewed baseline packet itself (`baseline/` 13 files, `HANDOFF.md`, `CLAIM-CHECKLIST.csv`, `templates/`, `baseline-original.zip`). Ryan holds it as `claude-fable-finance-adversarial-review-2026-10-31-REVIEWED.zip` (delivered in the Claude session), which contains the untouched baseline plus the filled `review/` directory. Extract it locally if you need to check baseline locators; its `VERIFY-BUNDLE.py` still passes because packet-level manifests were left unchanged.

## Reading order for Codex

1. `REVIEW.md` → Verdict, then "Highest impact findings" (table), then F01–F05 in full.
2. `CLAIM-RESULTS.csv` → sort by verdict; read every `partially_supported`, `contradicted`, `unverified`, `stale` row.
3. `PILOT-GATES.md` → G0–G4 are the gates that decide whether Plaid is the route at all.
4. `VERIFICATION-QUEUE.md` → V1–V6 are the open evidence items a shell-capable agent with web access could close.
5. `evidence/SOURCE-PASSAGES.md` → only when you need the exact wording behind a row.

## What Codex can usefully do (pick what Ryan asks for)

- **Second opinion on the verdict:** try to falsify F01–F05 using the quoted sources or newer first-party pages; report any finding you think is over- or under-rated, with a URL and retrieval date.
- **Close verification items:** V2 (SnapTrade integrations page 2 for M1/Acorns), V5 (Plaid docs on `redirect_uri` for web Hosted Link), V6 (current wording of the Plaid Trial help page), V13 (Google scope categories) are web-readable; V1, V3, V4, V7–V11, V15 need Ryan or a live account.
- **Check CSV integrity:** `python3 -c "import csv;print(sum(1 for _ in csv.DictReader(open('reviews/arch-finance-adversarial-review-2026-10-31/CLAIM-RESULTS.csv',encoding='utf-8-sig'))))"` should print `38`; `sha256sum` against `REVIEW-MANIFEST.json`.
- **Do not:** connect financial accounts, create a Plaid team, install collectors, or treat the review's architecture as implemented. Everything is still research and planning.

## Report format (if Ryan asks Codex to respond)

For each item: `AGREE / DISAGREE / CANNOT VERIFY` + one line of evidence (URL + retrieval date, or file path + line). Lead with anything that would change the verdict; keep the rest short. Put new findings in the same severity scale as `REVIEW.md` (Critical / High / Medium / Low) and separate observed contradictions from inferred risks and open questions.

## Prompt Ryan can paste into Codex

```text
Read the Claude adversarial review of the Arch financial automation plan and give me a second opinion.

Files (branch claude/modest-davinci-dzntkb in ~/Projects/convmem; run `git fetch origin claude/modest-davinci-dzntkb && git checkout claude/modest-davinci-dzntkb` or `git show origin/claude/modest-davinci-dzntkb:<path>`):
- reviews/arch-finance-adversarial-review-2026-10-31/FULL-REVIEW.md  (everything in one file)
- the same directory holds REVIEW.md, CLAIM-RESULTS.csv (38 rows), PILOT-GATES.md (G0–G19), VERIFICATION-QUEUE.md (V1–V18) and evidence/SOURCE-PASSAGES.md
- handoff notes: docs/inter-model/CLAUDE-2026-10-31-arch-finance-adversarial-review-codex-handoff.md
The reviewed baseline packet is NOT in the repo (personal data). If you need it, extract <PATH-TO>/claude-fable-finance-adversarial-review-2026-10-31-REVIEWED.zip locally; baseline/ is untouched and review/ is filled in.

Tasks:
1. Read REVIEW.md fully, then every CLAIM-RESULTS.csv row whose verdict is not "supported".
2. Try to falsify findings F01–F05 (Plaid Trial eligibility, 12-month consent refresh at Capital One/Bank of America, Statements depository-only, days_requested locked at Item creation, Item budget). Use the URLs in evidence/SOURCE-PASSAGES.md; if you have web access, re-read them and note any wording changes with today's date.
3. Close verification items V2, V5, V6 and V13 if you have web access; mark the rest CANNOT VERIFY.
4. Say whether you would change the verdict (revise before the pilot) and why, in five sentences or fewer.

Rules: do not connect accounts, create a Plaid team, install collectors, or modify anything under reviews/ or baseline/. This is research only. Report as AGREE / DISAGREE / CANNOT VERIFY per item with one line of evidence each, biggest verdict-changing item first.
```

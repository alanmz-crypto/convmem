# Handoff: pre-PC work for the Arch financial automation project

**Arc: none (ad-hoc).** Written by Claude on 2026-10-31 after the adversarial review (`reviews/arch-finance-adversarial-review-2026-10-31/REVIEW.md`, verdict "revise before the pilot"). This guide covers only the work that can be done **before the Arch PC is available** and is meant to be executed by the account owner ("Owner") together with a lower-tier agent ("Agent"). When a task becomes complicated, stop and escalate to Claude using the protocol in §8. Nothing here connects a financial account, creates a Plaid Item, mints an OAuth token or runs a browser against a bank.

---

## 1. What this phase produces (definition of done)

By the end of this phase these artifacts exist, all in a **private** location (see §2), none in the public convmem repository:

| # | Artifact | Produced by | Done when |
| --- | --- | --- | --- |
| P1 | `PROGRESS.md` | Agent | Every task T0–T9 has a status line (NOT STARTED / IN PROGRESS / DONE / ESCALATED) with a date |
| P2 | `g0-plaid-eligibility.md` | Owner, recorded by Agent | Says PASS or FAIL with the date, the plan name shown on the Plaid dashboard, and "Items used: 0 of 10" |
| P3 | `registry.csv` | Owner + Agent | One row per real account; every workbook alias resolved; Item budget sheet totals at most 8 Items plus 2 reserve |
| P4 | `decisions.md` | Owner | Decisions D1–D5 in §6 recorded with a date |
| P5 | `Originals/` + `inventory.csv` | Owner (downloads) + Agent (inventory) | Every available statement/CSV listed with institution, period, doc type, original filename, download date; the oldest available year per institution recorded; V3 and V4 from the review answered |
| P6 | `google-cloud-setup.md` | Owner, recorded by Agent | Project exists, both scopes added, publishing status "In production", OAuth desktop client created, **no consent granted yet** |
| P7 | `plan-v2/` | Agent | Field guide and runbook copies with corrections C-1 to C-12 from REVIEW.md applied; baseline untouched |
| P8 | `finance-collector/` | Agent (scaffold) | uv project with schema, snapshot writer, sync loop, report, systemd templates and passing fixture tests; Sandbox smoke test passed if Sandbox keys exist |
| P9 | `codex-second-opinion.md` | Owner runs Codex | Codex's AGREE/DISAGREE/CANNOT VERIFY list filed next to the review |
| P10 | `ESCALATIONS/` | Agent | One file per escalation (§8), or an empty folder |

Order of work: T0 → T1 → T2 → T3 (T3 runs in the background for several evenings) → T4 → T5 → T6 → T7 → T8 → T9. T6 and T7 can run while T3 continues.

---

## 2. Where to work, and hard stops

- **Location.** Create a private Git repository (for example `finance-pilot`, private) or a local folder outside convmem. The convmem repository is **public**; never commit the registry, inventory, downloads, keys, or anything naming accounts into it.
- **Inputs the Agent needs.** The review packet zip (`claude-fable-finance-adversarial-review-2026-10-31-REVIEWED.zip`, extracted locally) or the convmem branch `claude/modest-davinci-dzntkb`. Key files: `review/REVIEW.md` (findings, architecture, corrections C-1…C-12), `review/PILOT-GATES.md` (gates G0–G19), `review/VERIFICATION-QUEUE.md` (open items V1–V18), `review/evidence/plaid-directory-extract-2026-10-31.csv` (Plaid institution ids), `baseline/FIELD-GUIDE.md`, `baseline/PC-setup-runbook.txt`, `baseline/account-connection-plan.csv`.
- **Hard stops for the Agent (never do these):**
  1. Never ask for, accept, print, or store a password, one-time code, API secret or token in chat, in a file in the repo, or in a log. Secrets go only into a local `.env` file the Owner creates, listed in `.gitignore`.
  2. Never create a Plaid Item, call any Plaid endpoint with Production keys, or click "Request Production access". Sandbox keys only, and only when the Owner has placed them in `.env`.
  3. Never grant Google OAuth consent or mint a token in this phase.
  4. Never run a browser, script or "automation" against any bank, broker, insurer or tax portal. Downloads are done by the Owner by hand.
  5. Never edit anything under `baseline/`; copies go under `plan-v2/`.
  6. Never commit to the public convmem repository.
  7. Never invent a fact about a provider. If the review's evidence does not cover a question, write it in `ESCALATIONS/` and move on.

---

## 3. Owner tasks

### T0 Plaid eligibility (gate G0), about 30 minutes, Owner only

Why first: the review's "$0 starting cost" depends on this, and it needs no PC.

1. Use the account owner's own email address (the person who owns the bank accounts owns the Plaid team).
2. Go to `dashboard.plaid.com/signup`, create a **new** team, verify the email.
3. On the dashboard home, look for the **Trial plan application** button. If the only option is "Request Production access", stop: the team is not Trial-eligible (see FAIL below).
4. Complete the Trial application: accept Plaid's Master Services Agreement and the security attestations, complete identity verification. Most applications approve automatically; manual review takes 2–3 business days.
5. When approved, read the dashboard: plan name, "Items used" (must say 0 of 10), and note that Sandbox client id and secret are visible under keys. **Do not use the Production secret for anything in this phase.**
6. Tell the Agent the outcome in words only (PASS or FAIL, date, Items used). The Agent writes `g0-plaid-eligibility.md`.

PASS: Trial approved, 0 of 10 Items. Then also decide D3 in §6 as "not needed".
FAIL (no Trial offered or refused): record the exact wording shown. Decision D3 becomes live: the pilot ledger switches to Actual Budget + SimpleFIN Bridge ($15/year) for bank data, and Plaid is revisited at paid pricing later. Escalate to Claude with the wording (§8), because the architecture changes.

Facts the Owner should know (from the review, verified 2026-10-31): Trial is only for new US/Canada teams created on or after 2026-04-15 with no prior Production or Limited Production access; upgrading later is one-way; removing an Item never frees a slot; duplicate links count.

### T1 Decisions (see §6), 20 minutes, Owner

Record D1–D5 in `decisions.md`. The Agent may draft the file with the options; the Owner picks.

### T2 Account registry and Item budget, 1–2 hours, Owner with Agent

The Cash Flow workbook is the inventory. Resolve every informal label ("Red Card", "Amazon card", "Ryan Card", "Credit Card 1/2" and similar) to a real issuer, a real login and an owner.

The Agent prepares `registry.csv` with these columns, pre-filled where the review already knows the answer; the Owner fills the rest:

```
alias_in_workbook,institution,plaid_institution_id,login_group,owner,account_type,product_route,history_ceiling,consent_refresh,item_priority,notes
```

- `login_group`: a short code for "which username/password at that institution". Two accounts under one login share a group. **The number of distinct login groups that will use Plaid is the Item count.**
- `plaid_institution_id` from `review/evidence/plaid-directory-extract-2026-10-31.csv`: Bank of America `ins_127989`; Capital One `ins_128026`; M1 Finance `ins_116960`; Robinhood `ins_54`; Acorns `ins_137662`; Raisin `ins_138348`; Venmo - Personal `ins_132083`; Transamerica - Life Insurance `ins_123709`. Nationwide Life has no entry (document-only). Unknown card issuers: leave blank and add to the escalation list if the issuer cannot be found in the full directory file.
- `history_ceiling` (what Plaid can return at first link): Capital One 90 days; Bank of America 18 months for checking/savings/mortgage, current cycle plus 11 cycles for cards; others up to 730 days, unverified.
- `consent_refresh`: "12 months" for Bank of America and Capital One; blank otherwise.
- `product_route`: one of `plaid_item`, `csv_or_statements`, `documents_only`.

Then the Agent adds an **Item budget** block at the bottom of `decisions.md`:

| Priority | Login group | Item? | Reason |
| --- | --- | --- | --- |
| 1 | Bank of America (deposits + cards if same login) | yes | pilot |
| 2 | Capital One | yes | pilot |
| 3 | M1 Finance | yes | investments |
| 4 | Robinhood | yes | investments |
| 5 | Acorns | yes/no | only if Later must be live |
| 6 | Raisin | decide D2 | balances only; statements cover it |
| 7 | Venmo | decide D2 | CSV statements cover it |
| 8 | Transamerica Life | decide D1 | slot cannot be reclaimed |
| reserve | — | 2 slots | repairs and surprises |

Done when: total "yes" ≤ 8, two reserve slots remain, and every workbook alias has a row. If the count exceeds 8 (for example a second owner's separate logins), stop and escalate: the plan must change before anything is linked.

### T3 Historical document harvest, several evenings, Owner (hand downloads only)

Download what each portal offers today; the PC collector will hash and index it later. Save every file **with its original filename** under `Originals/<Institution>/<YYYY>/`. Do not open and re-save PDFs (that changes the hash). The Agent maintains `inventory.csv`:

```
institution,account_alias,period_start,period_end,doc_type,original_filename,relative_path,downloaded_on,notes
```

Where to click (verified 2026-10-31 unless marked):

| Institution | Path | What to note while there |
| --- | --- | --- |
| Capital One (bank) | Sign in → account → "view statements"; up to 7 years online, paperless enrolment required; website transaction list shows 2 years | Oldest statement year; CSV date-range limit in the download dialog (closes V4) |
| Capital One (cards) | Same place; Capital One says it keeps up to seven years of card statements online | Same as above |
| Bank of America | Online Banking → Accounts → Statements & Documents → choose account and year; older copies up to 7 years via "Request statements" | The oldest year the selector offers (two BofA pages disagree: 18 months vs 6 years; this closes V3) |
| M1 Finance | Profile icon → Documents → Statements / Trade Confirmations / Tax Forms (3 years direct; older via M1 Client Success); Invest → portfolio → Activity → "Activity Summary" for CSV | Whether the CSV includes holdings and tax lots or only activity |
| Acorns | Profile & Settings → Documents and Statements → pick document type (statements appear mid-month) | Whether Later/IRA statements are separate documents |
| Raisin | Documents → statements and tax documents → Print/Save (monthly consolidated statement; closed deposits' interest is not in the current statement) | List of products shown on the latest statement summary |
| Venmo | Statements → download CSV (app or web); large files are emailed instead | Date range available |
| Transamerica Life | Log in → Policy/Certificate → Policy/Certificate Summary (cash value); annual statements and policy copy where offered | Which portal accepted the policy number (closes part of V9) |
| Nationwide Life | Log in → select policy → Document Center | What document types exist |
| IRS | Online account → Records and Status → transcripts; only the taxpayer may log in | Which transcript types and years are offered |

Hard stop: no screen scraping, no "download all" scripts, no third-party converters. Hand downloads only.

### T4 Google Cloud preparation, 15 minutes, Owner (Agent records)

Goal: remove the seven-day token expiry trap before the PC exists, without minting a token.

1. In the Google Cloud console, create a project (any name, for example `finance-collector`).
2. Enable the **Gmail API** and the **Google Drive API** for the project.
3. Configure the OAuth consent/branding screen: user type **External**; app name and support email are the Owner's.
4. Add exactly two scopes: `https://www.googleapis.com/auth/gmail.readonly` and `https://www.googleapis.com/auth/drive.readonly`. The console will label both **Restricted**; that is expected.
5. Set the publishing status to **In production** (the "Publish app" button). **Do not** submit for verification; personal use is an exception, and the "Google hasn't verified this app" screen is expected later.
6. Create an OAuth client of type **Desktop app**. Download the client JSON and keep it private (it is not committed anywhere; it is not yet a user token).
7. Stop here. The consent click and the refresh token happen on the PC in a later phase.

The Agent writes `google-cloud-setup.md` with the project name, the two scopes, the publishing status and the date. Console menu names change often; if a step cannot be found, describe what is on screen in an escalation note rather than guessing.

### T5 Codex second opinion, Owner runs it, 30 minutes

On the computer in use now, with the convmem repo cloned:

```bash
cd ~/Projects/convmem && git fetch origin claude/modest-davinci-dzntkb && git checkout claude/modest-davinci-dzntkb
codex -c 'model_reasoning_effort="high"' exec "$(sed -n '/^```text$/,/^```$/p' docs/inter-model/CLAUDE-2026-10-31-arch-finance-adversarial-review-codex-handoff.md | sed '1d;$d')"
```

File the output as `codex-second-opinion.md`. Any DISAGREE item goes into `ESCALATIONS/` for Claude.

---

## 4. Agent tasks

### T6 Corrected plan v2, 1–2 hours, Agent

Copy `baseline/FIELD-GUIDE.md`, `baseline/PC-setup-runbook.txt` and `baseline/account-connection-plan.csv` into `plan-v2/` and apply, verbatim, the twelve corrections listed under "Corrections ready to apply" in `review/REVIEW.md` (C-1 to C-12). Each correction names the file, the section or row, and the replacement text. Also apply:

- In `plan-v2/account-connection-plan.csv`, delete SnapTrade from any M1 or Acorns wording (SnapTrade's listing has neither; verified 2026-10-31). Keep SnapTrade only as the Robinhood read-only fallback.
- Add a line under the Google OAuth correction: "Both scopes are classified Restricted by Google; publish to In production without verification."
- Add a "Pre-PC phase" section pointing to this handoff and the artifacts in §1.

Record in `plan-v2/CHANGELOG.md` which correction went where. Do not paraphrase the corrections; if a target sentence cannot be found in the baseline file, note it and escalate rather than inventing a placement.

### T7 Owner checklist files, 30 minutes, Agent

Turn §3 into three printable checklists the Owner can tick: `checklists/registry.md`, `checklists/document-harvest.md`, `checklists/google-cloud.md`. Pre-fill the registry CSV template (§T2 columns, eight institution rows with ids and ceilings). No new facts; only what is in this handoff and the review.

### T8 Collector scaffold, 1–3 days, Agent (escalation expected)

Build the minimal collector described in `review/REVIEW.md` → "Smallest workable architecture", items 2–6, as a separate uv project `finance-collector/`. Work in this order and stop at the first ambiguity.

1. **Skeleton.** `uv init`, Python 3.12 pinned, dependencies `plaid-python`, `typer`, `pytest`; `.gitignore` with `.env`, `*.sqlite`, `FeedSnapshots/`, `Originals/`, `Staging/`. Three commands: `link`, `sync`, `report` (empty stubs first). `link` will serve a one-page Link web SDK page on localhost and receive the public token from the page; Hosted Link is the alternate.
2. **Schema.** `schema.sql` with tables `items`, `accounts`, `raw_responses`, `transactions`, `investment_transactions`, `holdings_snapshots`, `balances_snapshots`, `documents`, `overrides`, `transfer_links`, `exceptions`, exactly as listed in REVIEW.md item 3, including: `transactions.transaction_id` primary key; `pending_transaction_id`; `removed_at`; `items.consent_expiration_time`; `overrides` applied after every import; `transfer_links.status` in (`candidate`, `confirmed`, `rejected`).
3. **Snapshot writer.** Every API response is written to `FeedSnapshots/<item_id>/<endpoint>/<UTC timestamp>.json` **before** parsing. A full rebuild of the database from snapshots must be possible (`sync --rebuild`).
4. **Sync loop.** `/transactions/sync` with the stored cursor per Item; apply `added`, `modified`, `removed`; link pending to posted via `pending_transaction_id`; store the `balances` object with its as-of time; call `/item/get` and store `consent_expiration_time`; raise an exception row 30 days before expiry with the text "use update mode, do not re-link".
5. **Fixtures and tests** (no network): write JSON fixtures from the sample responses in Plaid's documentation and tests for G4 (two syncs, zero duplicates; rebuild equals incremental), G5 (pending then posted = one logical transaction), G6 (two same-amount same-day transfers stay candidates), G11 (an override survives re-import and rebuild). G7 (statement arithmetic) needs a hand-made statement fixture; attempt it, escalate if unsure.
6. **Report.** `report` writes `Reports/status.md`: per Item last success, consent expiry, oldest transaction per account, missing periods, exception list.
7. **systemd templates.** `deploy/finance-sync.service` and `deploy/finance-sync.timer` (`OnCalendar=daily`, `Persistent=true`), plus a README line about `loginctl enable-linger` and secrets in 0600 files. Templates only; nothing installed.
8. **Sandbox smoke test, only if the Owner has put Sandbox keys in `.env`.** Use `/sandbox/public_token/create` with `ins_109508` and products `transactions`, exchange it, run `sync` twice, run `report`. Then try `link` in Sandbox two ways, no `redirect_uri` in either: (A) `/link/token/create` with `products: ["transactions"]`, `transactions.days_requested=730`, `required_if_supported_products: ["liabilities"]`, serve the local Link page, complete the Sandbox flow at "First Platypus Bank - OAuth" (`ins_129644`) with Plaid's test credentials in the pop-up, receive the public token on localhost and exchange it; (B) the same token request with a `hosted_link` object, open `hosted_link_url`, complete the flow, poll `/link/token/get`, exchange. Record which worked in `PROGRESS.md`. Sandbox Items do not count against the Trial limit; Production is never touched here.

Escalate (do not improvise) at: any Plaid error about `redirect_uri` or Hosted Link; any uncertainty about sign conventions for investments; the transfer-matching rules; statement reconciliation; anything that would store a secret.

### T9 Progress file and handback, continuous, Agent

Keep `PROGRESS.md` current after every work session: task, status, date, artifact path, one line of what happened. When the phase is done, or when an escalation blocks the next task, write `HANDBACK.md` (what is done, what is blocked, the exact question) so Claude can resume from one file.

---

## 5. Facts the Agent may rely on without re-checking (from the review, retrieved 2026-10-31)

- Plaid Trial: 10 lifetime Production Items; `/item/remove` does not free slots; duplicates count; products include Transactions, Balance, Liabilities, Investments, Statements; immediate OAuth access to Bank of America and Capital One; no support cases on Trial.
- `transactions.days_requested` defaults to 90, max 730, and is fixed when Transactions is first initialized on an Item (at Link, or on the first `/transactions/sync` for an Item that adds Transactions later). Put only the must-have product in `products`; use `required_if_supported_products` or `optional_products` for the others so Link does not filter institutions.
- Capital One: 90 days of history, no pending transactions, `/transactions/refresh` unsupported on card-only Items, consent refresh every 12 months, no Plaid Statements support.
- Bank of America: 18 months (deposits/mortgage) or current plus 11 cycles (cards); consent refresh every 12 months (new API); Plaid Statements for checking/savings only.
- Plaid Statements: depository accounts only, up to two years.
- Investments via Plaid: sales negative, purchases positive; `buy`/`contribution` rows are entirely outflows; `tax_lots` may be empty; investment transactions up to 24 months.
- Onboarding without a public URL: the plain Link web SDK on desktop needs no redirect URI (the bank opens in a pop-up); Hosted Link also needs none for desktop sessions (`redirect_uri` only when `is_mobile_app` is true), its public token is available from `/link/token/get` for six hours, default link lifetime 30 minutes. Plaid prefers the SDK route.
- Google: External app left in Testing gets 7-day tokens; In production without verification is allowed for personal use; `gmail.readonly` and `drive.readonly` are Restricted scopes; Drive export of native files is limited to 10 MB.
- SimpleFIN Bridge: $1.50/month or $15/year plus tax; 25 institutions; 24 requests/day; 90-day request window; Actual Budget pulls at most 90 days initially; upstream MX.
- SnapTrade Personal: free, 20 connections, Robinhood read-only; no M1 Finance or Acorns in its listing.
- systemd: `Persistent=true` works only with `OnCalendar=`; user timers cannot wake a suspended PC; lingering needed for logged-out runs.

Anything not in this list or in `review/REVIEW.md` is unknown and goes to an escalation note.

---

## 6. Decisions for the Owner (record in `decisions.md`)

- **D1 Transamerica Life:** spend a Plaid Item on the Life entry (fields unknown, slot cannot be reclaimed) or keep it document-only for the pilot. Default recommendation: document-only until the eight-Item budget is proven.
- **D2 Raisin and Venmo:** Items or CSV/statement collection. Default: CSV/statements during the pilot; Items later if slots remain.
- **D3 Fallback if T0 fails:** Actual Budget + SimpleFIN Bridge as the bank ledger. Default: yes, and escalate for the revised architecture.
- **D4 Private home for the finance project:** private Git repository name, or local-only folder with backups.
- **D5 Backup target:** external disk or restic repository for `Originals/` and the database; buy nothing else yet (no GPU before gate G19).

---

## 7. What must wait for the PC

Minting the Google refresh token; storing Plaid Production tokens; linking the first two Items (Bank of America, Capital One) with `days_requested=730`; the systemd timer and reboot tests (G10); the Drive export fidelity check against the real workbook (G13) if not done earlier by hand; the OCR benchmark (G19). Hardware inspection decides the Ollama backend only after G19.

---

## 8. Escalation protocol (how to come back to Claude)

Write one file per issue: `ESCALATIONS/YYYY-MM-DD-<task-id>-<short-slug>.md` containing:

1. Task id and goal in one sentence.
2. What was tried, as commands or clicks, and the exact output or error text (secrets redacted as `<REDACTED>`).
3. The decision or design question, phrased so it can be answered yes/no or by choosing between listed options.
4. Links to the relevant files (`registry.csv` row, fixture, test).

Then paste this into a Claude session with the convmem repo and the review packet available:

```text
Resume the Arch financial automation project. Read docs/inter-model/CLAUDE-2026-10-31-arch-finance-pre-pc-work-handoff.md, then PROGRESS.md and every file in ESCALATIONS/ in the private project folder I will point you to. Answer each escalation in order, update the handoff only where the facts changed, and tell me which task resumes next. Do not connect accounts or mint tokens.
```

Escalate immediately, without further attempts, when: T0 fails; the Item count exceeds 8; a Plaid or Google error mentions verification, redirect URIs or consent; any task would require typing a credential into the agent; the Agent's answer would contradict `review/REVIEW.md`; or a source page has changed from what the review quotes.

---

## 9. Prompt for the lower-tier agent (paste as the first message)

```text
You are the working agent for the pre-PC phase of a personal financial-records project. Your guide is docs/inter-model/CLAUDE-2026-10-31-arch-finance-pre-pc-work-handoff.md (also present as review/PRE-PC-WORK-HANDOFF.md in the review packet). Read it completely before doing anything, then read review/REVIEW.md sections "Verdict", "Smallest workable architecture" and "Corrections ready to apply".

Working location: <PRIVATE PROJECT FOLDER OR PRIVATE REPO>. Never write anything from this project into the public convmem repository.

Hard rules (no exceptions, no clever workarounds):
- Never ask for, accept, print or store passwords, one-time codes, API keys or tokens. Secrets exist only in a local .env that the owner creates and that is gitignored.
- Never create a Plaid Item, never use Production keys, never click "Request Production access". Sandbox keys only, and only if they are already in .env.
- Never grant Google OAuth consent or mint a token.
- Never run a browser, scraper or script against any bank, broker, insurer or tax site. The owner downloads documents by hand.
- Never modify baseline/ files; copies go to plan-v2/.
- Never invent a provider fact. If the guide's §5 or review/REVIEW.md does not state it, write an escalation note instead.

Work the tasks in this order and keep PROGRESS.md current after each session:
T0 (record the owner's Plaid eligibility result as they report it), T1 (draft decisions.md with options D1–D5 for the owner to pick), T2 (registry.csv template, then help the owner resolve every alias and compute the Item budget), T3 (maintain inventory.csv as the owner downloads documents; log the oldest-year and CSV-limit facts they report), T4 (record google-cloud-setup.md), T6 (plan-v2 with corrections C-1 to C-12 applied verbatim), T7 (three owner checklists), T8 (collector scaffold: skeleton, schema, snapshot writer, sync loop, fixture tests for G4/G5/G6/G11, report, systemd templates; Sandbox smoke test only if Sandbox keys exist), T9 (HANDBACK.md when done or blocked).

Stop and write ESCALATIONS/<date>-<task>-<slug>.md, then move to the next independent task, whenever: T0 fails; the Item budget exceeds 8; any Plaid or Google error mentions verification, redirect URIs or consent; a task would need a credential; you are unsure about investment sign conventions, transfer matching or statement reconciliation; or something contradicts review/REVIEW.md. Each escalation must contain the exact command or click path tried, the exact output with secrets redacted, and a yes/no or multiple-choice question.

Report at the end of every session in this format: tasks touched with status, artifacts written with paths, open escalations, and the single next action.
```

---

## 10. Resume prompt for Claude (for the Owner, when the phase is done or blocked)

```text
Resume the Arch financial automation project from the pre-PC handoff. The private project folder is at <PATH>. Read HANDBACK.md, PROGRESS.md, decisions.md, registry.csv, inventory.csv and every ESCALATIONS/ file. Then: (1) close each escalation with a decision and evidence, (2) verify the Item budget and the registry against review/REVIEW.md, (3) review finance-collector/ against the schema invariants and gates G4–G7 and G11, and (4) write the first-PC-session runbook (G1, G2, G3, G9, G10, G12) using plan-v2. Do not connect accounts or mint tokens.
```

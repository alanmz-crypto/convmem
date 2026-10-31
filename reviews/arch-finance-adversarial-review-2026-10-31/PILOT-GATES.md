# Pilot gates for the Arch financial automation proposal

Prepared 2026-10-31 as part of the adversarial review. These are cheap, falsifiable tests to run on the Arch PC before committing to the full build. None was executed during the review; no account was connected. Run them in order; each gate names the decision it resolves. "Owner" means the account owner, who performs every bank login.

Scope rules for the pilot: two Plaid Items only (Bank of America, Capital One), one complete checking/savings statement cycle, the minimal stack (Python project, SQLite, rclone, Gmail script, systemd timer). No OpenClaw, Ollama, Docling or Paperless-ngx until G0–G12 pass.

## G0 Plaid Trial eligibility

- Prerequisites: the owner's own email address; no prior Plaid dashboard team under that identity.
- Input or trial: create a new Plaid Dashboard team; confirm the Trial plan application appears; submit it (MSA, attestations, identity verification). Cost: about 30 minutes, $0.
- Expected output: approval email; Dashboard shows Trial plan with 0 of 10 Items used; Production keys available.
- Pass/fail: pass if Trial is approved and Production client id/secret exist. Fail if the Dashboard offers only a Production application (team predates 2026-04-15 or has prior Production/Limited Production access) or approval is refused.
- Decision resolved: Plaid is the primary route ($0) versus the fallback ledger (SimpleFIN + Actual Budget, $15/year) for bank data with Plaid considered later at paid pricing.

## G1 Hosted Link onboarding from the local PC

- Prerequisites: G0; the `link` command implemented; `transactions.days_requested=730` and products `transactions,liabilities` in the request; no webhook.
- Input or trial: call `/link/token/create` with a `hosted_link` object (`url_lifetime_seconds` set to 3600). Try first without `redirect_uri`; if Production rejects the request, add one static HTTPS URL that the owner controls and retry. Open `hosted_link_url` in the owner's normal browser; complete Bank of America OAuth. Poll `/link/token/get` every 30 seconds; exchange the public token.
- Expected output: `link_sessions[].results.item_add_results[].public_token` within the session; `/item/public_token/exchange` succeeds; `/accounts/get` lists the expected accounts.
- Pass/fail: pass if an access token is obtained without any always-on public service. Record whether `redirect_uri` was required. Fail if the session cannot complete (then test the web Link SDK on a static HTTPS page as the fallback before abandoning Plaid).
- Decision resolved: HANDOFF priority question 1 (whether the first connections can actually be made from a local PC).

## G2 Item accounting

- Prerequisites: G1.
- Input or trial: after linking Bank of America and Capital One, read the Dashboard Items count and `/item/get` for both. Attempt nothing else. Separately, write the Item budget table (eight institutions, reserve two) into PROJECT-STATE.json.
- Expected output: Dashboard shows exactly 2 Items used; both `/item/get` responses include `consent_expiration_time` roughly 12 months out.
- Pass/fail: pass if the count is 2 and expirations are recorded. Fail if any link created more than one Item (duplicate) or if a second owner login was needed for any account (then the budget must be recomputed before further links).
- Decision resolved: whether the remaining six planned institutions fit within 10 lifetime Items.

## G3 Coverage, fields and history depth per Item

- Prerequisites: G1.
- Input or trial: run `sync` once; for each account record type/subtype, oldest transaction date, pending count, balance timestamp; call `/statements/list` on the Bank of America Item (expect depository accounts only) and `/liabilities/get` for cards.
- Expected output: Bank of America deposits oldest date about 18 months back; Bank of America cards about 12 statement cycles; Capital One about 90 days; statements listed only for checking/savings; liabilities present for cards with no transaction detail.
- Pass/fail: pass if observed ceilings are within one cycle of the documented ones and the account list matches the owner's registry. Fail if an expected account or sub-account is missing (record it as a coverage gap, not a defect of the plan).
- Decision resolved: the backfill plan per account (which months must come from portal statements).

## G4 Repeat import creates no duplicates

- Prerequisites: G3; SQLite schema with `transactions.transaction_id` as primary key.
- Input or trial: run `sync` twice within an hour with the stored cursor; then run a full re-import of all saved `FeedSnapshots` from scratch into an empty database and compare.
- Expected output: identical row counts and identical per-account sums after the second run; the rebuilt database equals the incremental one on (account, transaction_id, amount, date).
- Pass/fail: pass if zero new rows on the second run and zero differences on rebuild. Fail otherwise.
- Decision resolved: idempotent ingestion (FIELD-GUIDE completion criterion "Repeated imports do not duplicate records").

## G5 Pending to posted handling

- Prerequisites: G4; a Bank of America debit card purchase made the day before the test.
- Input or trial: sync on day 1 (pending row present), sync on day 2 or 3 (posted row appears with `pending_transaction_id` set and the pending row in `removed`). For Capital One, confirm no pending rows ever appear and that `/transactions/refresh` on a card-only Item returns `PRODUCTS_NOT_SUPPORTED` (do not rely on it).
- Expected output: one logical transaction with both ids linked, `removed_at` set on the pending row, amounts reconciled (a tip adjustment changes the amount and must be shown as a modification, not a second purchase).
- Pass/fail: pass if the ledger shows one spend, not two, and the Capital One behaviour is recorded in the registry flags. Fail if a pending/posted pair survives as two rows.
- Decision resolved: the identity model for feed records.

## G6 Ambiguous same-amount transfers

- Prerequisites: G4; two transfers of the same amount on the same day between the owner's accounts (or a synthetic pair inserted into a test copy of the database).
- Input or trial: run the transfer matcher.
- Expected output: both pairs appear as candidates in `transfer_links` with status `candidate`; neither is auto-confirmed; one exception row asks the owner to pick.
- Pass/fail: pass if no candidate with more than one possible counterpart is confirmed automatically and a single-candidate pair is confirmed. Fail if the matcher guesses.
- Decision resolved: transfer and card-payment matching policy (never count the same money twice).

## G7 Statement balance reconciliation

- Prerequisites: G4; one complete Bank of America checking statement PDF (API Statements or portal download).
- Input or trial: parse opening balance, closing balance, total credits and debits from the PDF with a deterministic parser; compute opening + credits − debits from ledger rows dated inside the statement period; compare with the statement closing balance and with a dated `/accounts/balance/get` value.
- Expected output: zero difference to the cent on the statement; any difference to the real-time balance explained by transactions after the period end.
- Pass/fail: pass if the statement reconciles exactly or every residual is itemized as an exception with the missing or extra row identified. Fail if an unexplained residual remains.
- Decision resolved: the acceptance check that gates automatic acceptance of a cycle.

## G8 Partial history is visible, not silent

- Prerequisites: G3.
- Input or trial: generate the coverage report; for Capital One mark every month older than 90 days as "missing: needs statement"; drop one month's statement from Originals and re-run.
- Expected output: the report lists missing periods per account; removing a statement produces a visible gap.
- Pass/fail: pass if missing months are listed and a removed statement reappears as a gap. Fail if the report shows the account as complete.
- Decision resolved: FIELD-GUIDE criterion "Missing history and failed connections are visible".

## G9 Expired or revoked authorization is surfaced

- Prerequisites: G2.
- Input or trial: in Bank of America's own third-party access settings, revoke the Plaid connection (or wait for an `ITEM_LOGIN_REQUIRED` error, whichever is cheaper); run `sync`; also set a test Item's stored `consent_expiration_time` to 20 days ahead in the database.
- Expected output: the report shows the Item as "login required, repair with update mode" and a second exception "consent expires in 20 days".
- Pass/fail: pass if both conditions are visible within one scheduled run and the repair instruction says update mode, not re-link. Repair via update mode and confirm the Items count did not change (ties to G2).
- Decision resolved: recurring-auth handling without webhooks.

## G10 Recovery after reboot and power-off

- Prerequisites: systemd user timer installed with `OnCalendar=daily` and `Persistent=true`; `loginctl enable-linger` set; secrets in 0600 files or `systemd-creds`.
- Input or trial: cold boot the PC and do not log into the desktop; wait past the scheduled time; check `journalctl --user -u <service>`. Then power off for 48 hours (or set the clock), boot, and confirm the missed run executes once.
- Expected output: the job ran at boot without a graphical login, read its secrets, synced, wrote the report; after the 48-hour gap exactly one catch-up run occurred and the cursor advanced.
- Pass/fail: pass on both. Fail if the job needs a desktop login (keyring) or runs more than once.
- Decision resolved: credential storage and scheduler design.

## G11 Manual corrections survive re-import

- Prerequisites: G4; `overrides` table.
- Input or trial: correct one category and one transfer link by hand; re-run `sync` and a full rebuild from snapshots.
- Expected output: both corrections persist, with their evidence note; if a later feed update changes the underlying row, the report shows a conflict instead of discarding the correction.
- Pass/fail: pass if corrections persist across incremental and rebuild runs. Fail if either run reverts them.
- Decision resolved: FIELD-GUIDE criterion "Manual corrections survive reruns".

## G12 Google OAuth longevity

- Prerequisites: External OAuth app published to "In production" without verification; scopes `gmail.readonly` and `drive.readonly`; one consent by the owner.
- Input or trial: run the Drive and Gmail collectors daily for nine days.
- Expected output: no re-consent prompt; refresh succeeds on day 8 and day 9.
- Pass/fail: pass if day 9 succeeds. Fail if a 7-day expiry appears (the app is still in Testing, or the scopes changed).
- Decision resolved: HANDOFF priority question 5 (Google OAuth expiry).

## G13 Drive export fidelity

- Prerequisites: rclone configured with export formats `xlsx` (and `csv` for a per-tab values copy if used).
- Input or trial: export the Cash Flow workbook; record Drive file id, modifiedTime and md5; open the xlsx; count tabs; compare three known cells (one formula, one value, one date) against the live sheet; confirm the export is under 10 MB.
- Expected output: all tabs present; formulas preserved in xlsx; values match; file under the export limit.
- Pass/fail: pass if tab count and three cells match and a second export with no change is detected as unchanged (same md5). Fail if tabs are missing or the size limit triggers.
- Decision resolved: HANDOFF priority question on Drive export and version identity.

## G14 Card statement acquisition route

- Prerequisites: G3 (knowing which statements the API cannot supply).
- Input or trial: obtain one Bank of America card statement and one Capital One statement for the pilot cycle. First by hand into `Staging/` (time it). Optionally, a plain Playwright script against a dedicated browser profile (no OpenClaw, no other logins) with an owner-attended first login; run it once.
- Expected output: PDFs land in `Originals/<institution>/<period>.pdf` with hashes recorded; the manual route takes minutes; the scripted route either completes or hits MFA/anti-bot.
- Pass/fail: manual route always passes if the files arrive. The scripted route passes only after three consecutive monthly runs without intervention; until then it stays "manual".
- Decision resolved: whether browser automation earns a place in the architecture.

## G15 Investment feed semantics (M1 or Robinhood, third Item)

- Prerequisites: G2 budget allows a third Item.
- Input or trial: link one brokerage with `investments`; compare `/investments/holdings/get` total value with the broker's portal on the same day; inspect one `buy`/`contribution` transaction; check whether `tax_lots` is empty.
- Expected output: totals match within that day's price movement; the contribution row is split into a cash deposit and a purchase in the ledger; lot availability recorded.
- Pass/fail: pass if signs are normalized (inflows positive in the user's ledger) and the holdings total matches. Fail if contributions appear only as outflows.
- Decision resolved: investment normalization rules and whether the broker's CSV is still needed for lots.

## G16 Acorns sub-accounts (if linked)

- Input or trial: after linking, list accounts and check that Invest, Later (IRA) and any Checking account each appear with a subtype.
- Pass/fail: pass only if Later appears; otherwise Later stays on statement collection (Acorns says not every account shows up in every third-party app).

## G17 Raisin products (if linked)

- Input or trial: compare the accounts returned with the products listed on the current Raisin statement summary, including any closed deposit from the year.
- Pass/fail: pass if every open product appears as its own account with the right balance; closed deposits are reconciled from statements and tax documents, not the feed.

## G18 Transamerica Life values (if linked)

- Input or trial: link the Life entry; record every returned field; compare with the policy portal's Policy/Certificate Summary (cash value) and the latest annual statement (death benefit, loan, premiums).
- Pass/fail: pass if the feed's values can be mapped unambiguously to named policy fields; otherwise the policy is document-only and the Item slot should be released from the budget (it cannot be reclaimed, so decide before linking).

## G19 OCR and extraction benchmark (deferred, after G0–G12)

- Input or trial: 20 representative documents (10 English, 10 Thai; statements, receipts, a policy statement) with hand-recorded expected values for 5 fields each; run deterministic parsing, then Docling with EasyOCR Thai, on the actual PC (CPU first).
- Expected output: per-field accuracy and runtime per page.
- Pass/fail: pass for automatic acceptance only when amount/date fields are 100 percent correct on the set and every accepted document passes an arithmetic check; anything lower goes to the exception queue.
- Decision resolved: whether local OCR/LLM extraction is worth installing and whether a GPU purchase is justified.

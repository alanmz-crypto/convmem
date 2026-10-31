# Full adversarial review bundle — Arch financial automation handoff (2026-10-31)

Single-file concatenation of every review output so another agent can read the whole review from one path. The separate files in this directory are the canonical copies; this bundle is generated from them. The reviewed baseline packet (`baseline/`, HANDOFF.md, CLAIM-CHECKLIST.csv) is deliberately not in the repository because it carries personal identifiers; it is in the `claude-fable-finance-adversarial-review-2026-10-31-REVIEWED.zip` that was delivered in the Claude session, with `review/` already filled in.

Contents: 1. INDEX · 2. REVIEW · 3. PILOT-GATES · 4. VERIFICATION-QUEUE · 5. CLAIM-RESULTS · 6. SOURCE-PASSAGES

---



---

# Part 1: INDEX

_Source file: `INDEX.md`_

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


---

# Part 2: REVIEW

_Source file: `REVIEW.md`_

# Adversarial review of the Arch financial automation proposal

Review date: 2026-10-31
Reviewer: Claude, acting as the independent adversarial reviewer requested in CLAUDE-START-HERE.txt
Baseline archive SHA-256: 9eb49893ff57e239f69b998b57a9a0a19919af4d19dd9eb3eed02c2288b6cc3c (verified; the 13 members of baseline-original.zip are byte-identical to baseline/, and all 25 REVIEW-BUNDLE-MANIFEST.json entries and 12 FILE-MANIFEST.json entries match)
External source access and limits: the review sandbox could not open most websites directly (the outbound proxy refused plaid.com, support.plaid.com, Google, OpenClaw, institution and ArchWiki hosts). All external evidence below was retrieved on 2026-10-31 through two extraction services (Tavily page extraction and a TinyFish real-browser fetch) and, for GitHub-hosted documentation sources, direct raw.githubusercontent.com downloads. Verbatim passages, URLs and the retrieval method for every source are in `review/evidence/SOURCE-PASSAGES.md`. Plaid's institution directory CSV was downloaded in full (10,304 rows) and is saved as `review/evidence/plaid_us_institution_coverage_2026-10-31.csv`. Not accessible: the private ChatGPT pages, the Cash Flow workbook and source statements (not in the packet, not inspected), the Paperless-ngx documentation site (bot-blocked; its Markdown source on GitHub was read instead), page 2 of SnapTrade's integrations listing (rate-limited), and Capital One's credit-card CSV help page (404). No financial account was connected, no Plaid dashboard was created and no software was installed.

## Verdict

**Revise before the pilot.**

Most of the baseline's factual claims survive: all eight Plaid directory rows reproduce exactly from the current directory file, the Capital One 90-day limit, the Trial plan's 10-Item cap, SimpleFIN pricing and quotas, SnapTrade Personal terms, Tiller pricing and Excel behaviour, Google's seven-day Testing-mode token expiry and OpenClaw's download/existing-session limits are all quoted correctly from first-party pages. The Plaid-first, local-SQLite design is sound. However, four omissions change the plan materially and should be corrected before any account is linked: (1) Plaid's Trial is narrower than "eligible personal developers": it is only for new Plaid teams created on or after 2026-04-15 with no prior Production or Limited Production access, and the live help page says support cases are only available on paid plans; (2) Plaid documents a mandatory OAuth consent refresh every 12 months at both Capital One and Bank of America, which is recurring attended work the plan never mentions; (3) Plaid Statements covers only depository accounts, so the card-statement archive promised for Bank of America (and any Capital One statement) cannot come from the API; (4) transaction history depth is fixed at Item creation and cannot be extended later without consuming another of the 10 lifetime Items. With these corrections, an explicit Item budget, and the pilot gates in PILOT-GATES.md, a limited pilot (two Items, one statement cycle) is justified. The proposed tool stack should also be cut for the pilot: OpenClaw, Ollama, Docling and Paperless-ngx add rolling-release maintenance without being needed to pass any pilot gate.

## Highest impact findings

| ID | Severity | Confidence | Evidence status | Finding and practical impact |
| --- | --- | --- | --- | --- |
| F01 | High | High | Observed contradiction (eligibility narrower than stated) | Plaid Trial: only new US/CA Plaid teams created on or after 2026-04-15 without existing Production/Limited Production access; MSA and security attestations; identity verification; no support cases on Trial (live page). The "$0 starting cost" rests on this. |
| F02 | High | High | Observed omission | Plaid requires OAuth consent refresh every 12 months at Capital One and Bank of America (new API). Each refresh is an attended update-mode Link session; missing it disconnects the Item. Not in the plan's human-work list. |
| F03 | High | High | Observed contradiction | Plaid Statements supports only depository accounts. The account plan's "PDF statements" for Bank of America cannot include card statements; Capital One has no Statements support at all. Card statements fall to the browser/manual route. |
| F04 | High | High | Observed omission | Transactions history depth (`days_requested`, max 730) is locked at Item creation and "cannot be extended except by deleting and then recreating the Item", which costs a Trial Item. The runbook never says to set 730 on the first link. |
| F05 | High | High | Supported design risk | 10 lifetime Items versus 8 directory institutions, unknown card issuers, possible second-owner logins and duplicate links leaves at most two spare slots. The plan says "count Items" but gives no budget or no-re-link rule. |
| F06 | Medium | High | Observed omission | Capital One via Plaid: no pending transactions; `/transactions/refresh` unsupported for card-only Items; statements flag 0. Reconciliation and freshness logic must treat Capital One differently from Bank of America. |
| F07 | Medium | Medium | Unresolved question | Hosted Link plus `/link/token/get` is documented (public token available for six hours, no webhook required), but Plaid's docs say Hosted Link should be used only when the SDKs cannot be used, the default link lifetime is 30 minutes, and whether a Production HTTPS `redirect_uri` is still required for a web Hosted Link session is not stated. Not demonstrated. |
| F08 | Medium | High | Supported design risk | Google OAuth: the plan says "configure appropriately" but never states the fix. Publishing the External app to "In production" without verification (personal-use exception) removes the seven-day expiry; Testing status expires authorizations after seven days. |
| F09 | Medium | High | Observed omission | Plaid-specific reconciliation facts are missing: investment inflows are negative and `buy`/`contribution` is wholly an outflow; `/transactions/sync` balances are as-of the last scheduled pull, not real time; Bank of America history is 18 months (deposits) or 12 statement cycles (cards), not 24 months. |
| F10 | Medium | High | Supported design risk (unnecessary complexity) | Nine components (Plaid, SimpleFIN/Actual, SnapTrade, Docling, Ollama, OpenClaw, Paperless-ngx via Docker, SQLite, dashboard) with overlapping stores. None of OpenClaw, Ollama, Docling or Paperless is needed to pass a pilot gate; each adds rolling-Arch maintenance (Node 24/26, Docker, GPU backends). |
| F11 | Medium | High | Supported design risk | Browser route: managed OpenClaw browsers are headless by default, manual login needs a desktop session and full Chromium, automated logins "often trigger anti-bot defenses and can lock the account", and a signed-in browser profile gives the model account-wide access. Unattended portal downloads are unproven for every institution. |
| F12 | Medium | High | Supported design risk | Credentials after reboot: user timers with `Persistent=true` only catch up when the PC is powered on; `WakeSystem=` is privileged (system manager only); desktop keyrings are normally unlocked at graphical login, so a lingering service started at boot may not reach them. The plan flags the question but no credential storage design is chosen. |
| F13 | Low | High | Observed (evidence quality) | The research log mixes Windows-era queries (WSL2, Task Scheduler) with the later Arch follow-up; the Plaid Trial help page changed wording between two fetches on the same day; no raw page captures are bundled. Claims were nevertheless traceable and, where checked, accurate. |

## Detailed findings

### F01 Plaid Trial eligibility is narrower than the baseline states

- Severity and confidence: High; high.
- Evidence status: observed contradiction with the baseline's wording; the baseline's own caveat ("Eligibility also depends on whether the developer already has a Plaid production account") is incomplete.
- Baseline file and exact section, row or quote: `PC-finance-automation-report.html` §2 "Plaid now explicitly offers real production data to eligible new US/Canadian developers through a free Trial"; `FIELD-GUIDE.md` > Connection facts #2 "supports real accounts for eligible personal developers"; `PC-setup-runbook.txt` INITIAL COSTS "Plaid Trial can be free if eligible".
- Failing scenario or counterevidence: the account owner (or whoever will own the Plaid team) already created a Plaid dashboard team before 2026-04-15, or ever applied for Production or Limited Production. Plaid: "If your team has a pending or approved Production application, or existing Limited Production access, the Trial plan is not available — there is currently no self-service way to switch." The live help page (TinyFish fetch, 2026-10-31) also says "Trial plan customers can ask Bill, Plaid's AI assistant. Support cases are available only on paid plans." A cached copy retrieved minutes earlier still said Trial customers could start a support conversation, so the support position is changing.
- Source URL, retrieval date and short supporting passage: https://plaid.com/docs/account/billing/ (2026-10-31): "Free Trial plans are available to new Plaid teams (US/Canada only) created on or after April 15, 2026." https://support.plaid.com/hc/en-us/articles/39994173227159-What-is-the-Plaid-Trial-plan (2026-10-31): "The Trial plan is available to developers who: Are located in the United States or Canada; Do not already have an existing Plaid Production or Limited Production account." "Most Trial plan applications are approved automatically after identity verification." https://support.plaid.com/hc/en-us/articles/16110502116887 (2026-10-31): passage quoted above.
- Impact on the user's goal: if ineligible, the first connection has a cost (Pay-as-you-go pricing is only shown inside the Production application), and the "$0 starting cost" and "free Trial" statements fail. Even when eligible, the Trial has no human support, so a failed institution link has no escalation path.
- Smallest correction: replace the eligibility sentence (see Corrections C-1) and add a pre-pilot step: create a brand-new Plaid team under the account owner's own email, confirm the Trial application button appears, and record the approval email before planning any link.
- Acceptance test or proof needed: PILOT-GATES.md G0.

### F02 Annual OAuth consent refresh at Capital One and Bank of America is missing from the plan

- Severity and confidence: High; high.
- Evidence status: observed omission (the plan's "occasional reconnect" does not disclose a documented, mandatory, annual, attended step).
- Baseline file and exact section, row or quote: `account-connection-plan.csv` rows "Bank of America" (expected_human_step "Owner authorization and occasional reconnect") and "Capital One" ("Owner authorization; older history needs portal archive"); report §10 "(1) occasional account reconnection or MFA".
- Failing scenario or counterevidence: twelve months after linking, Plaid sends `PENDING_DISCONNECT` one week before expiry (only if a webhook is registered; the local design has none) and the Item stops updating unless the owner completes update mode. A silent stop is exactly the failure the plan's dashboard is meant to show, but the plan does not poll `consent_expiration_time`.
- Source URL, retrieval date and short supporting passage: https://plaid.com/docs/link/oauth/ (2026-10-31): "In the US, the following institutions require periodic OAuth consent refresh. Consent refresh at these institutions is required every 12 months, unless noted otherwise. ... Bank of America (new API only, see Bank of America for more details) ... Capital One ..." "To determine when consent expires, call /item/get and note the consent_expiration_time field. Plaid will also send a PENDING_DISCONNECT webhook ... one week before a user's consent is set to expire. To refresh consent for an Item, send it through update mode." https://plaid.com/docs/link/update-mode/ (2026-10-31): "If you receive the ITEM_LOGIN_REQUIRED error ... re-authenticate with Link in update mode when the user is next in your app."
- Impact on the user's goal: at least two attended re-authorizations per year for the two pilot institutions, plus ad hoc repairs. Update mode repairs the existing Item; re-linking instead would create a duplicate Item and consume quota (F05).
- Smallest correction: add to the recurring-work list and to the sync job: store `consent_expiration_time` from `/item/get` for every Item; raise an exception 30 days before expiry; the exception text must say "use update mode, do not re-link".
- Acceptance test or proof needed: G9 (expired or expiring authentication is visible before it bites).

### F03 Plaid Statements cannot deliver card statements

- Severity and confidence: High; high.
- Evidence status: observed contradiction.
- Baseline file and exact section, row or quote: `account-connection-plan.csv` row "Bank of America", primary_route "Plaid: balances, transactions, supported card liabilities and PDF statements", intended_cadence "Daily feed; monthly statement archive"; report §1 table column "PDF statements" = Listed for Bank of America and Acorns; report §2 "up to two years for supported statement extraction".
- Failing scenario or counterevidence: the monthly statement archive for Bank of America credit cards, and for every Capital One account, cannot be produced by the Statements product. The directory flag is institution-level; the product itself is restricted to depository accounts. Capital One's row has statements = 0.
- Source URL, retrieval date and short supporting passage: https://plaid.com/docs/statements/ (2026-10-31): "Statements currently supports only bank depository accounts (e.g. checking and savings accounts)." "Statements does not currently support all major or long-tail institutions, and should be used with a fallback option in case data is not available." https://plaid.com/docs/api/products/statements/ (2026-10-31): "You can request up to two years of data." Directory row ins_128026 Capital One: statements 0 (`review/evidence/plaid-directory-extract-2026-10-31.csv`).
- Impact on the user's goal: card statements (the records most needed for interest, fees and dispute history) come only from portal downloads, which is the plan's least reliable, most manual route (F11).
- Smallest correction: change the Bank of America route to "PDF statements for checking/savings only; card statements by monthly portal download"; change Capital One's fallback to "all statements by portal download (Capital One keeps up to seven years online)".
- Acceptance test or proof needed: G3 (statements list returned only for depository accounts) and G14 (one card statement obtained by the chosen non-API route).

### F04 History depth is fixed at Item creation

- Severity and confidence: High; high.
- Evidence status: observed omission.
- Baseline file and exact section, row or quote: report §2 "Plaid documents up to 24 months for transaction ... products"; `PC-setup-runbook.txt` steps 6–7 (no `days_requested` instruction); FIELD-GUIDE "First PC session" #3.
- Failing scenario or counterevidence: the first link is made with the default (90 days). The only way to get 24 months later is to delete and recreate the Item, which consumes one of the 10 lifetime slots and, for Capital One, still returns only 90 days.
- Source URL, retrieval date and short supporting passage: https://support.plaid.com/hc/en-us/articles/24631662544919 (2026-10-31): "If left unspecified, this option defaults to a 90-day transaction history for the Item ... The maximum allowable value is 730 days ... Once an Item is created and has received its historical pull of transaction information, its transaction history length cannot be extended except by deleting and then recreating the Item with the desired transactions.days_requested value." https://plaid.com/docs/transactions/ (2026-10-31): "Once the Item exists, Plaid retains every new transaction it sees, so the amount of available history grows for as long as the Item remains connected."
- Impact on the user's goal: a wasted Item and a permanently shallow history for the pilot institutions.
- Smallest correction: runbook step 6 must read "every /link/token/create request sets transactions.days_requested to 730 and lists every product the Item will ever need (transactions, liabilities, investments, statements as applicable)". Products can be added later via update mode, but history depth cannot.
- Acceptance test or proof needed: G3 records the oldest transaction date per account against the documented ceiling (Bank of America 18 months deposits / 12 cycles cards; Capital One 90 days).

### F05 The Item budget is unstated and nearly exhausted on paper

- Severity and confidence: High; high.
- Evidence status: supported design risk.
- Baseline file and exact section, row or quote: FIELD-GUIDE > Connection facts #2; report §2 "Count connections by institution and account owner before onboarding"; `account-connection-plan.csv` has 8 rows with institution ids plus "Other cards / Reprise / installments" with unresolved issuers.
- Failing scenario or counterevidence: 8 directory institutions = 8 Items if every account sits under one login per institution. One spouse login at any institution, one additional card issuer, or one accidental re-link after an `ITEM_LOGIN_REQUIRED` error reaches the cap, after which only a one-way paid upgrade creates more Items.
- Source URL, retrieval date and short supporting passage: https://support.plaid.com/hc/en-us/articles/39994173227159 (2026-10-31): "All access tokens created in Production will count against your Trial plan Item limit. This includes duplicate Items created when a user links the same account more than once." https://plaid.com/docs/link/duplicate-items/ (2026-10-31): "A duplicate Item will be created if the end user logs into the same institution with the same credentials a second time through Plaid Link". https://plaid.com/docs/account/billing/ (2026-10-31): "Removing Items created on a Trial plan (using /item/remove) will not allow you to create more Items." "If you added a subscription fee product (such as Investments, Liabilities, or Transactions) to an Item during your trial, upon upgrading to a paid plan, you will begin to be charged for that subscription."
- Impact on the user's goal: an upgrade is one-way and starts per-Item subscription billing for every existing Item.
- Smallest correction: add an Item budget table to the plan before linking: priority order (Bank of America, Capital One, M1, Robinhood, Acorns, Raisin, Venmo, Transamerica), reserve two slots, and the rule "never re-link; repair with update mode; verify on the Dashboard Items count after every link". Put the lowest-value feeds (Venmo, Raisin) on CSV/statement collection unless slots remain after the pilot.
- Acceptance test or proof needed: G2.

### F06 Capital One feed semantics differ from Bank of America

- Severity and confidence: Medium; high.
- Evidence status: observed omission.
- Baseline file and exact section, row or quote: report §2 callout "Capital One backfill is a separate job"; `account-connection-plan.csv` row "Capital One".
- Failing scenario or counterevidence: a pending-to-posted matcher designed on Bank of America behaviour will find no pending rows for Capital One; a "force refresh" step fails with `PRODUCTS_NOT_SUPPORTED` on a card-only Item; a freshness check that expects same-day updates is wrong.
- Source URL, retrieval date and short supporting passage: https://support.plaid.com/hc/en-us/articles/25286986638231 (2026-10-31): "The transaction data that Capital One provides does not include pending transactions." https://support.plaid.com/hc/en-us/articles/25922395286935 (2026-10-31): "/transactions/refresh is not supported on Items that include only non-depository accounts (e.g., credit cards)". https://support.plaid.com/hc/en-us/articles/25349321999511 (2026-10-31): "For Capital One accounts, only 90 days of transaction history is available. This limit is imposed by Capital One, so increasing transactions.days_requested above 90 will not return additional history."
- Impact on the user's goal: none on coverage, but silent assumptions produce false exceptions or missed ones.
- Smallest correction: per-institution capability flags in the registry (pending_supported, refresh_supported, history_ceiling_days, consent_refresh_months).
- Acceptance test or proof needed: G5 and G8.

### F07 Hosted Link from a local PC is documented but not demonstrated

- Severity and confidence: Medium; medium.
- Evidence status: unresolved question.
- Baseline file and exact section, row or quote: report §2 "test Plaid Hosted Link with an owner-completed browser login and local retrieval of the completed session through /link/token/get ... it exposes session completion information for six hours. This is a plausible local-PC onboarding route, subject to a production test." `PC-setup-runbook.txt` step 6.
- Failing scenario or counterevidence: three open points. (a) Plaid's own guidance: "Hosted Link should be used only when Plaid Link SDKs cannot be used" and "If none of these apply, you should not use Hosted Link". Nothing says the API refuses it, but the plan should not rely on a discouraged path without a fallback. (b) The documented sample request includes `redirect_uri`, which "When used in Production, must be an https URI"; the docs do not state whether a web (non-mobile) Hosted Link session can omit it. (c) The link's default lifetime without Plaid delivery is 30 minutes and session data is available for six hours, so the owner must complete the bank login promptly and the local poller must run within six hours.
- Source URL, retrieval date and short supporting passage: https://plaid.com/docs/link/hosted-link/ (2026-10-31): "In Hosted Link, there is no frontend integration required (or possible). You will instead receive information about the Link flow (including the public_token) via the SESSION_FINISHED webhook and the /link/token/get endpoint." "Detailed session data, including the public token, will also be available from /link/token/get for six hours after the session has completed ... you may want to use /link/token/get if your integration does not use webhooks". "If Plaid isn't delivering the URL, the default lifetime is 30 minutes." https://plaid.com/docs/api/link/ (2026-10-31): "Session data will be provided for up to six hours after the session has ended." `redirect_uri`: "When used in Production, must be an https URI."
- Impact on the user's goal: if a redirect URI is required, the user needs one HTTPS URL they control (a static page suffices); if Hosted Link proves unsuitable, the fallback is the standard web Link SDK hosted on a static HTTPS page that re-initializes Link after the OAuth redirect, with the public token pasted or polled.
- Smallest correction: keep the route, add the fallback sentence, and schedule the owner-attended session so link creation, bank login and local polling happen within one sitting.
- Acceptance test or proof needed: G1.

### F08 Google OAuth setup needs a concrete choice, not "configure appropriately"

- Severity and confidence: Medium; high.
- Evidence status: supported design risk.
- Baseline file and exact section, row or quote: report §5 "Configure the personal collector's publishing/authorization setup appropriately and test refresh behavior. Personal-use verification exemptions and publishing status are separate issues"; FIELD-GUIDE > Connection facts #5; runbook step 11.
- Failing scenario or counterevidence: the app is left in Testing (the default) and every Drive/Gmail token dies after seven days; or the user believes the personal-use exemption alone fixes expiry.
- Source URL, retrieval date and short supporting passage: https://developers.google.com/identity/protocols/oauth2 (2026-10-31): "A Google Cloud Platform project with an OAuth consent screen configured for an external user type and a publishing status of 'Testing' is issued a refresh token expiring in 7 days, unless the only OAuth scopes requested are a subset of name, email address, and user profile". https://support.google.com/cloud/answer/15549945 (2026-10-31): "Authorizations by a test user will expire seven days from the time of consent." https://developers.google.com/identity/protocols/oauth2/production-readiness/restricted-scope-verification (2026-10-31): "Personal use: One use case is if you are the only user of your app or if your app is used by only a few users, all of whom are known personally to you. You and your limited number of users might be comfortable with advancing through the unverified app screen". https://support.google.com/cloud/answer/7454865 (2026-10-31): "If your app remains unverified, the unverified app screen will be displayed before the consent screen, and your app will be limited to 100 new users until it is [verified]".
- Impact on the user's goal: weekly re-consent versus a one-time consent.
- Smallest correction: Corrections C-6: External user type, set Publishing status to "In production" (click Publish), do not submit for verification (personal-use exception), request only `gmail.readonly` and `drive.readonly` (the Cloud Console labels their category automatically), accept the "Google hasn't verified this app" screen once on the owner's account, store the refresh token with the collector's other secrets.
- Acceptance test or proof needed: G12.

### F09 Plaid-specific reconciliation facts the design must encode

- Severity and confidence: Medium; high.
- Evidence status: observed omission (the plan states goals, not the provider's actual semantics).
- Baseline file and exact section, row or quote: report §8 bullets "Use stable provider IDs ... Handle pending-to-posted changes" and "investment contributions"; FIELD-GUIDE > Completion criteria; runbook step 15 "investment sign conventions".
- Failing scenario or counterevidence: (a) an investment purchase imported as "positive = inflow" doubles portfolio contributions; a `buy`/`contribution` row is entirely an outflow although it also represents a cash deposit; (b) a balance check that compares a statement closing balance with the `balances` object from `/transactions/sync` uses a stale balance; (c) a backfill that assumes 24 months at Bank of America reports 6 missing months as a failure; (d) a European-style `authorized_date` assumption is irrelevant (that Plaid article is EU-only).
- Source URL, retrieval date and short supporting passage: https://plaid.com/docs/investments/ (2026-10-31): "Inflow, such as stock sales, is shown as a negative amount, and outflow, such as stock purchases, is positive." "Each holding also includes a tax_lots array ... or an empty array when the institution provides no lot-level data." https://support.plaid.com/hc/en-us/articles/40621176117271 (2026-10-31): "Since buy transactions are always positive, the entire transaction is represented as an outflow." https://support.plaid.com/hc/en-us/articles/15373441901207 (2026-10-31): "the balances object within the /transactions/get or /transactions/sync response is accurate as of the time Plaid made our scheduled request for transaction data". https://support.plaid.com/hc/en-us/articles/25348952076567 (2026-10-31): "For checking, savings, and mortgage accounts, transactions are available for the most recent 18 months. For credit cards (personal and small business), transactions are available for the current partial cycle, plus the 11 previous statement cycles."
- Impact on the user's goal: wrong signs and false exceptions undermine trust in the exception queue, which is the product.
- Smallest correction: write the invariants into the schema notes (Corrections C-8) and test them (G4–G7, G15).
- Acceptance test or proof needed: G4, G5, G6, G7, G15.

### F10 The stack is larger than the goal requires

- Severity and confidence: Medium; high.
- Evidence status: supported design risk (unnecessary complexity).
- Baseline file and exact section, row or quote: report §3 tool table and §4 "PC design"; FIELD-GUIDE "Recommended architecture" (nine rows); runbook steps 2, 13, 14 and the Docker/Compose, Ollama backend and Node runtime checks.
- Failing scenario or counterevidence: a rolling-release Arch PC running Docker (Paperless), a Node 24/26 gateway (OpenClaw), a GPU-backed Ollama and a Python OCR stack has four independent update surfaces before a single transaction is reconciled. Paperless duplicates the Originals folder ("Files consumed from the consumption directory are re-created inside this media directory and are removed from the consumption directory itself"), OpenClaw's browser is the riskiest component (F11), and no pilot gate needs an LLM.
- Source URL, retrieval date and short supporting passage: https://docs.openclaw.ai/install/ (2026-10-31): "Node 24.16.0+ on 24.x, or 26.1.0+ (24.22.1+/26.12.1+ strongly recommended for security)". Paperless-ngx setup.md (GitHub source, 2026-10-31): "For most users, Docker is the best option." https://wiki.archlinux.org/title/Ollama (2026-10-31): "Install the ollama package, which provides a daemon, command line tool, and CPU inference. For GPU inference: Install ollama-vulkan ... ollama-cuda ... ollama-rocm".
- Impact on the user's goal: more maintenance hours than the manual work the tools are meant to remove.
- Smallest correction: see "Smallest workable architecture" below; keep the optional tools as later additions gated on measured need.
- Acceptance test or proof needed: the pilot must pass G0–G12 with only the minimal stack installed.

### F11 Browser automation is the least reliable route and the plan leans on it for card statements

- Severity and confidence: Medium; high.
- Evidence status: supported design risk.
- Baseline file and exact section, row or quote: report §6 "test the managed download-capable profile with an owner-attended initial login"; runbook step 13; `account-connection-plan.csv` rows Nationwide, Allstate, "Other cards".
- Failing scenario or counterevidence: the managed profile is headless by default, so the one-time login needs a desktop session and full Chromium; anti-bot defences can lock accounts; passkeys need a headed profile; a profile holding bank sessions is readable by the model, so a prompt-injected page (or an emailed statement containing instructions) can steer an agent that has that browser.
- Source URL, retrieval date and short supporting passage: https://docs.openclaw.ai/tools/browser-login (2026-10-31): "Local managed browsers are headless by default. For manual login, use a browser host with a desktop session and full Chrome/Chromium; headless shell cannot show a login window." "Automated logins often trigger anti-bot defenses and can lock the account." https://docs.openclaw.ai/tools/browser/existing-session (2026-10-31): "Playwright-only features - PDF export, download interception, responsebody ... require a Playwright-backed profile, such as the managed openclaw profile." https://docs.openclaw.ai/gateway/security/browser-control (2026-10-31): "Enabling browser control gives the model a real browser. If that profile already has logged-in sessions, the model can access those accounts and data". Download actions exist: https://docs.openclaw.ai/tools/browser-control (2026-10-31) lists `openclaw browser download e12 report.pdf` and `waitfordownload`; PR openclaw/openclaw#101369 "feat(browser): expose agent download actions" merged (Jul 2026); current release v2026.10.6.
- Impact on the user's goal: an unattended monthly statement job that works for one bank may lock another; recovery is attended.
- Smallest correction: for the pilot, download card statements by hand into `Staging/` once a month (a few PDFs); promote a site to automation only after a scripted downloader (plain Playwright, no LLM in the loop, no other sessions in the profile) completes three consecutive monthly runs.
- Acceptance test or proof needed: G14.

### F12 Unattended jobs: catch-up, wake and credential access

- Severity and confidence: Medium; high.
- Evidence status: supported design risk; the plan asks the right question but leaves the design open.
- Baseline file and exact section, row or quote: report §4 "Scheduling"; runbook steps 5 and 16.
- Failing scenario or counterevidence: the PC is suspended overnight; a user timer cannot wake it; if the owner logs out, the service survives only with lingering; secrets kept in a desktop keyring are unavailable to a boot-time lingering service until the owner logs in.
- Source URL, retrieval date and short supporting passage: https://www.freedesktop.org/software/systemd/man/latest/systemd.timer.html (2026-10-31): "Persistent= ... useful to catch up on missed runs of the service when the system was powered down. Note that this setting only has an effect on timers configured with OnCalendar=." "WakeSystem= ... this functionality requires privileges and is thus generally only available in the system service manager." https://www.freedesktop.org/software/systemd/man/latest/loginctl.html (2026-10-31): "enable-linger ... a user manager is spawned for the user at boot and kept around after logouts."
- Impact on the user's goal: silent gaps if the PC sleeps; failed runs if secrets are keyring-bound.
- Smallest correction: store the Plaid access tokens and Google refresh token in files readable only by the service user (mode 0600) or via `systemd-creds` encrypt/decrypt, not a desktop keyring; enable lingering; use `OnCalendar=daily` with `Persistent=true`; accept that a suspended PC runs the job at the next wake.
- Acceptance test or proof needed: G10.

### F13 Evidence quality

- Severity and confidence: Low; high.
- Evidence status: observed.
- Baseline file and exact section, row or quote: `research-material.json` searches 1, 4, 5, 9, 23, 26, 28 (Windows, WSL2, Task Scheduler); `sources.json` entries 1, 2, 7, 11, 12, 16, 29, 30, 35, 43.
- Failing scenario or counterevidence: none material. Every checked first-party quotation was accurate at retrieval; the directory snapshot reproduces exactly (the live CSV still carries the same generation stamp, 2026-10-16T03:26:16.866Z, and 10,304 rows). The Plaid Trial help page changed wording between two fetches on 2026-10-31 (support availability and the MSA name), which shows why the plan's "recheck at setup" rule matters.
- Smallest correction: none required; the sources list is sound. Record retrieval dates per claim at setup time.

## Claims that survived challenge

- All eight Plaid directory rows (ids and the five product flags) match the current directory exactly; Nationwide has only retirement/securities and "Axos Bank for Nationwide" entries, no Life entry, exactly as the baseline said. Directory support remains institution-level: it says nothing about Robinhood crypto sub-accounts, Acorns Later, individual Raisin deposits or Transamerica policy fields.
- Capital One: 90-day Plaid history, imposed by Capital One, not overridable (verbatim).
- Plaid Trial: 10 lifetime Items, removal does not free slots, duplicates count, immediate OAuth access including Bank of America and Capital One, products include Transactions, Balance, Liabilities, Investments and Statements (verbatim).
- `/link/token/get` retains session data for six hours and is the documented path when webhooks are not used.
- Plaid Transactions up to 730 days; Investments transactions up to 24 months; Statements up to two years (ceilings, depository only).
- SimpleFIN Bridge: $1.50/month or $15/year plus tax, 25 institutions and 25 apps, 24 requests/day expected, 90-day request window distinct from available history (verbatim). Actual Budget's SimpleFIN sync pulls at most 90 days and updates daily via MX.
- SnapTrade Personal: free, up to 20 brokerage connections, Robinhood read-only OAuth with no trading; standard transactions refresh daily with a one-day delay.
- Tiller: $99/year after trial; Excel requires launching the add-in and clicking Fill; Google Sheets Auto Fill runs every six hours.
- Google: seven-day refresh tokens for External apps in Testing with non-basic scopes; personal-use exception to verification; Drive export limited to 10 MB; rclone exports native docs as docx/xlsx/pptx by default.
- OpenClaw: Linux Gateway as a systemd user service; managed Playwright profile supports download and waitfordownload; existing-session profiles lack download interception; manual login recommended.
- M1: CSV activity export; holdings/tax lots are a separate export; only the past three years of statements, confirmations and tax documents download directly.
- Raisin: consolidated monthly statement in the Documents tab with Print/Save; interest for closed deposits is not in the current statement (page updated 2026-08-20).
- Acorns: third-party linking is conditional ("all your accounts won't connect or show up on every third-party app"), data relays in 1–3 business days, 2FA is triggered by third-party integrations (page dated 2021-03-03).
- IRS: "Only the taxpayer should log into their account." Transcripts and compliance reports have documented limits.
- Venmo: downloadable CSV statements for personal accounts; large files are emailed instead.
- Transamerica service portal shows cash value under Policy/Certificate Summary; the correct portal for the actual policy is unknown.
- Arch: uv 0.13.1-1 and docker-compose 5.6.1-1 are in Extra (built October 2026); ollama, ollama-cuda, ollama-rocm and ollama-vulkan exist; Docling prefetches models for offline use including EasyOCR language packs (EasyOCR lists Thai); Ollama structured outputs enforce a JSON schema; systemd `Persistent=` and `enable-linger` behave as described.
- The "no automation percentage before the pilot" stance and the exception-queue goal are the right framing.

## Claim verification coverage

`review/CLAIM-RESULTS.csv` covers C01–C26 plus twelve added claims (A01–A12). Of the 38 rows: 20 supported, 15 partially supported (the baseline statement is correct but needs a qualification or omits a material fact; C01 Trial eligibility and C04 Hosted Link are in this group), 1 contradicted (C05, card statements via Plaid Statements), 1 unverified (A06, Bank of America's statement window, where two first-party pages conflict) and 1 stale (A09, the Trial support wording that changed between two fetches). SimpleFIN institution coverage (C12) and SnapTrade support for M1 and Acorns (C13) are recorded as supported claims with unverified sub-questions in VERIFICATION-QUEUE.md (V1, V2). Every verdict rests on first-party pages retrieved on 2026-10-31 except where the row says otherwise. No row rests on live-account evidence; none exists.

## Smallest workable architecture

Goal restated: maximum automatic collection with minimum ongoing human effort, on one Arch PC, with originals preserved and an exception queue instead of retyping.

Keep for the pilot:

1. One Plaid Trial team owned by the account owner; Hosted Link onboarding; every link token sets `days_requested=730` and all products the Item will need; products per institution from the directory (Transactions+Liabilities for banks/cards, Investments for M1/Robinhood/Acorns/Transamerica, Statements only for Bank of America depository accounts).
2. One Python project (uv, locked) with three entry points: `link` (create Hosted Link URL, poll `/link/token/get`, exchange and store the access token), `sync` (per-Item `/transactions/sync` cursor, `/investments/holdings/get` and `/investments/transactions/get` snapshots, `/liabilities/get`, `/accounts/balance/get`, `/item/get` for consent expiry; every raw response saved to `FeedSnapshots/` before parsing), `report` (CSV/XLSX export, status table, exception list as Markdown or HTML, no web server).
3. SQLite with these tables and invariants: `items` (institution, owner, consent_expiration_time, last_success), `accounts`, `raw_responses` (hash, endpoint, fetched_at), `transactions` (primary key = Plaid `transaction_id`; `pending_transaction_id` link; `removed_at`; amount sign normalized to signed cash flow; original currency), `investment_transactions` (Plaid sign convention normalized, `buy/contribution` split rule recorded), `holdings_snapshots` and `balances_snapshots` (dated; source = sync or realtime), `documents` (sha256, source, period, file path), `overrides` (manual corrections with evidence, applied after every import), `transfer_links` (candidate/confirmed, never auto-confirmed when more than one candidate matches), `exceptions`.
4. Files: `~/Finance/Originals` (immutable, hashed on arrival), `FeedSnapshots`, `Staging` (manual and emailed downloads), `Data/finance.sqlite`, `Reports`, `Backups` (nightly `sqlite3 .backup` plus rsync of Originals to a second disk or restic repository; restore tested once).
5. Drive and Gmail collectors as two small scripts: rclone (export formats xlsx and csv where possible, file id + modifiedTime + md5 recorded) and a Gmail `messages.list` query loop saving attachments under the message id, both using the "In production, unverified, personal use" OAuth app.
6. One `systemd --user` timer (`OnCalendar=daily`, `Persistent=true`, lingering enabled) running `sync` then `report`; secrets in 0600 files or `systemd-creds`.
7. Manual monthly step during the pilot: download card statements (Bank of America cards, Capital One) and any Nationwide/Allstate/IRS documents into `Staging/`. This is bounded, predictable work and it is what the browser route would have to beat.

Defer (add only when a measured gap appears after the pilot):

- OpenClaw: no pilot gate needs an AI operator; reconsider after three months of exception data shows which questions it would answer. If a browser downloader is wanted, write it as plain Playwright against a dedicated profile with no other sessions.
- Ollama/local LLM and Docling: start extraction with deterministic parsers (CSV/JSON, `pdfplumber`/`pdftotext` for text PDFs). Add Docling OCR only for scanned Thai/English documents after a 20-document benchmark with known expected values; add an LLM only for free-text classification where rules fail, with numeric fields never taken from the model.
- Paperless-ngx: the `documents` table plus a predictable folder layout covers search and provenance for the pilot; Paperless adds Docker and a second media store.
- SnapTrade Personal: only if Plaid's Robinhood Item lacks needed accounts or fields (note the Personal consumer key can trade where enabled, so never implement order endpoints).
- SimpleFIN + Actual Budget: the mature-tool alternative for bank/card transactions. Use it as the primary ledger if Plaid Trial is unavailable (G0 fails): $15/year, scheduled sync via the API's `runBankSync`, strong transfer matching and rules, but only ~90 days of initial history, bank-only data, requires `actual-server`, and bank-sync tokens are not end-to-end encrypted on that server.

Remove:

- Tiller (cloud-centred, Excel fill is manual, $99/year, no local-file goal).
- Any second financial store (Actual and SQLite together, or Paperless media plus Originals) during the pilot.
- A served dashboard; a generated report file is enough.

Why this minimizes ongoing effort: the only recurring human actions are the documented ones (annual consent refresh at two institutions, ad hoc Item repairs, a monthly statement download that takes minutes, IRS and insurer attended downloads), each surfaced by the report; everything else is deterministic, idempotent and restorable from files.

## Pilot gates

See `review/PILOT-GATES.md`. Order: G0 (Trial eligibility) and G1 (Hosted Link from the PC) decide whether Plaid is the route at all; G2–G3 fix the Item budget and coverage facts; G4–G7 and G11 prove the ledger invariants on one statement cycle; G8–G10 and G12 prove recovery and longevity; G13–G18 cover documents, the browser route and the investment/insurance feeds; G19 is the deferred OCR benchmark.

## Human work that remains

Conditional expectations, not percentages:

- Initial setup (one sitting each): create the Plaid team and pass identity verification; one Hosted Link session per Item (eight planned, two in the pilot); Google Cloud project, consent screen, publish, one consent; rclone authorization; alias resolution for "Red Card", "Amazon card", "Ryan Card", "Credit Card 1/2".
- Recurring, documented: Bank of America and Capital One consent refresh every 12 months (attended update-mode session each); `ITEM_LOGIN_REQUIRED` repairs when a bank changes something (attended, unpredictable); Google re-consent only if the token is revoked.
- Recurring, by design choice: monthly card-statement downloads until a per-site downloader passes three consecutive runs; Nationwide Life, Allstate dental, employer portals and IRS remain attended downloads (the IRS states only the taxpayer may log in).
- Data facts no feed can supply: cash tips, private loan terms and purposes, policy premium schedules not in the feed, gross versus net work income. The plan's "one structured correction" workflow is the right answer.
- Maintenance: Arch updates can break the Python environment or Playwright; keep the project locked with uv and re-run G4 after system updates.

## Corrections ready to apply

- C-1 (FIELD-GUIDE > Connection facts #2; report §2; runbook INITIAL COSTS). Replace "supports real accounts for eligible personal developers" with: "The Plaid Trial is available only to a new Plaid team (US/Canada) created on or after 2026-04-15 that has never applied for Production or Limited Production; it requires accepting Plaid's MSA with security attestations and identity verification; it gives up to 10 lifetime Production Items; Trial customers have no support cases. Verify eligibility by creating the team before planning any link." Evidence: Plaid billing docs and help articles 39994173227159 and 16110502116887 (2026-10-31).
- C-2 (account-connection-plan.csv rows Bank of America and Capital One; report §10). Add to expected_human_step: "Annual OAuth consent refresh via update mode (Plaid: required every 12 months at Capital One and Bank of America new API); the collector stores consent_expiration_time from /item/get and raises an exception 30 days ahead." Evidence: Plaid OAuth guide (2026-10-31).
- C-3 (account-connection-plan.csv row Bank of America primary_route; report §1 column "PDF statements"). Replace with: "PDF statements via Plaid for checking/savings only (depository accounts; up to two years); card statements by portal download." Capital One fallback: "All statements by portal download; Capital One keeps up to seven years online for active accounts." Evidence: Plaid Statements docs; Capital One help centre (2026-10-31).
- C-4 (runbook step 6). Add: "Every /link/token/create sets transactions.days_requested=730 and includes every product the Item will ever need; history depth cannot be extended later without recreating the Item, which consumes a Trial slot." Evidence: Plaid help article 24631662544919.
- C-5 (FIELD-GUIDE > First PC session #2; runbook step 3). Add an Item budget table: eight planned institutions, two reserve slots, "never re-link; repair with update mode; check the Dashboard Items count after every link; a paid upgrade is one-way and starts subscription billing on existing Items." Evidence: Plaid Trial and billing pages.
- C-6 (report §5; FIELD-GUIDE #5; runbook step 11). Replace "Configure ... appropriately" with: "Create an External OAuth app, request only gmail.readonly and drive.readonly, set Publishing status to In production without submitting for verification (personal-use exception), accept the unverified-app screen once; tokens issued in Testing status expire after seven days." Evidence: Google OAuth2, Manage App Audience, restricted-scope verification, unverified apps pages.
- C-7 (report §2 and account plan row Capital One). Add: "Capital One supplies no pending transactions, does not support /transactions/refresh on card-only Items, and has no Statements support." Evidence: Plaid help articles 25286986638231 and 25922395286935; directory row ins_128026.
- C-8 (report §8; runbook step 15). Add invariants: "Plaid investment amounts: inflows negative, outflows positive; buy/contribution rows are entirely outflows and must be split into a cash contribution and a purchase; tax_lots may be empty. Balances returned by /transactions/sync are as-of Plaid's last scheduled pull; use /accounts/balance/get for a dated real-time balance. Bank of America history: 18 months for deposits and mortgages, current cycle plus 11 cycles for cards." Evidence: Plaid Investments docs and help articles.
- C-9 (report §2 Hosted Link). Add: "Plaid recommends Hosted Link only when its SDKs cannot be used; if Production rejects a session without an HTTPS redirect URI, register one static HTTPS page; the link expires in 30 minutes by default and session data is retrievable for six hours." Evidence: Hosted Link and Link API docs.
- C-10 (report §3 tool table; FIELD-GUIDE architecture table). Mark OpenClaw, Ollama, Docling and Paperless-ngx as "deferred until a pilot gate shows the need"; mark SnapTrade and SimpleFIN as "fallback only"; delete Tiller.
- C-11 (runbook step 16). Replace with: "systemd --user timer, OnCalendar=daily, Persistent=true, loginctl enable-linger; secrets in 0600 files or systemd-creds, never a desktop keyring; a user timer cannot wake a suspended PC (WakeSystem= needs the system manager)." Evidence: systemd.timer and loginctl manuals.
- C-12 (account plan rows M1, Robinhood, Acorns, Raisin, Transamerica). Add the documented ceilings and caveats: M1 documents three years direct; Acorns third-party visibility conditional, 1–3 business-day relay, 2FA on integrations; Raisin closed-deposit interest absent from the current statement; Robinhood via SnapTrade is read-only; Transamerica field meanings unverified.

## Unresolved verification queue

See `review/VERIFICATION-QUEUE.md`: SimpleFIN institution coverage for the eight institutions; SnapTrade support for M1 and Acorns; Bank of America's statement window (two first-party pages say 18 months and six years); Capital One card CSV export window; Hosted Link `redirect_uri` requirement in Production; Plaid Trial support wording (page in flux); Acorns Later and Robinhood crypto sub-account visibility; Raisin per-deposit exposure; Transamerica field semantics and correct portal; Nationwide Life aggregator support (none found); Allstate and employer portals; OCR quality on representative Thai/English documents; the workbook itself.


---

# Part 3: PILOT-GATES

_Source file: `PILOT-GATES.md`_

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


---

# Part 4: VERIFICATION-QUEUE

_Source file: `VERIFICATION-QUEUE.md`_

# Verification queue

Items that could not be settled from public first-party sources during the 2026-10-31 review, with the exact evidence that would close each one and who or what can supply it. No live-account evidence exists anywhere in the packet or in this review.

| # | Claim or question | Baseline locator | What was found | Evidence still needed | Who or what can supply it |
| --- | --- | --- | --- | --- | --- |
| V1 | SimpleFIN Bridge supports Bank of America, Capital One, M1, Robinhood, Acorns, Raisin, Venmo, Transamerica | report §3 "Verify your institutions in its connection flow" | No public institution directory; Actual Budget docs say the upstream provider is MX; 90 days initial history | A screenshot or export of the Bridge institution search for each name after a $1.50 one-month signup, or a support reply | Owner, SimpleFIN support |
| V2 | SnapTrade supports M1 Finance and Acorns | account plan rows M1, Acorns | Listing pages read (1, 3, 4, 5) show Robinhood, Bank of America, Capital One, Transamerica, not M1 or Acorns; page 2 not retrievable (rate limit) | Read https://snaptrade.com/brokerage-integrations?page=2 or search the dashboard's connection portal | Anyone with web access; owner via SnapTrade Personal dashboard |
| V3 | Bank of America online statement window | account plan row Bank of America fallback | Two first-party pages disagree: digital-banking FAQ says "view, print and download up to 18 months of your statements"; the manage-statements page says "The most recent 6 years of monthly statements may be viewed online immediately" | The Statements & Documents year selector in the owner's Online Banking | Owner |
| V4 | Capital One credit-card CSV/export window | account plan row Capital One fallback | Help centre: 7 years of statements online, 2 years of transactions on the website (checking/savings page); the card download page returned 404; third parties say about 90 days for CSV | The date-range limit shown in the card's download dialog | Owner |
| V5 | Whether a web Hosted Link session in Production requires `redirect_uri` | report §2; runbook step 6 | Docs show `redirect_uri` in the sample and require HTTPS in Production; no statement for the non-mobile case | One `/link/token/create` call in Production without `redirect_uri` (G1) | Pilot G1 |
| V6 | Plaid Trial support availability and MSA wording | report §2 | Live page on 2026-10-31: "Support cases are available only on paid plans"; a cached copy minutes earlier said Trial customers can start a support conversation | Re-read the help article at setup time and keep the retrieval date | Anyone with web access |
| V7 | Acorns Later and Checking visible through Plaid; Robinhood crypto accounts visible | account plan rows Acorns, Robinhood | Acorns: "all your accounts won't connect or show up on every third-party app"; directory flags are institution-level | Account list after linking (G16) | Pilot |
| V8 | Raisin exposes each partner-bank deposit as a separate account via Plaid | account plan row Raisin | Directory: balance and transactions only; Raisin help documents Plaid only for linking the funding bank | Account list after linking (G17) or a Raisin support reply | Pilot, Raisin support |
| V9 | Transamerica Life feed field meanings; correct portal for the policy | account plan row Transamerica | Portal FAQ shows cash value in Policy/Certificate Summary; feed fields unknown; two portals exist (insuranceservicenow, MyTransamerica) | Policy number lookup on each portal; field list after linking (G18) | Owner, Transamerica |
| V10 | Nationwide Life/IUL via any aggregator | account plan row Nationwide | No Life entry in Plaid's directory (only retirement, securities and Axos entries) | SimpleFIN/MX institution search for "Nationwide Life"; otherwise document-only | Owner via V1 |
| V11 | Allstate dental and employer/contractor portal export behaviour | account plan rows Allstate, Work income | Not researched in the baseline beyond the plan statement | One manual download each; note MFA and file formats | Owner |
| V12 | OCR quality on the owner's Thai/English documents | report §5; runbook step 14 | EasyOCR lists Thai; Docling can prefetch its models; no accuracy data | G19 benchmark on the PC | Pilot |
| V13 | Google scope categories for `gmail.readonly` and `drive.readonly` | report §5 | Google says categories are shown automatically in the Cloud Console; the verification FAQ scope list was not retrieved | The category labels on the OAuth consent screen scope picker | Owner during setup |
| V14 | OpenClaw stable release contains the browser download actions | report §6 | Docs list `download`/`waitfordownload`; PR #101369 merged July 2026; latest release v2026.10.6 | `openclaw --version` and a `waitfordownload` run on the PC, if OpenClaw is ever installed | Deferred |
| V15 | The Cash Flow workbook's tabs, formulas and size | HANDOFF "The actual workbook ... not included" | Not inspected | G13 export and tab inventory | Owner |
| V16 | Paperless-ngx documentation site | sources 45, 46, 49 | Site bot-blocked; the same content was read from the project's GitHub `docs/` source | None needed unless the site version differs | — |
| V17 | Private ChatGPT pages (field guide, handoff) | HANDOFF links | Not accessible; the README says the packet is self-contained | None | — |
| V18 | Bank of America "new API" status for the owner's Items (consent refresh applies to new API Items only) | — | Plaid OAuth guide: "Bank of America (new API only ...)" | `consent_expiration_time` on the Item after G1 | Pilot G2 |


---

# Part 5: CLAIM-RESULTS

_Source file: `CLAIM-RESULTS.csv` (38 rows). Compact table first; the complete CSV follows as a fenced block._

| claim_id | review_target | verdict | confidence | test_or_follow_up |
| --- | --- | --- | --- | --- |
| C01 | Plaid Trial eligibility and actual real-account access | partially_supported | high | G0 |
| C02 | Plaid lifetime Item quota and household login accounting | supported | high | G2, G9 |
| C03 | Eight exact institution entries and product flags | supported | high | G3, G15-G18 |
| C04 | Local production Hosted Link onboarding | partially_supported | medium | G1 |
| C05 | BofA account types, liabilities and PDF statements | contradicted | high | G3, G9, G14 |
| C06 | Capital One 90-day feed and older-record backfill | partially_supported | high | G5, G8 |
| C07 | M1, Robinhood and Acorns investment coverage | partially_supported | medium | G15, G16 |
| C08 | Raisin underlying deposits and consolidated statements | partially_supported | medium | G17 |
| C09 | Transamerica Life feed versus actual IUL values | partially_supported | medium | G18 |
| C10 | Nationwide Life availability and fallback | supported | high | V10 |
| C11 | Statement API history and recurring collection | partially_supported | high | G3 |
| C12 | SimpleFIN price, quotas, history and data shape | supported | high | V1 |
| C13 | SnapTrade Personal free use and broker coverage | supported | high | V2 |
| C14 | Tiller exclusion and spreadsheet alternatives | supported | high | — |
| C15 | Complete Drive export and file/version identity | partially_supported | high | G13 |
| C16 | Email collection and Google OAuth longevity | supported | high | G12 |
| C17 | OpenClaw browser downloads and shipped Linux features | supported | medium | G14, V14 |
| C18 | Arch runtime, Python isolation, OCR and local AI feasibility | supported | high | G19 |
| C19 | Unattended systemd jobs and credentials after reboot | partially_supported | high | G10 |
| C20 | Financial normalization, duplicate control and reconciliation | partially_supported | high | G4, G5, G6, G7, G11 |
| C21 | AI/OCR extraction acceptance and financial precision | partially_supported | medium | G7, G19 |
| C22 | Starting cost and actual ongoing human burden | partially_supported | medium | G0, G9, G14 |
| C23 | Smallest workable architecture and competing tools | partially_supported | high | G0-G12 with the minimal stack only |
| C24 | Credentials, browser scope, document instructions and recovery | partially_supported | high | G10 |
| C25 | Source completeness, dates and reproducibility | partially_supported | medium | — |
| C26 | Work income, IRS, family loans and unrecorded cash | supported | high | — |
| A01 | Transactions history depth is fixed at Item creation (days_requested, max 730) | supported | high | G3 |
| A02 | OAuth consent refresh every 12 months at Capital One and Bank of America (new API) | supported | high | G9 |
| A03 | Investment amount signs and buy/contribution representation | supported | high | G15 |
| A04 | Balances from /transactions/sync are as-of Plaid's last scheduled pull | supported | high | G7 |
| A05 | Upgrading from Trial is one-way and starts subscription billing on existing Items | supported | high | G2 |
| A06 | Bank of America statement window | unverified | medium | V3 |
| A07 | Capital One statements and transaction list windows | supported | high | G8, V4 |
| A08 | Hosted Link URL lifetime and session data window | supported | high | G1 |
| A09 | Plaid Trial support availability wording | stale | medium | V6 |
| A10 | Acorns third-party access caveats | supported | medium | G16 |
| A11 | EasyOCR Thai support and Docling offline model prefetch | supported | medium | G19 |
| A12 | Paperless-ngx behaviour relevant to Originals | supported | high | — |

```csv
claim_id,review_target,verdict,confidence,baseline_locator,evidence_url_or_file,retrieved_date,short_supporting_passage,issue_or_qualification,smallest_correction,test_or_follow_up
C01,Plaid Trial eligibility and actual real-account access,partially_supported,high,report #feeds para 1-2; FIELD-GUIDE.md > Connection facts #2; PC-setup-runbook.txt INITIAL COSTS,https://plaid.com/docs/account/billing/ ; https://support.plaid.com/hc/en-us/articles/39994173227159 ; https://support.plaid.com/hc/en-us/articles/16110502116887,2026-10-31,"Free Trial plans are available to new Plaid teams (US/Canada only) created on or after April 15, 2026. | The Trial plan is available to developers who: Are located in the United States or Canada; Do not already have an existing Plaid Production or Limited Production account. | Support cases are available only on paid plans.","Real production data on Trial is supported, but eligibility is narrower than 'eligible personal developers': new team after 2026-04-15, no prior Production/Limited Production, MSA + security attestations, identity verification; no support cases (live page; cached copy differed).",Replace eligibility wording with the exact conditions; add 'create the team first and confirm the Trial button' as step 0.,G0
C02,Plaid lifetime Item quota and household login accounting,supported,high,FIELD-GUIDE.md > Connection facts #2; report #feeds para 2; PC-setup-runbook.txt step 3,https://support.plaid.com/hc/en-us/articles/39994173227159 ; https://plaid.com/docs/account/billing/ ; https://plaid.com/docs/link/duplicate-items/,2026-10-31,Trial plan accounts can create up to 10 Items ... An Item represents one end-user connection to a financial institution. | Calling /item/remove on the Trial plan does not free up slots ... This includes duplicate Items created when a user links the same account more than once. | A duplicate Item will be created if the end user logs into the same institution with the same credentials a second time through Plaid Link,"Item = login (baseline correct). Missing: explicit budget (8 institutions already), 'never re-link, use update mode' rule, and that a paid upgrade is one-way and starts subscription billing on existing Items.",Add the Item budget table with two reserve slots and the no-re-link rule.,"G2, G9"
C03,Eight exact institution entries and product flags,supported,high,baseline/verified-provider-coverage.csv rows 1-8; baseline/account-connection-plan.csv rows 1-8,review/evidence/plaid_us_institution_coverage_2026-10-31.csv (downloaded from https://plaid.com/documents/us_institution_coverage.csv) ; https://plaid.com/docs/institutions/,2026-10-31,"Generated on: 2026-10-16T03:26:16.866Z (10,304 rows). ins_127989 Bank of America 1,1,0,1,1; ins_128026 Capital One 1,1,0,1,0; ins_116960 M1 Finance 1,1,1,1,0; ins_54 Robinhood 1,1,1,1,0; ins_137662 Acorns 1,1,1,0,1; ins_138348 Raisin 1,1,0,0,0; ins_132083 Venmo - Personal 1,1,0,1,0; ins_123709 Transamerica - Life Insurance 1,1,1,0,0 (balance,transactions,investments,liabilities,statements). | This table is not updated in real time","All eight rows and flags reproduce exactly from the current file; flags are institution-level and say nothing about sub-accounts (Acorns Later, Robinhood crypto, Raisin deposits) or policy fields.",None to the rows; add 'institution-level only' next to every flag.,"G3, G15-G18"
C04,Local production Hosted Link onboarding,partially_supported,medium,report #feeds para 3; PC-setup-runbook.txt step 6,https://plaid.com/docs/link/hosted-link/ ; https://plaid.com/docs/api/link/ ; https://plaid.com/docs/link/oauth/,2026-10-31,"you may want to use /link/token/get if your integration does not use webhooks | Session data will be provided for up to six hours after the session has ended. | Hosted Link should be used only when Plaid Link SDKs cannot be used. | If Plaid isn't delivering the URL, the default lifetime is 30 minutes. | redirect_uri ... When used in Production, must be an https URI.",Documented but not demonstrated; Plaid discourages Hosted Link outside listed cases; whether a web session needs an HTTPS redirect_uri is unstated; the owner must complete login within the link lifetime and the poller within six hours.,Keep the route; add the fallback (web Link SDK on one static HTTPS page) and the timing constraints.,G1
C05,"BofA account types, liabilities and PDF statements",contradicted,high,"account-connection-plan.csv row Bank of America (primary_route, intended_cadence); report #coverage table column PDF statements",https://plaid.com/docs/statements/ ; https://plaid.com/docs/liabilities/ ; https://support.plaid.com/hc/en-us/articles/25348952076567 ; https://plaid.com/docs/link/oauth/,2026-10-31,"Statements currently supports only bank depository accounts (e.g. checking and savings accounts). | liabilities data does not contain detailed transaction history for credit card accounts | For checking, savings, and mortgage accounts, transactions are available for the most recent 18 months. For credit cards ... the current partial cycle, plus the 11 previous statement cycles. | Bank of America (new API only ...) ... required every 12 months",Card statements cannot come from Plaid Statements; card transaction history is 12 cycles; annual consent refresh applies.,Route: API statements for checking/savings only; card statements by portal download; add annual consent refresh to human steps.,"G3, G9, G14"
C06,Capital One 90-day feed and older-record backfill,partially_supported,high,report #feeds callout; account-connection-plan.csv row Capital One,https://support.plaid.com/hc/en-us/articles/25349321999511 ; https://support.plaid.com/hc/en-us/articles/25286986638231 ; https://support.plaid.com/hc/en-us/articles/25922395286935 ; https://www.capitalone.com/help-center/checking-savings/online-statements/ ; https://www.capitalone.com/help-center/checking-savings/transaction-history/,2026-10-31,"For Capital One accounts, only 90 days of transaction history is available. This limit is imposed by Capital One | The transaction data that Capital One provides does not include pending transactions. | /transactions/refresh is not supported on Items that include only non-depository accounts | You can view up to 7 years of statements online for active accounts. | Your past transactions list will show the past two years of account activity on the website.",90-day limit confirmed verbatim. Backfill path partly verified (statements 7 years online); CSV export window for cards unverified (third parties say ~90 days). No pending data; no refresh for card-only Items; annual consent refresh.,Add the pending/refresh/consent facts to the Capital One row; backfill = PDF statements (7 years) parsed locally.,"G5, G8"
C07,"M1, Robinhood and Acorns investment coverage",partially_supported,medium,"account-connection-plan.csv rows M1 Finance, Robinhood, Acorns / Later; report #coverage",https://plaid.com/docs/investments/ ; https://support.plaid.com/hc/en-us/articles/40621176117271 ; https://help.m1.com/en/articles/9331947 ; https://help.m1.com/en/articles/9331948 ; https://support.acorns.com/hc/en-us/articles/Third-Party-Integrations ; https://snaptrade.com/brokerage-integrations/robinhood-api,2026-10-31,"The /investments/transactions/get endpoint provides up to 24 months | Inflow, such as stock sales, is shown as a negative amount, and outflow ... is positive | tax_lots array ... or an empty array when the institution provides no lot-level data | M1: Only the past 3 years of monthly statements, trade confirmations, and tax documents are available for direct download. | Acorns: all your accounts won't connect or show up on every third-party app ... 1-3 business days | Robinhood via SnapTrade: Read-Only OAuth access ... this integration does not offer the ability to place trades.","Holdings/activity support is documented; Later/IRA visibility, Robinhood crypto sub-accounts and lot availability are unverified; sign conventions must be normalized.",Add sign-normalization rule and per-sub-account verification to the rows.,"G15, G16"
C08,Raisin underlying deposits and consolidated statements,partially_supported,medium,account-connection-plan.csv row Raisin US; report #account-specific,review/evidence/plaid-directory-extract-2026-10-31.csv ; https://www.raisin.com/en-us/education-center/how-to-read-your-raisin-account-statement/ ; https://support.raisin.com/hc/en-us/articles/44349853710228,2026-10-31,"ins_138348 Raisin balance 1, transactions 1, auth 0, statements 0 | Statements are available digitally in your Documents tab ... Print/Save button | Note that interest details for inactive (closed) deposits are not included in the current statement. | (Raisin help) Linking your primary bank account allows you to make deposits and withdrawals and is required to use Raisin.",Directory support only; whether each partner-bank product appears as its own account is unverified; closed-deposit interest needs statements/tax documents; Raisin documents Plaid only for funding-bank links.,Add the closed-deposit caveat; keep per-product verification.,G17
C09,Transamerica Life feed versus actual IUL values,partially_supported,medium,baseline/verified-provider-coverage.csv row Transamerica; report #account-specific,review/evidence/plaid-directory-extract-2026-10-31.csv ; https://insuranceservicenow.transamerica.com/FAQs.aspx,2026-10-31,"ins_123709 Transamerica - Life Insurance balance 1, transactions 1, investments 1, auth 0, statements 0; separate entry ins_127593 Transamerica - Retirement - NetXInvestor | The Cash Value, if any, is listed on the left hand side of the page under the Current Account Summary section.",Exact Life entry confirmed; field meanings and the correct portal for the policy unknown; the Item slot cannot be reclaimed if the feed proves useless.,Decide before linking whether to spend an Item; otherwise document-only.,G18
C10,Nationwide Life availability and fallback,supported,high,report #coverage para 'Nationwide needs product-level matching'; account-connection-plan.csv row Nationwide,review/evidence/plaid-directory-extract-2026-10-31.csv ; https://www.nationwide.com/personal/insurance/life/online-access-benefits,2026-10-31,"Directory name matches: ins_137009 Nationwide - Retirement; ins_116555 Nationwide Retirement Solutions - Deferred Compensation Plan; ins_131928 Nationwide Securities, LLC; ins_121040 Axos Bank for Nationwide. No Life entry. | Access policy documents: Log in > Select your policy > Document Center",Correctly qualified; fallback is an attended portal download (or a scripted downloader after G14 passes).,None.,V10
C11,Statement API history and recurring collection,partially_supported,high,"report #feeds para 7 and #documents; account-connection-plan.csv rows Bank of America, Acorns",https://plaid.com/docs/statements/ ; https://plaid.com/docs/api/products/statements/,2026-10-31,"You can request up to two years of data. | Statements currently supports only bank depository accounts | Statements does not currently support all major or long-tail institutions, and should be used with a fallback option | If the user connected their account less than two years ago, they can bypass the Link credentials pane and complete just the Statements consent step.",Two years is a ceiling; depository only; adding Statements to an existing Item needs an owner consent step via update mode; /statements/refresh exists but its behaviour was not verified.,Request statements in the initial link for Bank of America deposits; treat cards as portal-only.,G3
C12,"SimpleFIN price, quotas, history and data shape",supported,high,report #choices rows SimpleFIN + Actual Budget and para after the table,https://beta-bridge.simplefin.org/ ; https://beta-bridge.simplefin.org/info/developers ; https://www.simplefin.org/protocol.html ; https://actualbudget.org/docs/advanced/bank-sync/simplefin/ ; https://actualbudget.org/docs/api/reference/,2026-10-31,"Connect up to 25 institutions and 25 apps for either: $1.50 + tax per month, or $15.00 + tax per year | you are expected to make 24 requests or fewer per day | The date range of requests to /accounts ... is limited to 90 days at a time. The number of days of history available varies for each institution. | (Actual) Currently, the sync pulls at most 90 days of data from each linked account ... upstream provider, MX | runBankSync ... Run the 3rd party (GoCardless, SimpleFIN) bank sync operation",Interval vs history correctly distinguished; schema is balances/transactions only; institution coverage for the eight names not publicly listed (V1).,None.,V1
C13,SnapTrade Personal free use and broker coverage,supported,high,report #choices row SnapTrade Personal; account-connection-plan.csv row Robinhood,https://snaptrade.com/personal ; https://docs.snaptrade.com/docs/personal-vs-commercial ; https://snaptrade.com/brokerage-integrations/robinhood-api ; https://snaptrade.com/faq,2026-10-31,Free for personal use. Up to 20 brokerage connections | Personal users are currently completely free. | Read-Only OAuth access ... this integration does not offer the ability to place trades. | Standard transaction history is refreshed daily and delayed by one day on both options.,"Connection count resolved at 20; Robinhood read-only; M1/Acorns not found on the listing pages read (V2); the Personal consumer key can trade where enabled, so never implement order endpoints.",None beyond V2.,V2
C14,Tiller exclusion and spreadsheet alternatives,supported,high,report #choices row Tiller,https://tiller.com/pricing/ ; https://help.tiller.com/en/articles/432695 ; https://community.tiller.com/t/update-to-tillers-annual-price-starting-in-august-2026/34853,2026-10-31,"After 30 days, Tiller is just $99/year | Auto Fill is not available for Excel at this time. You must click the 'Fill Available Updates' button | Auto Fill is enabled for all new users on Google Sheets to automatically get new/available transaction and balance data into your spreadsheet every 6 hours","Accurate. The mature-tool alternative worth comparing is Actual Budget + SimpleFIN, not Tiller (see REVIEW.md architecture).",None.,—
C15,Complete Drive export and file/version identity,partially_supported,high,report #documents bullet Google Drive; PC-setup-runbook.txt steps 10-12,https://developers.google.com/workspace/drive/api/guides/manage-downloads ; https://rclone.org/drive/,2026-10-31,"Exported content is limited to 10 MB. | You can only download blob file content revisions that are marked as 'Keep Forever'. | By default the export formats are docx,xlsx,pptx,svg",Export support confirmed; the plan lacks a version identity rule (file id + modifiedTime + md5) and a per-tab values export; the workbook size vs 10 MB is unknown.,Add identity rule and size check.,G13
C16,Email collection and Google OAuth longevity,supported,high,report #documents 'A setup trap to avoid'; FIELD-GUIDE.md > Connection facts #5; runbook step 11,https://developers.google.com/identity/protocols/oauth2 ; https://support.google.com/cloud/answer/15549945 ; https://developers.google.com/identity/protocols/oauth2/production-readiness/restricted-scope-verification ; https://support.google.com/cloud/answer/7454865 ; https://developers.google.com/workspace/gmail/api/guides/list-messages,2026-10-31,publishing status of 'Testing' is issued a refresh token expiring in 7 days | Authorizations by a test user will expire seven days from the time of consent. | Personal use ... advancing through the unverified app screen | your app will be limited to 100 new users until it is [verified],"Correct, but the plan never names the fix: publish to In production without verification.",Apply correction C-6 in REVIEW.md.,G12
C17,OpenClaw browser downloads and shipped Linux features,supported,medium,report #browser paras 1-4; FIELD-GUIDE.md > Connection facts #6; runbook step 13,https://docs.openclaw.ai/platforms/linux ; https://docs.openclaw.ai/tools/browser-login ; https://docs.openclaw.ai/tools/browser-control ; https://docs.openclaw.ai/tools/browser/existing-session ; https://docs.openclaw.ai/install/ ; https://docs.openclaw.ai/releases ; https://github.com/openclaw/openclaw/pull/101369,2026-10-31,"starts the Gateway as a systemd user service | Local managed browsers are headless by default ... headless shell cannot show a login window | Automated logins often trigger anti-bot defenses and can lock the account. | Playwright-only features - PDF export, download interception ... require a Playwright-backed profile | openclaw browser download e12 report.pdf / waitfordownload | Node 24.16.0+ on 24.x, or 26.1.0+ | v2026.10.6 (latest) | feat(browser): expose agent download actions ... Merged",Claims are current; unattended portal downloads remain unproven per site; the browser is the highest-privilege component.,Defer OpenClaw; use manual monthly downloads until a scripted downloader passes three runs.,"G14, V14"
C18,"Arch runtime, Python isolation, OCR and local AI feasibility",supported,high,report #pc paras 'Arch setup' and 'Arch's ollama package'; runbook step 2,https://archlinux.org/packages/extra/x86_64/uv/ ; https://archlinux.org/packages/extra/x86_64/docker-compose/ ; https://wiki.archlinux.org/title/Ollama ; https://wiki.archlinux.org/title/Python ; https://docling-project.github.io/docling/usage/advanced_options/ ; https://docling-project.github.io/docling/usage/gpu/ ; https://docs.ollama.com/linux ; https://docs.ollama.com/capabilities/structured-outputs ; https://github.com/j1mmyson/EasyOCR,2026-10-31,"uv 0.13.1-1 (Extra, build 2026-10-14) | docker-compose 5.6.1-1 (Extra, build 2026-10-21) | Install the ollama package, which provides ... CPU inference. For GPU inference: ollama-vulkan / ollama-cuda / ollama-rocm | Docling: prefetch EasyOCR recognition models for specific languages | Structured outputs let you enforce a JSON schema on model responses | EasyOCR languages include Thai (th)",Packages and backends exist; hardware unknown; CPU-only OCR throughput unmeasured; OpenClaw needs Node 24.16+/26.1+.,Keep hardware inspection first; benchmark before installing AI components.,G19
C19,Unattended systemd jobs and credentials after reboot,partially_supported,high,report #pc 'Scheduling'; runbook steps 5 and 16,https://www.freedesktop.org/software/systemd/man/latest/systemd.timer.html ; https://www.freedesktop.org/software/systemd/man/latest/loginctl.html,2026-10-31,Persistent= ... catch up on missed runs of the service when the system was powered down. Note that this setting only has an effect on timers configured with OnCalendar=. | WakeSystem= ... requires privileges and is thus generally only available in the system service manager. | enable-linger ... a user manager is spawned for the user at boot and kept around after logouts.,Mechanisms confirmed; the plan leaves credential storage open; desktop keyrings are unavailable before graphical login; user timers cannot wake a suspended PC.,Secrets in 0600 files or systemd-creds; daily OnCalendar + Persistent; accept next-wake catch-up.,G10
C20,"Financial normalization, duplicate control and reconciliation",partially_supported,high,report #reconciliation bullets; FIELD-GUIDE.md > Completion criteria; runbook step 15,https://plaid.com/docs/api/products/transactions/ ; https://plaid.com/docs/investments/ ; https://support.plaid.com/hc/en-us/articles/40621176117271 ; https://support.plaid.com/hc/en-us/articles/15373441901207 ; https://support.plaid.com/hc/en-us/articles/25286986638231,2026-10-31,"The item_id is always unique; linking the same account at the same institution twice will result in two Items | added / modified / removed ... next_cursor | buy transactions are always positive, the entire transaction is represented as an outflow | balances object within the /transactions/sync response is accurate as of the time Plaid made our scheduled request | Capital One ... does not include pending transactions","Goals stated; provider semantics (pending_transaction_id linkage, removed handling, sign conventions, as-of balances, no-pending institutions) and the ambiguous-transfer rule are not written down.",Adopt the schema invariants in REVIEW.md 'Smallest workable architecture' item 3.,"G4, G5, G6, G7, G11"
C21,AI/OCR extraction acceptance and financial precision,partially_supported,medium,report #documents bullet 'Save facts with evidence'; report #reconciliation last para; runbook AUTOMATIC ACCEPTANCE,https://docs.ollama.com/capabilities/structured-outputs ; https://docling-project.github.io/docling/usage/advanced_options/,2026-10-31,Structured outputs let you enforce a JSON schema on model responses | Docling: The main purpose of Docling is to run local models which are not sharing any user data with remote services,"Principle is right; acceptance rules are not specified (statement arithmetic, cross-source totals, numeric fields never sourced from a model, two-engine agreement on scans).",Write the acceptance rules; benchmark on 20 documents.,"G7, G19"
C22,Starting cost and actual ongoing human burden,partially_supported,medium,report #cost paras 1-2; FIELD-GUIDE.md > User objective and Completion criteria; runbook INITIAL COSTS,https://plaid.com/docs/account/billing/ ; https://plaid.com/docs/link/oauth/ ; https://beta-bridge.simplefin.org/ ; https://snaptrade.com/personal,2026-10-31,"Trial – Free access. Limited to 10 Items | If you added a subscription fee product ... upon upgrading to a paid plan, you will begin to be charged | Consent refresh ... required every 12 months | $15.00 + tax per year | Free for personal use","$0 is conditional on G0; hidden recurring work: annual consent refresh at two institutions, ad hoc Item repairs, monthly card-statement downloads, attended IRS/insurer portals; no Plaid support on Trial.",Replace the cost paragraph with the conditional model in REVIEW.md 'Human work that remains'.,"G0, G9, G14"
C23,Smallest workable architecture and competing tools,partially_supported,high,report #choices table and #pc; FIELD-GUIDE.md > Recommended architecture,review/REVIEW.md > Smallest workable architecture,2026-10-31,—,Optional tools are sequenced as if cumulative; Paperless duplicates Originals; OpenClaw/Ollama/Docling are not needed for any gate; Actual Budget + SimpleFIN is the mature fallback ledger.,"Keep Plaid collector + SQLite + rclone/Gmail scripts + systemd; defer OpenClaw, Ollama, Docling, Paperless; remove Tiller and duplicate stores.",G0-G12 with the minimal stack only
C24,"Credentials, browser scope, document instructions and recovery",partially_supported,high,"report #browser last para; report #reconciliation; runbook steps 5, 13, 16",https://docs.openclaw.ai/gateway/security/browser-control ; https://docs.snaptrade.com/docs/build-with-ai ; https://www.simplefin.org/protocol.html ; https://raw.githubusercontent.com/paperless-ngx/paperless-ngx/main/docs/faq.md,2026-10-31,"Enabling browser control gives the model a real browser. If that profile already has logged-in sessions, the model can access those accounts and data | Your consumerKey can access your brokerage data and may be able to trade where trading is enabled | Stores Access URLs at least as securely as the user's financial data | Paperless-ngx never modifies your original documents","Concrete secrets: Plaid access tokens, Google refresh token, SimpleFIN access URL, SnapTrade consumer key (trade-capable), browser profile with bank sessions. Prompt injection matters only if an LLM reads documents or pages while holding tools; the minimal stack has no such path. Restore test not planned.",Add nightly sqlite .backup + Originals copy and one restore drill; keep LLMs away from tool-holding contexts.,G10
C25,"Source completeness, dates and reproducibility",partially_supported,medium,"baseline/research-material.json searches 1,4,5,9,23,26,28; baseline/sources.json; report #sources",review/evidence/SOURCE-PASSAGES.md,2026-10-31,"Directory file re-downloaded 2026-10-31 still reports Generated on: 2026-10-16T03:26:16.866Z with 10,304 rows.",Sources are first-party and accurate at retrieval; the log contains Windows-era queries; the Plaid Trial page changed wording between two fetches; no raw captures are bundled (this review adds verbatim passages).,Record retrieval dates per claim at setup.,—
C26,"Work income, IRS, family loans and unrecorded cash",supported,high,"report #account-specific bullets Work income, IRS, Family support",https://www.irs.gov/payments/online-account-for-individuals-frequently-asked-questions ; https://www.irs.gov/payments/online-account-for-individuals ; https://help.venmo.com/cs/articles/transaction-history-vhel281,2026-10-31,"No. Only the taxpayer should log into their account. Credentials should never be shared with others. | each account transcript only covers a single tax year, and may not show the most recent penalties, interest, changes or pending actions | Account statements allow you to view a detailed history of your Venmo transactions in a downloadable CSV file.",Correct boundaries; these remain attended or human-supplied facts.,None.,—
A01,"Transactions history depth is fixed at Item creation (days_requested, max 730)",supported,high,runbook steps 6-7 (omission); report #feeds para 7,https://support.plaid.com/hc/en-us/articles/24631662544919 ; https://plaid.com/docs/transactions/,2026-10-31,"Once an Item is created and has received its historical pull of transaction information, its transaction history length cannot be extended except by deleting and then recreating the Item | The default is 90 days and the maximum is 730 days",Recreating an Item consumes a Trial slot.,Set days_requested=730 in every /link/token/create.,G3
A02,OAuth consent refresh every 12 months at Capital One and Bank of America (new API),supported,high,"account-connection-plan.csv rows Bank of America, Capital One (omission)",https://plaid.com/docs/link/oauth/ ; https://plaid.com/docs/link/update-mode/,2026-10-31,"Consent refresh at these institutions is required every 12 months, unless noted otherwise. ... Bank of America (new API only ...) ... Capital One | call /item/get and note the consent_expiration_time field","Recurring attended work; no webhook in the local design, so poll /item/get.",Store consent_expiration_time; exception 30 days ahead; repair via update mode.,G9
A03,Investment amount signs and buy/contribution representation,supported,high,report #reconciliation (omission),https://plaid.com/docs/investments/ ; https://support.plaid.com/hc/en-us/articles/40621176117271,2026-10-31,"Inflow, such as stock sales, is shown as a negative amount, and outflow, such as stock purchases, is positive. | the entire transaction is represented as an outflow",Must be normalized before cash-flow math.,Normalization rule in schema notes.,G15
A04,Balances from /transactions/sync are as-of Plaid's last scheduled pull,supported,high,report #reconciliation 'Reconcile opening balances' (omission),https://support.plaid.com/hc/en-us/articles/15373441901207,2026-10-31,the balances object within the /transactions/get or /transactions/sync response is accurate as of the time Plaid made our scheduled request for transaction data,Use /accounts/balance/get for a dated real-time value when reconciling.,Record balance source and timestamp.,G7
A05,Upgrading from Trial is one-way and starts subscription billing on existing Items,supported,high,report #feeds 'Paid pricing must be checked',https://plaid.com/docs/account/billing/ ; https://support.plaid.com/hc/en-us/articles/39917307426967,2026-10-31,"If you added a subscription fee product (such as Investments, Liabilities, or Transactions) to an Item during your trial, upon upgrading to a paid plan, you will begin to be charged for that subscription. | Once your Production account is approved, you cannot revert to the Trial plan.",Exceeding 10 Items converts every existing Item into billable subscriptions.,State in the Item budget.,G2
A06,Bank of America statement window,unverified,medium,account-connection-plan.csv row Bank of America fallback,https://info.bankofamerica.com/en/digital-banking ; https://promotions.bankofamerica.com/digitalbanking/instructions/manage-statements-documents.html,2026-10-31,"You can view, print and download up to 18 months of your statements at any time. | The most recent 6 years of monthly statements may be viewed online immediately.",Two first-party pages conflict; copies up to 7 years can be ordered.,Check the year selector in Online Banking.,V3
A07,Capital One statements and transaction list windows,supported,high,account-connection-plan.csv row Capital One fallback,https://www.capitalone.com/help-center/checking-savings/online-statements/ ; https://www.capitalone.com/help-center/checking-savings/transaction-history/ ; https://www.capitalone.com/learn-grow/money-management/how-long-to-keep-credit-card-statements,2026-10-31,You can view up to 7 years of statements online for active accounts. | Your past transactions list will show the past two years of account activity on the website. | Capital One keeps up to seven years of credit card statements online for active accounts.,Card CSV export window still unverified (V4).,Backfill Capital One from PDF statements.,"G8, V4"
A08,Hosted Link URL lifetime and session data window,supported,high,report #feeds para 3,https://plaid.com/docs/link/hosted-link/ ; https://plaid.com/docs/api/link/,2026-10-31,"If Plaid isn't delivering the URL, the default lifetime is 30 minutes. | Cannot be longer than 21 days. | Session data will be provided for up to six hours after the session has ended.",Owner-attended timing constraint.,Set url_lifetime_seconds for the sitting; poll within six hours.,G1
A09,Plaid Trial support availability wording,stale,medium,report #feeds (no claim); sources.json #1,https://support.plaid.com/hc/en-us/articles/39994173227159 (two fetches on 2026-10-31: extraction-service copy vs real-browser copy),2026-10-31,"Cached copy: Trial plan customers can get support by starting a conversation at dashboard.plaid.com/support/new. | Live copy: Trial plan customers can ask Bill, Plaid's AI assistant. Support cases are available only on paid plans.",Page in flux; plan for no human support on Trial.,Re-read at setup; record the date.,V6
A10,Acorns third-party access caveats,supported,medium,account-connection-plan.csv row Acorns / Later,https://support.acorns.com/hc/en-us/articles/Third-Party-Integrations,2026-10-31,all your accounts won't connect or show up on every third-party app | it takes 1-3 business days for the updates to happen | Our Two-Factor Authentication is triggered ... 3rd party integrations,Page dated 2021-03-03; Later visibility must be tested.,None.,G16
A11,EasyOCR Thai support and Docling offline model prefetch,supported,medium,report #documents bullet 'English and Thai records',https://github.com/j1mmyson/EasyOCR ; https://docling-project.github.io/docling/usage/advanced_options/,2026-10-31,"Thai (th) in the EasyOCR language list | To prefetch EasyOCR recognition models for specific languages, repeat --easyocr-lang",Capability exists; accuracy on the owner's documents unmeasured.,None.,G19
A12,Paperless-ngx behaviour relevant to Originals,supported,high,report #pc 'An archive tool may own its own internal media store',https://raw.githubusercontent.com/paperless-ngx/paperless-ngx/main/docs/faq.md ; https://raw.githubusercontent.com/paperless-ngx/paperless-ngx/main/docs/setup.md,2026-10-31,"Files consumed from the consumption directory are re-created inside this media directory and are removed from the consumption directory itself. | Paperless-ngx never modifies your original documents. | For most users, Docker is the best option.","Confirms the duplication concern; copy into consume, never move Originals.",Defer Paperless.,—
```


---

# Part 6: SOURCE-PASSAGES (verbatim evidence)

_Source file: `evidence/SOURCE-PASSAGES.md`_

# Source passages captured during the review (retrieved 2026-10-31)

Method notes. The review sandbox's outbound proxy refused direct connections to plaid.com, support.plaid.com, developers.google.com, support.google.com, docs.openclaw.ai, docs.paperless-ngx.com, institution sites and wiki.archlinux.org. Pages were therefore read through (a) Tavily page extraction ("extract"), (b) a TinyFish real-browser fetch ("browser fetch"; used where extraction dropped list items or the site is JavaScript-rendered), and (c) direct downloads from raw.githubusercontent.com ("raw"). Quotations are verbatim from the returned text; "[...]" marks omitted text. Where two retrievals of the same page differed, both are shown. Nothing here is live-account evidence.

## Plaid

### https://support.plaid.com/hc/en-us/articles/39994173227159-What-is-the-Plaid-Trial-plan (extract and browser fetch)
- "The Plaid Trial plan provides free access to Plaid's production APIs. You can connect real financial accounts, call production endpoints, and build projects — no business registration, security questionnaire, or sales process required."
- Browser fetch: "The Trial plan is available to developers who: Are located in the United States or Canada; Do not already have an existing Plaid Production or Limited Production account."
- "US and Canadian institutions are available on Trial plans, all other institutions are not currently available on this plan type."
- Browser fetch: "Applying for a Trial plan requires accepting Plaid's standard Master Services Agreement (MSA). In the Agreements step of the application you'll check 'I agree to the latest Plaid Master Services Agreement,' along with attestations about keeping your accounts, data, and code secure." (The extraction copy read "Master Services Authorization Agreement".)
- Browser fetch, "What's included": "Auth — retrieve account and routing numbers; Transactions (including Recurring Transactions and Transactions Refresh); Balance — retrieve real-time account balances; Identity (including Identity Match) — retrieve account owner information; Assets — generate asset reports; Liabilities — retrieve loan and credit card data; Investments (including Investments Refresh); Statements — retrieve bank statements".
- Browser fetch, "What's not included": "Identity Verification; Signal Transaction Scores; Transfer; Consumer Report (by Plaid Check); Monitor; Protect; Income; Investments Move; Enrich; Layer; Payment Initiation".
- "Trial plan accounts can create up to 10 Items (connected financial accounts) in production. An Item represents one end-user connection to a financial institution."
- "API calls against your existing connected Items are not capped — you can make unlimited API calls to the Items you've already connected."
- "Calling /item/remove on the Trial plan does not free up slots against your 10-Item cap. If you've reached the limit, you'll need to upgrade to a paid Production plan to connect more. All access tokens created in Production will count against your Trial plan Item limit. This includes duplicate Items created when a user links the same account more than once."
- "The Trial plan includes immediate access to almost all OAuth institutions, including Bank of America, Chase, Wells Fargo, Capital One, Citi, Navy Federal, PNC, U.S. Bank, American Express, and Merrill. You don't need to complete the OAuth registration requirements in the Dashboard until you upgrade to a paid plan."
- "Most Trial plan applications are approved automatically after identity verification. If your application is flagged for manual review, Plaid's Customer Oversight team will follow up within 2–3 business days via email."
- Extraction copy: "Trial plan customers can get support by starting a conversation at dashboard.plaid.com/support/new." Browser fetch minutes later: "Trial plan customers can ask Bill, Plaid's AI assistant. Support cases are available only on paid plans."
- "Upgrading from the Trial plan to Production is a one-way change. Once your Production account is approved, you cannot revert to the Trial plan."

### https://plaid.com/docs/account/billing/ (extract)
- "Trial – Free access. Limited to 10 Items; upgrade to a paid plan to access more Items. Most appropriate for hobbyist use, or for evaluating and learning more about Plaid."
- "Pay-as-you-go – No minimum spend or commitment. Most appropriate for hobbyist use, or for early-stage small businesses."
- "A price list is not available in the documentation. To view pricing, apply for Production access."
- "Free Trial plans are available to new Plaid teams (US/Canada only) created on or after April 15, 2026."
- "You can create 10 Production Items on a Trial plan. After creating 10 Items in Production, you must upgrade to a paid plan to create more Production Items. Removing Items created on a Trial plan (using /item/remove) will not allow you to create more Items."
- "When using a Trial plan, be sure to persist your access tokens and do not lose track of them. All access tokens created in Production will count against your Trial plan Item limit."
- "The following products are available via Trial plans: Assets, Auth, Balance, Identity, Investments (including Investments Refresh), Liabilities, Transactions (including Transactions Refresh), Statements"
- "If you added a subscription fee product (such as Investments, Liabilities, or Transactions) to an Item during your trial, upon upgrading to a paid plan, you will begin to be charged for that subscription."
- "Upon upgrading to a paid plan, you will only retain Production access to any products you explicitly requested in your Production request form."

### https://support.plaid.com/hc/en-us/articles/16110502116887-What-are-Plaid-s-prices-and-pricing-plans-and-how-do-they-differ (browser fetch)
- "For developers in the US and Canada creating a new Plaid team on or after April 15, 2026, Plaid offers a free Trial plan. The Trial plan lets you use Plaid with real production data at no cost, with a cap of 10 Production Items. It includes eight bundled products: Auth, Transactions (including Transactions Refresh), Balance, Identity, Assets, Liabilities, Investments (including Investments Refresh), and Statements."
- "The Trial plan is available to new Plaid accounts that have not yet applied for or been granted any form of Production access. If your team has a pending or approved Production application, or existing Limited Production access, the Trial plan is not available — there is currently no self-service way to switch."

### https://support.plaid.com/hc/en-us/articles/39917307426967-How-do-I-upgrade-from-the-Trial-plan-to-a-paid-Production-plan (extract)
- "The Trial plan lets you build with real Production data at no cost, with a cap of up to 10 Production Items."
- "Describe your business — Enter your business type, business details, industry, and app details."
- "Once you submit a Production access application, you cannot revert to the Trial plan."

### https://support.plaid.com/hc/en-us/articles/16110110883479 (search snippet, "How are Sandbox, Production, Trial plan, and Limited Production different?")
- "Availability | All developers | All developers | US/CA developers, signups on or after April 15, 2026 | Existing Limited Production customers only (no new US/CA signups after April 15, 2026)"

### https://support.plaid.com/hc/en-us/articles/25349321999511-Why-am-I-not-getting-the-full-transaction-history-for-Capital-One-accounts (extract, advanced)
- "For Capital One accounts, only 90 days of transaction history is available. This limit is imposed by Capital One, so increasing transactions.days_requested above 90 will not return additional history. To retain transaction history beyond the 90-day window for these accounts, store transactions on your side as you receive them via /transactions/sync."

### https://support.plaid.com/hc/en-us/articles/25286986638231-Are-pending-transactions-returned-for-Capital-One-accounts (extract)
- "The transaction data that Capital One provides does not include pending transactions. As a result, pending transactions will not show in API data for those accounts. Transactions for Capital One accounts will surface via /transactions/sync once they post. If your application needs a current-day view of the current balance, you can call /accounts/balance/get to retrieve real-time balance information."

### https://support.plaid.com/hc/en-us/articles/25922395286935 (extract)
- "For Capital One (ins_128026), /transactions/refresh is not supported on Items that include only non-depository accounts (e.g., credit cards), and calling it on such an Item will return a PRODUCTS_NOT_SUPPORTED error. Capital One depository accounts (checking, savings) do support /transactions/refresh."

### https://support.plaid.com/hc/en-us/articles/25348952076567-Why-is-the-full-transaction-history-missing-for-Bank-of-America-accounts (extract)
- "to receive more than 90 days of transaction history, you will need to specify that in the transactions.days_requested parameter"
- "For checking, savings, and mortgage accounts, transactions are available for the most recent 18 months. For credit cards (personal and small business), transactions are available for the current partial cycle, plus the 11 previous statement cycles."

### https://support.plaid.com/hc/en-us/articles/24631662544919-Why-does-this-Item-include-only-three-months-of-transaction-history (extract)
- "If left unspecified, this option defaults to a 90-day transaction history for the Item. [...] The maximum allowable value is 730 days, allowing for the retrieval of up to two years of transaction data for an Item."
- "Once an Item is created and has received its historical pull of transaction information, its transaction history length cannot be extended except by deleting and then recreating the Item with the desired transactions.days_requested value."

### https://plaid.com/docs/transactions/ (extract, query-focused)
- "When Transactions is first initialized on an Item, days_requested controls how many days of history Plaid requests from the financial institution in the initial pull. The default is 90 days and the maximum is 730 days (about 24 months)."
- "Once the Item exists, Plaid retains every new transaction it sees, so the amount of available history grows for as long as the Item remains connected. /transactions/sync returns everything Plaid has stored for the Item, and the start_date parameter on /transactions/get has no age limit."

### https://plaid.com/docs/api/products/transactions/ (extract, query-focused)
- "The item_id is always unique; linking the same account at the same institution twice will result in two Items with different item_id values."
- Sample sync loop: "added = added.concat(data.added); modified = modified.concat(data.modified); removed = removed.concat(data.removed); [...] cursor = data.next_cursor".

### https://support.plaid.com/hc/en-us/articles/15373441901207 (extract)
- "requests to the /accounts/balance/get endpoint directly contact the financial institution in real-time to get the current balance at that precise moment in time. Whereas, the balances object within the /transactions/get or /transactions/sync response is accurate as of the time Plaid made our scheduled request for transaction data from your institution."
- "depending on the institution, these checks for fresh data occur less frequently, such as once per day. An Item's status.transactions.last_successful_update field, available via /item/get, will show the timestamp of the most recent successful update."

### https://support.plaid.com/hc/en-us/articles/40621176117271 (extract)
- "Investments transactions with type : buy and subtype : contribution actually represent two simultaneous transactions: a cash contribution (inflow) and the purchase of a security (outflow). [...] Since buy transactions are always positive, the entire transaction is represented as an outflow."

### https://support.plaid.com/hc/en-us/articles/16995061807255 (extract)
- "Note: this article is in reference to European institutions only" (date versus authorized_date semantics; not applicable to US Items).

### https://plaid.com/docs/investments/ (extract, query-focused)
- "The /investments/transactions/get endpoint provides up to 24 months of investment transactions data. [...] Inflow, such as stock sales, is shown as a negative amount, and outflow, such as stock purchases, is positive."
- "Each holding also includes a tax_lots array breaking out the cost basis, purchase price, and purchase date of each acquisition lot, or an empty array when the institution provides no lot-level data."
- "Plaid checks for updates to investment data at least once per day during market days (up to 2-4 times per day, depending on institution)"

### https://plaid.com/docs/liabilities/ (extract, query-focused)
- "With Liabilities, you can view account information for credit cards, PayPal credit accounts, closed-end loans (student, mortgage, auto, personal, home equity, and commercial loans), and lines of credit"
- "Note that liabilities data does not contain detailed transaction history for credit card accounts. For credit card account transactions, use the Transactions product."

### https://plaid.com/docs/statements/ (extract, query-focused)
- "Statements (US only) allows you to retrieve an exact, bank-branded, PDF copy of an end user's bank statement, directly from their bank."
- "Include a statements object containing fields start_date and end_date. Plaid allows extracting up to 2 years of statements."
- "Statements currently supports only bank depository accounts (e.g. checking and savings accounts)."
- "Statements support includes the following major institutions, constituting ~40% of US depository accounts: Bank of America, Chase (early availability [...]), Citibank, Fifth Third Bank, Huntington Bank, Navy FCU, Regions Bank, Truist, US Bank, Wells Fargo"
- "Statements does not currently support all major or long-tail institutions, and should be used with a fallback option in case data is not available."
- "If the user connected their account less than two years ago, they can bypass the Link credentials pane and complete just the Statements consent step. Otherwise, they will be prompted to complete the full Link flow."

### https://plaid.com/docs/api/products/statements/ (extract, query-focused)
- end_date: "You can request up to two years of data. To determine whether a statement falls within the specified date range, Plaid will use the statement posted date."
- "/statements/download [...] returns a single statement, exactly as provided by the financial institution, in the form of binary PDF data."
- "/statements/refresh" endpoint exists (request with access_token, start_date, end_date).

### https://plaid.com/docs/link/hosted-link/ (extract)
- "With Hosted Link, Plaid hosts the Link experience."
- "Hosted Link should be used only when Plaid Link SDKs cannot be used. Plaid's Link SDKs provide a more seamless end user experience, lower latency, and higher mobile conversion rates than Hosted Link."
- "Hosted Link is fully supported with all Plaid products and Link flows (including update mode), except for Layer, Identity Verification, and Embedded Institution Search."
- "Hosted Link is recommended only when one or more of the following applies: You are using Plaid within a webview-based mobile app. Your users are launching Link from outside an in-product context [...] You are launching Link from inside an iFrame [...] If none of these apply, you should not use Hosted Link"
- "Previously, Hosted Link was enabled via Plaid account managers; it is no longer necessary to request that your account manager enable Hosted Link."
- "Webhooks are strongly recommended when using Hosted Link, as the webhook is the primary means of delivering the public_token, as well as of informing you when your user has completed the Link session."
- "If you don't set this field, the default lifetime for Hosted Links sent by Plaid via SMS is 24 hours, and for links sent via email, it is 7 days. If Plaid isn't delivering the URL, the default lifetime is 30 minutes."
- Sample request includes "redirect_uri": "{{UNIVERSAL_OR_APP_LINK}}" and "webhook".
- "In Hosted Link, there is no frontend integration required (or possible). You will instead receive information about the Link flow (including the public_token) via the SESSION_FINISHED webhook and the /link/token/get endpoint."
- "Detailed session data, including the public token, will also be available from /link/token/get for six hours after the session has completed. In general, it is recommended to use the webhook to obtain the public token, since it will allow you to get the public token more promptly, but you may want to use /link/token/get if your integration does not use webhooks, or as a backup mechanism"
- "In /link/token/get the public_token is present in both the on_success object and the results object. It is recommended to use the results object"

### https://plaid.com/docs/api/link/ (extract, query-focused)
- "/link/token/get [...] This endpoint is used with Link flows that don't provide a public token via frontend callbacks, such as the Hosted Link flow and the Multi-Item Link flow."
- "link_sessions [...] Session data will be provided for up to six hours after the session has ended."
- "SESSION_FINISHED [...] By default, this webhook is sent only for sessions enabled for the Hosted Link flow (including Link Recovery flows), a Multi-Item Link flow, or a Layer flow. [...] This enablement will also enable [...] the ability to use /link/token/get to retrieve events for non-Hosted-Link sessions."
- hosted_link.completion_redirect_uri: "URI that Hosted Link will redirect to upon completion of the Link flow."
- hosted_link.url_lifetime_seconds: "Cannot be longer than 21 days. The default lifetime is 7 days for links delivered by email, 1 day for links delivered via SMS, and 30 minutes for links not sent via Plaid Link delivery."
- hosted_link.is_mobile_app: "This indicates whether the client is opening Hosted Link in a mobile app in an AsWebAuthenticationSession or Chrome custom tab. Default: false"
- redirect_uri: "A URI indicating the destination where a user should be forwarded after completing the Link flow; used to support OAuth authentication flows when launching Link in the browser or another app. [...] When used in Production, must be an https URI. Note that any redirect URI must also be added to the Allowed redirect URIs list in the developer dashboard."

### https://plaid.com/docs/link/oauth/ (extract, query-focused)
- "Redirect URIs must use HTTPS. The only exception is on Sandbox, where, for testing purposes, redirect URIs pointing to localhost are allowed over HTTP. Custom URI schemes are not supported in any environment."
- "In the US, the following institutions require periodic OAuth consent refresh. Consent refresh at these institutions is required every 12 months, unless noted otherwise. American Express; Bank of America (new API only, see Bank of America for more details); Brex (3 months); Capital One; Charles Schwab; Chase (new Items only; [...]); Citibank [...]; Fidelity; Navy Federal Credit Union; PNC; Revolut (US) (3 months); TD Bank; USAA (18 months)"
- "To determine when consent expires, call /item/get and note the consent_expiration_time field. Plaid will also send a PENDING_DISCONNECT webhook (for US/CA Items) [...] one week before a user's consent is set to expire. To refresh consent for an Item, send it through update mode."

### https://plaid.com/docs/link/update-mode/ (extract, query-focused)
- "Certain institutions enforce expiration dates on Item consent. You can find an Item's consent expiration date by calling /item/get and checking the consent_expiration_time value"
- "If you receive the ITEM_LOGIN_REQUIRED error via the ITEM: ERROR webhook, or if you receive either the PENDING_EXPIRATION or PENDING_DISCONNECT webhook, re-authenticate with Link in update mode when the user is next in your app."

### https://plaid.com/docs/link/duplicate-items/ (extract, query-focused)
- "An Item represents a login at a financial institution. [...] A duplicate Item will be created if the end user logs into the same institution with the same credentials a second time through Plaid Link (in the same application), and if an access token is requested for the Item."

### https://plaid.com/docs/institutions/ (extract)
- "Plaid supports over 10,000 institutions across the United States and Canada."
- "This table is not updated in real time; for the most up to date data, use /institutions/get or the Institutions page in the Dashboard."
- "Download this coverage as CSV."

### https://plaid.com/documents/us_institution_coverage.csv (extract; full file saved as review/evidence/plaid_us_institution_coverage_2026-10-31.csv)
- First line: "Generated on: 2026-10-16T03:26:16.866Z"; header "institution_id,name,country,assets,auth,balance,cra_base_report,cra_cashflow_insights,cra_income_insights,cra_monitoring,cra_network_insights,identity,identity_match,income_verification,investments,investments_auth,liabilities,protect_linked_bank,signal,statements,transactions,transfer"; 10,304 data rows.
- Rows for the named institutions are in review/evidence/plaid-directory-extract-2026-10-31.csv (19 rows).

## SimpleFIN and Actual Budget

### https://beta-bridge.simplefin.org/ (extract)
- "The SimpleFIN Bridge lets you securely share your financial transaction data with apps. Connect up to 25 institutions and 25 apps for either: $1.50 + tax per month, or $15.00 + tax per year"

### https://beta-bridge.simplefin.org/info/developers (extract)
- "The SimpleFIN Bridge is intended to provide daily updates to transaction data. As such, you are expected to make 24 requests or fewer per day."
- "The date range of requests to /accounts (i.e. difference between start-date and end-date) is limited to 90 days at a time. The number of days of history available varies for each institution."
- "Overlap the date window of transactions you fetch by about 5 days to make sure you don't miss transactions."

### https://www.simplefin.org/protocol.html (extract)
- "Version: 2.0.0-draft"; "The SimpleFIN protocol allows users to share read-only financial data with third parties."
- Account: "balance", "available-balance", "balance-date", "transactions"; Transaction: "id", "posted", "amount", "description", "pending" (optional).
- Checklist: "Stores Access URLs at least as securely as the user's financial data."
- "v2.0.0 - 2026-03-19 [...] NEW: Added conn_id to Account object to disambiguate between two different logins to the same bank."

### https://actualbudget.org/docs/advanced/bank-sync/simplefin/ (extract)
- "Currently, the sync pulls at most 90 days of data from each linked account."
- "SimpleFIN's data updates one time / day, roughly every 24 hours, for each linked account. The time of day that each bank updates in SimpleFIN may vary [...] (based on the bank and upstream provider, MX)."

### https://raw.githubusercontent.com/actualbudget/actual/master/packages/docs/docs/advanced/bank-sync.md (raw)
- "The integration only works if you are using actual-server."
- "The API secrets and keys for bank sync are stored on the server and are not covered by end-to-end encryption."
- "Syncing only happens while Actual is open. If you close Actual, it catches up the next time you open it."

### https://actualbudget.org/docs/api/reference/ (extract, query-focused)
- "runBankSync({ accountId }) → Promise<void> Run the 3rd party (GoCardless, SimpleFIN) bank sync operation. This will download the transactions and insert them into the ledger."
- "importTransactions [...] → Promise<{ errors, added, updated }>" (reconciling import).

## SnapTrade

### https://snaptrade.com/personal (extract)
- "Free for personal use." "Up to 20 brokerage connections" "API access to your own accounts" "Trading available with supported brokerages" "No credit card required"
- "Personal $0/month For developers using SnapTrade with their own brokerage accounts."

### https://docs.snaptrade.com/docs/personal-vs-commercial (extract)
- "Personal users are currently completely free."
- "Personal customers are limited to one free Personal client ID and consumer key for their own brokerage accounts."

### https://snaptrade.com/brokerage-integrations/robinhood-api (extract)
- "Read-Only OAuth access - Your credentials aren't shared with us or any app"
- "Does Robinhood have a developer API? No, Robinhood does not offer a developer API. Does the Robinhood API support trading? No, this integration does not offer the ability to place trades."

### https://docs.snaptrade.com/docs/build-with-ai (extract)
- "Your consumerKey can access your brokerage data and may be able to trade where trading is enabled. Keep it in server-side environment variables."

### https://snaptrade.com/faq (extract)
- "Standard transaction history is refreshed daily and delayed by one day on both options."
- "Your Personal API key only accesses your own brokerage accounts."

### https://snaptrade.com/brokerage-integrations (extract, pages 1, 3, 4, 5 via search snippets)
- Names seen: AJ Bell, Alpaca, Bank of America, Binance, BMO InvestorLine, BUX, Capital One, Chase, CIBC Investor's Edge, Citi, Coinbase, CommSec, DEGIRO, E*TRADE, Edward Jones, Empower, eToro, tastytrade, TD Direct Investing, TIAA, TradeStation, Tradier, Trading212, Transamerica, U.S. Bank, Upstox, Vanguard US, Wealthsimple, Webull Canada, Webull US, Wells Fargo, Zerodha. M1 Finance and Acorns were not seen; page 2 could not be retrieved (rate limit).

## Tiller

### https://tiller.com/pricing/ (extract)
- "After 30 days, Tiller is just $99/year, never any ads or hidden fees."

### https://help.tiller.com/en/articles/432695-how-often-is-new-data-added-to-my-tiller-powered-spreadsheet (extract)
- "By default, Auto Fill is enabled for all new users on Google Sheets to automatically get new/available transaction and balance data into your spreadsheet every 6 hours, 4 times a day."
- "Auto Fill is not available for Excel at this time. You must click the 'Fill Available Updates' button in order for the data to make it into your spreadsheet."
- "Tiller can only pull in cleared transaction data."

## Google

### https://developers.google.com/identity/protocols/oauth2 (extract, query-focused)
- "A Google Cloud Platform project with an OAuth consent screen configured for an external user type and a publishing status of 'Testing' is issued a refresh token expiring in 7 days, unless the only OAuth scopes requested are a subset of name, email address, and user profile (through the userinfo.email, userinfo.profile, openid scopes, or their OpenID Connect equivalents)."

### https://support.google.com/cloud/answer/15549945 (extract, "Manage App Audience")
- "Projects configured with a publishing status of Testing are limited to up to 100 test users listed in the OAuth consent screen."
- "Authorizations by a test user will expire seven days from the time of consent. If your OAuth client requests an offline access type and receives a refresh token, that token will also expire."
- "Projects configured with a publishing status of In production are available to any user with a Google Account. A project's publishing status is considered In production after selecting the Publish app button. Your project's configuration may be subject to verification before its name and logo are displayed on an authorization screen or before it may request authorization of sensitive or restricted scopes."

### https://developers.google.com/identity/protocols/oauth2/production-readiness/restricted-scope-verification (extract)
- "Personal use: One use case is if you are the only user of your app or if your app is used by only a few users, all of whom are known personally to you. You and your limited number of users might be comfortable with advancing through the unverified app screen and granting your personal accounts access to your app."
- "if your app is in the development, testing, or staging phases, verification isn't required."
- "If you store or transmit restricted scope data on servers, then you need to complete a security assessment."

### https://developers.google.com/identity/protocols/oauth2/production-readiness/overview (extract)
- "Testing | External | [...] Only users explicitly added to the test user allowlist can access the app (limited to a hard cap of 100 test users)."
- "the 7-day refresh token expiration limit for apps in the Testing status."

### https://support.google.com/cloud/answer/7454865 (extract, "Unverified apps")
- "An unverified app is an app or Apps Script that requests a sensitive or restricted OAuth scope, but hasn't gone through the Google verification process."
- "If your app remains unverified, the unverified app screen will be displayed before the consent screen, and your app will be limited to 100 new users until it is [verified]"

### https://support.google.com/cloud/answer/9110914 (extract, "OAuth App Verification Help Center")
- "When you add scopes to your project, scope categories (non-sensitive, sensitive, or restricted) are indicated automatically in the Google Cloud Console."
- "Apps requesting restricted scopes data need to complete 're-verification' annually."

### https://developers.google.com/workspace/drive/api/guides/manage-downloads (extract)
- "To export Google Workspace document byte content, use the files.export method with the ID of the file to export and the correct MIME type. Exported content is limited to 10 MB."
- "You can only download blob file content revisions that are marked as 'Keep Forever'."

### https://rclone.org/drive/ (extract)
- "When rclone downloads a Google doc it chooses a format to download depending upon the --drive-export-formats setting. By default the export formats are docx,xlsx,pptx,svg"
- "Google documents can also be exported as link files. These files will open a browser window for the Google Docs website of that document when opened."

### https://developers.google.com/workspace/gmail/api/guides/list-messages (extract)
- "This document explains how to call the Gmail API's messages.list method. [...] To retrieve full message details, use the messages.get method." "Last updated 2026-09-10 UTC."

## OpenClaw

### https://docs.openclaw.ai/platforms/linux (extract)
- "On this computer installs any missing local prerequisites and starts the Gateway as a systemd user service."
- "openclaw gateway install renders a systemd user unit by default."
- "installs the OpenClaw CLI and runs fresh local installations on the bundled OpenClaw Bun fork, without requiring a global CLI install; release builds install their matching stable version"

### https://docs.openclaw.ai/install/ (extract)
- "System requirements: Node 24.16.0+ on 24.x, or 26.1.0+ (24.22.1+/26.12.1+ strongly recommended for security) - Node 26 is recommended; the installer provisions Node 26 on macOS and Node 24 LTS on Linux when Node is missing"

### https://docs.openclaw.ai/tools/browser-login (extract)
- "Manual login (recommended) When a site requires login, sign in manually in the host browser's openclaw profile. Automated logins often trigger anti-bot defenses and can lock the account."
- "Local managed browsers are headless by default. For manual login, use a browser host with a desktop session and full Chrome/Chromium; headless shell cannot show a login window."
- "Use a headed profile to sign in with a passkey or security key."

### https://docs.openclaw.ai/tools/browser-control (extract)
- CLI examples: "openclaw browser download e12 report.pdf", "openclaw browser waitfordownload report.pdf", "openclaw browser create-profile --name attach --driver existing-session --cdp-url"
- Error contract includes "ACT_EXISTING_SESSION_UNSUPPORTED".

### https://docs.openclaw.ai/tools/browser/existing-session (extract)
- "Playwright-only features - PDF export, download interception, responsebody, and the agent actions requests, errors, text, and emulate require a Playwright-backed profile, such as the managed openclaw profile."

### https://docs.openclaw.ai/tools/browser (browser fetch of https://docs.openclaw.ai/browser)
- "Playwright-backed profiles save direct attachment navigations under the managed downloads directory and return { url, suggestedFilename, path } metadata after final-URL policy validation."
- "The built-in user profile attaches to your real signed-in Chrome session instead, via Chrome DevTools MCP."
- "This browser is not your daily driver. It is a safe, isolated surface for agent automation and verification."

### https://docs.openclaw.ai/gateway/security/browser-control (extract)
- "Enabling browser control gives the model a real browser. If that profile already has logged-in sessions, the model can access those accounts and data - treat browser profiles as sensitive state."

### https://docs.openclaw.ai/gateway/local-models (extract)
- "Ollama | CLI workflow, model library, hands-off systemd service"
- "Local models do not provide hosted providers' safety filters. Keep tool permissions and prompt-injection defenses appropriate for the model and task."

### https://docs.openclaw.ai/releases (extract)
- "October 2026 v2026.10.6 (latest) Security remediations, Windows setup, Discord commands, and iPhone Talk fixes."; earlier "v2026.8.2 [...] browser control without a running Gateway"; "v2026.8.1 (AKA OpenClaw 2.0)".

### https://github.com/openclaw/openclaw/pull/101369 (extract)
- "feat(browser): expose agent download actions [...] steipete merged 2 commits into main [...] steipete commented Jul 7, 2026"; "Merged via squash."

### https://github.com/openclaw/openclaw/issues/43457 (extract)
- "[Bug]: Browser downloads don't work for JavaScript-initiated blob downloads"; "fix evidence: commit 23a818fa2d1b".

## Institutions

### https://help.m1.com/en/articles/9331947-download-your-m1-invest-account-activity (extract)
- "You can view and download a CSV file of your account's activity and holdings information on the web and our mobile app on iOS."
- "Note: To download your account's holding and tax lot information, refer to Download and View Your Realized Gains on M1."

### https://help.m1.com/en/articles/9331948-how-to-find-download-and-manage-statements-forms-and-documents-on-m1 (extract)
- "Note: The Activity tab is for reference and can't be exported as a formal document."
- "Statements are generated within 7 business days after each month ends. If there's no account activity for the month, you will receive a quarterly statement instead of a monthly statement."
- "Documents Tab: Only the past 3 years of monthly statements, trade confirmations, and tax documents are available for direct download. Contact M1 Client Success if you need records older than 3 years. M1 retains account documents for 6 years after account closure"

### https://support.acorns.com/hc/en-us/articles/Third-Party-Integrations (browser fetch; published 2021-03-03)
- "You can link your Acorns account to some third-party finance apps. [...] But remember, all your accounts won't connect or show up on every third-party app."
- "Acorns Checking: You'll need your account and routing numbers to connect your Acorns Checking to another app."
- "Data Relay Timeframe: [...] Usually, it takes 1-3 business days for the updates to happen"
- "Our Two-Factor Authentication is triggered when you log in using your email and password. However, there's some additional situations that require Two-Factor Authentication. [...] 3rd party integrations"

### https://support.acorns.com/hc/en-us/articles/Trade-Confirmations-Monthly-Statements (browser fetch; published 2021-03-03)
- "Trade confirmations and monthly statements provide an entire history of all activity on your Acorns account."
- "From acorns.com: Log in to Acorns and click on 'Profile & Settings'; Click on 'Documents and Statements'; Use the dropdown menu on the top right of the screen to select the type of document"
- "Monthly statements are typically available around the middle of each month."

### https://www.raisin.com/en-us/education-center/how-to-read-your-raisin-account-statement/ (extract; "Last updated: August 20, 2026")
- "Statements are available digitally in your Documents tab: Log in to the Raisin platform and click Documents to view statements and tax documents."
- "Account statements are digital only, but you can print or save a copy at any time using the Print/Save button in the top right corner of the statement."
- "Note that interest details for inactive (closed) deposits are not included in the current statement."
- "Raisin generates account statements monthly."

### https://support.raisin.com/hc/en-us/articles/44349853710228 (browser fetch; "How does Plaid link my external bank account?", published 2026-09-16)
- "Linking your primary bank account allows you to make deposits and withdrawals and is required to use Raisin. Raisin never sees or stores your bank login credentials."

### https://www.nationwide.com/personal/insurance/life/online-access-benefits (extract)
- "View your policy details Log in > Select your policy"; "Access policy documents Log in > Select your policy > Document Center"

### https://insuranceservicenow.transamerica.com/FAQs.aspx (extract)
- "Q. How do I obtain the Current Cash Value of my Policy/Certificate? A. Step 1 Log In to your account. Step 2 Select the Policy/Certificate [...] Step 3 Select Policy/Certificate Summary from the Customer Service Features list. Step 4 The Cash Value, if any, is listed on the left hand side of the page under the Current Account Summary section."

### https://help.venmo.com/cs/articles/transaction-history-vhel281 (extract)
- "Account statements allow you to view a detailed history of your Venmo transactions in a downloadable CSV file. You can access statements for personal accounts, Teen Accounts, business profiles, and charity profiles both in the Venmo app and on the web."
- "Some files may be too large to download to your device. In this case, we'll send the statement to your email address instead."

### https://www.irs.gov/payments/online-account-for-individuals (extract)
- "Access your individual account information including balance, payments, tax records and more."
- "You can request an account transcript by mail. Note that each account transcript only covers a single tax year, and may not show the most recent penalties, interest, changes or pending actions."

### https://www.irs.gov/payments/online-account-for-individuals-frequently-asked-questions (extract)
- "Can I authorize someone else to access my online account? No. Only the taxpayer should log into their account. Credentials should never be shared with others."
- "A tax transcript shows the full details of your tax return [...] and covers only 1 year."

### https://www.capitalone.com/help-center/checking-savings/online-statements/ (extract)
- "You can view up to 7 years of statements online for active accounts."
- "To view your statements online, you will need to be enrolled in paperless statements."

### https://www.capitalone.com/help-center/checking-savings/transaction-history/ (extract)
- "Your past transactions list will show the past two years of account activity on the website. If you need information prior to the past two years, your statements will include the past seven years of transaction history."

### https://www.capitalone.com/learn-grow/money-management/how-long-to-keep-credit-card-statements (search snippet)
- "Capital One keeps up to seven years of credit card statements online for active accounts."

### https://info.bankofamerica.com/en/digital-banking (search snippet)
- "You can view, print and download up to 18 months of your statements at any time."
- "You can order copies of your statements beyond what is available online, up to 7 years ago."

### https://promotions.bankofamerica.com/digitalbanking/instructions/manage-statements-documents.html (search snippet)
- "The most recent 6 years of monthly statements may be viewed online immediately. Older statements up to 7 years can be requested in Online Banking or by contacting us."

## Arch, runtimes, OCR, scheduling, archive

### https://archlinux.org/packages/extra/x86_64/uv/ (extract)
- "uv 0.13.1-1 [...] Repository: Extra [...] Build Date: 2026-10-14 08:19 UTC"

### https://archlinux.org/packages/extra/x86_64/docker-compose/ (extract)
- "docker-compose 5.6.1-1 [...] Repository: Extra [...] Build Date: 2026-10-21 12:40 UTC"

### https://wiki.archlinux.org/title/Ollama (extract)
- "Install the ollama package, which provides a daemon, command line tool, and CPU inference. For GPU inference: Install ollama-vulkan for inference with Vulkan. Install ollama-cuda for inference with CUDA. Install ollama-rocm for inference with ROCm."
- "On AMD GPUs from RDNA 3 onward, ollama-vulkan is usually faster and uses less power than ollama-rocm"

### https://wiki.archlinux.org/title/Python (extract)
- "Python provides tools to create isolated virtual environments into which packages may be installed without conflicting with other virtual environments or the system packages."
- "uv — An extremely fast Python package installer and resolver, written in Rust."

### https://wiki.archlinux.org/title/Docker (extract)
- "If you want to be able to run the docker CLI command as a non-root user, add your user to the docker user group, re-login and restart docker.service."
- "To use it, install docker-compose."

### https://docs.ollama.com/linux (extract)
- "Adding Ollama as a startup service (recommended)"; "Create a service file in /etc/systemd/system/ollama.service"

### https://docs.ollama.com/capabilities/structured-outputs (extract)
- "Structured outputs let you enforce a JSON schema on model responses so you can reliably extract structured data"
- "It is ideal to also pass the JSON schema as a string in the prompt to ground the model's response."

### https://docling-project.github.io/docling/usage/advanced_options/ (extract)
- "By default, models are downloaded automatically upon first usage. If you would prefer to explicitly prefetch them for offline use (e.g. in air-gapped environments) you can do that"
- "To prefetch EasyOCR recognition models for specific languages, repeat --easyocr-lang with the same values used by EasyOcrOptions.lang"
- "The main purpose of Docling is to run local models which are not sharing any user data with remote services."

### https://docling-project.github.io/docling/usage/gpu/ (extract)
- "The current Docling OCR engines rely on third-party libraries, hence GPU support depends on the availability in the respective engines."
- "RapidOCR supports GPU acceleration through both its Torch and ONNX Runtime backends."

### https://github.com/j1mmyson/EasyOCR (search snippet of the EasyOCR README)
- Language list includes "Thai (th)".

### https://www.freedesktop.org/software/systemd/man/latest/systemd.timer.html (extract)
- "Persistent= Takes a boolean argument. If true, the time when the service unit was last triggered is stored on disk. When the timer is activated, the service unit is triggered immediately if it would have been triggered at least once during the time when the timer was inactive. [...] This is useful to catch up on missed runs of the service when the system was powered down. Note that this setting only has an effect on timers configured with OnCalendar=. Defaults to false."
- "WakeSystem= [...] Note that this functionality requires privileges and is thus generally only available in the system service manager."

### https://www.freedesktop.org/software/systemd/man/latest/loginctl.html (extract)
- "enable-linger [...] Enable/disable user lingering for one or more users. If enabled for a specific user, a user manager is spawned for the user at boot and kept around after logouts. This allows users who are not logged in to run long-running services."

### https://raw.githubusercontent.com/paperless-ngx/paperless-ngx/main/docs/setup.md (raw)
- "Installation script | Fastest first-time setup with guided prompts (recommended for most users) | Low"
- "For most users, Docker is the best option. It is faster to set up, easier to maintain, and ships with sensible defaults."

### https://raw.githubusercontent.com/paperless-ngx/paperless-ngx/main/docs/faq.md (raw)
- "Files consumed from the consumption directory are re-created inside this media directory and are removed from the consumption directory itself."
- "Paperless-ngx never modifies your original documents. It keeps checksums of all documents and uses a scheduled sanity checker to check that they remain the same."
- "The exporter is another easy way to get your files out of paperless with reasonable file names."

### https://raw.githubusercontent.com/paperless-ngx/paperless-ngx/main/docs/administration.md (raw)
- "Use the document exporter. The document exporter exports all your documents [...] The document exporter is also able to update an already existing export."
- "You cannot import the export generated with one version of paperless in a different version of paperless."

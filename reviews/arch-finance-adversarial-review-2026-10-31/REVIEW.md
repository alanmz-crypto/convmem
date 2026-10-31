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

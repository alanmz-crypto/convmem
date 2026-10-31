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

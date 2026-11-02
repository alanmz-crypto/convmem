# Codex second opinion on the adversarial review (sources re-read 2026-10-31)

Pasted by Ryan into the Claude session on 2026-11-01, verbatim. Codex was run with the prompt in `docs/inter-model/CLAUDE-2026-10-31-arch-finance-adversarial-review-codex-handoff.md`. Claude's response to each point is in `REVIEW.md` ("Second opinion" paragraph under "Claim verification coverage") and in the revised F04, F05, F07, C-4 and C-9.

---

Read `REVIEW.md` fully and all **18 non-supported rows** of the 38-row CSV. Sources were re-read on **2026-10-31**; the quoted eligibility, consent, Statements and history restrictions remain consistent with Claude's captures.

| Item | Opinion | Evidence |
|---|---|---|
| **F03 — Statements coverage** | **AGREE** | [Plaid explicitly limits Statements to depository accounts](https://plaid.com/docs/statements/); credit-card PDFs require another route. |
| **F04 — History lock** | **AGREE, with qualification** | The [Transactions API](https://plaid.com/docs/api/products/transactions/) locks history when **Transactions is initialized**, rather than merely when an Item exists; request 730 days at that point. |
| **F01 — Trial eligibility** | **AGREE** | [Billing documentation](https://plaid.com/docs/account/billing/) specifies new US/Canadian teams created on/after April 15, 2026; [eligibility also excludes prior Production access/applications](https://support.plaid.com/hc/en-us/articles/16110502116887). Your eligibility remains untested. |
| **F02 — Annual consent** | **AGREE** | The [OAuth guide](https://plaid.com/docs/link/oauth/) requires refresh every 12 months for Capital One and **Bank of America's new API**; that BofA qualification matters. |
| **F05 — Item budget** | **AGREE as a risk** | The [10 lifetime Item limit](https://support.plaid.com/hc/en-us/articles/39994173227159) is real, but eight directory entries do not establish eight required logins—and eight plus one is nine, not ten. |

The requested web checks have these results; documentary closure does **not** establish a successful account connection:

| Item | Opinion | Evidence |
|---|---|---|
| **V2 — SnapTrade M1/Acorns coverage** | **CANNOT VERIFY actual support** | [Page 2](https://snaptrade.com/brokerage-integrations?page=2) is now readable; neither institution appears across the published catalog or [access guide](https://docs.snaptrade.com/docs/broker-access-guide). The missing-page check is closed, but absence alone does not prove backend availability. |
| **V5 — Required customer redirect URI** | **DISAGREE with blanket requirement; documentary question closed** | Plaid says [desktop-web OAuth works without a redirect URI](https://plaid.com/docs/link/oauth/) and [Hosted Link manages bank OAuth redirects](https://plaid.com/docs/link/hosted-link/embedded-clients/); successful production onboarding still requires G1. |
| **V6 — Trial support and MSA** | **AGREE; closed** | The [current help page](https://support.plaid.com/hc/en-us/articles/39994173227159) says Bill assistance, paid-plan support cases, and "Master Services Agreement"; this matches Claude's later browser capture, with no further wording change observed. |
| **V13 — Google scope categories** | **AGREE; closed** | Google lists both [`gmail.readonly`](https://developers.google.com/workspace/gmail/api/auth/scopes) and [`drive.readonly`](https://developers.google.com/workspace/drive/api/guides/api-specific-auth) as **restricted** scopes. |

The remaining [verification-queue items](https://github.com/alanmz-crypto/convmem/blob/claude/modest-davinci-dzntkb/reviews/arch-finance-adversarial-review-2026-10-31/VERIFICATION-QUEUE.md) remain unverified:

| Item | Opinion | Evidence missing |
|---|---|---|
| V1 | **CANNOT VERIFY** | SimpleFIN institution-search results. |
| V3 | **CANNOT VERIFY** | Owner's BofA statement-year selector. |
| V4 | **CANNOT VERIFY** | Capital One card export-dialog limits. |
| V7 | **CANNOT VERIFY** | Linked Acorns/Robinhood subaccount lists. |
| V8 | **CANNOT VERIFY** | Raisin's returned deposit/account structure. |
| V9 | **CANNOT VERIFY** | Policy-specific Transamerica portal and field meanings. |
| V10 | **CANNOT VERIFY** | Nationwide Life coverage through another aggregator. |
| V11 | **CANNOT VERIFY** | Allstate and employer-portal export trials. |
| V12 | **CANNOT VERIFY** | Representative-document OCR benchmark. |
| V14 | **CANNOT VERIFY** | Installed OpenClaw version and download test. |
| V15 | **CANNOT VERIFY** | Original workbook reinspection for this second opinion. |
| V16 | **CANNOT VERIFY** | Paperless website/source-version comparison. |
| V17 | **CANNOT VERIFY** | Private Pages were not rechecked during this review. |
| V18 | **CANNOT VERIFY** | Actual BofA Item API version and consent expiry. |

**Verdict — AGREE: retain "revise before the pilot."** Statement scope, history initialization, consent monitoring and an actual owner-by-issuer Item budget need explicit treatment before linking. I would also remove Claude's blanket "all future products upfront" instruction: the API supports later Transactions initialization, and requiring every product can unnecessarily filter institutions. These are bounded corrections supporting a limited pilot, rather than grounds to abandon the approach.

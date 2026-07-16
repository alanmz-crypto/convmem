# CURSOR — Executive APPROVE / go lock (Round 2 trace)

**Date:** 2026-07-16
**From:** Cursor
**Status:** **APPROVED to execute** — waiting only on Ryan’s verbal **go**.
**Implements:** [CURSOR-executive-execution-plan-round-2-trace.md](CURSOR-executive-execution-plan-round-2-trace.md) (with acceptance item 7 tightened below)
**Architecture:** [CURSOR-architecture-round-2-trace.md](CURSOR-architecture-round-2-trace.md)
**PR:** [PR #35](https://github.com/alanmz-crypto/convmem/pull/35) (`fix/2026-07-15-ask-trace` @ `90835a8`, non-mergeable until rebase)

## Partner chain (final) — ChatGPT → Kiro → R1 → V4 → Grok

| Order | Lane | Verdict |
|---|---|---|
| 1 | ChatGPT | **APPROVE.** One non-blocking checklist tightening (item 7) absorbed below. |
| 2 | Kiro | No blockers; confirm after Cursor pushes rebased tip. |
| 3 | R1 | Ready for Ryan’s **go**; merge gates restated. |
| 4 | Continue-V4 | Affirm authorize — **note:** V4’s last paste summarized the *superseded* pointer (`CURSOR-execution-plan-round-2-trace.md` pre-REVISE steps). Canonical runbook is the executive execution plan (baseline, doctor, three-path `final_context`, `--force-with-lease`). Evidence-default flip stays out. |
| 5 | Grok | Affirm: surgical observability; hardest part is preserve-main rebase; all REVISE gates present. |

No remaining blockers from any lane.

---

## ChatGPT tightening (locked into acceptance)

Acceptance checklist item 7:

> Full suite and `doctor` are green when the baseline is green; otherwise, **zero new failures versus the recorded clean baseline**, with all pre-existing failures documented in the PR body.

Prevents an environment-specific baseline failure from making the plan formally impossible.

---

## What executes on Ryan’s **go**

1. **Baseline** on `origin/main` (`48e816f` or newer tip): record SHA; `unittest discover`; `python3 convmem.py doctor`.
2. **Preserve-main rebase** of `fix/2026-07-15-ask-trace` (or greenfield from `main` if unsafe). Manual `ask.py` from `main` + layer trace only — no whole-file `--ours`/`--theirs`.
3. **Contract rewrite** to `convmem.ask.trace.v1` (five truthful stages; skipped = `{status, reason, items:[]}`).
4. **Tests** including `final_context` fidelity on **normal, raw, and hybrid**.
5. **Verify** (focused + full suite + `doctor`) then:

```bash
git push --force-with-lease origin HEAD:fix/2026-07-15-ask-trace
```

6. Kiro + R1 confirm → **Ryan merges**.

## Out of scope (unchanged)

MCP `evidence` default flip; diversification; retrieval-eval rewrite; `retrieve_for_ask` extraction.

## Acceptance checklist (8)

1. Round 1 symbols unchanged vs `main`
2. `trace=False`: no `trace` key; only `evidence_status` / `ledger_id` on citations
3. `trace=True`: schema `convmem.ask.trace.v1`; all 5 stages; bounds/`truncated`
4. `recent_injected` ⊆ admitted recent only
5. `final_context` matches synthesis on normal, raw, and hybrid
6. Rerank and ledger dedupe are separate stages
7. Full suite + `doctor` green when baseline green; else zero new failures vs recorded baseline (pre-existing documented)
8. Durable `--trace` probe + baseline SHA in PR body; Kiro + R1 confirm; Ryan merges


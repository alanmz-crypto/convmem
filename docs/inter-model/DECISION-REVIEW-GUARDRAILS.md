# Decision and review guardrails (opt-in — not auto-loaded)

**Status:** available on request, **not** part of the always-loaded `TEAM_CHARTER` slice in `config/agent-protocol.md`.
**Author:** drafted from a Ryan-supplied philosophy doc; reviewed by Kiro and Claude (Sonnet 5).
**Use when:** an agent or Ryan explicitly invokes it — e.g. "apply the decision/review guardrails here" — to check whether continued analysis, review, or escalation is still earning its keep. It is a lens you reach for on request, not a background policy every session runs.

Why opt-in rather than default: this framework is optimized against over-processing (recursive review, requirement creep, escalation past decision value). Your existing charter is deliberately biased the other way — DB backups before mutations, `convmem doctor` gates, review-required lanes, the Sol-High conflict gate — because the blast radius here (production WordPress, shared ledger, multi-agent writes) is real. Making this framework a default risks an agent citing "diminishing returns" to wave off a safety step or a legitimate review escalation. Keeping it request-only means it augments judgment when asked, instead of quietly reweighting every review.

---

## Roles (context, not new authority)

- **Ryan owns final decisions:** architecture, scope, priorities, approvals.
- **Planning agents propose:** bounded plans, no silent scope/architecture expansion.
- **Implementers execute:** stop when implementation requires a new design decision.
- **Reviewers verify:** correctness, contracts, regressions, unresolved risk — not substitute architects.
- **The coordinating model guards the process:** notices when analysis is expanding without expected value, and says so.

Ryan asking for more analysis, review, or certainty is **not by itself** evidence more is needed — but it is also not, by itself, evidence that less is needed. This framework informs a recommendation; it does not decide for him.

## Escalation ladder: local → interface/contract → architectural

Classify a new concern before acting on it:

- **Local implementation** — a bug or defect fixable within the current plan/contract.
- **Interface/contract** — the concern crosses a boundary another lane depends on.
- **Architectural** — a design assumption, invariant, safety property, or required behavior is actually wrong.

Do not escalate merely because a problem is difficult, detailed, or found by a strong reviewer. Reopen a settled architectural decision only on concrete evidence that an architectural assumption is wrong.

**Disputed classification — tiebreaker.** If the reviewer (e.g. Kiro, Copilot audit) and the coordinating model disagree about the level of a finding, the coordinating model does **not** get to resolve it by fiat in either direction. Route the disagreement to Ryan with both classifications stated. This mirrors the existing Sol-High principle (a reviewer's verdict is not overridden by another lane's say-so) — it just applies it to classification disputes below the Sol-High conflict threshold, where a full Sol-High call would be overkill but silent override would erode review authority.

## When flagging over-investigation

State briefly, in this order:

1. **Pattern** — what appears to be happening (recursive review, requirement creep, etc.).
2. **Evidence** — why it looks like that pattern.
3. **Level** — local / interface / architectural.
4. **Decision value** — what a plausible result of further investigation could actually change. If no realistic answer exists, that's the signal to stop.
5. **Stop rule** — the cheapest reasonable condition for considering the matter settled.

Then recommend **continue**, **narrow**, or **stop and execute**. Ryan keeps the decision; the point is to make the tradeoff explicit rather than defaulting to "one more layer of review."

## Delta review after an initial full review

A first independent review may examine the whole relevant system. Later reviews on the same artifact/revision should normally be **delta reviews**, asking only:

- Were the identified defects fixed?
- Did the fixes introduce regressions?
- Has genuinely new evidence appeared?
- Does any new finding actually require reopening a settled decision?

Consolidate overlapping findings; distinguish blockers from improvements. A reviewer finding ten issues does not automatically justify ten new requirements. This sharpens — does not replace — the existing Sol-High "same target + same revision" gate and the charter's delta-review references.

## Non-negotiable floor

**These guardrails rank below system/tool guards, lane must-nots, and DB/secrets/external safety in the existing bounded-autonomy precedence stack.** They govern how much analysis and review to do — never whether to honor a safety invariant, a review-required lane's authority, or a contract. A DB backup, a Copilot audit, a Kiro sign-off gate, or an unresolved correctness/safety finding is never "over-investigation," and "stop rule" reasoning must never be used to skip one or to override a reviewer's own escalation without Ryan's arbitration (see tiebreaker above).

## Adoption note

This is deliberately **not** wired into any surface's always-loaded rules, steering files, or hooks — building that would itself be the "one-off procedure becoming unnecessary infrastructure" pattern this framework warns against. If a specific friction point recurs often enough to justify a standing rule, propose that as a targeted charter amendment (see [`TEAM-CHARTER-2026-07-06.md`](TEAM-CHARTER-2026-07-06.md)) rather than expanding this doc in place.

## Related

- [`TEAM-CHARTER-2026-07-06.md`](TEAM-CHARTER-2026-07-06.md) — Sol-High conflict gate, delta-review references, lane must-nots this framework sits beneath.

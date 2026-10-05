# Review Request: OpenClaw Opportunity Map (adversarial review, v1)

**Date:** 2026-10-05
**Author:** Claude Code (Opus 5.5)
**For:** Kiro (formal design review). The Copilot audit lane may optionally audit the security-boundary section.
**Authorization:** Ryan, 2026-10-05 (verbal: "Give me a thorough handoff so you can have an adversarial review.")
**Arc:** none (ad-hoc). Strategy input to ConvMem Switchboard and OpenClaw Watch Coverage; changes no arc state.

---

## Resume state

| Field | Value |
|-------|--------|
| **State** | `BLOCKED_ON_RYAN`: waiting for Ryan to route the packet to Kiro. Nothing is blocked on implementation |
| **Branch** | `docs/2026-10-05-openclaw-opportunity-map-review` (this doc only) |
| **Tip SHA** | see `git log -1` on the branch (this commit) |
| **Push status** | pushed to origin |
| **PR** | not opened. Do not open until Ryan asks |
| **Ryan GATE** | Hand the packet to Kiro. After the verdict, Ryan decides: revise into v2, narrow to a first slice, or drop |
| **Track A ingest** | `~/.claude/projects/-home-lauer-Projects-convmem/b95b425e-5341-4538-8528-8054bfe945e3.jsonl` |

---

## What this is (a review request, not a build)

Ryan asked for a broad systems assessment: given OpenClaw, his projects, machine,
services, data, workflows and AI tools, what *could* be built? The result is a
private claude.ai page with 19 sections plus six short lists (A–F) and 84
candidate ideas. It has feasibility tiers, trust boundaries, foundational-system
candidates, a leverage ranking and a verification list. Its central thesis is:
**OpenClaw should be a thin, always-on front door (channels, timing, approvals);
ConvMem stays the memory of record; verification lives outside OpenClaw.**

This request asks Kiro to **try to falsify** that assessment before Ryan uses it
to narrow scope.

## Where the review material is (local only)

> **The review packet is deliberately not in git.** This repository is public,
> and the assessment contains household and personal context plus
> security-sensitive host notes. Never commit, push or paste packet contents.

| Item | Location |
|---|---|
| Sealed bundle | `artifacts/openclaw-opportunity-map-adversarial-review-v1.zip` (untracked, read-only) |
| Bundle SHA-256 | `3a6ab9254046c85bf7a491da3c2b8579404f82c3be9195354b14e14573e94596` |
| Assessment (exact v1 bytes) SHA-256 | `772f4283fcc090c3af26c0767c532e787c798760cf9855218121cc31b662e302` |
| Seal | `artifacts/openclaw-opportunity-map-adversarial-review-v1-seal.json` |
| Unpacked copy | `artifacts/openclaw-opportunity-map-adversarial-review-v1/`: **start at `README-FIRST.md`** |
| Live page (Ryan only; private) | https://claude.ai/artifact/FF8hrm2DjDuw9bHCP53wsd (version 1) |

The packet holds Ryan's original brief verbatim, the exact v1 page, a claims
ledger (every load-bearing claim with evidence, status and re-check command),
raw evidence captured 2026-10-05, the OpenClaw docs as fetched, and an author
self-critique, which the reviewer should read **last**.

## Assignment (summary; the full rubric is in the packet README)

1. Re-verify factual claims, including OpenClaw doc pages the author did not read.
2. Check conformance to Ryan's brief (19 sections, A–F, per-idea fields, tiers, and "say if something should live outside OpenClaw").
3. Steelman alternatives to the thesis, including "OpenClaw isn't needed for the top opportunities."
4. Check that no top-10 recommendation creates an injection, exfiltration, impersonation or irreversible-action path, or bypasses existing invariants (Ryan-only ledger writes and merges, lane must-nots, bounded autonomy, Switchboard hard stops).
5. Check internal consistency and material omissions.

**Verdict:** Kiro returns exactly `PASS` or `FAIL`; any other lane returns
`ADVISORY PASS` or `ADVISORY FAIL`. A FAIL requires at least one High finding.
Each finding states severity, failure path, exact location, evidence, the
violated requirement or invariant, and the minimum correction.

**Known post-publish corrections (author self-reported):** one operational
failure was understated in duration; another was described as silent although
its unit has a desktop-notification hook; and one ID series collides. Details
are in the packet's `CLAIMS-LEDGER.md` (A4, A6, E4).

## What NOT to do

- Do not install, upgrade or configure OpenClaw (upgrades are separately gated per the Switchboard brief).
- Do not fix the operational findings the assessment reports; they are Ryan's call.
- Do not read credential or secret file contents.
- Do not edit the assessment. Findings go in the verdict, and the author revises.
- Do not run `convmem record`, `add`, bulk `index` or `verify`.
- Do not copy packet contents into any tracked file, PR, issue or comment.

## Acceptance criteria

- [ ] Kiro verdict (`PASS`/`FAIL`) delivered to Ryan, against the exact bundle hash above
- [ ] Each finding carries all six required fields
- [ ] Self-critique items are explicitly confirmed, rejected or re-rated
- [ ] Ryan decides the next step (v2 revision, first-slice narrowing, or drop)

## Branch convention

```
docs/2026-10-05-openclaw-opportunity-map-review
```

This branch carries only this handoff doc and the LATEST pointer. Squash OK.

## Related files

| What | Path |
|------|------|
| Switchboard arc brief | [`STATUS-openclaw-convmem-integration.md`](../plans/STATUS-openclaw-convmem-integration.md) |
| Watch-coverage arc brief | [`STATUS-openclaw-watch-coverage.md`](../plans/STATUS-openclaw-watch-coverage.md) |
| Team charter (lanes, Kiro role) | [`TEAM-CHARTER-2026-07-06.md`](TEAM-CHARTER-2026-07-06.md) |
| Packet entry point (local, untracked) | `artifacts/openclaw-opportunity-map-adversarial-review-v1/README-FIRST.md` |

## Leaving / picking up checklist

**Author (leaving):**

- [x] This file committed on a pushed branch
- [x] `LATEST.md` bullet at top with link and resume state
- [x] No STATUS Update Log line (no arc owns this work)
- [x] Review packet sealed locally; hashes above

**Reviewer (picking up):**

- [ ] Verify the bundle SHA-256 before reading
- [ ] Read the packet in the README order; self-critique last
- [ ] Return the verdict to Ryan; do not post it publicly if it quotes packet content

**TL;DR:** [Arc: none (ad-hoc)] Kiro is asked to adversarially review the
OpenClaw Opportunity Map v1. The sealed packet is local-only because the repo
is public. The verdict is PASS/FAIL with six-field findings, and Ryan decides
what happens next.

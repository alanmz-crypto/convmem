# T3 Residual Closure Evidence — Arc Trapdoor Hunt

> Evidence-only packet for the separately authorized residual T3 closure lane.
> This packet does not repair implementation, alter locked requirements, or
> promote repository VERIFY rows.

```text
Status:       Evidence collection pending
Arc:          Trapdoor Hunt
Starting basis: 8d9b7f00b171e1f9a1d2d2e57f9e674ab9d9a17e
Locked T3:    aae0cad0bb05b0e436e213b28abbe0ff05ba2e91
Branch:       verify/2026-08-19-trapdoor-t3-residual
Worktree:     isolated clone/worktree to be recorded with the PR
PR:           to be recorded after the first evidence commit
```

## Evidence-only boundary

This lane may add deterministic fixtures, tests, serialized evidence, and
controlled regression commands for exactly V3f, V3h, V4m, V8c, V8e, V8g, V9a,
and V9d. It must not repair implementation, weaken an oracle, change the
locked T3 requirements, or promote repository VERIFY rows from `PENDING`.

Migration, Verified Ingress Bootstrap, CG-1/CG-2, complete-data recovery,
Shadow, R2b, T4, T5, and broad fault-injection/endurance work are excluded.
If an oracle exposes an implementation defect, this lane records the failure
and stops for a separate Ryan correction grant.

## Authorized residual rows

| VERIFY row | Required evidence | Observed result | Disposition |
|---|---|---|---|
| V3f | Deterministic secret-exclusion scan retaining semantic bytes | PENDING | PENDING |
| V3h | Supported-profile crash/atomic-publication durability evidence | PENDING | PENDING |
| V4m | Finalized T3 mutator census plus universal overlap evidence or immutable staging proof | PENDING | PENDING |
| V8c | Same-root multi-model corroboration/elevation negative control | PENDING | PENDING |
| V8e | Retrieval → conversation → recapture → distill untrusted-chain fixture | PENDING | PENDING |
| V8g | Bounded provider omission/fallback negative controls | PENDING | PENDING |
| V9a | Controlled exact-tip focused/full regression evidence | PENDING | PENDING |
| V9d | Controlled retrieval/dedupe regression evidence | PENDING | PENDING |

All repository VERIFY rows remain formally `PENDING` throughout this lane.

## Stop and handoff rule

Any implementation defect, architecture conflict, missing authority boundary,
or need to weaken an oracle stops this lane. The failure must be reported to
Ryan for a separately authorized correction; no repair is performed here.


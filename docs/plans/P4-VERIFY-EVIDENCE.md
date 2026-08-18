# P4 Verification Evidence — Arc Trapdoor Hunt

> Evidence packet scaffold for the separately authorized T3 P4 verification
> lane. This file records observations and recommendations; it does not change
> the locked T3 requirements or promote repository VERIFY rows.

```text
Status:       P4 PR #207 recorded; evidence collection not started
Arc:          Trapdoor Hunt
Starting basis: 6ec5b6c031ae8fdedbd90ef1392232d25f0bfaf1
Locked T3:    aae0cad0bb05b0e436e213b28abbe0ff05ba2e91
Branch:       verify/2026-08-18-trapdoor-t3-p4
Worktree:     /home/lauer/Projects/convmem-trapdoor-t3-p4
PR:           https://github.com/alanmz-crypto/convmem/pull/207
```

## Evidence-only boundary

P4 runs deterministic locked VERIFY oracles and collects reproducible
commands, outputs, hashes, serialized fixtures, negative controls, regression
results, and no-live-mutation evidence against one exact implementation tip.

If a locked requirement fails, P4 records the failure and stops. P4 does not
repair implementation, weaken an oracle, alter a requirement, or reinterpret a
failure as PASS. All repository VERIFY rows remain `PENDING` unless a separate
governance decision records otherwise.

Migration, live migration, production data or Chroma mutation, Verified Ingress
Bootstrap, CG-1/CG-2 implementation or activation, Shadow, R2b, T4, T5,
ranking/recency/temporal redesign, and broad endurance or fault-injection work
are excluded.

## Evidence mapping

| VERIFY row | Evidence | Observed result | Recommended disposition |
|---|---|---|---|
| To be populated from the locked VERIFY contract | — | — | PENDING |

## Validation record

- Exact implementation revision tested: to be recorded.
- Focused verification: to be recorded.
- Controlled full-suite differential: to be recorded.
- Pylint: to be recorded.
- `git diff --check`: to be recorded.
- No-live-mutation proof: to be recorded.
- V4m mutator-census disposition: to be recorded.
- Kiro evidence review: to be recorded.
- Copilot targeted audit: to be recorded.

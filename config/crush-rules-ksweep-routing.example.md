# RETIRED — Crush ksweep-routing stopgap (do not deploy)

**Status:** Retired 2026-07-22 after P1.3 source-trust ranking merged
([PR #78](https://github.com/alanmz-crypto/convmem/pull/78)).

`scripts/deploy-agent-protocol.sh` no longer copies this file into
`~/.config/crush/rules/`. Ranking prefers `kiro_steering` / ledger /
inter-model over stale chat distillations, so the static route is redundant.

Historical content (for archaeology only) lived here as a path table for
`#ksweep-*` → `.kiro/steering/*.md` and a warning that corpus “no standalone
ksweep file” claims were outdated.

If Crush still has `ksweep-routing.md` under rules, move it aside (deploy
script does this automatically) or:

```bash
mkdir -p ~/.config/crush/rules-retired
mv ~/.config/crush/rules/ksweep-routing.md ~/.config/crush/rules-retired/
```

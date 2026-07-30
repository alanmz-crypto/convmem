# Kiro handoff — C7 operational runbook corrective review

**Lane:** Kiro design review / sign-off.  
**Date:** 2026-07-30.  
**Mode:** Plan. Review and planning only; do not modify code or live state.

## Current state

C7, the payload-free writer-session census, is merged to `main` at
`869aec7431b600ed7602a7a64ff98502340be066` (Shadow writer-census merge,
PR #134). Shadow remains disabled and activation remains forbidden. No live
writer census has been armed.

The recent runbook is directionally useful but contains three corrections that
must be incorporated before Ryan uses it:

1. `convmem.py writer-census-start` **does** acquire the existing C3 exclusive
   writer lease, bounded to 30 seconds, before it calls
   `writer_census.start_writer_census`. The library function alone does not;
   the CLI operation does.
2. The runbook must not tell operators to stop systemd units or otherwise
   control services. That is outside current authorization. Existing tail
   behavior is sufficient: wait for sessions that opened before the window end
   to close; post-window opens generate no new census event.
3. Freeze the exact deployed Git revision for the entire observation window,
   not just two source files. Every C7 open validates its runtime revision
   against the header.

## Objective

Produce a corrected, decision-ready C7-to-C6 operational runbook that Ryan can
execute manually. It must distinguish read-only preflight from operations that
mutate the new census directory. It must not authorize C7 arm, C6, or
activation.

## Required source checks

Ground every claim in the merged C7 code:

- `convmem.py`: `writer-census-start`, `writer-census-status`, and
  `writer-census-report` commands.
- `writer_census.py`: header/journal/report behavior and refusal codes.
- `chroma_write_store.py`: C3 shared and exclusive writer leases and C7 open /
  close ordering.
- `shadow_canary.py`: report binding and C6 inputs.

Do not rely on chat claims or a local checkout merely because it has a branch
named `main`. Deployment proof must be collected on the host that will run the
census.

## Required output

Return a concise runbook with these sections:

1. **Deployment proof** — exact deployed revision, C7 hook presence, C3
   protocol, canonical Chroma root, canonical writer-gate path, and proof that
   active compliant writers have the deployed revision. State what cannot be
   proven by a sandboxed/local process scan.
2. **Pre-arm decision table** — required clean/no-prior-census condition,
   30-second exclusive-gate behavior, expected success artifact names/modes,
   all refusal conditions, and the explicit Ryan-only arm command.
3. **Observation rules** — seven complete UTC days, exact revision/root/gate /
   protocol freeze, permitted read-only checks, no hand edits, and tail-close
   handling without service control.
4. **Report acceptance** — report creation, strict validation, artifact mode,
   SHA-256 capture, header/report identity comparison, and the required
   independent evidence review before C6.
5. **C6 readiness boundary** — list the still-missing fresh inputs, including
   the unresolved event-size-evidence source. Do not prescribe reading or
   creating a live Shadow ledger while Shadow is disabled.
6. **Stop/abort matrix** — exact condition, observable signal, whether the
   census is merely incomplete or irrecoverably invalid, and the safe next
   action.

End with exactly one verdict:

```text
C7 OPERATIONAL RUNBOOK READY
```

or:

```text
C7 OPERATIONAL RUNBOOK HOLD — <specific missing evidence or decision>
```

## Prohibited

- Do not start a census or create its directory.
- Do not modify implementation, configuration, docs, services, Chroma, Shadow
  artifacts, backups, or production settings.
- Do not grant or imply authorization for C6 or activation.


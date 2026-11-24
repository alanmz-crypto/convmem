# Issue: one investigated Timeshift fault keeps `convmem doctor` in FAIL

**Status:** Resolved, won't fix (2026-10-23). The CPU was replaced and the
tripwire (`cpu_tripwire.py`, doctor check, `known_bad_cpus` config) was removed,
so this blocker no longer exists. The acknowledgment design is moot.
**Severity:** High for session-start availability (the required doctor gate
cannot reach exit 0 without a reboot or an approved acknowledgment mechanism)
**Discovered:** 2026-10-22, Codex audit
**Arc:** Codex (operational follow-up; no new code change in this report)
**Files:** `cpu_tripwire.py:172-241` (`evaluate`),
`doctor.py:900-905` and `doctor.py:1799-1805`

## Evidence

The required doctor run returned exit 1 with this check as the only failure:

```text
[FAIL] cpu_tripwire: 1 hardware fault(s) not on a known-bad CPU:
timeshift[835726] segfault on CPU 13 at 2026-10-22T13:01:22-05:00
```

This is consistent with the current policy: `cpu_tripwire.evaluate` fails on
any kernel-attributed fault on a CPU that is not in the configured known-bad
set, and `doctor` maps that verdict to a failed check. It is not being reported
here as a parser false positive.

## Impact

The fault is already investigated as a single Timeshift event, but the live
system has no bounded way to retire exactly that event while preserving the
fail-closed behavior for new faults. Every subsequent session-start doctor run
continues to fail on the same boot-scoped journal evidence, so agents following
the session protocol cannot satisfy the doctor-exit-0 prerequisite. A reboot is
the current no-code fallback, but it is not a durable acknowledgment workflow.

The current mainline documentation routes this to the doctor-acknowledgment
design in PR #415. That PR is design-only; it does not change the runtime
tripwire or acknowledge the event.

## Suggested resolution

Implement and verify the bounded acknowledgment design before changing the
policy: bind an acknowledgment to this boot and this exact journal event,
validate the record strictly, render the acknowledged event as a visible WARN,
and continue to FAIL on any new event, a different boot, a machine check, or a
known-bad CPU returning online. Until that implementation is merged and the
runtime acceptance gate is explicitly granted, keep treating the doctor FAIL
as active evidence rather than clearing it or weakening the CPU policy.

<!-- ref: ../cpu_tripwire.py — fail/warn policy for current-boot native faults -->
<!-- ref: ../doctor.py — maps the tripwire verdict to the session-start gate -->
<!-- ref: ../docs/inter-model/LATEST.md — current routing to the acknowledgment design -->

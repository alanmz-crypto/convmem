# Progress watchdog (Crush)

After the session-start ritual (`doctor` → `brief` → `unresolved`), before
answering Ryan's question, produce a **≤10 line progress report** if any of the
following are true:

1. **Doctor warns `arc_staleness`** — list the stale arcs by name and days since
   last update.

2. **Standing checks are DUE** — name them and say what's needed.

3. **Any unresolved observation has `last_touched` > 14 days ago** — name it and
   note the age.

4. **LATEST.md contains items marked "unmerged" or "PENDING" that are > 7 days
   old** — name the PR/branch and the age.

**Format:**

> **Progress check:** {n} items need attention.
> - {item}: {what's stale and what would unblock it}
> - ...

If nothing triggers, say nothing — do not produce an empty report. Do not repeat
the full doctor output. This is a *filtered summary* of things that are aging.

**This is not investigation.** Do not open files, run commands, or start debugging
based on this report. Just surface the signals. If Ryan asks you to dig in, then
investigate.

**Do not produce this report if:**
- Ryan's first message is clearly scoped to a specific task ("fix X", "review Y")
- The session is a soft-close / handoff-only session
- You already produced a progress report in this session

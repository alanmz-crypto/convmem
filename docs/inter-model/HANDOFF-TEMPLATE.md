# Implementation Handoff: <short title>

**Date:** YYYY-MM-DD  
**Author:** <Lane> (e.g. Kiro design, Cursor implementation, Codex architecture)  
**For:** <Target lane> (e.g. Cursor or Codex)  
**Authorization:** Ryan, YYYY-MM-DD (<how authorized — verbal, PR, arc brief>)

---

## Resume state

| Field | Value |
|-------|--------|
| **State** | `NOT_STARTED` \| `IN_PROGRESS` \| `BLOCKED_ON_RYAN` \| `READY_FOR_PR` |
| **Branch** | `<feat\|fix\|docs>/YYYY-MM-DD-<slug>` |
| **Tip SHA** | `<full or short SHA>` |
| **Push status** | `pushed to origin` \| `local-only — must push before cloud` |
| **PR** | `#NNN` or `not opened` |
| **Ryan GATE** | What Ryan must do before implementation continues (or `none`) |
| **Track A ingest** | `~/.cursor/projects/.../agent-transcripts/<uuid>/<uuid>.jsonl` (optional) |

---

## What to build

<One paragraph: product goal and user-visible outcome.>

**Why this exists:** <Problem being solved — tie to arc or audit if applicable.>

---

## Integration point

<file>:<approx-line> — where the change lands.

```python
# minimal insertion snippet or call-site context
```

---

## Specification

### Inputs

- <files, config keys, env — or "none">

### Algorithm / behavior

```
pseudocode or numbered steps
```

### Output / contract

- <exact shapes, CLI messages, DoctorCheck tuples, API responses>

### Constants

```python
# named constants if applicable
```

---

## What NOT to build

- <explicit non-goals — scope creep firewall>
- <features deferred to a future slice>

---

## Test expectations

Focused tests in `tests/test_<module>.py`:

1. **<case name>:** <given → expected>
2. **<case name>:** …

Use `tmp_path` / fixtures; do not depend on live corpus or changing STATUS files unless integration test is explicit.

---

## Acceptance criteria

- [ ] <verifiable done condition>
- [ ] <verifiable done condition>
- [ ] No regression in existing suite
- [ ] Ruff / pylint clean per repo gates

---

## Branch convention

```
<feat|fix|docs>/YYYY-MM-DD-<slug>
```

Push immediately after each commit. Open PR when acceptance criteria pass. Ryan squash-merges unless PR says **Do not squash**.

---

## Related files

| What | Path |
|------|------|
| | |

---

## Leaving / picking up checklist

**Author (leaving):**

- [ ] This file committed (or on pushed branch)
- [ ] `LATEST.md` bullet at top with link and resume state
- [ ] `STATUS-*.md` Update Log line (if arc tracked)
- [ ] Branch pushed (or `local-only` flagged above)

**Implementer (picking up):**

- [ ] Read this file before first edit
- [ ] `convmem work resume <branch>` or start from branch convention
- [ ] State Goal / role / system state / next action if STATUS arc applies

<!-- Canonical template. Example: KIRO-2026-08-13-arc-staleness-check-handoff.md -->

# convmem Orchestration Note for Kiro, Cursor, Sonnet, Claude, and ChatGPT Sessions

Date: 2026-06-22  
Author role: ChatGPT orchestration  
Audience: other models/agents working on convmem  
Purpose: reduce Ryan as the middleman by creating a shared context bridge without adding premature agent-to-agent complexity.

---

## Position

`convmem brief` is the correct next move.

The project already has working retrieval, a read-only MCP server, a decision/evidence direction, and multiple agents using different surfaces. The current bottleneck is not another retrieval primitive. The bottleneck is that each model starts with a different partial picture unless Ryan manually summarizes the state.

A compact generated brief solves that immediately.

Do not build agent messaging yet. Do not build MCP write tools yet. Do not create autonomous decision writes yet. First create a reliable shared-context artifact that every agent can consume.

---

## Recommended next build

Add:

```bash
convmem brief
```

Primary output:

```text
~/.local/share/convmem/brief.md
```

Optional stdout mode:

```bash
convmem brief --print
```

Optional explicit output:

```bash
convmem brief --out /path/to/file.md
```

This command should generate a concise, current, model-readable state block for any agent session.

---

## Why this matters

Kiro can query convmem directly from shell.

Cursor can use shell and has MCP registered.

Crush/Cursor/Continue may eventually consume MCP directly.

ChatGPT and Claude web/chat sessions cannot directly call Ryan's local MCP server or shell. They only know what is pasted into the chat.

Therefore, the practical bridge is:

```text
local convmem state
    ↓
convmem brief
    ↓
brief.md
    ↓
Cursor/Kiro read automatically
    ↓
ChatGPT/Claude receive one paste
```

This is the simplest structure that improves all agents without pretending platform limits are solved.

---

## Scope constraints

Keep `convmem brief` read-only.

It should not:

- write decisions
- approve decisions
- send messages to agents
- mutate the corpus
- run synthesis unless already supported safely
- trigger watch/refine/monitor
- become a dashboard
- become a chat system

It should only gather and format current project context.

---

## Suggested content of `brief.md`

The output should be compact and predictable.

Recommended sections:

```markdown
# CONVMEM BRIEF

Generated: <timestamp>
Corpus: <unit count> units, <summary count> summaries
Tests: <count passing/failing if known>
Watch: <enabled/disabled/unknown>
MCP: <status>
Last verified: <timestamp/source if known>

## Current State
- ...

## Active P0
1. ...
2. ...
3. ...

## Recent Decisions
- Decision: ...
  Rationale: ...
  Constraints: ...
  Alternatives rejected: ...

## Active Risks / Open Questions
- ...

## Agent Routing
- Kiro: reviewer/signer
- Cursor: implementer
- Sonnet: MCP expert
- Claude: strategist
- ChatGPT: orchestration
- DeepSeek: runtime synthesis only

## Before Working
- Search convmem for prior relevant decisions.
- Treat current status docs as higher priority than stale handoffs.
- Do not create final decisions autonomously.
- If proposing a decision, write it as a proposal pending human/Kiro confirmation.
```

---

## Data sources

Prefer pulling from current machine-readable or canonical sources rather than hand-authored stale docs.

Priority order:

1. live `convmem stats`
2. current status file, if one exists
3. decision/evidence ledger
4. recent monitor/watch state
5. current MCP registration/verification state
6. archived handoffs only as historical context

If the brief includes stale or unverified information, mark it explicitly as:

```text
Unverified:
Stale:
Unknown:
```

Do not present stale handoff facts as current truth.

---

## Cursor integration

Add or update Cursor rule:

```text
Before working on convmem, read ~/.local/share/convmem/brief.md if it exists.
If the brief is missing or stale, run convmem brief first.
Use convmem search/ask before making architectural or implementation assumptions.
Do not treat proposals as accepted decisions.
```

Cursor should use the brief as session orientation, not as a replacement for targeted search.

---

## Kiro integration

Kiro should start convmem sessions by running:

```bash
convmem brief
```

Then use targeted queries when needed:

```bash
convmem ask "what did we decide about watch and Kiro DB exclusion?"
convmem ask "what is the current MCP verification status?"
convmem ask "what are the active P0 tasks?"
```

Kiro should remain reviewer/signer, not just another implementer.

---

## ChatGPT / Claude integration

For hosted chat models without shell/MCP access, Ryan or Kiro should paste the output of:

```bash
convmem brief --print
```

at the start of the session.

The receiving model should treat the brief as orientation, then ask for targeted `convmem ask` output only if a specific claim needs verification.

This reduces Ryan's burden from "explain the project again" to "paste one generated context block."

---

## Relationship to `propose_decision`

`convmem brief` should come before `propose_decision`.

Reason:

A shared context artifact is safer and lower complexity than a write-capable MCP tool. The team should first prove that all agents can consume the same current context reliably.

Later, `propose_decision` can be built as a two-stage flow:

```text
agent proposes
    ↓
pending proposal written
    ↓
human/Kiro reviews
    ↓
approved decision enters ledger
```

Agents may propose decisions. They must not directly create final signed decisions.

---

## Human confirmation gate for future decisions

When an agent proposes a decision inside Cursor or Crush, the correct UX is:

1. Agent calls or generates a proposal.
2. Proposal is saved as pending.
3. Tool returns a short confirmation block.
4. Agent stops and asks the human/Kiro to approve.
5. Only `convmem decision approve <pending_id>` writes the final decision.

Example:

```text
Pending decision created: dec-pending-20260622-001

Choice:
Exclude live Kiro DB from watch ingestion.

Rationale:
Live sqlite files caused OOM risk during watch ingestion.

Risks:
May miss some Kiro conversations until manual/index-safe extraction path exists.

Alternatives rejected:
- Index live DB directly
- Disable Kiro ingestion entirely
- Copy DB every watch cycle

Approve:
convmem decision approve dec-pending-20260622-001

Reject:
convmem decision reject dec-pending-20260622-001 --reason "..."
```

This is similar to a Git pull request. Agents can draft. Humans/Kiro sign.

---

## Coordination structure recommendation

Current handoff count is too high. Multiple handoff docs become stale and create disagreement.

Move toward this structure:

```text
docs/
  STATUS.md
  ARCHITECTURE.md
  DECISIONS.md
  AGENT-ROLES.md
  archive/
```

### STATUS.md
Current operational truth:
- corpus counts
- test status
- active P0/P1/P2
- watch state
- MCP state
- known risks
- last verified timestamp

### ARCHITECTURE.md
Stable design:
- Chroma/embedding model
- distillation path
- ledger model
- MCP read-only tool contract
- watch/refine/monitor structure
- single-writer rule

### DECISIONS.md
Human-readable index of accepted decisions, ideally generated or backed by ledger entries.

### AGENT-ROLES.md
Routing:
- Kiro = reviewer/signer
- Cursor = implementer
- Sonnet = MCP expert
- Claude = strategist
- ChatGPT = orchestration
- DeepSeek = runtime only

All older handoffs should move to `docs/archive/` and be marked superseded.

Do not delete them immediately. Archive first.

---

## Strong recommendation

Approve building `convmem brief` now.

Definition of done:

1. `convmem brief` command exists.
2. It writes `~/.local/share/convmem/brief.md`.
3. It can print to stdout.
4. It includes corpus stats, current state, active P0, recent decisions, active risks, and agent routing.
5. It marks unknown/stale/unverified facts clearly.
6. Cursor rule tells Cursor to read it before working.
7. Kiro uses it at session start.
8. ChatGPT/Claude receive it by paste when needed.

After this is proven, revisit:

- `propose_decision`
- decision approval workflow
- write-capable MCP tools
- automated brief refresh after watch/refine

Do not skip directly to agent messaging or autonomous writes.

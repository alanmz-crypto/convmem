# README — OpenClaw + ConvMem (plain-language orientation)

**This file is for humans, not agents.** The `ARCHITECTURE-*`, `EXECUTION-*`,
`STATUS-*`, and `VERIFY-*` files in this folder are written for AI agents
picking up mid-task — terse, jargon-heavy, assuming you already know the
vocabulary. This file exists so a person (Ryan, or anyone he loops in later)
can understand *what this work is and why it exists* without needing an AI
session open to translate it.

**Name for this whole effort:** **ConvMem Switchboard** — locked in
2026-09-23. Other candidates considered and rejected: Agent Memory Layer,
Context Bridge, Party Line, Commons, plain "Switchboard" without the ConvMem
prefix (reads as OpenClaw-owned rather than ConvMem-owned). Update this line
if the name ever changes, and keep it in sync with `README.md`.

## The problem, in one paragraph

OpenClaw is an orchestrator — it dispatches AI agents to go do things.
ConvMem is a memory system — it remembers what agents have already learned
and done, so the next agent doesn't have to relearn it. The open question
this work answers is: **when OpenClaw hands a task to one of its agents,
does that agent automatically get to use ConvMem's memory, or does it start
cold every time?**

A concrete example: if one agent does some Gmail work using a command-line
tool, and that work gets recorded into ConvMem, will an agent that OpenClaw
dispatches later to do more Gmail work automatically find and use that
recorded knowledge — or will it reinvent the wheel? Today, the honest answer
is: **it depends on wiring nobody has finished designing yet.** ConvMem's
memory is shared and tool-agnostic once something is recorded into it — any
agent that knows to *ask* ConvMem can retrieve it. What's still undecided is
whether OpenClaw's dispatched agents are actually given the means and the
habit of asking.

## The jargon, translated once

You'll see these terms in the arc's `ARCHITECTURE-*` and `EXECUTION-*` docs.
Here's what they mean in plain English, so you don't need to ask an AI to
translate them every time:

- **Context engineering** — the general discipline of deciding what
  information an AI agent gets to see, when, and how it arrives. This whole
  effort is an exercise in context engineering.
- **Agent memory / shared memory / cross-agent memory** — a store that
  multiple different AI agents can all read from and write to, so knowledge
  survives past any single conversation. ConvMem *is* this, for this
  project.
- **Retrieval-Augmented Generation (RAG)** — the technique of having an AI
  look something up in a knowledge store before answering, instead of
  relying only on what it already "knows." When an agent runs `convmem ask`
  before doing work, that's RAG.
- **Model Context Protocol (MCP)** — the standard way an AI agent connects
  to an external tool or data source, like ConvMem. "Giving an agent an MCP
  connection to ConvMem" means wiring it up so the agent can call ConvMem's
  tools directly.
- **Multi-agent orchestration** — one system (here, OpenClaw) coordinating
  several AI agents to get a task done, rather than one agent doing
  everything itself.
- **Context propagation / capability inheritance** — the specific question
  of whether a dispatched sub-agent automatically gets the parent's tools,
  permissions, and memory access, or has to be given them explicitly. This
  is the crux of the open question above, and it isn't settled yet.

## How the pieces actually fit together

```text
OpenClaw (orchestrator)
  │
  ├─ dispatches child agents to do tasks
  │     └─ (open question: do these children get an MCP connection
  │         to ConvMem, or do they start with no memory access?)
  │
  └─ has its own read-only MCP connection to ConvMem
        (bounded plan reviewed by Kiro — see ARCHITECTURE- and EXECUTION-
        openclaw-convmem-integration.md; currently no durable-write capability,
        no `record`/`approve`, scoped retrieval only, and no Execute grant)

ConvMem (shared memory)
  │
  ├─ committed repo knowledge about OpenClaw itself (docs, code, config)
  │     watched and indexed like any other project file
  │     (see STATUS-openclaw-watch-coverage.md for current state)
  │
  └─ session transcripts from whichever agent did the work
        (Claude, Codex, Kiro, Crush, etc.) — indexed after the fact,
        searchable by anyone afterward, regardless of which tool
        produced it
```

Two separate arcs are doing different parts of this:

- **OpenClaw Watch Coverage** — makes sure ConvMem can read OpenClaw's own
  *committed* project files (plans, code, config) so agents maintaining or
  extending OpenClaw have something to look up. This does **not** touch
  OpenClaw's live runtime data (credentials, databases, memory, session
  transcripts) — that's explicitly excluded for safety reasons (constantly
  changing, potentially sensitive, format not yet pinned down).
- **OpenClaw + ConvMem integration** (the ConvMem Switchboard effort) — defines
  the bounded connector that lets OpenClaw *query* ConvMem at runtime. The
  fixture architecture and T0–T5 execution overlay have Kiro PASS, while the
  existing implementation is partial and real OpenClaw qualification remains
  blocked behind separate gates.

Neither arc has yet answered the child-agent question above. That requires
watching a real OpenClaw run happen — you can't design it from documentation
alone, because it depends on how OpenClaw actually behaves when it spawns a
sub-agent, which nobody has observed yet.

## Where to look for the current state

Don't duplicate implementation status here — it changes too fast and would
go stale. Instead:

- [`STATUS-openclaw-watch-coverage.md`](STATUS-openclaw-watch-coverage.md) —
  current state of the repo-knowledge watch (PR status, what's merged, what's
  blocked).
- [`ARCHITECTURE-openclaw-convmem-integration.md`](ARCHITECTURE-openclaw-convmem-integration.md) —
  current design of the runtime connector (scope, constraints, open
  questions).
- [`EXECUTION-openclaw-convmem-integration.md`](EXECUTION-openclaw-convmem-integration.md) and
  [`EXECUTION-openclaw-convmem-milestone-plan.md`](EXECUTION-openclaw-convmem-milestone-plan.md) —
  bounded implementation ownership, checkpoints, evidence, and later gates.

## What "done" looks like for the child-agent question

1. The watch-coverage wiring lands (PR merged, OpenClaw's approved files in
   the watched checkout).
2. OpenClaw runs once, for real, on a task — ideally one where prior
   recorded knowledge (like a Gmail CLI example) would help, so it's obvious
   whether the dispatched agent reaches for ConvMem or starts cold.
3. Someone inspects what actually happened: did the child agent have an MCP
   or CLI connection to ConvMem? Did it use it? Where did its transcript
   land?
4. That observation turns into an explicit design decision — written up
   properly, reviewed by Kiro, not assumed — about whether dispatched agents
   inherit ConvMem access by default.

## Update log

| Date | Who | Change |
|---|---|---|
| 2026-09-23 | Claude/Codex | Updated orientation after the exact-tip Kiro PASS: the bounded T0–T5 plan is ready for Ryan's Execute decision; implementation and live qualification remain gated. |

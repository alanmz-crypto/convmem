# How to Take Smart Notes — appendix notes

**Source:** *How to Take Smart Notes* · pp. 31–38 (four note types), pp. 40–41 (writing as thinking), p. 53 (no one starts from scratch), pp. 66–84 (permanent notes and linking)

Focused slice covering the note-type system, linking discipline, and the philosophical spine that justifies convmem's evidence-unit architecture. Skips the motivational framing (aimed at students) and habit-building (aimed at humans, not agents).

## The four note types (pp. 31–38)

Ahrens defines four distinct note types by function, not by topic:

| Note type | Purpose | Convmem equivalent |
|-----------|---------|--------------------|
| **Fleeting notes** | Capture ideas before they evaporate; temporary, rough | Raw session transcripts, inbox files |
| **Literature notes** | Extract what matters from a source; written in your own words | Extracted PDF pages in `staging/builder-reference/` |
| **Permanent notes** | Atomic, self-contained ideas written for future contexts you cannot predict | `dec_prop_*` and `obs_*` entries in the ledger |
| **Project notes** | Collected notes tied to a specific project; discarded or archived when the project ends | The `project=` slug in brief; session-scoped context |

The critical insight: **mixing note types by topic** (e.g., filing everything under "convmem") buries the structure. The slip-box works because each type serves a different retrieval purpose. Convmem's domain taxonomy is a secondary organization; the primary structure is the type distinction (observation vs. decision vs. verification) and the `relates_to` graph.

## Writing is the only thing that matters (pp. 40–41)

> Writing is not the outcome of thinking; it is the medium of thinking.

This principle justifies why convmem's ledger records observations and decisions as written artifacts rather than as structured data. The act of writing a `dec_prop_*` entry forces clarity that a form field or a dropdown cannot. If you cannot state a decision in one sentence with a rationale, you haven't thought it through.

This also justifies why `ask()` synthesizes from evidence units rather than from a single canonical document — the synthesis _is_ the thinking, and forcing the model to assemble evidence from atomic units produces better reasoning than retrieving a pre-written summary.

## Permanent notes and linking (pp. 66–84)

The core of the method:

- **A permanent note must make sense without its original context.** If you need to remember the conversation that produced an `obs_*` for it to be useful, the note is not permanent. It needs more context in its rationale.
- **Links matter more than categories.** Where a note sits in a hierarchy matters less than what it connects to. Convmem's `relates_to` edges implement this directly; `related()` traverses the graph regardless of domain prefix.
- **Bottom-up structure beats top-down taxonomy.** Let clusters emerge from links rather than deciding categories in advance. Convmem's domain prefixes are a lightweight helper, but the real structure is emergent in the `relates_to` graph.
- **Deliberately build meaningful connections** (p. 72). Every `--relates-to` is an assertion that two ideas are connected in a way that matters. The more links, the higher the probability that `related()` surfaces something useful.

The book's linking rule applies directly to the ledger: **a permanent note (decision) should be linked to at least one existing note (observation)**. An orphan decision is a missed opportunity for the next `related()` traversal.

## No one ever starts from scratch (p. 53)

> The idea that nobody ever starts from scratch suddenly becomes very concrete. If we take it seriously and work accordingly, we literally never have to start from scratch again.

This is the closest textual argument for convmem's **no-auto-merge, let-duplicates-coexist-until-reviewed** decision. The slip-box does not force consolidation; it lets connections emerge naturally. A new observation that overlaps an existing one is not noise — it's an opportunity for a new connection.

Applied to convmem: before `convmem record`, run `convmem search` or `ask`. The ledger already contains prior art. Starting from scratch means you missed it.

## Usage

This appendix covers the note-type mechanics and linking discipline that directly inform convmem's ledger architecture. The opening motivation chapters (aimed at students writing papers) and the closing habit-building chapter (aimed at human behavior) are not included — they don't map to agent or system architecture decisions.

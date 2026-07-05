# Kleppmann — builder digest (convmem)

**Source:** *Designing Data-Intensive Applications* · Ch. 5 (Replication) pp. 157–203, Ch. 9 (Consistency and Consensus, light touch) pp. 322–330, Ch. 11 (Stream Processing) pp. 436–484

**Read when:** designing the ledger → Chroma replication model, watch daemon as stream processor, event-time vs processing-time trade-offs, index drift analysis, or any question about why convmem uses single-writer and avoids consensus.

## Principles

- **Derived data is separate from the source of truth.** The system of record (JSONL ledger) is authoritative. Derived views (Chroma embeddings, summaries) can be rebuilt from it. This distinction is the core of the book's dataflow philosophy.
- **Single-leader replication** is the simplest correct model: one node accepts writes, all others are read-only followers. Convmem today uses single-leader: the JSONL ledger is the leader; Chroma is an asynchronous read replica.
- **Replication lag is a feature, not a bug.** Asynchronous replication means followers are temporarily stale. The question is whether your application can tolerate it. Convmem's index drift (Chroma 3683 vs JSONL 12401) is tolerable because the ledger is always authoritative.
- **Avoid consensus by design, not by algorithm.** Single-writer (one machine, one process) avoids the entire distributed consensus problem space. This is the right choice until you need multi-writer — and you probably don't.
- **Stream processing is for unbounded data.** Events arrive continuously; the system reacts as they happen. Convmem's watch daemon is a stream consumer; the ledger is an event log; Chroma is a materialized view.
- **Event time and processing time are distinct.** The time an event occurred (event time) and the time it was processed (processing time) can differ arbitrarily due to delays, batching, or failures. Stream processing systems must handle both.

## Ch. 5 — Replication (how Chroma follows the ledger)

### Leader-based replication in convmem

The JSONL ledger is the **leader** — the single source of truth that accepts writes. Chroma is the **asynchronous follower** — it reads data changes from the ledger and applies them to its own storage.

Three phases from the book (p. 161):
1. **Snapshot** — `convmem index` takes a consistent snapshot of the ledger (reads all approved decisions)
2. **Catch-up** — the indexer processes the snapshot and writes embeddings to Chroma
3. **Ongoing replication** — new decisions are indexed incrementally via `record --approve-last`

This is **asynchronous replication**: a write to the ledger is acknowledged immediately; Chroma may lag. The book's analysis of async replication (p. 160) applies directly: if the leader fails after a write but before replication, the write may not appear in the follower. Convmem's equivalent: if the machine crashes between `record --approve-last` and the next index pass, the decision exists in the ledger but not in Chroma. Recovery is automatic on next index.

### Synchronous vs. asynchronous

The book distinguishes two models (pp. 159–160):

| Model | Behavior | Convmem equivalent |
|-------|----------|--------------------|
| Synchronous | Leader waits for follower ACK before acknowledging write | Not used — would block CLI until Chroma finishes embedding |
| Asynchronous | Leader acknowledges immediately; follower catches up later | Current design — CLI returns immediately, index happens async |
| Semi-synchronous | One synchronous follower, rest async | Could apply if we add a write-ahead log follower |

Convmem's choice of full async is correct for its workload: the ledger is the durable record; Chroma is a search optimization. Losing the optimization is acceptable; losing the ledger is not.

### Failover and the single-writer rationale

In multi-node replication, leader failure requires **failover**: promoting a follower, reconfiguring clients, handling split-brain risks (pp. 162–163). The book discusses fencing (STONITH) to prevent two nodes from both believing they are leader.

Convmem avoids failover entirely by design: **single machine, single process, single writer.** There is no leader election because there is only one leader. This is why multi-leader and leaderless replication patterns (pp. 179–184) are not needed — they solve problems that convmem's architecture deliberately avoids.

**If you ever need multi-writer** (e.g., two machines both writing to the ledger), the book's analysis of conflict resolution (p. 181) applies: last-write-wins, CRDTs, or application-level merge. But that day is far off — single-writer is the right default.

### Replication implementations (p. 164)

The book describes three replication implementation approaches:

| Approach | How it works | Convmem parallel |
|----------|-------------|------------------|
| Statement-based | Replicate SQL statements | Not applicable |
| Write-ahead log (WAL) | Ship the log bytes | JSONL append is the WAL |
| Logical (row-based) | Ship changed rows as events | Distill pipeline: decisions → units |

Convmem's JSONL ledger is both the **source of truth** and the **replication log**. This is the book's WAL model: the log is the authoritative record; everything else is derived from it.

## Ch. 9 — Consistency and Consensus (light touch)

### Why convmem doesn't need consensus

The book opens Ch. 9 with the fundamental problem (p. 322): reaching consensus in spite of network faults and process failures is surprisingly tricky. Paxos, Raft, and Zab exist to solve this.

Convmem doesn't need consensus because:

**Single-writer by fiat.** One machine, one process, one JSONL file. There is no split-brain, no leader election, no clock skew between writers. The cross-surface protocol (propose → review → approve) involves multiple agents but only one ledger writer — Ryan's CLI.

**Linearizability is unnecessary.** The book distinguishes linearizability (strong consistency, p. 324) from eventual consistency (p. 323). Convmem operates at eventual consistency: a decision is visible in the ledger immediately but may not appear in search results for minutes. This is acceptable because the ledger is always the authoritative source.

**If multi-agent write contention becomes a live problem**, revisit this chapter. The consensus algorithms (Raft especially) provide a framework for agreeing on a single write order across multiple writers. But that would require multi-writer first, which is a prerequisite that hasn't been met.

### The single-writer framing

The strongest argument for single-writer is that it eliminates an entire class of failure modes the book spends 66 pages analyzing. Every consensus algorithm, every conflict resolution strategy, every linearizability guarantee is a solution to a problem that single-writer simply doesn't have.

Document this explicitly in the ADR when it comes up: **convmem avoids consensus by design, not by algorithm.**

## Ch. 11 — Stream Processing (event-driven convmem)

### Streams vs. batches

The book distinguishes two processing models (pp. 435–436):

| Model | Data | Convmem example |
|-------|------|-----------------|
| Batch (Ch. 10) | Bounded — knows when input ends | `convmem index`, distill.py |
| Stream (Ch. 11) | Unbounded — events arrive continuously | Watch daemon, refine daemon |

The watch daemon is a stream consumer: it monitors inbox files for changes and reacts incrementally. The refine daemon is a micro-batch stream (Spark Streaming model, p. 473): it fires on a schedule and processes a window of recent observations.

### Message brokers vs. databases

The book's comparison (pp. 440–441) maps directly to convmem's architecture:

| Property | Database | Message broker | Convmem ledger |
|----------|----------|---------------|----------------|
| Data retention | Until deleted | Delete after delivery | Append-only, never deleted |
| Read after write | Yes | No (destructive read) | Yes |
| Replay | Any point | Limited window | Full history |

The JSONL ledger is a **database**: it keeps data forever, allows point-in-time queries, and supports replay. But the watch daemon treats it as a **message source**: events are consumed and processed incrementally.

### Log-based message brokers (Kafka model)

The book describes Kafka's architecture (pp. 443–444): a **partitioned, append-only log** where consumers track their position. This is exactly what convmem's ledger is:

- **Partitions** → one partition per domain or site (implicitly through the single JSONL file)
- **Consumer offset** → downstream processing state in `processed.json`
- **Replay** → delete `processed.json` and re-index from the beginning

The key insight from the book: a log-based broker combines the durability of a database with the streaming semantics of a message broker. Convmem's ledger does the same.

### Event time vs. processing time

A central distinction in stream processing (p. 436): **event time** is when the event actually occurred; **processing time** is when the system got around to handling it. They can differ arbitrarily.

Convmem examples:

| Scenario | Event time | Processing time | Gap |
|----------|-----------|----------------|-----|
| CLI `record --approve-last` | When Ryan runs the command | When the indexer processes it | Minutes to hours |
| Monitor webhook | When the check fails | When the watch daemon picks it up | Seconds to minutes |
| Inbox file dropped | When the file was created | When watch debounce fires | Configurable (default ~30s) |

The refinement daemon's periodic synthesis is a **tumbling window** (p. 473): it fires every N minutes and processes all events in that window. This is the simplest correct stream processing model.

### Exactly-once semantics

The book discusses delivery guarantees (pp. 470–474):

| Guarantee | Meaning | Convmem status |
|-----------|---------|----------------|
| At-most-once | May lose events | Watch daemon: at-least-once via file-system inotify |
| At-least-once | May duplicate events | Index: idempotent (same chunk ID = overwrite) |
| Exactly-once | Neither lose nor duplicate | Current design approximates via idempotency |

The indexer achieves exactly-once semantics because chunk IDs (`{document}:{chunk_index}`) are deterministic: processing the same decision twice overwrites the same Chroma document. This is the book's recommended approach — make the operation idempotent rather than trying to prevent duplicates.

### Event sourcing and the ledger

The book's discussion of event sourcing (pp. 456–459) could describe convmem's ledger directly:

> The fundamental idea is to record an append-only log of events, and derive the current state by replaying events from the log. An append-only ledger captures the fact that the state of the system is the result of the mutations that happened over time.

This is exactly convmem's architecture. The ledger is the event log. Chroma is a **derived state** built by replaying events. If the derived state is corrupted, you don't try to fix it in place — you delete it and replay from the source.

The book's accounting analogy (p. 457) is apt: accountants don't erase incorrect transactions; they append compensating transactions. Convmem's `relates_to` chain does the same — superseding a decision doesn't delete it; it adds a child decision that overrides it.

## convmem Hooks

- **Chroma is an async follower, not a peer.** Treat index drift as replication lag, not data corruption. The ledger is the truth; the lag is tolerable.
- **Single-writer is a design choice worth documenting.** The ADR for multi-writer should begin with "what problem does multi-writer solve that single-writer doesn't?" and reference DDIA Ch. 5 + Ch. 9.
- **Index idempotency is your exactly-once guarantee.** Deterministic chunk IDs make re-indexing safe. Don't break this contract.
- **Separate event time from processing time** in monitoring data. A monitor check's timestamp is event time; the time the watch daemon processes it is processing time. Log both.
- **The ledger is an event log.** If you add a new derived view (e.g., a graph database for `related()` traversal), build it by replaying the ledger — not by writing to it separately.
- **Tumbling windows for the refine daemon.** Periodic synthesis is a correctly designed stream processing application (micro-batch). Don't make it real-time unless there's a proven latency requirement.

## Anti-patterns for Agents

- Do not design multi-writer because "it might be needed someday." Single-writer avoids consensus, conflict resolution, and failover — three of the hardest problems in distributed systems. Revisit only when single-writer provably fails.
- Do not treat Chroma as a peer of the ledger. It's a derived view. If they disagree, the ledger wins.
- Do not implement complex stream processing (event-time windows, watermarks, exactly-once protocols) before the simple tumbling-window approach has been proven insufficient.
- Do not write to Chroma directly. Every write must go through the ledger first, even if it means adding latency. Bypassing the ledger creates unrecoverable state.
- Do not confuse "it's on one machine" with "it doesn't need replication semantics." The ledger-Chroma relationship has the same consistency properties as any leader-follower system — name them explicitly.

## Related digests

- **Ousterhout** — the single-writer design is a deep module: narrow interface (one writer), broad behavior (avoids consensus).
- **Hard Parts** — if the watch daemon becomes a bottleneck, the trade-off worksheet applies: split into a dedicated ingest worker vs. keep the monolith.
- **Zeller** — replication lag between ledger and Chroma is a known failure mode. When debugging a missing search result, check index drift first.

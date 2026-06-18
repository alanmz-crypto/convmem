# Evidence chain demo (`convmem related`)

Milestone B adds graph traversal over the ledger without a graph database.
Units link via `relates_to` metadata on decisions and verifications.

## Seed the chain

```bash
convmem add --file examples/observations.jsonl
convmem add --file examples/decision.jsonl
convmem add --file examples/verification.jsonl
```

## Traverse from an observation

```bash
convmem related obs001
```

Expected sections:

- **Observation** — the anchor finding (`obs001`, summary, domain)
- **Decisions** — all decisions whose `relates_to` is `obs001`
- **Verifications** — all verifications whose `relates_to` is `obs001`

## Traverse from a decision

```bash
convmem related dec_001
```

Shows the decision, its parent observation id (`relates_to`), sibling decisions on the same observation, and verifications for that observation.

## Traverse from a verification

```bash
convmem related ver_001
```

Shows the verification, parent observation, and the full decision chain for that observation.

## Not found

```bash
convmem related obs999
# exit code 1 — clear error, no traceback
```

## Notes

- `related` is separate from `search` and `ask` — it does metadata traversal, not embedding search.
- Legacy units (no `ledger_id`) are skipped during index build.
- At ~1500 units, one `related` call does a single metadata scan via `build_ledger_index()`.

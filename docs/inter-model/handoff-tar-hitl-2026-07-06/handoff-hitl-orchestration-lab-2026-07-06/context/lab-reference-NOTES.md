# Lab reference — application guide

Hand-curated companion to the generated [`README.md`](README.md) index.
Read this before changing lab gates or synthesis fixtures.

## Read when

| Task | Slice / doc |
|------|-------------|
| Adding or changing a smoke gate | [building-evolutionary-architectures-fitness-functions.md](building-evolutionary-architectures-fitness-functions.md) |
| Fail-open vs fail-closed on a check | [release-it-stability-patterns.md](release-it-stability-patterns.md) |
| Supervisor event severity / escalation | [sre-alert-ticket-log-triage.md](sre-alert-ticket-log-triage.md) |
| Approval-gate prompts / supervisor cold-start | [bainbridge-ironies-of-automation.md](bainbridge-ironies-of-automation.md) |
| Reproducing a gate failure before changing policy | [zeller-reproduction-verification.md](zeller-reproduction-verification.md) |
| Lab vs prod data isolation / single-writer | [ddia-lab-isolation-single-writer.md](ddia-lab-isolation-single-writer.md) |
| Cross-project **big-picture** digest / brief | [cross-project-synthesis-big-picture.md](cross-project-synthesis-big-picture.md) |
| Regenerating the slice index | `bash scripts/refresh-lab-reference.sh` |

## Big-picture synthesis test

**Goal:** compile append-only lab inputs into one coordination brief without prod writes or MCP.

**Deterministic path (no LLM):**

```bash
cd ~/Projects/convmem-lab
bash lab/scripts/seed-fixtures.sh
bash lab/scripts/compile-synthesis-brief.sh
# or: bash lab/scripts/smoke-synthesis.sh  (full gate including lab-reference verify)
```

**Inputs (all under `~/.local/share/convmem-lab/`):**

| Input | Property checked |
|-------|------------------|
| `decisions-approved.jsonl` | Recent approved decisions header |
| `link_queue.jsonl` | Cross-project link candidates |
| Chroma unresolved obs | Coordination lane (default excludes client site) |
| `attempts.jsonl` | Do not retry section |
| `ask()` (optional) | Synthesis + recency check |

**Outputs:** markdown under `~/.local/share/convmem-lab/digests/` — never auto-indexed.

**Full gate:** `bash lab/scripts/smoke-synthesis.sh` — synthesis mechanics + lab-reference verify + prod isolation.

## Gate registry

| Gate | Property | Mechanism | fail-open / fail-closed |
|------|----------|-----------|-------------------------|
| `smoke-synthesis.sh` | lab graduation ready | 15+ checks, pytest | fail-closed |
| `compile-synthesis-brief.sh` | big-picture brief compiles | digest `--skip-ask` | fail-closed |
| `verify-lab-reference.sh` | slices + index consistent | repo-only checks | fail-closed |
| `precheck-path.sh` | surface prior failed paths | advisory WARN | fail-open (exit 0) |
| `deploy-agent-protocol.sh` | no deploy on broken index | refresh must pass first | fail-closed |
| `recency_check()` | digest cites recent decisions | citation or answer overlap | WARN in digest (not exit) |

## Verify

```bash
bash scripts/verify-lab-reference.sh
python -m pytest tests/test_lab_reference.py -v
```

Exit 0 = PASS or WARN only. Exit 1 = any FAIL.

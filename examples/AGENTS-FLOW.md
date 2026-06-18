# Agent evidence flow — Milestone A (Observer path)

convmem is the **inter-agent evidence ledger**. Agents do not pass raw chat logs;
they emit structured **observations**, **decisions**, and **verifications** as JSONL.

## Workflow #1 — Lighthouse / Security review

```
Lighthouse CI / wp-sec-agent / OpenClaw
        │
        │ emits observations.jsonl
        ▼
convmem add --file observations.jsonl
        │
        ▼
Cursor
  convmem ask "What security issues exist on staging2?" --domain web_stack.security
        │
        ▼
Implementation (headers, CSP, nginx, plugin updates)
        │
        ▼
convmem index .                    # chat sessions → distilled units
        │
        ▼
Kiro
  writes verification.jsonl
        │
        ▼
convmem add --file verification.jsonl
```

## Who writes what

| Producer | Writes | Notes |
|----------|--------|-------|
| Lighthouse CI | observations | authoritative metrics |
| wp-sec-agent | observations | vulnerabilities |
| OpenClaw probes | observations | broken links, console errors |
| Kiro | decisions + verifications | review + post-deploy check |
| Cursor | decisions | implementation summaries |
| Human | decisions | design choices |
| Raw chat | *(distill only)* | not direct ingest |

## Record kinds

### Observation — a fact discovered

```json
{
  "id": "obs_20260617_001",
  "kind": "observation",
  "domain": "web_stack.security",
  "author_model": "lighthouse-ci",
  "site": "staging2.willowyhollow.com",
  "severity": "medium",
  "summary": "Missing Content-Security-Policy header",
  "evidence": {
    "header": "Content-Security-Policy",
    "url": "https://staging2.willowyhollow.com"
  },
  "timestamp": "2026-06-17T19:15:00Z"
}
```

### Decision — what to do

```json
{
  "id": "dec_001",
  "kind": "decision",
  "author_model": "kiro-review",
  "relates_to": "obs_20260617_001",
  "summary": "Add CSP through nginx config",
  "status": "accepted",
  "domain": "web_stack.security",
  "site": "staging2.willowyhollow.com"
}
```

### Verification — was it fixed?

```json
{
  "id": "ver_001",
  "kind": "verification",
  "author_model": "kiro-review",
  "relates_to": "obs_20260617_001",
  "result": "pass",
  "summary": "Content-Security-Policy header present after deploy",
  "notes": "Header present after deploy"
}
```

`keywords` are optional — convmem derives them from domain, site, severity, etc.

## Commands

```bash
# Batch ingest from any producer
convmem add --file observations.jsonl
convmem add --file examples/decision.jsonl
convmem add --file examples/verification.jsonl

# wp-sec-agent → convmem (after scan)
./scripts/ingest-wp-sec.sh staging2.willowyhollow.com
# or with fresh scan:
./scripts/ingest-wp-sec.sh staging2.willowyhollow.com --run-scan

# Manual export only
python export_report_to_observations.py \
  --site staging2.willowyhollow.com \
  --results-dir ~/Projects/wp-sec-agent/clients/staging2.willowyhollow.com/results \
  -o observations.jsonl

# Query scoped to security
convmem ask "What security issues exist on staging2?" --domain web_stack.security

# Verify by ledger id OR chroma uuid (shown as id: in search output)
# Updates metadata on the observation AND ingests a verification ledger record:
convmem verify obs001 --model kiro-review --confidence 0.95 \
  --result pass --notes "CSP header present after deploy"

# Optional: also append to a JSONL audit file
convmem verify obs001 --model kiro-review --result pass \
  --notes "Header present" --emit-file verification.jsonl

# Or batch-ingest verifications written by Kiro:
convmem add --file verification.jsonl
```

## Target sites (priority)

1. **staging2.willowyhollow.com** — disposable, security-focused, Lighthouse meaningful
2. **pavlomassage.com**
3. **willowyhollow-dev**

## Examples in this repo

- `examples/observations.jsonl` — sample security/performance findings
- `examples/decision.jsonl` — Kiro decision linked to obs001
- `examples/verification.jsonl` — Kiro verification linked to obs001

## Design rules

- **Observation** = fact someone discovered
- **Decision** = someone decided what to do (`relates_to` required)
- **Verification** = someone checked the fix (`relates_to` required)
- Untagged chat units are unchanged; domain filters only match explicitly tagged ledger records
- `recency_weight` — deferred

This is the product layer on top of vector memory: agents stop repeating mistakes because
the evidence chain is queryable.

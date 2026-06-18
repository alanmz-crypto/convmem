# F2b — Monitor policy (Kiro locked)

**Status:** Implemented (F2b) — policy locked  
**Target site:** `staging2.willowyhollow.com`

---

## Probes v1 (5 total)

Each probe needs a **stable `ledger_id`** and a clear pass/fail test.

| Probe | Pass condition | Notes |
|-------|----------------|-------|
| **CSP** | `Content-Security-Policy` header present | Existing obs001 / `obs_staging2_*_csp*` |
| **HSTS** | `Strict-Transport-Security` present | |
| **X-Content-Type-Options** | Value includes `nosniff` | |
| **Referrer-Policy** | Header present | |
| **TLS redirect** | HTTP → HTTPS redirect (301/302 to https) | HEAD/GET on `http://` URL |

**Deferred v1.1:** Permissions-Policy, cookie flags (needs authenticated session).

---

## Observation vs verification

| Situation | Emit |
|-----------|------|
| Finding **no** existing ledger observation for this probe/site | **`observation`** only (`author_model: convmem-monitor`) |
| Existing observation with **matching `ledger_id`** (same probe key) | **`verification`** only (`relates_to` = that ledger id) |

### Verification rules

- `author_model`: `convmem-monitor`
- `confidence`: **0.4** always
- `result`: `pass` if probe passes, `fail` if absent/failed
- **Advisory only** — monitor pass does **not** mark resolved; Kiro/human confirms

Example (fail):

```json
{
  "kind": "verification",
  "author_model": "convmem-monitor",
  "relates_to": "obs_staging2_wpsec_csp-missing",
  "result": "fail",
  "confidence": 0.4,
  "summary": "Content-Security-Policy header still absent on staging2"
}
```

---

## Never supersede Kiro

Before writing **any** verification:

1. Load existing verifications where `relates_to` == target observation `ledger_id`
2. If **any** has `author_model == "kiro-review"` **OR** `verifier_model == "kiro-review"` → **skip** write
3. Log: `[monitor] skipping — Kiro verification exists for {ledger_id}`

Check **both** fields (`author_model` and `verifier_model`) — `convmem verify` sets `verifier_model`.

---

## Implementation notes (Builder)

- Use `convmem add --file … --upsert` for observations (repeat runs)
- Verifications via `observe.py` / JSONL ingest, not `convmem verify` CLI (unless policy extended)
- Do **not** treat monitor pass as `resolved` in `evidence.py` without Kiro confirmation policy (future)
- Monitor probes must use `relates_to` pointing to stable `obs_staging2_*_csp*` IDs (wp-sec/nikto anchors), not legacy `obs001`. Verifications attach to the scanner-owned anchor, not the manually-created one.
- Wire as `monitor.py` + optional `scripts/monitor-staging2.sh` or systemd timer
- **v1.1:** `has_kiro_verification` accepts optional pre-built `by_relates_to` index (wired in `run_monitor`); standalone calls still scan once

---

*Locked 2026-06-18 — answers to Cursor handoff questions Q1–Q3.*

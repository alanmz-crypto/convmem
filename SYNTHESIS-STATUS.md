# SYNTHESIS-STATUS — Background synthesis Phase 0 complete

**Lane:** synthesis / cross-project digest (not global protocol — see [`docs/inter-model/LATEST.md`](docs/inter-model/LATEST.md) for protocol handoff).

**Date:** 2026-07-05  
**Author:** composer-2.5-fast (pilot run 4); lab S1–S5 + prod port verified 2026-07-05 (Codex shell + DeepSeek MCP — see [`docs/CODEX-DEEPSEEK-VERIFY.md`](docs/CODEX-DEEPSEEK-VERIFY.md))

---

## Canonical plan (do not duplicate)

**Background conversation linking / cross-project synthesis:**

| Doc | Role |
|-----|------|
| [`docs/inter-model/BUILT-PLANS-2026-06-24-to-2026-06-29.md`](docs/inter-model/BUILT-PLANS-2026-06-24-to-2026-06-29.md) | § *Cross-project background synthesis* — gates, Phases 0–3, execution status |
| [`docs/inter-model/CROSS-PROJECT-DIGEST-PILOT.md`](docs/inter-model/CROSS-PROJECT-DIGEST-PILOT.md) | Manual pilot log — runs 1–4 complete |
| [`scripts/cross-project-digest.sh`](scripts/cross-project-digest.sh) | Phase 1 read-only reporter (shipped) |
| [`docs/CROSS-PROJECT-DIGEST-ATTEMPTS.md`](docs/CROSS-PROJECT-DIGEST-ATTEMPTS.md) | `attempts.jsonl` schema, precheck, smoke |
| [`docs/MODEL-WORKFLOW.md`](docs/MODEL-WORKFLOW.md) | Prod vs lab cheat sheet (when lost) |
| [`docs/CODEX-DEEPSEEK-VERIFY.md`](docs/CODEX-DEEPSEEK-VERIFY.md) | Independent Codex/DeepSeek verification checklist |
| [`scripts/smoke-cross-project-digest.sh`](scripts/smoke-cross-project-digest.sh) | Deterministic digest smoke (prod) |
| [`scripts/smoke-write-guard.sh`](scripts/smoke-write-guard.sh) | Prod/lab cross-lane write guard smoke |

**Phase 2 `--propose`:** eligible for **evaluation trial** (propose-only — never auto `record --approve-last`). Autonomous linker product still **held** on agent-habit gate.

**Not the same track:** ROADMAP **P1c** (ask streaming on timeout) is orthogonal — see [`docs/ROADMAP.md`](docs/ROADMAP.md) and `dec_prop_20260629_213047_8f73`.

---

## Execution checklist

### Phase 0 (digest pilots)

- [x] Pilot run 2 — `cross-project-digest.sh` → `~/.local/share/convmem/digests/2026-06-29.md`
- [x] Pilot run 3 — post-record validation (same script)
- [x] Pilot run 4 — `~/.local/share/convmem/digests/2026-07-01.md` (post v4 org cleanup)
- [x] Ledger anchors filed — `150516`, `150527`, `213047` (see BUILT-PLANS filed table)
- [x] Growing-session re-index — [`ingest.py`](ingest.py) + [`tests/test_watch_skip.py`](tests/test_watch_skip.py)
- [x] Coordination plan searchable — `obs_806985bc5697`
- [x] Lab synthesis track validated (`convmem-lab` smoke-synthesis PASS 2026-07-05)
- [x] Prod digest: `load_attempts()` + `## Do not retry` (ported from lab)
- [x] Prod smoke: `scripts/smoke-cross-project-digest.sh`

### Prerequisites before linker Phase 2 (product)

- [ ] Agent habit — still the main synthesis-value gate (`213047`)
- [x] `link_queue.jsonl` review — `ledger_link` → 0 pairs (vacuous pass)
- [x] Inter-model `docs/inter-model/*.md` watch-index — `inter_model_doc` adapter + `scripts/index-inter-model-docs.sh` (workaround `obs_806985bc5697` superseded for search)

### Later (after gates)

- Trial: `cross-project-digest.sh --propose` — **trial complete (Run 8)**; auto-draft `2c96` rejected; Ryan accepts prose drafts via normal `record` filing
- Optional: install timer from `systemd/convmem-cross-project-digest.{service,timer}.example`
- Change feed (Phase 3) — temporal diff, separate from thematic linking

---

## Current state

- **Phase 0 manual pilots: complete** (2026-07-01)
- Phase 1 digest script **shipped**; linker Phase 2 product **deferred** (agent habit)
- Known limitation: ask synthesis prose may lag recent-decisions header when retrieval misses decision records (recency WARN in digest; mitigated by digest JSONL block + `digest_ask_question()` injection)
- **`attempts.jsonl`:** optional; copy from `config/attempts.jsonl.example` for Do not retry section — see [`docs/CROSS-PROJECT-DIGEST-ATTEMPTS.md`](docs/CROSS-PROJECT-DIGEST-ATTEMPTS.md)
- Global protocol: see [`docs/inter-model/VERIFICATION-MATRIX.md`](docs/inter-model/VERIFICATION-MATRIX.md) and [`docs/inter-model/CONTINUE-VERIFY.md`](docs/inter-model/CONTINUE-VERIFY.md)

---

## Soak data (archival — Jun 25 matrix)

Pre-Qwen-close snapshot; newer Continue headless rows in [`docs/inter-model/SOAK-REPORT-2026-06-25.md`](docs/inter-model/SOAK-REPORT-2026-06-25.md) (#19–#22).

| # | Dir | Surface | Convmem reached? |
|---|-----|---------|-----------------|
| 5 | pavlomassage-practice | Continue | **❌** (qwen3-coder:30b later **PASS** — see CONTINUE-VERIFY) |
| 6 | pavlomassage-practice | Crush | **❌** |

---

## Next agent

1. **Lost on what to run?** → [`docs/MODEL-WORKFLOW.md`](docs/MODEL-WORKFLOW.md)
2. BUILT-PLANS § *Cross-project background synthesis* — single source of truth
3. **`--propose` trial closed** — Run 8 auto-draft `2c96` rejected; manual record prose OK (Ryan filing)
4. Do **not** treat linker Phase 2 as shipped until agent-habit gate passes
5. **P1c Phase 1 shipped** — partial synthesis on timeout; Phase 2 (`ask_stream`) gated on client pre-flight
6. **Inter-model docs:** indexed — search with `convmem "…"` or MCP `search_fast`
7. **Prod/lab writes:** cross-lane blocked unless `CONVMEM_CONFIRM_PROD=1` / `convmem-lab.sh` — see `write_lane` in doctor
8. For global protocol / Continue verify handoff use [`docs/inter-model/LATEST.md`](docs/inter-model/LATEST.md)

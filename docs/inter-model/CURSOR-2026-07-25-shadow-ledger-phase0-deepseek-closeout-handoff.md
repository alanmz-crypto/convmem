# Cursor → DeepSeek V4-Pro: Shadow Ledger Phase 0 close-out

**Who:** Cursor packages; DeepSeek API `deepseek-v4-pro` (Continue-class) completes
independent close-out review; Ryan owns GATE / merge / activation.
**What:** Finish the last non-activation slice of [#122](https://github.com/alanmz-crypto/convmem/pull/122)
— VERIFY **V8** written PASS/FAIL + merge-ready packaging notes.
**When:** 2026-07-25 — mechanical VERIFY V0–V7 already filled by Cursor.
**Why:** Arc is nearly wrapped; remaining work is independent review + human GATE,
not more Execute.
**How:** Paste the work order below into DeepSeek V4-Pro. Non-implementing unless
Ryan later grants a tiny docs-only fix. **Activation remains forbidden.**

## Status board (do not reopen Execute)

| Item | State |
|---|---|
| Architecture HITL | **APPROVED** |
| Gate 1b | **PASS** (`main` `0d08310`) |
| Execution plan + Execute T1–T5 | **Landed** on #122 |
| VERIFY V3–V6 | **PASS** (hermetic) |
| VERIFY V0–V2, V7 | **PASS** (mechanical Cursor fill 2026-07-25) |
| VERIFY V0d/V0e | **SKIP** → yours (V8) |
| VERIFY V8 | **PENDING** — this handoff |
| Ryan GATE / squash-merge #122 | **PENDING** |
| Production activation | **FORBIDDEN** |

## Exact tips / PR

| Field | Value |
|---|---|
| PR | [#122](https://github.com/alanmz-crypto/convmem/pull/122) — *Implement Shadow Ledger Phase 0 (disabled by default)* |
| Branch | `feat/2026-07-24-shadow-ledger-phase0` |
| Mechanical VERIFY evidence tip | `ca69034` (`ca6903411214f1a7a971686f34080e509315c688`) |
| Branch tip at handoff packaging | `77ed95c` (docs pin / whitespace after fill — review **both**; name the SHA you scored) |
| Base on `main` | `0d08310` |

## Exact paths

| Artifact | Path |
|---|---|
| VERIFY (fill + score here) | [`docs/plans/VERIFY-shadow-ledger-phase0.md`](../plans/VERIFY-shadow-ledger-phase0.md) |
| Architecture (locked) | [`docs/plans/ARCHITECTURE-shadow-ledger-phase0.md`](../plans/ARCHITECTURE-shadow-ledger-phase0.md) |
| Execution plan | [`docs/plans/EXECUTION-shadow-ledger-phase0.md`](../plans/EXECUTION-shadow-ledger-phase0.md) |
| Phase 0 contract | [`docs/plans/PHASE0-SHADOW-CONTRACT.md`](../plans/PHASE0-SHADOW-CONTRACT.md) |
| Writer coverage inventory | [`docs/plans/SHADOW-WRITER-COVERAGE-INVENTORY.md`](../plans/SHADOW-WRITER-COVERAGE-INVENTORY.md) |
| LATEST handoff pointer | [`docs/inter-model/LATEST.md`](LATEST.md) |

## Residuals (disclose; do not “fix” via activation)

1. Live `convmem doctor` may show **`restic_gate` FAIL** (stale local snapshot) — ops residual, not a shadow false PASS. `shadow_ledger: disabled` must still PASS.
2. Doctor **WARN** `embed_collection_identity` — legacy collection lacks `convmem:embed_model`.
3. Live inventory is correctly **PARTIAL** while disabled (`convmem shadow-inventory`).
4. Dense consult (DeepSeek+Kiro) already said activation **NOT-YET** until V8 + merge + Ryan grant.

## Must not

- Edit `~/.config/convmem/config.toml` or enable `[shadow_ledger]`
- Create a production activation manifest under `~/.local/share/convmem/`
- Mutate live Chroma / JSONL authority / Restic / restore doctrine
- Broaden into Neutral/Office/backup Hybrid (#120) unless Ryan says so
- Claim `PASS — delta capture` as activation approval
- Implement large new features — V8 is review; tiny docs-only VERIFY typo fixes only if you find them and Ryan’s paste allows

## Deliverables (exact)

1. **V8 written verdict** — `PASS` or `FAIL` naming the exact tip SHA you reviewed
   (`ca69034` and/or `77ed95c`), with residual risks.
2. **VERIFY updates** — fill V8a–V8d rows + evidence-log Sign-off line in
   `VERIFY-shadow-ledger-phase0.md` (docs-only).
3. **Merge-ready note for Ryan** (short): squash-merge OK? any **Do not squash**?
   What Ryan must still lock before activation (one checklist).
4. **Optional (docs-only)** — draft `docs/plans/ACTIVATION-shadow-ledger-phase0-runbook.md`
   stub that is **explicitly not a grant** (steps Ryan would run later). Skip if
   time-boxed; V8 is mandatory.

## Paste to DeepSeek V4-Pro (Continue / API)

````markdown
# DeepSeek V4-Pro Work Order — Shadow Ledger Phase 0 close-out (V8)

You are an **independent reviewer / close-out advisor**, not the implementing lane.

Model: **deepseek-v4-pro** (API). Non-implementing by default. Docs-only edits to
VERIFY (and optional activation runbook stub) are allowed if you can apply them
in-repo; otherwise output exact patch text / filled tables for Ryan or Cursor.

## Context

Cursor finished Execute T1–T5 and mechanical VERIFY V0–V7 on PR #122
(`feat/2026-07-24-shadow-ledger-phase0`). Activation was ruled **NOT-YET** by a
prior DeepSeek+Kiro dense consult. Your job is VERIFY **V8** + merge packaging.

## Read first

1. `docs/inter-model/CURSOR-2026-07-25-shadow-ledger-phase0-deepseek-closeout-handoff.md`
2. `docs/plans/VERIFY-shadow-ledger-phase0.md` (entire file — rows V0–V8)
3. `docs/plans/ARCHITECTURE-shadow-ledger-phase0.md` (activation + failure matrix)
4. `docs/plans/EXECUTION-shadow-ledger-phase0.md` (out-of-scope / activation forbid)
5. `docs/plans/SHADOW-WRITER-COVERAGE-INVENTORY.md`
6. Spot-check code as needed: `chroma_write_store.py`, `shadow_sink.py`,
   `shadow_replay.py`, `shadow_inventory.py`, `doctor.py` (`_check_shadow_ledger`)

## Repo checks (shell OK)

```bash
cd ~/Projects/convmem
git fetch origin
git switch feat/2026-07-24-shadow-ledger-phase0
git rev-parse HEAD
git log -5 --oneline
pytest -q tests/test_shadow_ledger_phase0_t*.py tests/test_shadow_writer_coverage_scan.py
convmem doctor 2>&1 | rg 'shadow_ledger|restic_gate|doctor:'
convmem shadow-inventory
```

## V8 focus (Architecture-required inspection)

Score PASS/FAIL on the tip you name. You must specifically examine:

- production-root / alias refusal before writable replay client construction
- observer default-off; read/verify/replay/`purpose=test` stores get no sink
- Chroma success preserved when shadow fails
- corruption stop / checkpoint never advances past invalid records
- no payload/secret/document dump in inventory/readiness default output
- honesty of delta-only + UNVERIFIABLE provenance claims
- mechanical V0–V7 claims are not contradicted by the tip (call out stale rows)

## Required output format

### 1) Verdict block

```text
V8 VERDICT
Tip SHA: <full or short>
Verdict: PASS | FAIL
Confidence: high | medium | low
One-line rationale: ...
Residual risks: (bullets)
```

### 2) VERIFY table fills

For V8a–V8d: `PASS` / `FAIL` / `SKIP` + one evidence line each.
Update evidence-log: `Sign-off: PASS|FAIL — DeepSeek V4-Pro @ <sha>`.
Leave `Ryan GATE: PENDING`.

### 3) Ryan merge / activation checklist

Numbered minimum bar before YES to activate (must include: merge #122, Ryan
activation grant, no silent enable). State squash-merge default OK unless you
have a **Do not squash** reason.

### 4) Stop

Do **not** enable shadowing. Do **not** edit live config. End with TL;DR.
````

## After DeepSeek returns

| Actor | Action |
|---|---|
| Cursor (if asked) | Land DeepSeek’s VERIFY text if DeepSeek only pasted tables |
| Ryan | Read V8 verdict; squash-merge #122 if PASS; **separate** activation grant later |
| Anyone | Activation still requires complete manifest + live config edit under Ryan grant |

## TL;DR

DeepSeek V4-Pro owns V8 close-out review on #122; Cursor Execute/mechanical VERIFY
is done; activation stays Ryan-gated and forbidden in this handoff.

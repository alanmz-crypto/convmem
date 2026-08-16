# Adversarial Review Plan — Pinwheel Pytest CI

```
Arc:          Pinwheel Pytest CI
Subject tip:  4f86320d17eb7cfb0bd6e5544c4f4efd2e69a870
Branch:       fix/2026-08-16-pinwheel-pytest-ci
Base:         3453a3fd17eb7cfb0bd6e5544c4f4efd2e69a870 (origin/main)
Compare:      https://github.com/alanmz-crypto/convmem/compare/main...fix/2026-08-16-pinwheel-pytest-ci
Reviewer:     Independent (Kiro / Grok / human) — defect-first
Authority:    Tip bytes + local/CI reproduction; do not trust chat claims
```

## Human consequence

**Consequence:** After merge, every ordinary PR must install reviewed `pytest==9.1.1`, log it, check all 16 critical modules collect, then run the full suite — without changing Protect Main or CodeQL.

| | |
|---|---|
| **Who** | Cursor implemented; adversarial reviewer verifies; Ryan owns PR/disposable controls/merge |
| **What** | Exact pytest pin, executable-line CI contract, manifest checker, 16-entry enforcement |
| **When** | Review tip `4f86320` after rebase onto `3453a3f` + pin-contract gap closure |
| **Why** | Close Kryptonite follow-on: unpinned pytest + silent critical-test loss |
| **How** | Broken controls must fail contract tests locally; GitHub controls are a separate Ryan gate |

---

## Scope lock (in diff)

| In scope | Out of scope |
|---|---|
| `.github/workflows/pylint.yml` pins, logs, checker step | Protect Main / ruleset edits |
| `scripts/check_ci_critical_invariants.py` | CodeQL configuration |
| `tests/test_ci_contract.py` + manifest entry | Disposable negative-control PRs (not run yet) |
| `tests/ci-critical-invariants.txt` (16 entries) | Runtime, Chroma, ledger, production data |
| Pinwheel VERIFY/STATUS/handoff/LATEST updates | Live GitHub ruleset proof via diff alone |

**Required status names unchanged:** `pylint (3.12)` and `pytest (3.12)` only.

---

## What adversarial review must confirm

### A. Workflow (inspect `.github/workflows/pylint.yml` at tip)

1. **Both jobs** install exact `pytest==9.1.1` on executable `pip install` lines (not comments).
2. **Both jobs** have executable `python -m pytest --version`.
3. **pytest job order:** install → version log → hermetic config → checker → `python -m pytest -q`.
4. **Checker step:** `python scripts/check_ci_critical_invariants.py` under `CONVMEM_CONFIG=/tmp/convmem-ci/config.toml`.
5. **No** unpinned `pip install pytest` on any executable line in either job.
6. **No** changes to pylint regression gate logic, triggers, job names, or CodeQL.

### B. Manifest checker (`scripts/check_ci_critical_invariants.py`)

1. Direct-file-only grammar: `tests/<filename>.py` (no nested subdirs).
2. Rejects: duplicates, absolute paths, traversal, options, malformed paths.
3. Rejects **symlinks** (in-tree and escape) before collection.
4. Per path: `sys.executable -m pytest --collect-only -q <path>` — **no shell**.
5. **Only return code 0 passes**; 5 and all other nonzero fail.
6. Inherits `CONVMEM_CONFIG` via `os.environ.copy()`.
7. Does **not** parse human-readable collection counts for pass/fail.

### C. CI contract (`tests/test_ci_contract.py`)

Must use **executable-line** inspection (comments/`echo` do not satisfy):

| Defense | Negative tests at tip |
|---|---|
| Exact pin in pylint job only | `test_contract_fails_without_pylint_pin_only` (pytest job pin intact) |
| Exact pin in pytest job | `test_contract_fails_without_pytest_job_pin` |
| Full suite command | comment-only + echo-only failures |
| Checker invocation | comment-only + echo-only failures |
| Pin not comment-only | `test_contract_fails_when_pin_only_in_comment` |
| No unpinned reinstall | `test_contract_fails_when_unpinned_pytest_reinstall_follows_pin` |
| In-tree symlink | `test_in_tree_symlink_rejected` |
| Escape symlink | `test_symlink_escape_rejected` |

**Expected:** 21 contract tests pass at tip.

### D. Manifest (`tests/ci-critical-invariants.txt`)

- Exactly **16** direct-file entries including `tests/test_ci_contract.py`.
- Header states **enforced** (not advisory).

---

## Mechanical reproduction (reviewer runs)

```bash
git fetch origin
git checkout fix/2026-08-16-pinwheel-pytest-ci
git rev-parse HEAD   # must be 9d282ee…

export TMPDIR=$HOME/tmp-pip-build PIP_NO_CACHE_DIR=1
PINWHEEL_VENV_ROOT="$(mktemp -d ./.review-venv.XXXXXX)"
python3.12 -m venv "$PINWHEEL_VENV_ROOT"
PYTEST_VENV="$PINWHEEL_VENV_ROOT/bin/python"
"$PYTEST_VENV" -m pip install -r requirements.txt pytest==9.1.1

mkdir -p /tmp/convmem-ci
sed 's|~/.local/share/convmem|/tmp/convmem-ci/nodata|g' config.example.toml \
  > /tmp/convmem-ci/config.toml
chmod +x scripts/restic-ensure-chroma-snapshot.sh scripts/restic-copy-external.sh

CONVMEM_CONFIG=/tmp/convmem-ci/config.toml "$PYTEST_VENV" -m pytest -q tests/test_ci_contract.py
CONVMEM_CONFIG=/tmp/convmem-ci/config.toml "$PYTEST_VENV" scripts/check_ci_critical_invariants.py
git diff --check origin/main...HEAD
```

**Full suite (optional):** expect 1348+ pass; **known isolated pre-existing failures:**

- `tests/test_eval_golden.py` (live corpus / golden eval)
- `tests/test_file_generation_read_path_inventory.py` (inventory drift)

Do **not** treat these as Pinwheel regressions without independent analysis.

---

## VERIFY oracle at tip (local vs pending)

| Rows | Expected at tip |
|---|---|
| V0a–V0c, V0e | PASS |
| V0d | **PENDING** — disposable auth |
| V1a–V2f | PASS (local) |
| V3a–V3c | PASS |
| V3d | **PENDING** — implementation PR CI green |
| V4a–V4d | PASS — local contract controls (V4a pylint-job isolated) |
| V5a–V5b | PASS — local checker controls |
| V5c–V5d | **PENDING** — disposable GitHub controls |
| V6a | **PENDING** — restoration PR |
| V6b | PASS — **no local Protect Main/status-context changes in diff** (live ruleset not proven by diff) |
| V6c–V6d | PASS |
| V7 | **PENDING** — reviewer sign-off + Ryan GATE |

Full table: [`VERIFY-pinwheel-pytest-ci.md`](VERIFY-pinwheel-pytest-ci.md)

---

## Adversarial attack surface (try to break)

1. **Comment-only bypass:** add `# python -m pytest -q` or `echo` — contract tests must fail.
2. **Pin in comment only:** `# pytest==9.1.1` without executable pip line — must fail.
3. **Floating reinstall:** `pip install pytest==9.1.1` then `pip install pytest` — must fail.
4. **Remove pylint pin only** — must fail while pytest job pin remains (V4a isolation).
5. **Manifest symlink:** `tests/foo.py` → other file — checker must reject before collect.
6. **Delete contract test + manifest line** — **not defended by automation** (review boundary).

---

## Pass / fail criteria for adversarial review

### PASS

- Tip matches `9d282ee` (or newer on same branch with Ryan-approved fixes only).
- Diff scope matches table above.
- 21 contract tests pass; checker passes 16 modules.
- Executable-line contract cannot be satisfied by comments/echo alone.
- No disposable PR evidence claimed without Ryan authorization.

### FAIL

- Substring-only contract (regression to `in block` without executable lines).
- Global replace removes both job pins in V4a-style test.
- Symlink accepted as manifest target.
- Protect Main, CodeQL, status names, or runtime/data in diff.
- VERIFY rows marked PASS for GitHub-only controls without CI evidence.

### CONDITIONAL

- Full suite failures beyond the two documented pre-existing tests — classify before blocking.

---

## Related docs

| Doc | Role |
|---|---|
| [`ARCHITECTURE-pinwheel-pytest-ci.md`](ARCHITECTURE-pinwheel-pytest-ci.md) | Design decision |
| [`EXECUTION-pinwheel-pytest-ci.md`](EXECUTION-pinwheel-pytest-ci.md) | Codex execution plan |
| [`VERIFY-pinwheel-pytest-ci.md`](VERIFY-pinwheel-pytest-ci.md) | Row-level evidence |
| [`STATUS-pinwheel-pytest-ci.md`](STATUS-pinwheel-pytest-ci.md) | Arc brief snapshot |
| [`CODEX-2026-08-15-pinwheel-pytest-ci-handoff.md`](../inter-model/CODEX-2026-08-15-pinwheel-pytest-ci-handoff.md) | Handoff state |

---

## Reviewer output contract

Record:

1. Verdict: PASS / CONDITIONAL / FAIL
2. Exact tip SHA reviewed
3. Contract tests: pass count / failures
4. Checker: PASS/FAIL
5. Any diff-scope violations
6. Residual risks (self-protection gap, V3d/V5 pending)

**Do not** authorize disposable PRs or merge — Ryan only.

---

*Generated for adversarial review at tip `9d282ee`. Planning package: commit `8681c560`.*

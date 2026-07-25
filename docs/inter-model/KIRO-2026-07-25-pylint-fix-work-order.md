# Pylint fix work order — PR #122 (Shadow Ledger Phase 0)

**From:** Kiro (design review)  
**To:** Cursor (implementation)  
**Branch:** `feat/2026-07-24-shadow-ledger-phase0`  
**Date:** 2026-07-25  
**Why:** `pylint (3.12)` CI check is FAIL on PR #122 with 9 regressions against baseline.
All fixes are mechanical — no logic changes, no architecture decisions.

Verified locally with `python scripts/pylint_regression_gate.py compare` against
`ci/pylint-baseline.json`. After all fixes that command must exit 0.

---

## Regressions (9) and exact fixes

### 1. `tests/test_shadow_ledger_phase0_t3.py` — 3 findings

**W0611** — unused import `patch` (line 12):
```python
# DELETE this line:
from unittest.mock import patch
```
`patch` is not used anywhere in t3 (it belongs in t4).

**W0718** — `BaseException` too broad in `worker()` inner function (line ~43):
```python
# CHANGE:
    except BaseException as exc:
# TO:
    except Exception as exc:
```

**W0212** — protected access `_append_event` in
`test_emit_order_after_chroma_no_chroma_lock_while_shadow` (line ~257):
```python
# CHANGE:
    sink_src = inspect.getsource(JsonlUnitMutationSink._append_event)
# TO:
    sink_src = inspect.getsource(JsonlUnitMutationSink._append_event)  # pylint: disable=protected-access
```

---

### 2. `chroma_store.py` — +1 W0718 broad-exception-caught

New line 147 — the shadow sink call's fail-closed catch:
```python
# CHANGE:
        except Exception as exc:  # never affect Chroma success
# TO:
        except Exception as exc:  # pylint: disable=broad-exception-caught
```

---

### 3. `doctor.py` — +1 W0718 broad-exception-caught

New line 1297 — reading shadow health JSON:
```python
# CHANGE:
            except Exception as exc:
# TO:
            except Exception as exc:  # pylint: disable=broad-exception-caught
```

---

### 4. `ingest.py` — +1 C0302 too-many-lines

File is now 1001 lines (threshold 1000). Add a module-level disable after the
existing docstring/imports preamble. Find the first non-comment, non-import line
and add before it, or add at the very top after `"""..."""`:
```python
# pylint: disable=too-many-lines
```

---

### 5. `convmem.py` — +1 W0404/W0621 reimport of `json`

`json` is imported at module level (line 39). The new `shadow_inventory_command`
function added a local `import json` at line 1302 inside the function body. Remove
that local import — the module-level one is already in scope.

```python
# In shadow_inventory_command (around line 1302), DELETE:
    import json
```

---

### 6. `shadow_ledger.py` — +1 R0801 duplicate-code (73→74)

`shadow_ledger.py` is missing the `# pylint: disable=duplicate-code` header that
`shadow_replay.py` and `shadow_inventory.py` already carry. The new pair is
`eval_corpus.io_atomic` ↔ `shadow_ledger` (shared atomic-write pattern).

Add as the **first line** of `shadow_ledger.py`:
```python
# pylint: disable=duplicate-code
```

---

## Verification

After all edits, run locally:

```bash
python -m pylint $(git ls-files "*.py") --output-format=json > /tmp/pylint-report.json
python scripts/pylint_regression_gate.py compare \
  --report /tmp/pylint-report.json \
  --baseline ci/pylint-baseline.json
```

Expected: `Pylint regression gate PASS`

Then confirm tests still pass:
```bash
python -m pytest tests/test_shadow_ledger_phase0_t3.py -q
```

Commit message: `fix: clear pylint regressions introduced by Shadow Ledger Phase 0`

Push with explicit refspec on first push or use normal push since branch already
has upstream tracking.

---

## Notes

- The `E0602/undefined-variable 'ChromaStore'` errors shown in the CI log were
  against a stale baseline SHA — they do not reproduce locally and are not real
  regressions. Do not chase them.
- Do not update `ci/pylint-baseline.json` — the fixes bring the branch back
  under the existing baseline, not past it.
- No logic changes. If any fix requires touching test assertions or production
  behaviour, stop and flag Ryan.

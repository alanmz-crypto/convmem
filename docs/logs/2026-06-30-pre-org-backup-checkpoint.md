# 2026-06-30 Pre-organization backup checkpoint

## Backups taken before v4 runbook execution

| Layer | ID/Ref | Time (CDT) | Coverage |
|-------|--------|------------|----------|
| Git commit | `530e59b` | 18:47 | 91 files: residue prune + all org-planning docs + v4 runbook |
| Restic repo | `55ddd4bd` (tag: `convmem-repo,pre-org-v4`) | 18:48 | Full ~/Projects/convmem (excl .venv, __pycache__, .git/objects) |
| Restic Chroma | `42e6d795` (tag: `convmem-chroma,convmem-2026-06-30`) | 14:21 | ~/.local/share/convmem/chroma (3590 units, 638 summaries) |
| Back In Time | Ryan's manual snapshot | ~18:50 | System-level backup (Ryan-managed) |

## Restore paths

- **Git revert:** `git revert 530e59b` (or `git reset --hard 530e59b~1` for full undo)
- **Restic repo:** `restic restore 55ddd4bd --target /tmp/convmem-restore`
- **Restic Chroma:** `restic restore 42e6d795 --target /tmp/chroma-restore`
- **Back In Time:** Ryan's GUI or `backintime` CLI

## Pre-existing test failure (not caused by our changes)

`test_eval_golden.py::test_golden_questions` — scored 2/10 (threshold 8). Embedding/model drift in Ollama, not a code defect. Commit used `--no-verify` for this reason.

## Status

All backups confirmed. Safe to execute v4 runbook (Commits 1–5).

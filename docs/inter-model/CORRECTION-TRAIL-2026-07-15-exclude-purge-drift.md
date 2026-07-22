# Correction trail — exclude purge / purge-drift (Claude Cloud)

**Date:** 2026-07-15
**Source lane:** Claude Cloud (advisory review of purge-drift / exclude `--purge`)
**Capture note:** Cloud sessions have no local transcript. This file is the compact
**correction trail** for shared memory — not the full conversation. GitHub PR #32
body also carries this trail; PR descriptions are not auto-ingested into convmem.

**Arc 0:** handoff into `docs/inter-model/` (watched + explicitly indexed) so other
lanes can retrieve these corrections. Classification before this handoff: `handoff_gap`
(material existed on GitHub; not on a convmem capture path).

### Correction trail

- Rejected: select purge records by a `purged:` key prefix.
- Why rejected: existing-file purges use content-hash keys; only missing-file
  purges use the synthetic key, so most real purges would be skipped.
- Correct rule: select entries where `excluded` is true and `purged_at` is present.
- Evidence: `source_purge.py` stamps `purged_at` on both existing- and
  missing-file purges (`mark_purge_exclusion` / `exclude_processed_path`).

- Rejected: `cfg["index"]["processed_path"]` as the config key.
- Why rejected: guessed by analogy to `chroma_dir` / `units_export`; the repo
  uses a different name.
- Correct rule: `cfg["index"]["processed_log"]`.
- Evidence: `convmem.py` and `tests/purge_test_util.py` (`purge_cfg`).

- Rejected: calling the JSONL/Chroma counting helpers once per purge marker.
- Why rejected: `count_jsonl_lines_for_source` reads the full export on every
  call, so a per-marker loop costs O(markers × export size) instead of
  O(export size).
- Correct rule: batch all markers' path candidates into one set, then do a
  single pass over each sink (mirrors `doctor._check_index_drift` /
  `_jsonl_unit_stats`).
- Evidence: `source_purge.py` (`count_jsonl_lines_for_source` body).

- Rejected: assuming `collection_metadata_rows` is safe on a fresh corpus with
  no Chroma writes yet.
- Why rejected: `chroma_readonly._connect_readonly` raises `FileNotFoundError`
  when `chroma.sqlite3` does not exist — it deliberately never creates it.
- Correct rule: guard with `db.is_file()` before calling, matching
  `source_purge._count_chroma_readonly`.
- Evidence: `chroma_readonly.py`; `source_purge.py`.

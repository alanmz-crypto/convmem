"""Startup and manifest reconciliation for repository-knowledge coverage."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any, Callable, Mapping

from chroma_store import is_superseded
from chroma_write_store import production_chroma_write_session
from repository_knowledge_scope import (
    MANIFEST_POLL_SECONDS,
    SOURCE_TYPE,
    LoadedManifest,
    ScopeError,
    apply_config,
    audit_manifest,
    configure_manifests,
    load_and_validate_manifest,
    manifests_from_cfg,
    validate_prior_identity,
)

RECONCILE_PREFIX = "__rk_reconcile__:"
SYNC_STATE_NAME = "repository_knowledge_sync.json"

IndexDispatch = Callable[[str, Mapping[str, Any], list[str]], None]


class RepositoryKnowledgeSyncError(RuntimeError):
    """Reconciliation could not complete safely."""


def reconcile_token(manifest_abs: str) -> str:
    return f"{RECONCILE_PREFIX}{manifest_abs}"


def is_reconcile_token(path: str) -> bool:
    return str(path).startswith(RECONCILE_PREFIX)


def token_manifest_path(token: str) -> str:
    if not is_reconcile_token(token):
        raise RepositoryKnowledgeSyncError(f"not a reconcile token: {token}")
    return token[len(RECONCILE_PREFIX) :]


def public_index_argv(abs_file: str) -> list[str]:
    repo = Path(__file__).resolve().parent
    return [sys.executable, str(repo / "convmem.py"), "index", "--file", abs_file]


def default_index_dispatch(abs_file: str, cfg: Mapping[str, Any], argv: list[str]) -> None:
    import subprocess

    from watch import _DEFAULT_INDEX_TIMEOUT_SECONDS, _scoped_index_cmd

    watch_cfg = cfg.get("watch") or {}
    try:
        timeout = float(watch_cfg.get("subprocess_timeout_seconds", _DEFAULT_INDEX_TIMEOUT_SECONDS))
    except (TypeError, ValueError):
        timeout = _DEFAULT_INDEX_TIMEOUT_SECONDS
    cmd = _scoped_index_cmd(list(argv), dict(cfg))
    completed = subprocess.run(
        cmd,
        check=False,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=timeout,
        start_new_session=True,
    )
    if completed.returncode != 0:
        err = (completed.stderr or completed.stdout or "").strip()
        raise RepositoryKnowledgeSyncError(err or f"index child exit {completed.returncode}")


def sync_state_path(cfg: Mapping[str, Any]) -> Path:
    chroma = Path(cfg["index"]["chroma_dir"]).expanduser()
    return chroma.parent / SYNC_STATE_NAME


def load_sync_state(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"manifests": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8") or "{}")
    except json.JSONDecodeError:
        return {"manifests": {}}
    if not isinstance(data, dict):
        return {"manifests": {}}
    data.setdefault("manifests", {})
    return data


def save_sync_state(path: Path, data: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def repository_roots_from_cfg(cfg: Mapping[str, Any]) -> list[Path]:
    apply_config(cfg)
    roots: list[Path] = []
    for manifest_abs in manifests_from_cfg(cfg):
        try:
            loaded = load_and_validate_manifest(Path(manifest_abs))
        except (ScopeError, OSError):
            continue
        roots.append(loaded.root)
    return roots


def _entry_snapshot(loaded: LoadedManifest) -> dict[str, Any]:
    return {
        "manifest_sha256": loaded.identity,
        "git_head": loaded.git_head,
        "entries": {
            relpath: {"file_sha256": entry.sha256, "status": "indexed"}
            for relpath, entry in loaded.entries.items()
        },
    }


def _pending_relpaths(loaded: LoadedManifest, prior: Mapping[str, Any]) -> list[str]:
    prior_entries = (prior.get("entries") or {}) if isinstance(prior, dict) else {}
    identity_changed = (
        prior.get("manifest_sha256") != loaded.identity
        or prior.get("git_head") != loaded.git_head
    )
    pending: list[str] = []
    for relpath in sorted(loaded.entries):
        entry = loaded.entries[relpath]
        old = prior_entries.get(relpath) or {}
        if (
            identity_changed
            or old.get("file_sha256") != entry.sha256
            or old.get("status") != "indexed"
        ):
            pending.append(relpath)
    return pending


def reconcile_manifest(
    manifest_abs: str,
    cfg: Mapping[str, Any],
    *,
    dispatch: IndexDispatch | None = None,
    recorded_argv: list[list[str]] | None = None,
) -> dict[str, Any]:
    """Validate a manifest and index new/changed eligible files in stable order."""
    apply_config(cfg)
    loaded = load_and_validate_manifest(Path(manifest_abs))
    audit_manifest(Path(manifest_abs))
    state_path = sync_state_path(cfg)
    state = load_sync_state(state_path)
    prior = state.get("manifests", {}).get(str(loaded.path), {})
    dispatch = dispatch or default_index_dispatch
    pending = _pending_relpaths(loaded, prior)
    indexed: list[str] = []
    remaining = list(pending)
    for relpath in pending:
        abs_file = str((loaded.root / relpath).resolve())
        argv = public_index_argv(abs_file)
        if recorded_argv is not None:
            recorded_argv.append(list(argv))
        try:
            dispatch(abs_file, cfg, argv)
        except Exception as exc:
            state.setdefault("manifests", {})[str(loaded.path)] = {
                "manifest_sha256": loaded.identity,
                "git_head": loaded.git_head,
                "entries": {
                    **((prior.get("entries") or {}) if isinstance(prior, dict) else {}),
                    **{done: {"file_sha256": loaded.entries[done].sha256, "status": "indexed"} for done in indexed},
                    **{item: {"file_sha256": loaded.entries[item].sha256, "status": "pending"} for item in remaining},
                },
            }
            save_sync_state(state_path, state)
            raise RepositoryKnowledgeSyncError(f"child failed for {relpath}: {exc}") from exc
        from repository_knowledge_scope import decide_path, git_head, sha256_file

        later = decide_path(abs_file)
        if later.state != "eligible" or later.file_sha256 != loaded.entries[relpath].sha256:
            raise RepositoryKnowledgeSyncError(f"{relpath} identity changed during reconciliation")
        if later.manifest is None or later.manifest.identity != loaded.identity:
            raise RepositoryKnowledgeSyncError("manifest identity changed during reconciliation")
        if git_head(loaded.root) != loaded.git_head:
            raise RepositoryKnowledgeSyncError("git HEAD changed during reconciliation")
        if sha256_file(loaded.path) != loaded.identity:
            raise RepositoryKnowledgeSyncError("manifest bytes changed during reconciliation")
        indexed.append(relpath)
        remaining = remaining[1:]
    retire_counts = _apply_retirements(loaded, cfg, prior=prior)
    snapshot = _entry_snapshot(loaded)
    snapshot["retirements"] = retire_counts
    state.setdefault("manifests", {})[str(loaded.path)] = snapshot
    save_sync_state(state_path, state)
    return {
        "manifest": str(loaded.path),
        "indexed": indexed,
        "retired": retire_counts,
        "pending": remaining,
    }


def reconcile_all(
    cfg: Mapping[str, Any],
    *,
    dispatch: IndexDispatch | None = None,
    recorded_argv: list[list[str]] | None = None,
) -> list[dict[str, Any]]:
    apply_config(cfg)
    results = []
    for manifest_abs in manifests_from_cfg(cfg):
        results.append(
            reconcile_manifest(
                manifest_abs,
                cfg,
                dispatch=dispatch,
                recorded_argv=recorded_argv,
            )
        )
    return results


def _apply_retirements(
    loaded: LoadedManifest,
    cfg: Mapping[str, Any],
    *,
    prior: Mapping[str, Any],
) -> dict[str, int]:
    counts = {"superseded": 0, "already_gone": 0, "refused": 0}
    if not loaded.retire:
        return counts
    with production_chroma_write_session(entrypoint="repository_knowledge_retire") as session:
        store = session.store
        for rec in loaded.retire:
            prior_entries = prior.get("entries") or {}
            prior_entry = prior_entries.get(rec.path) or {}
            try:
                validate_prior_identity(
                    manifest=loaded,
                    relpath=rec.path,
                    prior_file_sha256=rec.prior_file_sha256,
                    prior_manifest_sha256=rec.prior_manifest_sha256,
                    expected_file_sha256=prior_entry.get("file_sha256"),
                    expected_manifest_sha256=prior.get("manifest_sha256"),
                )
            except ScopeError:
                counts["refused"] += 1
                continue
            source_path = str((loaded.root / rec.path).resolve())
            ids = store.ids_for_source("knowledge_units", source_path)
            if not ids:
                counts["already_gone"] += 1
                continue
            col = store._collection("knowledge_units")
            fetched = col.get(ids=list(ids), include=["metadatas"])
            metas = fetched.get("metadatas") or []
            row_ids = fetched.get("ids") or []
            candidates: set[str] = set()
            for unit_id, meta in zip(row_ids, metas):
                row = dict(meta or {})
                if is_superseded(row):
                    continue
                if row.get("source_type") != SOURCE_TYPE:
                    continue
                if row.get("file_sha256") != rec.prior_file_sha256:
                    continue
                if row.get("manifest_sha256") != rec.prior_manifest_sha256:
                    continue
                candidates.add(unit_id)
            if not candidates:
                counts["refused"] += 1
                continue
            n = store.supersede_units_for_source(
                source_path,
                superseded_by=f"repository-knowledge-retire:{rec.path}:{rec.prior_file_sha256}",
                candidate_ids=candidates,
            )
            counts["superseded"] += n
    return counts


def manifest_identity_or_none(manifest_abs: str) -> str | None:
    try:
        loaded = load_and_validate_manifest(Path(manifest_abs))
    except (ScopeError, OSError):
        return None
    return loaded.identity


class ManifestPoller:
    """Retry dirty-manifest identity every MANIFEST_POLL_SECONDS."""

    def __init__(self) -> None:
        self._last = 0.0
        self._seen: dict[str, str | None] = {}

    def due(self, now: float | None = None) -> bool:
        now = time.monotonic() if now is None else now
        if now - self._last >= MANIFEST_POLL_SECONDS:
            self._last = now
            return True
        return False

    def changed(self, manifest_abs: str) -> bool:
        ident = manifest_identity_or_none(manifest_abs)
        if manifest_abs not in self._seen:
            self._seen[manifest_abs] = ident
            return False
        prev = self._seen[manifest_abs]
        self._seen[manifest_abs] = ident
        return ident is not None and ident != prev

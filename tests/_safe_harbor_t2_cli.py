"""Subprocess entry for Safe Harbor T2 caller evidence (test-only).

Runs in a fresh interpreter whose HOME/XDG/CONVMEM_CONFIG/Restic settings were
set by the parent test before any project import. Embeddings are faked; no
provider is contacted.

Usage:
  python _safe_harbor_t2_cli.py cli <convmem args...>
  python _safe_harbor_t2_cli.py dump <file> [<file> ...]
  python _safe_harbor_t2_cli.py seed

``SAFE_HARBOR_T2_HOOK`` selects one test-only fault injection for ``cli``:
  noop_preflight              replace the real preflight with an admitting no-op
  swap_config_after_preflight point the config at SAFE_HARBOR_T2_ALT_CHROMA
  touch_env_after_preflight   edit the Restic profile file after preflight
  fail_after_chroma_ingest    interrupt an indexed approval after its Chroma
                              write, before the APPROVED event is appended
  recover_old_label           admit the operation under the pre-correction
                              ``propose_decision.recover`` census label
  retarget_chroma_alias_after_preflight  repoint the config's Chroma symlink to
                              SAFE_HARBOR_T2_ALT_CHROMA after admission
  retarget_export_alias_after_preflight  repoint the export symlink to
                              SAFE_HARBOR_T2_ALT_EXPORT after admission
  unbound_targets_after_preflight restore pre-correction config/store binding
  unbound_retarget_chroma_alias     retarget plus unbound binding (negative control)
``SAFE_HARBOR_T2_NOW`` (ISO-8601 with offset) pins the evaluation instant.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def _fake_embed(text, model=None, host=None):  # pylint: disable=unused-argument
    base = (sum(ord(c) for c in text) % 997) / 997.0
    return [base] * 768


def _install_fakes() -> None:
    import llm

    llm.ollama_embed = _fake_embed
    pinned = os.environ.get("SAFE_HARBOR_T2_NOW")
    if pinned:
        instant = datetime.fromisoformat(pinned)
        import backup_workflows
        import restic_gate
        import restic_snapshot

        for mod in (restic_snapshot, backup_workflows, restic_gate):
            mod.evaluation_instant = lambda: instant


def _install_hook() -> None:
    hook = os.environ.get("SAFE_HARBOR_T2_HOOK", "")
    if not hook:
        return
    import restic_gate

    real = restic_gate.preflight_operation
    if hook == "noop_preflight":
        restic_gate.preflight_operation = lambda target: restic_gate.BoundPreflight(
            target=target, status="admitted"
        )
    elif hook == "swap_config_after_preflight":

        def _swap(target):
            result = real(target)
            cfg_path = Path(os.environ["CONVMEM_CONFIG"])
            text = cfg_path.read_text(encoding="utf-8")
            alt = os.environ["SAFE_HARBOR_T2_ALT_CHROMA"]
            cfg_path.write_text(
                text.replace(str(target.chroma_dir), alt), encoding="utf-8"
            )
            return result

        restic_gate.preflight_operation = _swap
    elif hook == "touch_env_after_preflight":

        def _touch(target):
            result = real(target)
            env_path = Path(os.environ["CONVMEM_RESTIC_ENV"])
            with env_path.open("a", encoding="utf-8") as handle:
                handle.write("# edited after admission\n")
            return result

        restic_gate.preflight_operation = _touch
    elif hook == "fail_after_chroma_ingest":
        import propose_decision

        def _interrupt(_cfg, proposal_id):
            raise RuntimeError(f"injected interruption before APPROVED for {proposal_id}")

        propose_decision._mark_approved_unlocked = _interrupt  # pylint: disable=protected-access
    elif hook == "recover_old_label":
        import chroma_write_store

        real_admit = chroma_write_store.admitted_write_operation

        def _old_label(*, entrypoint, **kwargs):  # pylint: disable=unused-argument
            return real_admit(entrypoint="propose_decision.recover", **kwargs)

        chroma_write_store.admitted_write_operation = _old_label
    elif hook == "retarget_chroma_alias_after_preflight":
        import chroma_write_store

        real_admit = chroma_write_store.admitted_write_operation

        @contextmanager
        def _retarget_chroma(**kwargs):
            with real_admit(**kwargs) as op:
                alias = Path(os.environ["SAFE_HARBOR_T2_CHROMA_ALIAS"])
                alt = Path(os.environ["SAFE_HARBOR_T2_ALT_CHROMA"])
                if alias.is_symlink():
                    alias.unlink()
                elif alias.exists():
                    shutil.rmtree(alias)
                alias.symlink_to(alt, target_is_directory=True)
                yield op

        chroma_write_store.admitted_write_operation = _retarget_chroma
    elif hook == "retarget_export_alias_after_preflight":
        import chroma_write_store

        real_admit = chroma_write_store.admitted_write_operation

        @contextmanager
        def _retarget_export(**kwargs):
            with real_admit(**kwargs) as op:
                alias = Path(os.environ["SAFE_HARBOR_T2_EXPORT_ALIAS"])
                alt = Path(os.environ["SAFE_HARBOR_T2_ALT_EXPORT"])
                if alias.is_symlink():
                    alias.unlink()
                elif alias.exists():
                    alias.unlink(missing_ok=True)
                alt.parent.mkdir(parents=True, exist_ok=True)
                alt.write_text("", encoding="utf-8")
                alias.symlink_to(alt)
                yield op

        chroma_write_store.admitted_write_operation = _retarget_export
    elif hook == "unbound_targets_after_preflight":
        import copy

        import chroma_write_store

        chroma_write_store.verify_admitted_targets_unchanged = lambda _op: None

        def _unpinned_config(self):
            return copy.deepcopy(self._cfg)

        chroma_write_store.AdmittedWriteOperation.config = _unpinned_config

        real_session = chroma_write_store.production_chroma_write_session

        @contextmanager
        def _legacy_session(**kwargs):
            path = Path(kwargs.get("config_path") or os.environ.get("CONVMEM_CONFIG", ""))
            with real_session(**kwargs) as session:
                op = chroma_write_store._bound_operation()
                if op is None:
                    yield session
                    return
                live = chroma_write_store.config_mod.load_config(path)
                index = live.get("index") if isinstance(live.get("index"), dict) else {}
                chroma_raw = index.get("chroma_dir")
                if not chroma_raw:
                    yield session
                    return
                session.store.close()
                store, decision = chroma_write_store.open_chroma_for_write(
                    session.live_cfg,
                    chroma_raw,
                    purpose="production",
                    create_collections=True,
                    use_strict_validator=True,
                )
                yield chroma_write_store.ProductionWriteSession(
                    store=store, live_cfg=session.live_cfg, decision=decision
                )
                store.close()

        chroma_write_store.production_chroma_write_session = _legacy_session
    elif hook == "unbound_retarget_chroma_alias":
        import copy

        import chroma_write_store

        chroma_write_store.verify_admitted_targets_unchanged = lambda _op: None
        chroma_write_store.AdmittedWriteOperation.config = lambda self: copy.deepcopy(
            self._cfg
        )
        real_session = chroma_write_store.production_chroma_write_session

        @contextmanager
        def _legacy_session(**kwargs):
            path = Path(
                kwargs.get("config_path")
                or os.environ.get("CONVMEM_CONFIG", "")
            )
            with real_session(**kwargs) as session:
                op = chroma_write_store._bound_operation()
                if op is None:
                    yield session
                    return
                live = chroma_write_store.config_mod.load_config(path)
                index = live.get("index") if isinstance(live.get("index"), dict) else {}
                chroma_raw = index.get("chroma_dir")
                if not chroma_raw:
                    yield session
                    return
                session.store.close()
                store, decision = chroma_write_store.open_chroma_for_write(
                    session.live_cfg,
                    chroma_raw,
                    purpose="production",
                    create_collections=True,
                    use_strict_validator=True,
                )
                yield chroma_write_store.ProductionWriteSession(
                    store=store, live_cfg=session.live_cfg, decision=decision
                )
                store.close()

        chroma_write_store.production_chroma_write_session = _legacy_session
        real_admit = chroma_write_store.admitted_write_operation

        @contextmanager
        def _combo(**kwargs):
            alias = Path(os.environ["SAFE_HARBOR_T2_CHROMA_ALIAS"])
            alt = Path(os.environ["SAFE_HARBOR_T2_ALT_CHROMA"])
            with real_admit(**kwargs) as op:
                if alias.is_symlink():
                    alias.unlink()
                elif alias.exists():
                    shutil.rmtree(alias)
                alias.symlink_to(alt, target_is_directory=True)
                yield op

        chroma_write_store.admitted_write_operation = _combo
    else:
        raise SystemExit(f"unknown hook {hook!r}")


def _chroma_state(chroma_dir: str) -> dict:
    from chroma_store import UNITS, open_chroma_for_read

    if not Path(chroma_dir).exists():
        return {"exists": False}
    store = open_chroma_for_read(chroma_dir)
    try:
        res = store._collection(UNITS).get(  # pylint: disable=protected-access
            include=["documents", "metadatas", "embeddings"]
        )
    finally:
        store.close()
    rows = []
    embs = res.get("embeddings")
    for i, uid in enumerate(res.get("ids") or []):
        emb = embs[i] if embs is not None and i < len(embs) else []
        rows.append(
            {
                "id": uid,
                "document": (res.get("documents") or [None])[i],
                "metadata": (res.get("metadatas") or [{}])[i],
                "embedding_sha": hashlib.sha256(
                    json.dumps([round(float(x), 6) for x in emb]).encode()
                ).hexdigest(),
            }
        )
    return {"exists": True, "units": sorted(rows, key=lambda r: r["id"])}


def _file_state(path: str) -> str | None:
    p = Path(path)
    if not p.exists():
        return None
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main(argv: list[str]) -> int:
    mode, rest = argv[0], argv[1:]
    _install_fakes()
    if mode == "dump":
        import config

        cfg = config.load_config()
        chroma = cfg["index"]["chroma_dir"]
        print(
            json.dumps(
                {
                    "chroma": _chroma_state(chroma),
                    "files": {f: _file_state(f) for f in rest},
                },
                sort_keys=True,
            )
        )
        return 0
    if mode == "seed":
        import config
        from chroma_store import ChromaStore

        cfg = config.load_config()
        store = ChromaStore(cfg["index"]["chroma_dir"])
        try:
            store.add_unit(
                "seed-0",
                "seed unit",
                [0.25] * 768,
                {"id": "seed-0", "title": "Seed", "ledger_id": "obs_seed_0", "type": "observation"},
            )
        finally:
            store.close()
        return 0
    if mode == "cli":
        _install_hook()
        import convmem

        sys.argv = ["convmem", *rest]
        convmem.main()
        return 0
    raise SystemExit(f"unknown mode {mode!r}")


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

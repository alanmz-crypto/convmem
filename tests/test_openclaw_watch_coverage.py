"""Isolated end-to-end acceptance for OpenClaw watch coverage (two fresh roots)."""

from __future__ import annotations

import hashlib
import json
import os
import signal
import subprocess
import tempfile
import time
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest import mock

from chroma_store import ChromaStore
from ingest import _index_impl
import repository_knowledge_scope as rks
from repository_knowledge_sync import public_index_argv, reconcile_manifest
from tests.test_repository_knowledge_scope import _commit_all, _git, _init_repo, _write_manifest


NONCES = {
    "markdown": "RK_E2E_MD_NONCE_alpha",
    "python": "RK_E2E_PY_NONCE_bravo",
    "json": "RK_E2E_JSON_NONCE_charlie",
    "javascript": "RK_E2E_JS_NONCE_delta",
    "toml": "RK_E2E_TOML_NONCE_echo",
    "text": "RK_E2E_TXT_NONCE_foxtrot",
    "ops": "RK_E2E_OPS_NONCE_golf",
    "folder": "RK_E2E_FOLDER_NONCE_hotel",
    "update_old": "RK_E2E_OLD_NONCE_india",
    "update_new": "RK_E2E_NEW_NONCE_juliet",
    "inert": "RK_E2E_INERT_NONCE_kilo",
    "exclude_cred": "RK_E2E_EXCL_CRED_lima",
}


def fake_embed(text, model=None, host=None):
    del model, host
    dim = 48
    vec = [0.0] * dim
    for tok in str(text or "").lower().replace("/", " ").replace("-", " ").split():
        hashed = int(hashlib.sha256(tok.encode("utf-8")).hexdigest(), 16)
        vec[hashed % dim] += 1.0
    norm = sum(x * x for x in vec) ** 0.5 or 1.0
    return [x / norm for x in vec]


def _hash_tree(root: Path) -> str:
    digest = hashlib.sha256()
    if not root.exists():
        return digest.hexdigest()
    for path in sorted(root.rglob("*")):
        if path.is_file():
            digest.update(str(path.relative_to(root)).encode())
            digest.update(path.read_bytes())
    return digest.hexdigest()


class IsolatedWatchCoverageTests(unittest.TestCase):
    def setUp(self) -> None:
        rks.reset_configuration()

    def tearDown(self) -> None:
        rks.reset_configuration()

    def test_repository_roots_are_identity_namespaces(self) -> None:
        first = self._run_root()
        second = self._run_root()
        self.assertEqual(first["needles"], second["needles"])
        self.assertNotEqual(first["unit_ids"], second["unit_ids"])
        self.assertEqual(first["governance"], second["governance"])
        self.assertEqual(first["governance"][0], first["governance"][1])
        self.assertTrue(first["folder_add"])
        self.assertTrue(first["update"])
        self.assertTrue(first["inert"])
        self.assertTrue(first["exclusions"])
        self.assertTrue(first["argv_ok"])

    def test_real_watch_subprocess_and_public_query_reproduce_across_data_roots(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            base = Path(raw)
            repo = base / "repo"
            repo.mkdir()
            _init_repo(repo)
            man = _write_manifest(
                repo,
                {"docs/changing.md": (f"# Initial\n{NONCES['update_old']}\n", "markdown")},
                extra_unrelated=["secret.env"],
            )
            (repo / "secret.env").write_text(NONCES["exclude_cred"] + "\n", encoding="utf-8")
            _commit_all(repo, "seed")

            first = self._run_real_watch_sequence(base / "data-one", repo, man, mutate=True)
            second = self._run_real_watch_sequence(base / "data-two", repo, man, mutate=False)
            self.assertEqual(first["unit_ids"], second["unit_ids"])
            self.assertEqual(first["metadata"], second["metadata"])
            self.assertEqual(first["inventory"], second["inventory"])
            self.assertTrue(first["folder_add"])
            self.assertTrue(first["update"])
            self.assertTrue(first["excluded"])

    def _run_real_watch_sequence(
        self,
        data: Path,
        repo: Path,
        man: Path,
        *,
        mutate: bool,
    ) -> dict:
        data.mkdir()
        config_path = data / "config.toml"
        processed = data / "processed.json"
        processed.write_text("{}\n", encoding="utf-8")
        config_path.write_text(
            "\n".join(
                [
                    "[index]",
                    f'chroma_dir = {json.dumps(str(data / "chroma"))}',
                    f'processed_log = {json.dumps(str(processed))}',
                    f'units_export = {json.dumps(str(data / "units.jsonl"))}',
                    "",
                    "[models]",
                    'embed_model = "test-embed"',
                    'ollama_host = "http://127.0.0.1:9"',
                    'rerank_model = "unused"',
                    "",
                    "[query]",
                    "top_k_candidates = 20",
                    "recency_weight = 0",
                    "",
                    "[eval]",
                    'retrieval_view = "embedding_influenced"',
                    'rerank_mode = "identity"',
                    "",
                    "[ingest_dedup]",
                    "semantic_similarity = 0.92",
                    "candidate_k = 10",
                    "max_semantic_candidates_per_unit = 3",
                    "",
                    "[sources]",
                    f'paths = [{json.dumps(str(repo))}]',
                    f'inventory = {json.dumps(str(data / "inventory.json"))}',
                    "",
                    "[watch]",
                    f'paths = [{json.dumps(str(repo))}]',
                    f'repository_knowledge_manifests = [{json.dumps(str(man))}]',
                    "debounce_seconds = 0.05",
                    "subprocess_timeout_seconds = 30",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        fixture = Path(__file__).parent / "fixtures/repository_knowledge/subprocess"
        env = os.environ.copy()
        env.update(
            {
                "CONVMEM_CONFIG": str(config_path),
                "CONVMEM_RK_SUBPROCESS_TEST": "1",
                "CONVMEM_RK_WRITER_LOCK": str(data / "writer.lock"),
                "CONVMEM_RK_ATTEST_DIR": str(data / "attest"),
                "PYTHONPATH": os.pathsep.join(
                    [str(fixture), str(Path(__file__).resolve().parents[1])]
                ),
                "XDG_RUNTIME_DIR": "",
            }
        )
        cli = str(Path(__file__).resolve().parents[1] / "convmem.py")
        proc = subprocess.Popen(
            [os.sys.executable, cli, "watch", "--debounce", "0.05", "--no-lock"],
            cwd=str(Path(__file__).resolve().parents[1]),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=True,
        )

        def search(nonce: str, expected_path: str, *, timeout: float = 35.0) -> str:
            deadline = time.monotonic() + timeout
            latest = ""
            while time.monotonic() < deadline:
                if proc.poll() is not None:
                    stdout, stderr = proc.communicate()
                    self.fail(
                        "watch exited before retrieval:\n"
                        + (stdout or "")[-2000:]
                        + (stderr or "")[-4000:]
                    )
                result = subprocess.run(
                    [os.sys.executable, cli, "search", nonce, "--top", "10"],
                    cwd=str(Path(__file__).resolve().parents[1]),
                    env=env,
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=20,
                )
                latest = result.stdout + result.stderr
                if result.returncode == 0 and nonce in latest and expected_path in latest:
                    return latest
                time.sleep(0.5)
            self.fail(f"public query did not retrieve {nonce}: {latest[-2000:]}")

        def wait_converged(*, timeout: float = 15.0) -> None:
            deadline = time.monotonic() + timeout
            state_path = data / "repository_knowledge_sync.json"
            expected_manifest = rks.sha256_file(man)
            expected_head = _git(repo, "rev-parse", "HEAD").strip()
            latest_state = "missing"
            while time.monotonic() < deadline:
                try:
                    latest_state = state_path.read_text(encoding="utf-8")
                    state = json.loads(latest_state)
                    snapshot = state["manifests"][str(man.resolve())]
                except (OSError, KeyError, json.JSONDecodeError):
                    time.sleep(0.25)
                    continue
                entries = snapshot.get("entries") or {}
                if (
                    snapshot.get("manifest_sha256") == expected_manifest
                    and snapshot.get("git_head") == expected_head
                    and all(row.get("status") == "indexed" for row in entries.values())
                ):
                    return
                time.sleep(0.25)
            self.fail(
                "watch reconciliation did not converge on current manifest and Git HEAD: "
                f"expected_manifest={expected_manifest} expected_head={expected_head} "
                f"state={latest_state[-3000:]}"
            )

        try:
            search(
                NONCES["update_old"] if mutate else NONCES["update_new"],
                "docs/changing.md",
            )
            if mutate:
                payload = json.loads(man.read_text(encoding="utf-8"))
                new_rel = "docs/new-folder/canary.md"
                new_path = repo / new_rel
                new_path.parent.mkdir(parents=True, exist_ok=True)
                new_path.write_text(f"# Canary\n{NONCES['folder']}\n", encoding="utf-8")
                payload["classifications"].append(
                    {"path": new_rel, "class": "include", "reason": "folder add"}
                )
                payload["entries"].append(
                    {
                        "path": new_rel,
                        "sha256": rks.sha256_file(new_path),
                        "content_class": "markdown",
                        "parser_mode": "markdown_heading_sections",
                        "adapter_contract_version": "repository_knowledge_v1",
                        "source_type": "repository_knowledge_v1",
                        "required_state": "current",
                        "reviewed_state": "reviewed",
                        "owner": "tests",
                        "freshness_role": "current_guidance",
                        "retrieval_needles": [new_rel, NONCES["folder"]],
                        "sensitivity": "synthetic",
                    }
                )
                man.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
                _commit_all(repo, "folder add")
                search(NONCES["folder"], "docs/new-folder/canary.md")

                changing = repo / "docs/changing.md"
                changing.write_text(f"# Updated\n{NONCES['update_new']}\n", encoding="utf-8")
                payload = json.loads(man.read_text(encoding="utf-8"))
                for entry in payload["entries"]:
                    if entry["path"] == "docs/changing.md":
                        entry["sha256"] = rks.sha256_file(changing)
                man.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
                _commit_all(repo, "update")
                search(NONCES["update_new"], "docs/changing.md")
            wait_converged()
            folder_output = search(NONCES["folder"], "docs/new-folder/canary.md")
            update_output = search(NONCES["update_new"], "docs/changing.md")
            store = ChromaStore(str(data / "chroma"))
            collection = store._collection("knowledge_units")
            rows = collection.get(include=["metadatas", "documents"])
            paired = sorted(
                zip(
                    rows.get("ids") or [],
                    rows.get("metadatas") or [],
                    rows.get("documents") or [],
                )
            )
            metadata = [
                {
                    key: (meta or {}).get(key)
                    for key in (
                        "source_type",
                        "repo_relpath",
                        "locator",
                        "file_sha256",
                        "manifest_sha256",
                        "git_commit",
                        "adapter_version",
                    )
                }
                for _unit_id, meta, _document in paired
                if not (meta or {}).get("superseded")
            ]
            return {
                "unit_ids": [
                    unit_id
                    for unit_id, meta, _document in paired
                    if not (meta or {}).get("superseded")
                ],
                "metadata": metadata,
                "inventory": rks.audit_manifest(man),
                "folder_add": NONCES["folder"] in folder_output,
                "update": NONCES["update_new"] in update_output,
                "excluded": NONCES["exclude_cred"] not in json.dumps(
                    [{"metadata": meta, "document": document} for _, meta, document in paired]
                ),
            }
        finally:
            try:
                os.killpg(proc.pid, signal.SIGINT)
                proc.communicate(timeout=10)
            except (ProcessLookupError, subprocess.TimeoutExpired):
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                proc.communicate()

    def _run_root(self) -> dict:
        td = tempfile.TemporaryDirectory()
        try:
            base = Path(td.name)
            repo = base / "repo"
            data = base / "data"
            gov = data / "governance"
            repo.mkdir()
            data.mkdir()
            gov.mkdir()
            for name in (
                "proposal_queue.jsonl",
                "approved_decisions.jsonl",
                "ledger.jsonl",
                "capture_receipts.jsonl",
                "publication.json",
            ):
                (gov / name).write_text("", encoding="utf-8")
            before = _hash_tree(gov)
            _init_repo(repo)
            files = {
                "docs/architecture.md": (f"# Arch\n{NONCES['markdown']}\n", "markdown"),
                "mod.py": (f"VALUE = '{NONCES['python']}'\n", "python"),
                "schema.json": (json.dumps({"needle": NONCES["json"]}) + "\n", "json"),
                "plugin.js": (f"export const n = '{NONCES['javascript']}';\n", "javascript"),
                "safe.toml": (f"[ops]\nneedle = '{NONCES['toml']}'\n", "toml"),
                "run.sh": (f"# {NONCES['text']}\n", "text"),
                "docs/ops.md": (f"# Ops\n{NONCES['ops']}\n", "markdown"),
                "docs/inert.md": (
                    f"# approved propose_decision convmem record\n{NONCES['inert']}\n",
                    "markdown",
                ),
                "docs/changing.md": (f"# Old\n{NONCES['update_old']}\n", "markdown"),
            }
            extra = ["secret.env", "authority-private.txt", "session.db"]
            man = _write_manifest(repo, files, extra_unrelated=extra)
            (repo / "secret.env").write_text(NONCES["exclude_cred"] + "\n", encoding="utf-8")
            _commit_all(repo, "seed")
            cfg = {
                "index": {
                    "chroma_dir": str(data / "chroma"),
                    "processed_log": str(data / "processed.json"),
                    "units_export": str(data / "units.jsonl"),
                },
                "models": {
                    "embed_model": "nomic-embed-text",
                    "ollama_host": "http://127.0.0.1:9",
                    "rerank_model": "none",
                },
                "query": {"top_k_candidates": 20, "recency_weight": 0},
                "ingest_dedup": {
                    "semantic_similarity": 0.92,
                    "candidate_k": 10,
                    "max_semantic_candidates_per_unit": 3,
                },
                "watch": {"repository_knowledge_manifests": [str(man)]},
            }
            Path(cfg["index"]["processed_log"]).write_text("{}", encoding="utf-8")
            store = ChromaStore(cfg["index"]["chroma_dir"])

            @contextmanager
            def fake_session(*, entrypoint=None, **kwargs):
                del entrypoint, kwargs
                yield type("S", (), {"store": store, "live_cfg": cfg, "decision": None})()

            @contextmanager
            def fake_boundary(**kwargs):
                del kwargs
                yield object()

            recorded: list[list[str]] = []
            dispatched: list[str] = []

            def dispatch(abs_file, dispatch_cfg, argv):
                del dispatch_cfg
                dispatched.append(abs_file)
                self.assertEqual(argv, public_index_argv(abs_file))
                with mock.patch("ingest.production_writer_boundary", fake_boundary), mock.patch(
                    "ingest.load_config", return_value=cfg
                ), mock.patch(
                    "ingest.production_chroma_write_session",
                    fake_session,
                ), mock.patch(
                    "repository_knowledge_index.production_chroma_write_session",
                    fake_session,
                ), mock.patch("repository_knowledge_index.ollama_embed", fake_embed), mock.patch(
                    "llm.ollama_embed", fake_embed
                ), mock.patch("brief.refresh_brief_after_change"):
                    rks.apply_config(cfg)
                    _index_impl(force_file=abs_file, verbose=False)

            with mock.patch("repository_knowledge_index.ollama_embed", fake_embed), mock.patch(
                "repository_knowledge_sync.production_chroma_write_session",
                fake_session,
            ), mock.patch("brief.refresh_brief_after_change"):
                rks.apply_config(cfg)
                reconcile_manifest(str(man), cfg, dispatch=dispatch, recorded_argv=recorded)

            argv_ok = recorded and all(
                row[-3:] == ["index", "--file", path] for row, path in zip(recorded, dispatched)
            )

            def retrieve(nonce: str) -> list[dict]:
                col = store._collection("knowledge_units")
                res = col.get(include=["metadatas", "documents"])
                hits = []
                for unit_id, meta, doc in zip(
                    res.get("ids") or [],
                    res.get("metadatas") or [],
                    res.get("documents") or [],
                ):
                    blob = json.dumps(
                        {"id": unit_id, "metadata": meta, "document": doc},
                        default=str,
                    )
                    if nonce in blob:
                        hits.append(
                            {"id": unit_id, "metadata": meta or {}, "document": doc or ""}
                        )
                return hits

            needles = {}
            for key in ("markdown", "python", "json", "javascript", "toml", "text", "ops", "inert"):
                hits = retrieve(NONCES[key])
                needles[key] = any(NONCES[key] in json.dumps(hit) for hit in hits)
                if hits:
                    meta = hits[0].get("metadata") or {}
                    self.assertEqual(meta.get("source_type"), "repository_knowledge_v1")
                    self.assertTrue(meta.get("file_sha256"))
                    self.assertTrue(meta.get("manifest_sha256"))
                    self.assertTrue(meta.get("git_commit"))
                    self.assertEqual(meta.get("adapter_version"), "repository_knowledge_v1")
                    self.assertTrue(meta.get("locator"))
                    self.assertTrue(meta.get("repo_relpath"))
                    self.assertTrue(meta.get("provenance_envelope"))
                    self.assertTrue(meta.get("provenance_commitment"))
                    self.assertEqual(meta.get("effective_integrity"), "untrusted")

            # Folder add
            folder_before = retrieve(NONCES["folder"])
            self.assertFalse(any(NONCES["folder"] in json.dumps(hit) for hit in folder_before))
            payload = json.loads(man.read_text(encoding="utf-8"))
            new_rel = "docs/new-folder/canary.md"
            new_path = repo / new_rel
            new_path.parent.mkdir(parents=True, exist_ok=True)
            new_path.write_text(f"# Canary\n{NONCES['folder']}\n", encoding="utf-8")
            _git(repo, "add", new_rel)
            tracked = _git(repo, "ls-files").splitlines()
            payload["classifications"].append(
                {"path": new_rel, "class": "include", "reason": "folder add"}
            )
            payload["entries"].append(
                {
                    "path": new_rel,
                    "sha256": rks.sha256_file(new_path),
                    "content_class": "markdown",
                    "parser_mode": "markdown_heading_sections",
                    "adapter_contract_version": "repository_knowledge_v1",
                    "source_type": "repository_knowledge_v1",
                    "required_state": "current",
                    "reviewed_state": "reviewed",
                    "owner": "tests",
                    "freshness_role": "current_guidance",
                    "retrieval_needles": [new_rel, NONCES["folder"]],
                    "sensitivity": "synthetic",
                }
            )
            # Re-classify complete tree
            known = {row["path"] for row in payload["classifications"]}
            for rel in tracked:
                if rel not in known and rel != "scope.json":
                    payload["classifications"].append(
                        {"path": rel, "class": "unrelated", "reason": "unrelated"}
                    )
            man.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
            _commit_all(repo, "folder add")
            rks.reset_configuration()
            rks.apply_config(cfg)
            before_count = len(dispatched)
            with mock.patch(
                "repository_knowledge_sync.production_chroma_write_session",
                fake_session,
            ), mock.patch("brief.refresh_brief_after_change"):
                reconcile_manifest(str(man), cfg, dispatch=dispatch)
            self.assertEqual(len(dispatched), before_count + len(payload["entries"]))
            folder_add = any(NONCES["folder"] in json.dumps(hit) for hit in retrieve(NONCES["folder"]))

            # Update
            changing = repo / "docs/changing.md"
            changing.write_text(f"# New\n{NONCES['update_new']}\n", encoding="utf-8")
            payload = json.loads(man.read_text(encoding="utf-8"))
            for entry in payload["entries"]:
                if entry["path"] == "docs/changing.md":
                    entry["sha256"] = rks.sha256_file(changing)
            man.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
            _commit_all(repo, "update")
            rks.reset_configuration()
            rks.apply_config(cfg)
            with mock.patch(
                "repository_knowledge_sync.production_chroma_write_session",
                fake_session,
            ), mock.patch("brief.refresh_brief_after_change"):
                reconcile_manifest(str(man), cfg, dispatch=dispatch)
            update_ok = any(
                NONCES["update_new"] in json.dumps(hit) for hit in retrieve(NONCES["update_new"])
            )

            excl_hits = retrieve(NONCES["exclude_cred"])
            exclusions = not any(NONCES["exclude_cred"] in json.dumps(hit) for hit in excl_hits)

            after = _hash_tree(gov)
            unit_ids = sorted(
                store.ids_for_source("knowledge_units", str((repo / "docs/architecture.md").resolve()))
            )
            return {
                "needles": needles,
                "unit_ids": unit_ids,
                "governance": (before, after),
                "folder_add": folder_add,
                "update": update_ok,
                "inert": needles.get("inert"),
                "exclusions": exclusions,
                "argv_ok": argv_ok,
            }
        finally:
            td.cleanup()


if __name__ == "__main__":
    unittest.main()

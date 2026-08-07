"""Authorized Ollama model-store acquisition receipts."""

from __future__ import annotations

import hashlib
import json
import os
import stat
import subprocess
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from eval_corpus.ollama_identity import OllamaIdentityError


class ModelAcquisitionError(RuntimeError):
    """A pull was not authorized or did not produce the approved identity."""


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _store_inventory(root: Path | str) -> dict[str, Any]:
    base = Path(root).expanduser().absolute()
    info = base.lstat()
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
        raise ModelAcquisitionError(f"model store must be a real directory: {base}")
    entries: list[dict[str, Any]] = []
    for candidate in sorted(base.rglob("*"), key=lambda path: path.relative_to(base).as_posix()):
        item = candidate.lstat()
        if stat.S_ISLNK(item.st_mode):
            raise ModelAcquisitionError(f"model store symlink is forbidden: {candidate}")
        entries.append(
            {
                "path": candidate.relative_to(base).as_posix(),
                "kind": "directory" if stat.S_ISDIR(item.st_mode) else "file",
                "size": item.st_size,
                "device": item.st_dev,
                "inode": item.st_ino,
                "link_count": item.st_nlink,
                "mtime_ns": item.st_mtime_ns,
            }
        )
    body = {"root": str(base), "entries": entries}
    raw = json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return {**body, "inventory_sha256": hashlib.sha256(raw).hexdigest()}


def run_authorized_model_pull(
    *,
    ollama_binary: Path | str,
    model_store_path: Path | str,
    model_tag: str,
    expected_digest: str,
    ollama_host: str,
    identity_client: Any,
    authorized: bool,
    run_fn: Callable[..., Any] = subprocess.run,
) -> dict[str, Any]:
    """Run one exact pull and prove the post-pull digest."""
    if not authorized:
        raise ModelAcquisitionError("model pull requires consumed human authorization")
    if not model_tag or not expected_digest:
        raise ModelAcquisitionError("model pull requires model tag and expected digest")
    binary = Path(ollama_binary).expanduser().absolute()
    binary_info = binary.lstat()
    if stat.S_ISLNK(binary_info.st_mode) or not stat.S_ISREG(binary_info.st_mode):
        raise ModelAcquisitionError("ollama binary must be a regular non-symlink file")
    started_at = _timestamp()
    before_inventory = identity_client.list_models()
    before_store = _store_inventory(model_store_path)
    process = run_fn(
        [str(binary), "pull", model_tag],
        capture_output=True,
        check=False,
        env={
            "PATH": os.environ.get("PATH", ""),
            "OLLAMA_HOST": ollama_host,
            "OLLAMA_MODELS": str(Path(model_store_path).expanduser().absolute()),
        },
    )
    stdout = process.stdout if isinstance(process.stdout, bytes) else str(process.stdout).encode()
    stderr = process.stderr if isinstance(process.stderr, bytes) else str(process.stderr).encode()
    finished_at = _timestamp()
    after_inventory = identity_client.list_models()
    after_store = _store_inventory(model_store_path)
    report: dict[str, Any] = {
        "schema_version": "model_pull_receipt_v1",
        "operation": "model_pull",
        "model_tag": model_tag,
        "expected_digest": expected_digest,
        "started_at": started_at,
        "finished_at": finished_at,
        "argv": [str(binary), "pull", model_tag],
        "exit_code": int(process.returncode),
        "stdout": stdout.decode("utf-8", errors="replace"),
        "stderr": stderr.decode("utf-8", errors="replace"),
        "stdout_sha256": hashlib.sha256(stdout).hexdigest(),
        "stderr_sha256": hashlib.sha256(stderr).hexdigest(),
        "pre_model_inventory": before_inventory,
        "post_model_inventory": after_inventory,
        "pre_store_inventory": before_store,
        "post_store_inventory": after_store,
    }
    if process.returncode != 0:
        report["status"] = "FAILED"
        return report
    try:
        resolved = identity_client.resolve_model(model_tag)
        observed_digest = str(resolved.get("model_digest") or "")
    except Exception as exc:
        raise ModelAcquisitionError(f"post-pull identity resolution failed: {exc}") from exc
    if observed_digest != expected_digest:
        raise OllamaIdentityError(
            f"post-pull digest mismatch: observed={observed_digest} expected={expected_digest}"
        )
    report["resolved_identity"] = resolved
    report["status"] = "OK"
    return report


__all__ = ["ModelAcquisitionError", "run_authorized_model_pull"]

#!/usr/bin/env python3
"""One-shot exact-source checkpoint bootstrap; never called by watch/ingest.

The grant file is a reviewed operational input, not self-authorization. Run
only after Ryan approves the exact runtime, transform/provider binding, source,
backup, and durable HTTP-attempt budget. This script does not edit live config
or control the watcher.
"""

# The imports below follow the repo-root path insertion used by standalone scripts.
# ruff: noqa: I001
# The hyphenated script name follows scripts/ convention; exact int checks reject bool.
# pylint: disable=invalid-name,unidiomatic-typecheck,too-many-locals,too-many-statements

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from adapters.detect import detect_format  # pylint: disable=wrong-import-position
from adapters.kiro_session_jsonl import parse_complete_prefix  # pylint: disable=wrong-import-position
from bootstrap_safety import (  # pylint: disable=wrong-import-position
    BootstrapGrantError,
    BootstrapOperationJournal,
    canonical_json,
    grant_fingerprint,
    sha256_file,
    validate_grant,
)
from chroma_write_store import (  # pylint: disable=wrong-import-position
    current_implementation_revision,
)
from config import (  # pylint: disable=wrong-import-position
    CONFIG_PATH,
    incremental_jsonl_settings,
    load_config,
)
from incremental_jsonl import (  # pylint: disable=wrong-import-position
    IncrementalJsonlCoordinator,
    IncrementalJsonlError,
    compute_transform_fingerprint,
    source_state_id,
)
from incremental_jsonl_production import ProductionBoundary  # pylint: disable=wrong-import-position
from ingest import ProviderUnavailableError, chunk_messages  # pylint: disable=wrong-import-position
from llm import (  # pylint: disable=wrong-import-position
    ProviderAttemptBudgetExceeded,
    provider_http_accounting,
    resolve_generation_binding,
)


class BootstrapRunRefused(RuntimeError):
    """A handled invocation emitted a durable terminal receipt but did not commit."""

    def __init__(self, receipt: dict[str, Any]):
        super().__init__(str(receipt.get("failure_code") or receipt.get("outcome")))
        self.receipt = receipt


def _read_grant(path: Path) -> dict[str, Any]:
    raw = path.expanduser().absolute()
    if raw.resolve(strict=True) != raw or raw.is_symlink():
        raise BootstrapGrantError("grant path contains a symlink")
    info = raw.stat()
    if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid():
        raise BootstrapGrantError("grant must be an owned regular file")
    if info.st_mode & 0o077:
        raise BootstrapGrantError("grant must have mode 0600 or stricter")
    grant = json.loads(raw.read_text(encoding="utf-8"))
    return validate_grant(grant)


def _require_watcher_disabled() -> None:
    result = subprocess.run(
        [
            "systemctl", "--user", "show", "convmem-watch.service",
            "-p", "ActiveState", "-p", "UnitFileState", "-p", "MainPID",
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=15,
    )
    fields = dict(line.split("=", 1) for line in result.stdout.splitlines() if "=" in line)
    if fields != {"ActiveState": "inactive", "UnitFileState": "disabled", "MainPID": "0"}:
        raise RuntimeError("watcher must be inactive and disabled with MainPID=0")


def _runtime_revision() -> str:
    repo = Path(__file__).resolve().parent.parent
    status = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
        timeout=15,
    )
    if status.stdout:
        raise BootstrapGrantError("runtime worktree must be clean")
    revision = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
        timeout=15,
    ).stdout.strip()
    if len(revision) != 40 or revision.lower() != revision:
        raise BootstrapGrantError("runtime revision is not a canonical Git SHA")
    return revision


def _resolved_generation(models: dict, role: str) -> dict[str, str]:
    model = str(models[f"{role}_model"])
    resolved = resolve_generation_binding(model)
    if resolved.get("fallback") is not False:
        raise BootstrapGrantError(f"{role} provider fallback is forbidden")
    provider = str(resolved["provider"])
    if provider == "deepseek":
        if not os.environ.get("DEEPSEEK_API_KEY", "").strip():
            raise BootstrapGrantError(
                f"{role} credential is absent from the invoking process"
            )
        base_url = str(models.get("deepseek_base_url", "https://api.deepseek.com"))
    elif provider == "ollama":
        base_url = str(models["ollama_host"])
    else:
        raise BootstrapGrantError(f"{role} provider is unsupported")
    return {
        "provider": provider,
        "model": str(resolved["resolved_model"]),
        "base_url": base_url.rstrip("/"),
        "fallback": "false",
    }


def _effective_binding(cfg: dict, config_path: Path) -> dict[str, Any]:
    index = cfg.get("index")
    models = cfg.get("models")
    if not isinstance(index, dict) or not isinstance(models, dict):
        raise BootstrapGrantError("index/models configuration missing")
    distill = cfg.get("distill") or {}
    if not isinstance(distill, dict):
        raise BootstrapGrantError("distill configuration is invalid")
    if os.environ.get("CONVMEM_FAIL_ON_FALLBACK") != "1":
        raise BootstrapGrantError("CONVMEM_FAIL_ON_FALLBACK=1 is required")
    summarize = _resolved_generation(models, "summarize")
    distilled = _resolved_generation(models, "distill")
    embedding = {
        "provider": "ollama",
        "model": str(models["embed_model"]),
        "base_url": str(models["ollama_host"]).rstrip("/"),
        "fallback": "false",
    }
    chunk_size = int(index.get("chunk_size", 2))
    overlap = int(index.get("chunk_overlap", 0))
    min_confidence = float(distill.get("min_confidence", 0.6))
    implementation = current_implementation_revision()
    embed_dimension = incremental_jsonl_settings(cfg).embed_dimension
    return {
        "runtime_revision": _runtime_revision(),
        "config_sha256": sha256_file(config_path),
        "chunk_size": chunk_size,
        "chunk_overlap": overlap,
        "min_confidence": min_confidence,
        "summarize": summarize,
        "distill": distilled,
        "embedding": embedding,
        "transform_fingerprint": compute_transform_fingerprint(
            chunk_size=chunk_size,
            overlap=overlap,
            min_confidence=min_confidence,
            models=models,
            embed_dimension=int(embed_dimension or 0),
            implementation_revision=str(implementation),
        ),
    }


def _grant_binding(grant: dict[str, Any]) -> dict[str, Any]:
    return {
        "runtime_revision": grant["runtime_revision"],
        "config_sha256": grant["config_sha256"],
        "chunk_size": grant["chunk_size"],
        "chunk_overlap": grant["chunk_overlap"],
        "min_confidence": float(grant["min_confidence"]),
        "summarize": {
            "provider": grant["summarize_provider"],
            "model": grant["summarize_model"],
            "base_url": grant["summarize_base_url"],
            "fallback": "false",
        },
        "distill": {
            "provider": grant["distill_provider"],
            "model": grant["distill_model"],
            "base_url": grant["distill_base_url"],
            "fallback": "false",
        },
        "embedding": {
            "provider": grant["embedding_provider"],
            "model": grant["embedding_model"],
            "base_url": grant["embedding_base_url"],
            "fallback": "false",
        },
        "transform_fingerprint": grant["transform_fingerprint"],
    }


def _binding_fingerprint(binding: dict[str, Any]) -> str:
    return hashlib.sha256(
        ("convmem-bootstrap-binding-v1:" + canonical_json(binding)).encode("utf-8")
    ).hexdigest()


def _read_transaction(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _path_inventory(path: Path) -> dict[str, Any]:
    if path.is_file():
        return {"kind": "file", "size": path.stat().st_size, "sha256": sha256_file(path)}
    if not path.is_dir():
        return {"kind": "absent"}
    files = []
    for child in sorted(item for item in path.rglob("*") if item.is_file()):
        files.append(
            {
                "path": str(child.relative_to(path)),
                "size": child.stat().st_size,
                "sha256": sha256_file(child),
            }
        )
    return {"kind": "directory", "files": files}


def _mutation_inventory(coordinator: IncrementalJsonlCoordinator, journal: BootstrapOperationJournal) -> dict[str, Any]:
    data_root = Path(coordinator.cfg["index"]["chroma_dir"]).parent
    roles = {
        "processed": Path(coordinator.cfg["index"]["processed_log"]),
        "export": Path(coordinator.cfg["index"]["units_export"]),
        "dedupe_queue": data_root / "dedupe_queue.jsonl",
        "duplicate_suppressions": data_root / "ingest_duplicate_suppressions.jsonl",
        "synthesis_failures": data_root / "synthesis_failures.jsonl",
        "writer_attestations": coordinator.attest_dir,
        "writer_census": coordinator.census_dir,
        "prepared_cache": coordinator.paths["prepared"],
        "incremental_source_state": coordinator.state_dir,
        "operation_ledger": journal.root,
        "invocation_receipts": journal.invocations_path,
    }
    return {name: _path_inventory(path) for name, path in roles.items()}


def _failure_code(exc: BaseException) -> str:
    if isinstance(exc, ProviderAttemptBudgetExceeded):
        return "provider_http_budget_exhausted"
    if isinstance(exc, ProviderUnavailableError):
        return "provider_fatal_refusal"
    if isinstance(exc, IncrementalJsonlError):
        return exc.code
    if isinstance(exc, BootstrapGrantError):
        return "preflight_refused"
    return type(exc).__name__


def _receipt(
    *,
    grant: dict[str, Any],
    journal: BootstrapOperationJournal,
    binding: dict[str, Any],
    coordinator: IncrementalJsonlCoordinator | None,
    outcome: str,
    mode: str,
    failure_code: str | None,
) -> dict[str, Any]:
    transaction = (
        _read_transaction(coordinator.paths["transaction"])
        if coordinator is not None
        else None
    )
    counters = coordinator.counters.as_dict() if coordinator is not None else {}
    summarize_success = int(
        getattr(coordinator.counters, "summarize_success", 0)
        if coordinator is not None
        else 0
    )
    distill_success = int(
        getattr(coordinator.counters, "distill_success", 0)
        if coordinator is not None
        else 0
    )
    result = coordinator.last_result if coordinator is not None else None
    accounting = journal.accounting()
    recovery_available = bool(
        transaction
        and journal.current is not None
        and journal.current.ordinal <= int(grant["max_recovery_invocations"])
    )
    receipt = {
        "outcome": outcome,
        "mode": mode,
        "transaction_phase": (
            str(transaction.get("phase")) if transaction else ("COMMITTED" if outcome == "committed" else "NONE")
        ),
        "failure_code": failure_code,
        "logical_attempts": {
            "summarize": int(counters.get("summarize", 0)),
            "distill": int(counters.get("distill", 0)),
        },
        "logical_successes": {
            "summarize": summarize_success,
            "distill": distill_success,
        },
        **accounting,
        "chunks": int(getattr(result, "chunks", 0)),
        "summaries": int(getattr(result, "chunks", 0)),
        "units": int(getattr(result, "units", 0)),
        "active_generation": str(getattr(result, "active_generation", "")),
        "exact_suppressed": int(getattr(result, "exact_suppressed", 0)),
        "semantic_candidates_queued": int(getattr(result, "semantic_queued", 0)),
        "provider_calls": counters,
        "effective_binding": binding,
        "binding_fingerprint": _binding_fingerprint(binding),
        "recovery_remains_available": recovery_available,
        "source": grant["source"],
        "prefix_sha256": grant["prefix_sha256"],
        "backup_snapshot": grant["backup_snapshot"],
    }
    if coordinator is not None:
        receipt["isolation_evidence"] = coordinator.last_evidence
        receipt["mutation_inventory"] = _mutation_inventory(coordinator, journal)
    return receipt


def bootstrap(grant: dict[str, Any]) -> dict[str, Any]:
    """Apply one reviewed grant with durable budget and invocation accounting."""

    grant = validate_grant(grant)
    source = Path(grant["source"])
    cfg = load_config()
    config_path = Path(CONFIG_PATH).expanduser().absolute()
    original_settings = incremental_jsonl_settings(cfg)
    if original_settings.enabled:
        raise BootstrapGrantError("bootstrap requires the normal route to remain default-off")
    index = cfg.get("index")
    if not isinstance(index, dict):
        raise BootstrapGrantError("index configuration missing")
    table = dict(index.get("incremental_jsonl") or {})
    table.update(
        enabled=True,
        live_sources=[str(source)],
        embed_dimension=grant["embed_dimension"],
        allow_full_rebuild=False,
    )
    index["incremental_jsonl"] = table
    boundary = ProductionBoundary(cfg, source, config_path=config_path)
    settings = incremental_jsonl_settings(cfg)
    state_root = boundary.resolve_mutable(settings.state_dir, label="incremental state")
    source_state = state_root / source_state_id(str(source))
    expected_binding = _grant_binding(grant)
    journal = BootstrapOperationJournal(source_state, grant, expected_binding)
    transaction_path = source_state / "transaction.json"
    existing_transaction = _read_transaction(transaction_path)
    fingerprint = grant_fingerprint(grant)
    recoverable = bool(
        existing_transaction
        and existing_transaction.get("bootstrap_existing") is True
        and existing_transaction.get("grant_fingerprint") == fingerprint
        and existing_transaction.get("phase") in {"PREPARING", "transform_failed", "APPLYING"}
    )
    authority = journal.begin_invocation(recoverable_transaction=recoverable)
    observed_binding: dict[str, Any] = expected_binding
    coordinator: IncrementalJsonlCoordinator | None = None
    terminal_written = False
    if not authority.authorized:
        receipt = journal.finish(
            _receipt(
                grant=grant,
                journal=journal,
                binding=observed_binding,
                coordinator=None,
                outcome="refused",
                mode="recovery",
                failure_code=authority.refusal_code,
            )
        )
        raise BootstrapRunRefused(receipt)
    try:
        observed_binding = _effective_binding(cfg, config_path)
        if observed_binding != expected_binding:
            raise BootstrapGrantError("effective runtime/config/transform/provider binding mismatch")
        if settings.embed_dimension != grant["embed_dimension"]:
            raise BootstrapGrantError("effective embedding dimension differs from grant")
        _require_watcher_disabled()
        if detect_format(source) != "jsonl_kiro_session":
            raise BootstrapGrantError("first bootstrap slice supports one Kiro JSONL source")
        view = parse_complete_prefix(str(source))
        if (
            view.prefix_sha256 != grant["prefix_sha256"]
            or view.complete_boundary != grant["complete_boundary"]
        ):
            raise BootstrapGrantError("source prefix differs from the reviewed grant")
        chunks = len(
            chunk_messages(view.messages, grant["chunk_size"], grant["chunk_overlap"])
        )
        if chunks > grant["max_chunks"]:
            raise BootstrapGrantError("source exceeds the reviewed transform-chunk cap")
        coordinator = IncrementalJsonlCoordinator(
            boundary,
            source,
            cfg=cfg,
            models=cfg.get("models") or {},
            chunk_size=grant["chunk_size"],
            overlap=grant["chunk_overlap"],
            min_confidence=float(grant["min_confidence"]),
            embed_dimension=grant["embed_dimension"],
            bootstrap_existing=True,
            expected_prefix_sha256=grant["prefix_sha256"],
            max_bootstrap_chunks=grant["max_chunks"],
            bootstrap_grant_fingerprint=fingerprint,
            bootstrap_operation_id=grant["operation_id"],
            bootstrap_binding_fingerprint=_binding_fingerprint(expected_binding),
        )
        coordinator.require_existing_embedding_dimension(grant["embed_dimension"])
        with provider_http_accounting(
            journal.consume_provider_http_attempt,
            journal.report_provider_usage,
        ):
            result = coordinator.run()
        receipt_payload = _receipt(
            grant=grant,
            journal=journal,
            binding=observed_binding,
            coordinator=coordinator,
            outcome=result.outcome,
            mode=result.mode,
            failure_code=None if result.outcome == "committed" else result.outcome,
        )
        receipt = journal.finish(receipt_payload)
        terminal_written = True
        if result.outcome != "committed":
            raise BootstrapRunRefused(receipt)
        return receipt
    except BootstrapRunRefused:
        raise
    except Exception as exc:
        if not terminal_written:
            receipt = journal.finish(
                _receipt(
                    grant=grant,
                    journal=journal,
                    binding=observed_binding,
                    coordinator=coordinator,
                    outcome="failed",
                    mode="recovery" if authority.recovery else "bootstrap_existing",
                    failure_code=_failure_code(exc),
                )
            )
            terminal_written = True
            setattr(exc, "bootstrap_receipt", receipt)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--grant-file", type=Path, required=True)
    parser.add_argument("--execute", action="store_true", help="run the reviewed one-shot bootstrap")
    args = parser.parse_args()
    if not args.execute:
        parser.error("--execute is required for the reviewed one-shot bootstrap")
    try:
        receipt = bootstrap(_read_grant(args.grant_file))
    except BootstrapRunRefused as exc:
        print(json.dumps(exc.receipt, sort_keys=True))
        return 1
    except Exception as exc:  # terminal receipt was already fsynced when possible
        receipt = getattr(exc, "bootstrap_receipt", None)
        if isinstance(receipt, dict):
            print(json.dumps(receipt, sort_keys=True))
        raise
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

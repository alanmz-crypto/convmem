"""Format registry for incremental JSONL coordinator routes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from adapters import codex_history_jsonl, codex_rollout_jsonl, kiro_session_jsonl
from adapters.jsonl_prefix import CompletePrefixView

ParsePrefix = Callable[..., CompletePrefixView]


@dataclass(frozen=True)
class IncrementalFormatSpec:
    format_id: str
    adapter_module: str
    adapter_contract_version: str
    tool: str
    parse_complete_prefix: ParsePrefix
    snapshot_basename: str
    session_meta_path: str | None = None


_KIRO = IncrementalFormatSpec(
    format_id="jsonl_kiro_session",
    adapter_module="adapters.kiro_session_jsonl",
    adapter_contract_version="kiro-complete-prefix-v1",
    tool="kiro",
    parse_complete_prefix=kiro_session_jsonl.parse_complete_prefix,
    snapshot_basename="messages.jsonl",
    session_meta_path="session.json",
)

_CODEX_HISTORY = IncrementalFormatSpec(
    format_id="jsonl_codex_history",
    adapter_module="adapters.codex_history_jsonl",
    adapter_contract_version="codex-history-complete-prefix-v1",
    tool="codex",
    parse_complete_prefix=codex_history_jsonl.parse_complete_prefix,
    snapshot_basename="history.jsonl",
)

_CODEX_ROLLOUT = IncrementalFormatSpec(
    format_id="jsonl_codex_rollout",
    adapter_module="adapters.codex_rollout_jsonl",
    adapter_contract_version="codex-rollout-complete-prefix-v1",
    tool="codex",
    parse_complete_prefix=codex_rollout_jsonl.parse_complete_prefix,
    snapshot_basename="rollout.jsonl",
)

FORMAT_SPECS: dict[str, IncrementalFormatSpec] = {
    _KIRO.format_id: _KIRO,
    _CODEX_HISTORY.format_id: _CODEX_HISTORY,
    _CODEX_ROLLOUT.format_id: _CODEX_ROLLOUT,
}

# S2 keeps production routing on Kiro only; S3 enables Codex under isolation.
KIRO_ROUTE_FORMATS = frozenset({_KIRO.format_id})
ISOLATED_CODEX_FORMATS = frozenset({_CODEX_HISTORY.format_id, _CODEX_ROLLOUT.format_id})
ALL_ISOLATED_FORMATS = KIRO_ROUTE_FORMATS | ISOLATED_CODEX_FORMATS


def get_format_spec(format_id: str | None) -> IncrementalFormatSpec | None:
    if format_id is None:
        return None
    return FORMAT_SPECS.get(format_id)


def source_state_id(format_id: str, canonical_path: str) -> str:
    import hashlib

    return hashlib.sha256(f"{format_id}:{canonical_path}".encode("utf-8")).hexdigest()


def routed_formats(*, isolated_codex: bool = False) -> frozenset[str]:
    if isolated_codex:
        return ALL_ISOLATED_FORMATS
    return KIRO_ROUTE_FORMATS

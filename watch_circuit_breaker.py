"""Persisted watch circuit-breaker and live-route refusal quarantine state."""

from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path

_DEFAULT_CB_FILE_CRASH_THRESHOLD = 3
_DEFAULT_CB_TIMEOUT_THRESHOLD = 3
_DEFAULT_CB_GLOBAL_THRESHOLD = 5
_DEFAULT_CB_GLOBAL_WINDOW_SECONDS = 30 * 60

_LIVE_ROUTE_REFUSED_PREFIX = "live_route_refused:"
_REFUSAL_OUTCOME_RE = re.compile(r"[a-z0-9_]+(?::[a-z0-9_]+)*")
_REFUSAL_DIGEST_RE = re.compile(r"[0-9a-f]{64}")


def _parse_refusal_line(line: str) -> tuple[str, str] | None:
    if not line.startswith(_LIVE_ROUTE_REFUSED_PREFIX):
        return None
    body = line[len(_LIVE_ROUTE_REFUSED_PREFIX):]
    # A greedy outcome pattern would swallow the digest, so strip it first.
    head, sep, tail = body.rpartition(":")
    if sep and _REFUSAL_DIGEST_RE.fullmatch(tail):
        outcome, digest = head, tail
    else:
        outcome, digest = body, ""
    if not _REFUSAL_OUTCOME_RE.fullmatch(outcome):
        return None
    return outcome, digest


def parse_live_route_refused(message: str) -> tuple[str, str] | None:
    """Return (outcome, digest) when a whole stderr line is a refusal marker."""
    for line in message.splitlines():
        parsed = _parse_refusal_line(line.strip())
        if parsed:
            return parsed
    return None


def refusal_quarantine_key(path: str, prefix_digest: str) -> str:
    return f"{path}\0{prefix_digest}"


def circuit_breaker_state_path_from_config(cfg: dict) -> Path:
    watch_cfg = cfg.get("watch") or {}
    if watch_cfg.get("circuit_breaker_state_file"):
        return Path(watch_cfg["circuit_breaker_state_file"]).expanduser()
    chroma = Path(cfg["index"]["chroma_dir"]).expanduser()
    return chroma.parent / "watch_circuit_breaker.json"


class CircuitBreakerState:
    """Per-path native-fault/timeout quarantine plus a global breaker."""

    def __init__(self, state_path: Path):
        self.state_path = state_path
        self._data = self._load()

    def _load(self) -> dict:
        try:
            raw = self.state_path.read_text(encoding="utf-8")
        except OSError:
            return {"paths": {}, "global_events": [], "refusals": {}}
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return {"paths": {}, "global_events": [], "refusals": {}}
        if not isinstance(data, dict):
            return {"paths": {}, "global_events": [], "refusals": {}}
        data.setdefault("paths", {})
        data.setdefault("global_events", [])
        data.setdefault("refusals", {})
        return data

    def _save(self) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.state_path.with_name(self.state_path.name + f".tmp{os.getpid()}")
        tmp.write_text(json.dumps(self._data, indent=2) + "\n", encoding="utf-8")
        os.replace(tmp, self.state_path)

    def is_quarantined(self, path: str) -> bool:
        entry = self._data["paths"].get(path)
        return bool(entry and entry.get("quarantined"))

    def is_refusal_quarantined(self, path: str, prefix_digest: str) -> bool:
        key = refusal_quarantine_key(path, prefix_digest)
        entry = self._data["refusals"].get(key)
        return bool(entry and entry.get("quarantined"))

    def has_refusal_quarantine_for_path(self, path: str) -> bool:
        prefix = f"{path}\0"
        for key, entry in self._data.get("refusals", {}).items():
            if key.startswith(prefix) and entry.get("quarantined"):
                return True
        return False

    def record_refusal(
        self,
        path: str,
        *,
        outcome: str,
        prefix_digest: str,
        now: float | None = None,
    ) -> bool:
        if now is None:
            now = time.time()
        key = refusal_quarantine_key(path, prefix_digest)
        entry = self._data["refusals"].setdefault(
            key,
            {
                "path": path,
                "prefix_sha256": prefix_digest,
                "outcome": outcome,
                "first_refused_at": now,
                "quarantined": False,
            },
        )
        entry["outcome"] = outcome
        entry["prefix_sha256"] = prefix_digest
        entry.setdefault("first_refused_at", now)
        entry["quarantined"] = True
        self._save()
        return True

    def list_refusal_quarantines(self) -> list[dict]:
        rows: list[dict] = []
        for entry in self._data.get("refusals", {}).values():
            if entry.get("quarantined"):
                rows.append(dict(entry))
        rows.sort(key=lambda item: item.get("first_refused_at", 0))
        return rows

    def record_success(self, path: str) -> None:
        entry = self._data["paths"].get(path)
        if entry and not entry.get("quarantined"):
            del self._data["paths"][path]
            self._save()

    def record_failure(
        self,
        path: str,
        *,
        native_fault: bool,
        timeout: bool,
        now: float | None = None,
        crash_threshold: int = _DEFAULT_CB_FILE_CRASH_THRESHOLD,
        timeout_threshold: int = _DEFAULT_CB_TIMEOUT_THRESHOLD,
    ) -> bool:
        if now is None:
            now = time.time()
        entry = self._data["paths"].setdefault(
            path, {"native_crash_count": 0, "timeout_count": 0, "quarantined": False}
        )
        if native_fault:
            entry["native_crash_count"] += 1
            self._data["global_events"].append(now)
            if entry["native_crash_count"] >= crash_threshold:
                entry["quarantined"] = True
        elif timeout:
            entry["timeout_count"] += 1
            if entry["timeout_count"] >= timeout_threshold:
                entry["quarantined"] = True
        self._save()
        return bool(entry["quarantined"])

    def global_breaker_tripped(
        self,
        *,
        now: float | None = None,
        global_threshold: int = _DEFAULT_CB_GLOBAL_THRESHOLD,
        global_window_seconds: float = _DEFAULT_CB_GLOBAL_WINDOW_SECONDS,
    ) -> bool:
        if now is None:
            now = time.time()
        cutoff = now - global_window_seconds
        recent = [t for t in self._data["global_events"] if t >= cutoff]
        if len(recent) != len(self._data["global_events"]):
            self._data["global_events"] = recent
            self._save()
        return len(recent) >= global_threshold

    def clear(self, path: str | None = None) -> None:
        if path is None:
            self._data = {"paths": {}, "global_events": [], "refusals": {}}
        else:
            self._data["paths"].pop(path, None)
            prefix = f"{path}\0"
            for key in list(self._data.get("refusals", {})):
                if key.startswith(prefix):
                    self._data["refusals"].pop(key, None)
        self._save()

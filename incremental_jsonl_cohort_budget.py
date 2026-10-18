"""Durable cohort paid-HTTP budget for selected Kiro incremental runs."""

from __future__ import annotations

import json
import os
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterator

from llm import ProviderAttemptBudgetExceeded

ProviderAttemptPermit = Callable[[dict[str, object]], None]

_LEDGER_VERSION = 1


@dataclass(frozen=True)
class CohortBudgetSettings:
    ledger_path: Path
    max_paid_http_attempts: int
    operation_id: str


class CohortBudgetError(RuntimeError):
    def __init__(self, code: str, detail: str):
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


def _atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    os.chmod(path.parent, 0o700)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    os.replace(tmp, path)
    os.chmod(path, 0o600)


def _read_ledger(path: Path) -> dict:
    if not path.is_file():
        return {
            "version": _LEDGER_VERSION,
            "operation_id": "",
            "reserved": 0,
            "consumed": 0,
            "max_paid_http_attempts": 0,
        }
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise CohortBudgetError("cohort_ledger_corrupt", "ledger is not an object")
    return payload


class CohortBudgetLedger:
    """Serialize reservations under a short budget lock; release before HTTP."""

    def __init__(self, settings: CohortBudgetSettings):
        self.settings = settings
        self._lock_path = settings.ledger_path.with_suffix(".lock")

    def _acquire_budget_lock(self) -> int:
        import fcntl

        fd = os.open(self._lock_path, os.O_CREAT | os.O_RDWR, 0o600)
        fcntl.flock(fd, fcntl.LOCK_EX)
        return fd

    @staticmethod
    def _release_budget_lock(fd: int) -> None:
        import fcntl

        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)

    def _persist(self, payload: dict) -> None:
        _atomic_json(self.settings.ledger_path, payload)

    def reserve_paid_http_attempt(self, event: dict[str, object]) -> str:
        fd = self._acquire_budget_lock()
        try:
            ledger = _read_ledger(self.settings.ledger_path)
            if ledger.get("operation_id") and ledger["operation_id"] != self.settings.operation_id:
                raise CohortBudgetError("cohort_operation_mismatch", "ledger operation identity")
            reserved = int(ledger.get("reserved") or 0)
            consumed = int(ledger.get("consumed") or 0)
            ceiling = int(self.settings.max_paid_http_attempts)
            if consumed + reserved >= ceiling:
                raise ProviderAttemptBudgetExceeded("cohort paid HTTP cap exhausted")
            reservation_id = f"{consumed + reserved + 1:08d}"
            ledger.update(
                {
                    "version": _LEDGER_VERSION,
                    "operation_id": self.settings.operation_id,
                    "reserved": reserved + 1,
                    "consumed": consumed,
                    "max_paid_http_attempts": ceiling,
                    "last_event": dict(event),
                }
            )
            self._persist(ledger)
            return reservation_id
        finally:
            self._release_budget_lock(fd)

    def finalize_reservation(self, reservation_id: str, *, success: bool) -> None:
        fd = self._acquire_budget_lock()
        try:
            ledger = _read_ledger(self.settings.ledger_path)
            reserved = int(ledger.get("reserved") or 0)
            consumed = int(ledger.get("consumed") or 0)
            if reserved <= 0:
                raise CohortBudgetError("cohort_reservation_missing", reservation_id)
            ledger["reserved"] = reserved - 1
            if success:
                ledger["consumed"] = consumed + 1
            else:
                # Crash-conservative: failed attempts still count against the cap.
                ledger["consumed"] = consumed + 1
            self._persist(ledger)
        finally:
            self._release_budget_lock(fd)

    def permit_callback(self) -> ProviderAttemptPermit:
        def permit(event: dict[str, object]) -> None:
            reservation_id = self.reserve_paid_http_attempt(event)
            # Release budget lock before HTTP; finalize after the call completes.
            setattr(permit, "_last_reservation", reservation_id)

        return permit

    @contextmanager
    def accounting(self) -> Iterator[ProviderAttemptPermit]:
        permit = self.permit_callback()

        def finalize(success: bool) -> None:
            reservation_id = getattr(permit, "_last_reservation", None)
            if reservation_id:
                self.finalize_reservation(str(reservation_id), success=success)
                delattr(permit, "_last_reservation")

        try:
            yield permit
            finalize(True)
        except Exception:
            finalize(False)
            raise

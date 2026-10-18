"""V2 paid permit ledger and composed provider guards (Arc #286 T2)."""

from __future__ import annotations

import fcntl
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable, Iterator

from bootstrap_codex_v2 import grant_fingerprint_v2, validate_grant_v2
from bootstrap_codex_v2_authority import (
    AuthorityView,
    load_authority,
    operation_root,
)
from bootstrap_codex_v2_publication import append_jsonl_line
from bootstrap_safety import (
    ProviderAttemptBudgetExceeded,
    _new_provider_attempt_paid_cap_consumed,
    _provider_attempt_paid_cap_consumed,
    _read_jsonl,
    _validate_provider_attempt_event,
    utc_now,
)

ProviderPermit = Callable[[dict[str, object]], None]


def compose_provider_permits(*permits: ProviderPermit) -> ProviderPermit:
    """Run every guard before transport; do not replace ContextVar callbacks."""

    def composed(event: dict[str, object]) -> None:
        for permit in permits:
            permit(event)

    return composed


@contextmanager
def operation_accounting_lock(operation_dir: Path) -> Iterator[None]:
    operation_dir.mkdir(parents=True, exist_ok=True)
    lock_path = operation_dir / "operation_accounting.lock"
    handle = lock_path.open("a+", encoding="utf-8")
    try:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        handle.close()


class CodexV2PaidLedger:
    """Durable permits keyed to authority invocation ordinal (not journal starts)."""

    def __init__(self, state_dir: Path, grant: dict[str, Any]) -> None:
        self.grant = validate_grant_v2(grant)
        self.fingerprint = grant_fingerprint_v2(self.grant)
        self.state_dir = state_dir
        self.operation_dir = operation_root(state_dir, self.grant)
        self.permits_path = self.operation_dir / "v2_provider_permits.jsonl"
        self.max_attempts = int(self.grant["max_provider_http_attempts"])
        self.max_recoveries = int(self.grant["max_recovery_invocations"])
        self.lifetime_paid_cap = self.max_attempts * (1 + self.max_recoveries)
        self._authority: AuthorityView | None = None

    def bind_authority(self) -> AuthorityView:
        authority = load_authority(self.state_dir)
        if authority is None:
            raise ProviderAttemptBudgetExceeded("v2_authority_missing")
        if authority.record["grant_fingerprint_v2"] != self.fingerprint:
            raise ProviderAttemptBudgetExceeded("v2_authority_fingerprint_mismatch")
        if authority.terminal:
            raise ProviderAttemptBudgetExceeded("v2_authority_terminal")
        self._authority = authority
        return authority

    @property
    def authority(self) -> AuthorityView:
        if self._authority is None:
            return self.bind_authority()
        return self._authority

    def consume_provider_http_attempt(self, event: dict[str, object]) -> None:
        authority = self.authority
        if not authority.reservation_active:
            raise ProviderAttemptBudgetExceeded("reservation_inactive")
        _validate_provider_attempt_event(event)
        paid = _new_provider_attempt_paid_cap_consumed(event)
        with operation_accounting_lock(self.operation_dir):
            rows = _read_jsonl(self.permits_path)
            ordinal = authority.invocation_ordinal
            ordinal_rows = [row for row in rows if int(row.get("invocation_ordinal") or 0) == ordinal]
            paid_local = sum(_provider_attempt_paid_cap_consumed(row) for row in ordinal_rows)
            paid_total = sum(_provider_attempt_paid_cap_consumed(row) for row in rows)
            if paid and paid_local >= self.max_attempts:
                raise ProviderAttemptBudgetExceeded(
                    f"provider_http_budget_exhausted:{paid_local}/{self.max_attempts}"
                )
            if paid and paid_total >= self.lifetime_paid_cap:
                raise ProviderAttemptBudgetExceeded(
                    f"provider_http_budget_exhausted:{paid_total}/{self.lifetime_paid_cap}"
                )
            append_jsonl_line(
                self.permits_path,
                {
                    "record_type": "permit_consumed",
                    "recorded_at": utc_now(),
                    "operation_id": self.grant["operation_id"],
                    "grant_fingerprint_v2": self.fingerprint,
                    "invocation_ordinal": ordinal,
                    "authority_revision": authority.revision,
                    "attempt_ordinal": len(ordinal_rows) + 1,
                    "paid_cap_consumed": paid,
                    **event,
                },
                stage="v2_permit",
            )

    def accounting(self) -> dict[str, Any]:
        authority = self.authority
        rows = _read_jsonl(self.permits_path)
        ordinal = authority.invocation_ordinal
        ordinal_rows = [row for row in rows if int(row.get("invocation_ordinal") or 0) == ordinal]
        paid_current = sum(_provider_attempt_paid_cap_consumed(row) for row in ordinal_rows)
        paid_total = sum(_provider_attempt_paid_cap_consumed(row) for row in rows)
        return {
            "invocation_ordinal": ordinal,
            "authority_revision": authority.revision,
            "permitted_http_attempts": paid_current,
            "cumulative_permitted_http_attempts": paid_total,
            "observed_provider_http_attempts": len(ordinal_rows),
            "lifetime_paid_cap": self.lifetime_paid_cap,
        }


def outer_budget_permit_factory(remaining: int) -> ProviderPermit:
    consumed = {"count": 0}

    def permit(_event: dict[str, object]) -> None:
        if consumed["count"] >= remaining:
            raise ProviderAttemptBudgetExceeded("outer_budget_exhausted")
        consumed["count"] += 1

    return permit

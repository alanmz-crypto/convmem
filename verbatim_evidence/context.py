"""Ask-path labeling for summary versus verbatim source evidence."""

from __future__ import annotations

from verbatim_evidence.escape import escape_metadata, quote_block
from verbatim_evidence.types import EvidenceResult, EvidenceScope, EvidenceStatus

LABEL_SUMMARY = "summary"
LABEL_VERBATIM_SOURCE = "verbatim_source"
LABEL_UNAVAILABLE = "verbatim_evidence_unavailable"

_UNAVAILABLE_GUIDANCE = (
    "Exact source evidence is unavailable for this candidate. "
    "Do not claim the source does not exist; keep the summary as "
    "summary-origin context only."
)

_SESSION_SCOPE_NOTE = (
    "Session-scoped evidence may come from elsewhere in the session, "
    "not only the summarized message window."
)

_VERBATIM_PREAMBLE = (
    "Evidence labels in this context:\n"
    f"- {LABEL_SUMMARY}: generated conversation summary (not verbatim proof)\n"
    f"- {LABEL_VERBATIM_SOURCE}: bounded exact excerpt from the source message\n"
    f"- {LABEL_UNAVAILABLE}: source identified but exact evidence unavailable "
    "(do not claim the source is absent)\n"
)


def _validated_summary_offsets(meta: dict) -> tuple[int | None, int | None, bool]:
    """Return (start, end, valid). Reject non-integers and partial pairs."""

    def _as_offset(value: object) -> int | None | str:
        if value is None:
            return None
        if isinstance(value, bool) or not isinstance(value, int):
            return "invalid"
        return value

    start = _as_offset(meta.get("start_offset"))
    end = _as_offset(meta.get("end_offset"))
    if start == "invalid" or end == "invalid":
        return None, None, False
    if (start is None) ^ (end is None):
        return None, None, False
    if start is None:
        return None, None, True
    return start, end, True


def format_labeled_context(
    *,
    summary_text: str,
    summary_meta: dict | None,
    evidence: EvidenceResult,
    citation_start: int = 1,
) -> tuple[str, list[dict], list[dict]]:
    """Build labeled context text, citation rows, and structured items.

    Always emits the summary item. When evidence is available, appends each
    bounded excerpt as ``verbatim_source``. Otherwise appends one structured
    unavailable marker — never fabricates verbatim text.
    """
    meta = dict(summary_meta or {})
    items: list[dict] = [
        {
            "label": LABEL_SUMMARY,
            "text": summary_text,
            "metadata": meta,
        }
    ]
    if evidence.status is EvidenceStatus.AVAILABLE and evidence.excerpts:
        for excerpt in evidence.excerpts:
            items.append(
                {
                    "label": LABEL_VERBATIM_SOURCE,
                    "text": excerpt.excerpt,
                    "metadata": {
                        "source_path": excerpt.source_path,
                        "adapter_kind": excerpt.adapter_kind,
                        "session_id": excerpt.session_id,
                        "message_id": excerpt.message_id,
                        "role": excerpt.role,
                        "timestamp": excerpt.timestamp,
                        "message_ordinal": excerpt.message_ordinal,
                        "truncated": excerpt.truncated,
                        "cut_leading": excerpt.cut_leading,
                        "cut_trailing": excerpt.cut_trailing,
                        "content_digest_sha256": excerpt.content_digest_sha256,
                        "evidence_status": evidence.status.value,
                        "scope": (evidence.scope or excerpt.scope).value,
                        "partial": evidence.partial,
                        "partial_reason": evidence.partial_reason,
                        "reason": evidence.reason,
                    },
                }
            )
    else:
        items.append(
            {
                "label": LABEL_UNAVAILABLE,
                "text": _UNAVAILABLE_GUIDANCE,
                "metadata": {
                    "source_path": evidence.source_path or meta.get("source_path"),
                    "adapter_kind": evidence.adapter_kind,
                    "evidence_status": evidence.status.value,
                    "reason": evidence.reason,
                    "scope": evidence.scope.value if evidence.scope else None,
                    "partial": evidence.partial,
                    "partial_reason": evidence.partial_reason,
                },
            }
        )

    lines: list[str] = [_VERBATIM_PREAMBLE.rstrip()]
    if evidence.scope is EvidenceScope.SESSION or any(
        item.get("metadata", {}).get("scope") == EvidenceScope.SESSION.value
        for item in items
        if item.get("label") == LABEL_VERBATIM_SOURCE
    ):
        lines.append(_SESSION_SCOPE_NOTE)
    if evidence.reason == "offsets_ignored_session_scope":
        lines.append("offsets_ignored_session_scope")

    citations: list[dict] = []
    n = citation_start
    for item in items:
        label = item["label"]
        text = (item.get("text") or "").strip()
        item_meta = item.get("metadata") or {}
        src = escape_metadata(item_meta.get("source_path") or "")
        if label == LABEL_SUMMARY:
            tool = escape_metadata(item_meta.get("tool") or "?")
            when = escape_metadata(item_meta.get("when") or "")
            start, end, offsets_valid = _validated_summary_offsets(item_meta)
            header = f"[{n}] (label={escape_metadata(label)}, {tool}"
            if when:
                header += f", {when}"
            if offsets_valid and start is not None and end is not None:
                header += f") messages {start}–{end}"
            elif item_meta.get("start_offset") is not None or item_meta.get(
                "end_offset"
            ) is not None:
                header += ", reason=invalid_locator)"
            else:
                header += ")"
            lines.append(
                f"{header}\n{quote_block(text)}\n    Source: {src}"
            )
        elif label == LABEL_VERBATIM_SOURCE:
            role = escape_metadata(item_meta.get("role") or "?")
            mid = escape_metadata(item_meta.get("message_id") or "")
            digest = escape_metadata(item_meta.get("content_digest_sha256") or "")
            scope = escape_metadata(item_meta.get("scope") or "")
            trunc = " truncated=true" if item_meta.get("truncated") else ""
            if item_meta.get("cut_leading"):
                trunc += " cut_leading=true"
            if item_meta.get("cut_trailing"):
                trunc += " cut_trailing=true"
            partial = ""
            if item_meta.get("partial"):
                partial = f", partial=true, partial_reason={escape_metadata(item_meta.get('partial_reason') or '')}"
            reason = item_meta.get("reason")
            reason_suffix = ""
            if reason:
                reason_suffix = f", reason={escape_metadata(reason)}"
            lines.append(
                f"[{n}] (label={escape_metadata(label)}, role={role}, "
                f"message_id={mid}, scope={scope}{trunc}{partial}{reason_suffix})\n"
                f"{quote_block(text)}\n"
                f"    Source: {src}\n    Digest: {digest}"
            )
        else:
            status = escape_metadata(item_meta.get("evidence_status") or "unknown")
            reason = escape_metadata(item_meta.get("reason") or "")
            lines.append(
                f"[{n}] (label={escape_metadata(label)}, status={status}, reason={reason})\n"
                f"{quote_block(text)}\n    Source: {src}"
            )
        citations.append(
            {
                "n": n,
                "context_label": label,
                "source_path": item_meta.get("source_path") or "",
                "evidence_status": item_meta.get("evidence_status"),
                "session_id": item_meta.get("session_id") or meta.get("session_id"),
                "message_id": item_meta.get("message_id"),
                "content_digest_sha256": item_meta.get("content_digest_sha256"),
                "reason": item_meta.get("reason"),
                "scope": item_meta.get("scope"),
                "partial": item_meta.get("partial"),
                "partial_reason": item_meta.get("partial_reason"),
            }
        )
        n += 1

    return "\n\n".join(lines), citations, items

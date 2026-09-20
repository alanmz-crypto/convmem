"""Ask-path labeling for summary versus verbatim source evidence."""

from __future__ import annotations

from verbatim_evidence.types import EvidenceResult, EvidenceStatus

LABEL_SUMMARY = "summary"
LABEL_VERBATIM_SOURCE = "verbatim_source"
LABEL_UNAVAILABLE = "verbatim_evidence_unavailable"

_UNAVAILABLE_GUIDANCE = (
    "Exact source evidence is unavailable for this candidate. "
    "Do not claim the source does not exist; keep the summary as "
    "summary-origin context only."
)

_VERBATIM_PREAMBLE = (
    "Evidence labels in this context:\n"
    f"- {LABEL_SUMMARY}: generated conversation summary (not verbatim proof)\n"
    f"- {LABEL_VERBATIM_SOURCE}: bounded exact excerpt from the source message\n"
    f"- {LABEL_UNAVAILABLE}: source identified but exact evidence unavailable "
    "(do not claim the source is absent)\n"
)


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
                        "content_digest_sha256": excerpt.content_digest_sha256,
                        "evidence_status": evidence.status.value,
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
                },
            }
        )

    lines: list[str] = [_VERBATIM_PREAMBLE.rstrip()]
    citations: list[dict] = []
    n = citation_start
    for item in items:
        label = item["label"]
        text = (item.get("text") or "").strip()
        item_meta = item.get("metadata") or {}
        src = item_meta.get("source_path") or ""
        if label == LABEL_SUMMARY:
            tool = item_meta.get("tool") or "?"
            when = item_meta.get("when") or ""
            start = item_meta.get("start_offset")
            end = item_meta.get("end_offset")
            header = f"[{n}] (label={label}, {tool}"
            if when:
                header += f", {when}"
            header += f") messages {start}–{end}"
            lines.append(f"{header}\n    {text}\n    Source: {src}")
        elif label == LABEL_VERBATIM_SOURCE:
            role = item_meta.get("role") or "?"
            mid = item_meta.get("message_id") or ""
            digest = item_meta.get("content_digest_sha256") or ""
            trunc = " truncated=true" if item_meta.get("truncated") else ""
            lines.append(
                f"[{n}] (label={label}, role={role}, message_id={mid}"
                f"{trunc})\n    {text}\n"
                f"    Source: {src}\n    Digest: {digest}"
            )
        else:
            status = item_meta.get("evidence_status") or "unknown"
            reason = item_meta.get("reason") or ""
            lines.append(
                f"[{n}] (label={label}, status={status}, reason={reason})\n"
                f"    {text}\n    Source: {src}"
            )
        citations.append(
            {
                "n": n,
                "context_label": label,
                "source_path": src,
                "evidence_status": item_meta.get("evidence_status"),
                "session_id": item_meta.get("session_id") or meta.get("session_id"),
                "message_id": item_meta.get("message_id"),
                "content_digest_sha256": item_meta.get("content_digest_sha256"),
                "reason": item_meta.get("reason"),
            }
        )
        n += 1

    return "\n\n".join(lines), citations, items

"""Evidence-chain display for `convmem related` (graph traversal, not search)."""

from __future__ import annotations

import typer

from ledger import related_chain


def _rule(title: str) -> str:
    return f"{title}\n{'─' * len(title)}"


def _obs_lines(meta: dict) -> list[str]:
    lid = (meta.get("ledger_id") or meta.get("id") or "").strip()
    title = (meta.get("title") or "").strip()
    domain = (meta.get("domain") or "").strip()
    lines = [lid]
    if title:
        lines.append(title)
    if domain:
        lines.append(domain)
    return lines


def _decision_lines(meta: dict) -> list[str]:
    lid = (meta.get("ledger_id") or meta.get("id") or "").strip()
    title = (meta.get("title") or "").strip()
    lines = [lid]
    if title:
        lines.append(title)
    return lines


def _verification_lines(meta: dict) -> list[str]:
    lid = (meta.get("ledger_id") or meta.get("id") or "").strip()
    result = (meta.get("result") or meta.get("verification_result") or "").strip().upper()
    conf = meta.get("verified_confidence", meta.get("confidence"))
    author = (meta.get("author_model") or meta.get("verifier_model") or "").strip()
    lines = [lid]
    if result:
        lines.append(result)
    if conf is not None and conf != "":
        lines.append(f"confidence={conf}")
    if author:
        lines.append(f"author={author}")
    return lines


def _emit_section(title: str, blocks: list[list[str]]) -> None:
    if not blocks:
        return
    typer.echo(_rule(title))
    typer.echo()
    for i, block in enumerate(blocks):
        if i:
            typer.echo()
        typer.echo("\n".join(block))


def render_related(store, ledger_id: str) -> bool:
    """Print evidence chain for ledger_id. Returns False if not found."""
    chain = related_chain(store, ledger_id)
    if chain is None:
        return False

    kind = chain["target_kind"]
    target_meta = chain["target"]["metadata"]

    if kind == "observation":
        _emit_section("Observation", [_obs_lines(target_meta)])
        _emit_section("Decisions", [_decision_lines(m) for m in chain["decisions"]])
        _emit_section(
            "Verifications", [_verification_lines(m) for m in chain["verifications"]]
        )
        return True

    if kind == "decision":
        _emit_section("Decision", [_decision_lines(target_meta)])
        anchor = chain["anchor_id"]
        if anchor:
            typer.echo(_rule("relates_to"))
            typer.echo()
            typer.echo(anchor)
            typer.echo()
        _emit_section(
            "Sibling decisions", [_decision_lines(m) for m in chain["siblings"]]
        )
        _emit_section(
            "Verifications", [_verification_lines(m) for m in chain["verifications"]]
        )
        return True

    if kind == "verification":
        _emit_section("Verification", [_verification_lines(target_meta)])
        anchor = chain["anchor_id"]
        if anchor:
            typer.echo(_rule("relates_to"))
            typer.echo()
            typer.echo(anchor)
            typer.echo()
        if chain["observation"]:
            _emit_section("Observation", [_obs_lines(chain["observation"])])
        _emit_section(
            "Decision chain", [_decision_lines(m) for m in chain["decisions"]]
        )
        return True

    # Unknown ledger kind — show target only.
    _emit_section("Unit", [_obs_lines(target_meta)])
    return True

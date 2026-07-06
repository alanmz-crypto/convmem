"""Human-friendly next-step hints after CLI commands and scripts."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import typer

# Disable all footers: CONVMEM_NO_NEXT_STEPS=1


def _disabled() -> bool:
    return os.environ.get("CONVMEM_NO_NEXT_STEPS", "").strip() == "1"


def emit_next_steps(lines: list[str]) -> None:
    """Print a short bullet list of suggested follow-ups."""
    if _disabled() or not lines:
        return
    typer.echo("")
    typer.echo("── Next steps ──")
    for line in lines:
        typer.echo(f"  • {line}")


def workspace_context() -> dict:
    """Infer project lane from cwd for tailored hints."""
    cwd = Path.cwd().resolve()
    name = cwd.name.lower()
    ctx: dict = {"cwd": str(cwd), "slug": name}

    for part in cwd.parts:
        low = part.lower()
        if low == "willowyhollow-practice":
            ctx.update(
                {
                    "lane": "willowyhollow-practice",
                    "staging_site": "staging2.willowyhollow.com",
                    "guide": "~/Projects/convmem/docs/WILLOWYHOLLOW-WEBDEV-GUIDE.md",
                    "deploy_doc": "Deploy Workflow — willowyhollow.md",
                }
            )
            return ctx
        if low == "convmem":
            ctx.update({"lane": "convmem", "guide": "docs/MODEL-WORKFLOW.md"})
            return ctx
        if low == "willowyhollow" and "practice" not in name:
            ctx.update({"lane": "willowyhollow-preview", "staging_site": "staging2.willowyhollow.com"})
            return ctx

    ctx["lane"] = name or "general"
    return ctx


def after_doctor(*, passed: bool, v1: bool = False) -> None:
    if not passed:
        emit_next_steps(
            [
                "Fix failing checks above, then rerun: convmem doctor",
                "Recovery: ~/Projects/convmem/docs/RECOVER.md",
            ]
        )
        return
    ctx = workspace_context()
    lines = [
        "convmem tldr  # one-page cheat sheet",
        "convmem brief --stdout-only",
        "convmem unresolved" + (
            f" --site {ctx['staging_site']}"
            if ctx.get("staging_site")
            else "  # add --site <host> for client work"
        ),
    ]
    if ctx.get("lane") == "willowyhollow-practice":
        lines.extend(
            [
                "TLDR: ~/Projects/convmem/docs/WILLOWYHOLLOW-TLDR.md",
                "Read: Deploy Workflow — willowyhollow.md (exact deploy commands)",
                f"Guide: {ctx.get('guide', '')}",
            ]
        )
    else:
        lines.append('convmem "your topic"  # search before ask')
    if not v1:
        lines.append("convmem doctor --v1  # watch RSS, digest timer, locks")
    emit_next_steps(lines)


def after_brief(*, unresolved_count: int = 0, stale_handoff: bool = False) -> None:
    ctx = workspace_context()
    lines: list[str] = []
    if stale_handoff:
        lines.append("Update docs/inter-model/LATEST.md or read the newest inter-model file")
    if unresolved_count > 0:
        site = ctx.get("staging_site")
        if site:
            lines.append(f"convmem unresolved --site {site}")
        else:
            lines.append(f"convmem unresolved  # {unresolved_count} open")
    if ctx.get("lane") == "willowyhollow-practice":
        lines.extend(
            [
                'convmem "deploy staging2 functions.php"  # memory (no --site)',
                "scripts/sync-practice-to-preview.sh  # validate on :8080 before git push",
            ]
        )
    else:
        lines.append('convmem "your question"  # or: convmem ask "…"')
    lines.append("convmem record -i  # after a durable win (you: record --approve-last)")
    emit_next_steps(lines)


def after_search(
    *,
    query: str,
    site: str | None,
    n_results: int,
) -> None:
    ctx = workspace_context()
    lines: list[str] = []
    if n_results == 0:
        if site:
            lines.append(f'Try without --site: convmem "{query}"')
        lines.append(f'convmem ask "{query}"' + (f' --site {site}' if site else ""))
        if ctx.get("lane") == "willowyhollow-practice":
            lines.append("Deploy steps: Deploy Workflow — willowyhollow.md (repo file)")
    else:
        lines.append(f'convmem ask "{query[:60]}"' + (f" --site {site}" if site else ""))
        lines.append("convmem open <source_path>  # from hit metadata")
        if ctx.get("lane") == "willowyhollow-practice" and not site:
            lines.append(
                "Staging security: convmem unresolved --site staging2.willowyhollow.com"
            )
    emit_next_steps(lines)


def after_ask(
    *,
    question: str,
    site: str | None,
    n_citations: int,
    synthesis_failed: bool = False,
    synthesis_interrupted: bool = False,
) -> None:
    ctx = workspace_context()
    lines: list[str] = []
    if synthesis_failed or n_citations == 0:
        lines.append(f'convmem "{question[:50]}"  # raw search hits')
        if ctx.get("lane") == "willowyhollow-practice":
            lines.append("Repo runbook: Deploy Workflow — willowyhollow.md")
    if synthesis_interrupted:
        lines.append("Partial answer — citations above are still authoritative")
    if ctx.get("lane") == "willowyhollow-practice":
        lines.extend(
            [
                "Work on :8081 → preview :8080 → git push staging (theme-only)",
                "convmem record -i  # save what worked → record --approve-last",
            ]
        )
    elif n_citations > 0:
        lines.append("convmem record -i  # if this answer should become durable fact")
    emit_next_steps(lines)


def after_unresolved(*, site: str | None, count: int) -> None:
    ctx = workspace_context()
    lines: list[str] = []
    if count == 0:
        lines.append("convmem brief --stdout-only")
        lines.append('convmem "your next task"')
    else:
        site_q = site or ctx.get("staging_site") or "staging2.willowyhollow.com"
        lines.append(f'convmem ask "How do we fix these?" --site {site_q}')
        lines.append(f'convmem "{site_q} CSP SiteGround"')
        if "willowyhollow" in (site or "") or ctx.get("lane", "").startswith("willowyhollow"):
            lines.append("Site fix is in WordPress/hosting — not convmem index")
            lines.append("After fix: convmem monitor --site " + site_q + " --dry-run")
    if site and not site.startswith("staging2"):
        lines.append(f"Also check: convmem unresolved --site staging2.willowyhollow.com")
    emit_next_steps(lines)


def after_record_pending() -> None:
    emit_next_steps(["convmem record --approve-last  # you approve — then searchable"])


def after_record_approved(*, summary: str, ledger_id: str, site: str = "") -> None:
    q = (summary or ledger_id)[:60]
    if site:
        q = f"{site} {q}"[:70]
    emit_next_steps(
        [
            f'convmem "{q}"  # verify indexed',
            "convmem brief --stdout-only",
        ]
    )


def after_index(*, files_processed: int, units_indexed: int) -> None:
    lines = ["convmem doctor", 'convmem "topic from new index"']
    if files_processed == 0:
        lines.insert(0, "No files changed — use --file PATH --force to re-ingest one file")
    elif units_indexed:
        lines.insert(0, f"Indexed {units_indexed} unit(s) — spot-check search")
    emit_next_steps(lines)


def script_hints(name: str, **opts: object) -> None:
    """Hints for shell scripts (call via scripts/emit-next-steps.sh)."""
    if _disabled():
        return
    name = name.strip().lower().replace("_", "-")
    if name == "cross-project-digest":
        skip = bool(opts.get("skip_ask"))
        lines = [
            "Review digest under ~/.local/share/convmem/digests/",
            "bash scripts/smoke-cross-project-digest.sh  # regression smoke",
        ]
        if not skip:
            lines.insert(0, "Read ## Recency check — header vs ask citations")
        else:
            lines.append("Full synthesis: scripts/cross-project-digest.sh  # needs DEEPSEEK_API_KEY")
        emit_next_steps(lines)
        return
    if name == "smoke-cross-project-digest":
        emit_next_steps(
            [
                "Weekly timer: bash scripts/install-cross-project-digest-timer.sh",
                "Pilot log: docs/inter-model/CROSS-PROJECT-DIGEST-PILOT.md",
            ]
        )
        return
    if name == "install-digest-timer":
        emit_next_steps(
            [
                "systemctl --user list-timers convmem-cross-project-digest.timer",
                "journalctl --user -u convmem-cross-project-digest -f  # after fire",
                "Manual run: scripts/cross-project-digest.sh --skip-ask",
            ]
        )
        return
    if name == "smoke-write-guard":
        emit_next_steps(
            [
                "Lab: bash ~/Projects/convmem-lab/lab/scripts/smoke-synthesis.sh",
                "Prod work: cd ~/Projects/convmem && convmem doctor",
            ]
        )
        return
    if name == "index-inter-model":
        emit_next_steps(
            [
                'convmem "CROSS-PROJECT-DIGEST-PILOT"  # spot-check',
                "Optional: add [watch].extra_paths for docs/inter-model in config.toml",
            ]
        )
        return


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    if not argv:
        typer.echo("Usage: emit-next-steps.sh <script-name> [key=value ...]", err=True)
        return 1
    kwargs: dict = {}
    for arg in argv[1:]:
        if "=" in arg:
            k, v = arg.split("=", 1)
            kwargs[k.replace("-", "_")] = v not in ("0", "false", "no")
    script_hints(argv[0], **kwargs)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

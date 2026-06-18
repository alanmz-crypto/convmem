"""Open the source chat session for a search/ask hit."""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass
class OpenTarget:
    """How to open a hit's underlying conversation."""

    label: str
    command: list[str] | None = None
    hint: str | None = None
    cwd: str | None = None

    def format_line(self) -> str:
        if self.command:
            return f"Open: {' '.join(self.command)}"
        if self.hint:
            return f"Open: {self.hint}"
        return f"Open: {self.label}"


def _cursor_slug_to_path(slug: str) -> Path | None:
    parts = slug.split("-")
    if len(parts) < 2 or parts[0] != "home":
        return None
    base = Path("/") / parts[0] / parts[1]
    if len(parts) > 2:
        return base.joinpath(*parts[2:])
    return base


def _session_id_from_path(path: str) -> str | None:
    p = Path(path)
    if "agent-transcripts" in p.parts:
        return p.parent.name
    if p.name == "store.db" and "cursor" in p.parts and "chats" in p.parts:
        return p.parent.name
    if p.suffix == ".json" and ".continue" in p.parts:
        from adapters.json_chat import read_session_meta

        meta = read_session_meta(path)
        return meta.get("session_id") or p.stem
    return None


def _continue_workspace_from_path(path: str) -> str | None:
    if ".continue" not in Path(path).parts:
        return None
    from adapters.json_chat import read_session_meta

    ws = read_session_meta(path).get("workspace_directory") or ""
    return ws if ws and os.path.isdir(ws) else None


def _conversation_id_at_offset(path: str, offset: int | None) -> str | None:
    """Resolve Kiro conversation_id by re-parsing (works without re-index)."""
    if offset is None:
        return None
    from adapters.sqlite_chat import parse

    try:
        messages = parse(path)
    except Exception:
        return None
    if offset < 0 or offset >= len(messages):
        return None
    cid = messages[offset].get("conversation_id")
    return cid if isinstance(cid, str) and cid else None


def resolve_open_target(meta: dict) -> OpenTarget:
    """Map result metadata to an open action."""
    path = str(meta.get("source_path") or "")
    tool = meta.get("tool") or ""
    p = Path(path)
    session_id = meta.get("session_id") or _session_id_from_path(path)
    conversation_id = meta.get("conversation_id") or _conversation_id_at_offset(
        path, meta.get("start_offset")
    )
    editor = os.environ.get("EDITOR", "cursor")

    if tool == "kiro" or "kiro-cli" in path:
        if conversation_id:
            cmd = ["kiro-cli", "chat", "--resume-id", conversation_id]
            return OpenTarget(
                label="Kiro chat session",
                command=cmd,
                hint=f"kiro-cli chat --resume-id {conversation_id}",
            )
        return OpenTarget(
            label="Kiro database",
            hint="kiro-cli chat --resume-picker  (conversation id not indexed — re-run convmem index)",
        )

    if tool == "cursor" or "agent-transcripts" in p.parts or (
        p.name == "store.db" and "cursor" in p.parts
    ):
        if "agent-transcripts" in p.parts:
            idx = p.parts.index("projects")
            slug = p.parts[idx + 1]
            workspace = _cursor_slug_to_path(slug)
            agent_id = p.parent.name
            if workspace and workspace.is_dir():
                cmd = ["cursor", "-r", str(workspace)]
                return OpenTarget(
                    label=f"Cursor project ({workspace.name})",
                    command=cmd,
                    hint=(
                        f"cursor -r {workspace}  "
                        f"— then open agent chat {agent_id[:8]}… in Composer history"
                    ),
                )
            return OpenTarget(
                label="Cursor agent transcript",
                command=["cursor", "-g", path],
                hint=f"cursor -g {path}",
            )
        if p.name == "store.db":
            composer_id = p.parent.name
            return OpenTarget(
                label="Cursor Composer chat",
                hint=(
                    f"Open Cursor → Composer history → chat {composer_id[:8]}… "
                    f"(store.db chats are not fully indexed yet)"
                ),
            )

    if tool == "continue" or (".continue" in p.parts and p.suffix == ".json"):
        sid = session_id or _session_id_from_path(path)
        workspace = (
            meta.get("workspace_directory")
            or _continue_workspace_from_path(path)
        )
        if sid and _which("cn"):
            cmd = ["cn", "--fork", sid]
            hint = f"cn --fork {sid}"
            if workspace:
                hint += f"  (in {workspace})"
            return OpenTarget(
                label="Continue CLI session",
                command=cmd,
                hint=hint,
                cwd=workspace,
            )
        if sid:
            return OpenTarget(
                label="Continue session",
                hint=f"cn --fork {sid}  (install Continue CLI: npm i -g @continuedev/cli)",
            )
        return OpenTarget(
            label="Continue sessions",
            command=["cn", "ls"] if _which("cn") else None,
            hint="cn ls  — pick session interactively",
        )

    if tool == "aider" or p.name == ".aider.chat.history.md":
        cmd = ["cursor", "-g", path]
        if not _which("cursor"):
            cmd = [editor, path] if editor else None
        return OpenTarget(
            label="Aider chat history",
            command=cmd,
            hint=f"cursor -g {path}",
        )

    if tool == "crush" or (p.name == "crush.db" and ".crush" in p.parts):
        workspace = meta.get("workspace_directory") or str(p.parent.parent)
        sid = session_id or ""
        sid_hint = f" (session {sid[:8]}…)" if sid else ""
        return OpenTarget(
            label="Crush session",
            hint=f"cd {workspace} && crush{sid_hint}  — history in {p}",
            cwd=workspace if workspace and os.path.isdir(workspace) else None,
        )

    if tool == "openwebui" or "webui" in path:
        return OpenTarget(
            label="Open WebUI",
            hint="Open your Open WebUI instance in the browser (chat is in webui.db)",
        )

    if path and os.path.isfile(path):
        pager = os.environ.get("PAGER", "less")
        return OpenTarget(
            label="Source file",
            command=[pager, path],
            hint=f"{pager} {path}",
        )

    return OpenTarget(label="unknown source", hint=path or "no source path")


def _which(cmd: str) -> str | None:
    from shutil import which

    return which(cmd)


def run_open(meta: dict, *, dry_run: bool = False) -> OpenTarget:
    """Print or execute the open action for a hit."""
    target = resolve_open_target(meta)
    if dry_run or not target.command:
        return target
    try:
        subprocess.run(target.command, check=False, cwd=target.cwd)
    except OSError:
        pass
    return target

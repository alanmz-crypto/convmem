#!/usr/bin/env python3
"""Atomic retrieval-action counting for Portland baseline Rerun2."""
from __future__ import annotations

import re
import shlex
from dataclasses import dataclass


RITUAL_RE = re.compile(
    r"\bconvmem\s+(doctor|brief(\s+--stdout-only)?|unresolved|tldr|stats)\b",
    re.I,
)
READ_CMDS = {"cat", "head", "tail", "sed", "less", "more", "bat"}
SEARCH_CMDS = {"rg", "grep", "find", "fd", "ag"}
GH_RETRIEVAL = re.compile(r"\bgh\s+(search|api|repo\s+view|issue\s+view|pr\s+view)\b", re.I)
CONVMEM_RETRIEVAL = re.compile(r"\bconvmem\s+(search|ask|related)\b", re.I)
SPLIT_RE = re.compile(r"\s*(?:;|&&|\|\|)\s*")


@dataclass
class ParsedAction:
    action_number: int
    tool_class: str
    command: str
    is_ritual: bool
    protocol_violation: str = ""


def _strip_wrapper(command: str) -> str:
    cmd = command.strip()
    for prefix in ("/usr/bin/zsh -lc ", "bash -lc ", "zsh -lc "):
        if cmd.startswith(prefix):
            return cmd[len(prefix) :].strip().strip("'\"")
    return cmd.strip().strip("'\"")


def _classify_segment(segment: str) -> tuple[str, bool, str]:
    seg = segment.strip()
    if not seg or seg in {"true", "false", ":"}:
        return "noop", False, ""
    if RITUAL_RE.search(seg):
        return "protocol_ritual", True, ""
    if CONVMEM_RETRIEVAL.search(seg):
        return "convmem_retrieval", False, ""
    if GH_RETRIEVAL.search(seg):
        return "gh_retrieval", False, ""
    try:
        parts = shlex.split(seg)
    except ValueError:
        parts = seg.split()
    if not parts:
        return "noop", False, ""
    base = parts[0].split("/")[-1]
    if base in SEARCH_CMDS:
        return "shell_search", False, ""
    if base in READ_CMDS:
        return "shell_read", False, ""
    retrieval_hits = 0
    if any(base == c or c in seg for c in SEARCH_CMDS):
        retrieval_hits += 1
    if any(f" {c} " in f" {seg} " or seg.startswith(c + " ") for c in READ_CMDS):
        retrieval_hits += seg.count(" cat ") + seg.count(" head ") + seg.count(" tail ")
    if retrieval_hits > 1:
        return "compound", False, "multiple independent retrievals in one shell segment"
    return "other", False, ""


def count_command_actions(command: str) -> list[tuple[str, bool, str]]:
    inner = _strip_wrapper(command)
    if SPLIT_RE.search(inner):
        segments = [s for s in SPLIT_RE.split(inner) if s.strip()]
        if len(segments) > 1:
            out: list[tuple[str, bool, str]] = []
            for seg in segments:
                tool_class, ritual, violation = _classify_segment(seg)
                if tool_class not in {"noop", "other"}:
                    out.append((tool_class, ritual, violation))
            if out:
                return out
    tool_class, ritual, violation = _classify_segment(inner)
    if tool_class in {"noop", "other"}:
        return []
    return [(tool_class, ritual, violation)]


def classify_mcp_tool(tool_name: str) -> tuple[str, bool]:
    name = (tool_name or "").lower()
    if any(x in name for x in ("search", "ask", "related", "brief", "unresolved")):
        if "brief" in name or "unresolved" in name:
            return "protocol_ritual", True
        return "convmem_retrieval", False
    return "other", False


def parse_codex_jsonl(events: list[dict]) -> list[ParsedAction]:
    actions: list[ParsedAction] = []
    n = 0
    for ev in events:
        if ev.get("type") != "item.completed":
            continue
        item = ev.get("item") or {}
        itype = item.get("type")
        if itype == "command_execution":
            cmd = item.get("command") or ""
            for tool_class, ritual, violation in count_command_actions(cmd):
                n += 1
                actions.append(
                    ParsedAction(
                        action_number=n,
                        tool_class=tool_class,
                        command=cmd,
                        is_ritual=ritual,
                        protocol_violation=violation,
                    )
                )
        elif itype == "mcp_tool_call":
            tool_name = item.get("tool") or item.get("name") or ""
            tool_class, ritual = classify_mcp_tool(tool_name)
            if tool_class == "convmem_retrieval":
                n += 1
                actions.append(
                    ParsedAction(
                        action_number=n,
                        tool_class=tool_class,
                        command=f"mcp:{tool_name}",
                        is_ritual=ritual,
                    )
                )
    return actions


def budget_actions(actions: list[ParsedAction]) -> list[ParsedAction]:
    return [a for a in actions if not a.is_ritual and a.tool_class != "other"]

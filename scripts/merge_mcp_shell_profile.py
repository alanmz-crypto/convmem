#!/usr/bin/env python3
"""Merge CONVMEM_MCP_PROFILE=shell into an MCP client config without clobbering env.

Usage:
  python3 scripts/merge_mcp_shell_profile.py <config.json> <cursor|kiro|crush>

Prints one of: added | updated | unchanged
Never prints env values.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROFILE_KEY = "CONVMEM_MCP_PROFILE"
PROFILE_VALUE = "shell"

# JSON path from root → server block that owns "env"
SERVER_PATHS = {
    "cursor": ("mcpServers", "convmem"),
    "kiro": ("mcpServers", "convmem"),
    "crush": ("mcp", "convmem"),
}


def merge_shell_profile(config_path: Path, client: str) -> str:
    """Set CONVMEM_MCP_PROFILE=shell on the convmem server env; preserve other keys."""
    if client not in SERVER_PATHS:
        raise ValueError(f"unknown client: {client}")
    path = SERVER_PATHS[client]
    with open(config_path, encoding="utf-8") as f:
        cfg = json.load(f)

    cur: dict = cfg
    for key in path[:-1]:
        nxt = cur.get(key)
        if not isinstance(nxt, dict):
            nxt = {}
            cur[key] = nxt
        cur = nxt
    server_key = path[-1]
    server = cur.get(server_key)
    if not isinstance(server, dict):
        server = {}
        cur[server_key] = server

    env = server.get("env")
    if not isinstance(env, dict):
        env = {}
        server["env"] = env

    prior = env.get(PROFILE_KEY)
    if prior == PROFILE_VALUE:
        return "unchanged"
    action = "updated" if PROFILE_KEY in env else "added"
    env[PROFILE_KEY] = PROFILE_VALUE

    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)
        f.write("\n")
    return action


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(
            "usage: merge_mcp_shell_profile.py <config.json> <cursor|kiro|crush>",
            file=sys.stderr,
        )
        return 2
    config_path = Path(argv[1])
    client = argv[2]
    if not config_path.is_file():
        print(f"missing config: {config_path}", file=sys.stderr)
        return 1
    print(merge_shell_profile(config_path, client))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

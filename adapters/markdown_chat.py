"""Adapter for Aider chat history files (.aider.chat.history.md).

Format (observed in real files):
    # aider chat started at 2026-05-31 04:15:43
    > Aider v0.86.2          ← session preamble, skipped
    > Main model: ...
    #### user message here
    assistant response (plain text and/or lines prefixed with "> ")
    > Tokens: 903 sent, ...  ← dropped
    #### next user message
"""

import re

SESSION_HEADER = re.compile(r"^# aider chat started at (.+)$", re.MULTILINE)
USER_HEADER = re.compile(r"^#### (.+)$")
ASSISTANT_META = re.compile(
    r"^(> )?(Tokens:|Applied edit to|Commit [a-f0-9]+|Add file to the chat\?|"
    r"Create [^ ]+\?|^C again to exit|^C KeyboardInterrupt)"
)


def _normalize_assistant(lines: list[str]) -> str:
    out: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            out.append("")
            continue
        if ASSISTANT_META.match(line) or ASSISTANT_META.match(stripped):
            continue
        if line.startswith("> "):
            out.append(line[2:])
        elif line.startswith(">"):
            out.append(line[1:].lstrip())
        else:
            out.append(line)
    return "\n".join(out).strip()


def parse(filepath: str) -> list[dict]:
    """Parse an Aider .aider.chat.history.md file into canonical messages.

    Returns:
        [{"role": "user"|"assistant", "content": str, "timestamp": str|None}, ...]
    """
    with open(filepath, "r", encoding="utf-8") as f:
        text = f.read()

    messages: list[dict] = []
    parts = SESSION_HEADER.split(text)

    # parts[0] is any content before the first session header (usually empty)
    i = 1
    while i < len(parts):
        session_ts = parts[i].strip()
        body = parts[i + 1] if i + 1 < len(parts) else ""
        i += 2

        lines = body.splitlines()
        idx = 0
        while idx < len(lines):
            m = USER_HEADER.match(lines[idx])
            if not m:
                idx += 1
                continue

            user_content = m.group(1).strip()
            idx += 1

            assistant_lines: list[str] = []
            while idx < len(lines):
                if USER_HEADER.match(lines[idx]):
                    break
                assistant_lines.append(lines[idx])
                idx += 1

            if user_content:
                messages.append(
                    {
                        "role": "user",
                        "content": user_content,
                        "timestamp": session_ts or None,
                    }
                )

            assistant_content = _normalize_assistant(assistant_lines)
            if assistant_content:
                messages.append(
                    {
                        "role": "assistant",
                        "content": assistant_content,
                        "timestamp": session_ts or None,
                    }
                )

    return messages

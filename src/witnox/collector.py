"""Read-only, aggregate-only Claude Code JSONL collector (initial backend)."""

from __future__ import annotations

import json
import sys
from collections import Counter
from datetime import UTC, datetime, timedelta
from pathlib import Path

from tqdm import tqdm

from .commands import count_commands, parse_shell


def _timestamp(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00" if value.endswith("Z") else value)
        if parsed.tzinfo is None:
            return None
        return parsed.astimezone(UTC)
    except ValueError:
        return None


def collect_claude(
    root: Path,
    days: int = 7,
    now: datetime | None = None,
    progress: bool | None = None,
    include_commands: bool = False,
) -> dict:
    """Count distinct assistant tool-use blocks without retaining arguments or message content.

    Progress goes to stderr; by default it is shown only on interactive terminals.
    The event ID within a file is used for deduplication. Repeated snapshots of the
    same assistant message are merged, while distinct blocks in one message are counted.
    This parser is intentionally conservative and does not infer shell commands.
    """
    if days < 1:
        raise ValueError("days must be >= 1")
    cutoff = (now or datetime.now(UTC)) - timedelta(days=days)
    counts: Counter[str] = Counter()
    seen: set[tuple[str, str]] = set()
    shell_invocations: list[tuple[str, str | None]] = []
    shell_tool_calls = 0
    stores = sorted(p for p in root.glob(".claude*") if p.is_dir())
    paths = sorted(
        path
        for store in stores
        if (store / "projects").is_dir()
        for path in (store / "projects").rglob("*.jsonl")
    )
    show_progress = sys.stderr.isatty() if progress is None else progress
    with tqdm(
        paths,
        desc="Scanning Claude logs",
        unit="file",
        file=sys.stderr,
        disable=not show_progress,
        dynamic_ncols=True,
    ) as files:
        for path in files:
            try:
                with path.open("r", encoding="utf-8", errors="replace") as stream:
                    for line in stream:
                        try:
                            event = json.loads(line)
                        except (ValueError, TypeError):
                            continue
                        if not isinstance(event, dict) or event.get("type") != "assistant":
                            continue
                        stamp = _timestamp(event.get("timestamp"))
                        if stamp is None or stamp < cutoff:
                            continue
                        msg = event.get("message")
                        if not isinstance(msg, dict):
                            continue
                        content = msg.get("content")
                        if not isinstance(content, list):
                            continue
                        for idx, block in enumerate(content):
                            if not isinstance(block, dict) or block.get("type") != "tool_use":
                                continue
                            name = block.get("name")
                            if not isinstance(name, str) or not name:
                                continue
                            block_id = block.get("id")
                            if not isinstance(block_id, str) or not block_id:
                                msg_id = msg.get("id")
                                if not isinstance(msg_id, str) or not msg_id:
                                    continue  # cannot deduplicate reliably
                                block_id = f"{msg_id}:{idx}"
                            key = (str(path), block_id)
                            if key not in seen:
                                seen.add(key)
                                counts[name] += 1
                                if include_commands and name in {"Bash", "PowerShell"}:
                                    shell_tool_calls += 1
                                    data = block.get("input")
                                    if isinstance(data, dict):
                                        command = data.get("command")
                                        if isinstance(command, str):
                                            shell_invocations.extend(parse_shell(command, name))
            except OSError:
                continue
    result = {
        "source": "claude",
        "days": days,
        "files_scanned": len(paths),
        "tool_calls": sum(counts.values()),
        "tools": dict(counts.most_common()),
    }
    if include_commands:
        result["commands"] = {
            "shell_tool_calls": shell_tool_calls,
            **count_commands(shell_invocations),
            "method": "conservative_estimate_not_execution_trace",
        }
    return result


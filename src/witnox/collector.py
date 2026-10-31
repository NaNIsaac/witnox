"""Read-only, aggregate-only Claude Code JSONL collector (initial backend)."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
import json


def _timestamp(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            return None
        return parsed.astimezone(timezone.utc)
    except ValueError:
        return None


def collect_claude(root: Path, days: int = 7, now: datetime | None = None) -> dict:
    """Count distinct assistant tool-use blocks without retaining arguments or message content.

    The event ID within a file is used for deduplication. Repeated snapshots of the
    same assistant message are merged, while distinct blocks in one message are counted.
    This parser is intentionally conservative and does not infer shell commands.
    """
    if days < 1:
        raise ValueError("days must be >= 1")
    cutoff = (now or datetime.now(timezone.utc)) - timedelta(days=days)
    counts: Counter[str] = Counter()
    files = 0
    seen: set[tuple[str, str]] = set()
    stores = sorted(p for p in root.glob(".claude*") if p.is_dir())
    for store in stores:
        projects = store / "projects"
        if not projects.is_dir():
            continue
        for path in projects.rglob("*.jsonl"):
            files += 1
            try:
                with path.open("r", encoding="utf-8", errors="replace") as stream:
                    for line in stream:
                        try:
                            event = json.loads(line)
                        except (ValueError, TypeError):
                            continue
                        if event.get("type") != "assistant":
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
            except OSError:
                continue
    return {"source": "claude", "days": days, "files_scanned": files,
            "tool_calls": sum(counts.values()), "tools": dict(counts.most_common())}

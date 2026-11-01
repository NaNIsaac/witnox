"""Conservative, local-only multi-provider tool-call summaries.

Provider formats can change. Unknown event shapes are skipped, not guessed.
No account IDs, paths, prompts, arguments or raw tool names are exported.
"""

from __future__ import annotations

import json
from collections import Counter
from datetime import UTC, datetime, timedelta
from pathlib import Path

from .collector import _timestamp

CODEX_TOOLS = frozenset({
    "exec_command", "write_stdin", "apply_patch", "update_plan",
    "view_image", "web_search", "open_image", "request_user_input",
    "shell_command", "spawn_agent", "send_input", "wait", "close_agent",
})
GEMINI_TOOLS = frozenset({
    "run_shell_command", "read_file", "write_file", "replace", "glob",
    "grep_search", "list_directory", "web_fetch", "google_web_search",
    "save_memory", "read_many_files", "edit_file", "search_file_content",
    "run_shell", "shell", "execute_command",
})


def _safe_tool(name: object, allowlist: frozenset[str]) -> str:
    if not isinstance(name, str):
        return "other"
    return name if name in allowlist else "other"


def _result(provider: str, files: int, counts: Counter[str]) -> dict:
    return {
        "provider": provider,
        "files_scanned": files,
        "tool_calls": sum(counts.values()),
        "tools": dict(counts.most_common()),
    }


def collect_codex(root: Path, cutoff: datetime) -> dict:
    """Count Codex response_item function/custom tool calls (not output records)."""
    counts: Counter[str] = Counter()
    files = 0
    seen: set[tuple[str, str]] = set()
    home = root / ".codex"
    for directory in (home / "sessions", home / "archived_sessions"):
        if not directory.is_dir():
            continue
        for path in directory.rglob("*.jsonl"):
            files += 1
            try:
                with path.open(encoding="utf-8", errors="replace") as stream:
                    for number, line in enumerate(stream):
                        try:
                            event = json.loads(line)
                        except (ValueError, TypeError):
                            continue
                        if not isinstance(event, dict) or event.get("type") != "response_item":
                            continue
                        stamp = _timestamp(event.get("timestamp"))
                        if stamp is None or stamp < cutoff:
                            continue
                        payload = event.get("payload")
                        if not isinstance(payload, dict):
                            continue
                        kind = payload.get("type")
                        if kind not in {"function_call", "custom_tool_call", "web_search_call"}:
                            continue
                        # Deduplicate by call_id if present, otherwise JSONL line identity.
                        call_id = payload.get("call_id")
                        marker = call_id if isinstance(call_id, str) else f"line:{number}"
                        key = (str(path), marker)
                        if key in seen:
                            continue
                        seen.add(key)
                        if kind == "web_search_call":
                            counts["web_search"] += 1
                        else:
                            counts[_safe_tool(payload.get("name"), CODEX_TOOLS)] += 1
            except OSError:
                continue
    return _result("codex", files, counts)


def collect_gemini(root: Path, cutoff: datetime) -> dict:
    """Count Gemini CLI stored chat toolCalls, which may include failed calls."""
    counts: Counter[str] = Counter()
    files = 0
    seen: set[tuple[str, str]] = set()
    temp = root / ".gemini" / "tmp"
    if temp.is_dir():
        for path in temp.glob("*/chats/*.json"):
            files += 1
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError, UnicodeError):
                continue
            if not isinstance(data, dict) or not isinstance(data.get("messages"), list):
                continue
            for msg_index, message in enumerate(data["messages"]):
                if not isinstance(message, dict) or message.get("type") != "gemini":
                    continue
                stamp = _timestamp(message.get("timestamp"))
                if stamp is None or stamp < cutoff:
                    continue
                calls = message.get("toolCalls")
                if not isinstance(calls, list):
                    continue
                for index, call in enumerate(calls):
                    if not isinstance(call, dict):
                        continue
                    call_id = call.get("id")
                    marker = call_id if isinstance(call_id, str) else f"{msg_index}:{index}"
                    key = (str(path), marker)
                    if key in seen:
                        continue
                    seen.add(key)
                    counts[_safe_tool(call.get("name"), GEMINI_TOOLS)] += 1
    return _result("gemini", files, counts)


def collect_accounts(root: Path, days: int = 7, now: datetime | None = None) -> dict:
    """Compare providers and distinct local Claude stores without revealing account identity."""
    if days < 1:
        raise ValueError("days must be positive")
    cutoff = (now or datetime.now(UTC)) - timedelta(days=days)
    stores = sorted(
        p for p in root.glob(".claude*")
        if p.is_dir() and (p / "projects").is_dir()
    )
    claude_stores = []
    from .collector import collect_claude

    for i, store in enumerate(stores, 1):
        # Collect only this store using a temporary routing argument? No: reuse
        # original Claude collector on a private path by adding stores filter.
        result = collect_claude(root, days=days, now=now, progress=False, stores=[store])
        claude_stores.append({
            "store": f"claude-{i}",
            "files_scanned": result["files_scanned"],
            "tool_calls": result["tool_calls"],
            "tools": result["tools"],
        })
    codex = collect_codex(root, cutoff)
    gemini = collect_gemini(root, cutoff)
    total = sum(s["tool_calls"] for s in claude_stores)
    return {
        "days": days,
        "providers": [
            {"provider": "claude", "files_scanned": sum(s["files_scanned"] for s in claude_stores),
             "tool_calls": total},
            {"provider": "codex", "files_scanned": codex["files_scanned"],
             "tool_calls": codex["tool_calls"]},
            {"provider": "gemini", "files_scanned": gemini["files_scanned"],
             "tool_calls": gemini["tool_calls"]},
        ],
        "claude_stores": claude_stores,
        "details": {"codex": codex, "gemini": gemini},
        "note": "Local stores are not necessarily distinct accounts. Counts are tool requests, not completed tasks.",
    }

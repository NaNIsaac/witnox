"""Empty provider call IDs must not cause unrelated calls to be dropped."""
import json
from datetime import UTC, datetime

from witnox.providers import collect_accounts


def test_empty_codex_call_ids_are_distinct(tmp_path):
    stamp = datetime.now(UTC).isoformat()
    folder = tmp_path / ".codex" / "sessions"
    folder.mkdir(parents=True)
    record = {
        "type": "response_item",
        "timestamp": stamp,
        "payload": {"type": "function_call", "call_id": "", "name": "exec_command"},
    }
    (folder / "rollout.jsonl").write_text(
        "\n".join(json.dumps(record) for _ in range(2)) + "\n", encoding="utf-8"
    )
    summary = collect_accounts(tmp_path)
    assert summary["details"]["codex"]["tool_calls"] == 2
    assert summary["details"]["codex"]["tools"] == {"exec_command": 2}


def test_empty_gemini_call_ids_are_distinct(tmp_path):
    stamp = datetime.now(UTC).isoformat()
    folder = tmp_path / ".gemini" / "tmp" / "project" / "chats"
    folder.mkdir(parents=True)
    message = {
        "type": "gemini",
        "timestamp": stamp,
        "toolCalls": [
            {"id": "", "name": "read_file"},
            {"id": "", "name": "run_shell_command"},
        ],
    }
    (folder / "session.json").write_text(
        json.dumps({"messages": [message]}), encoding="utf-8"
    )
    summary = collect_accounts(tmp_path)
    assert summary["details"]["gemini"]["tool_calls"] == 2
    assert summary["details"]["gemini"]["tools"] == {
        "read_file": 1,
        "run_shell_command": 1,
    }


def test_nonempty_call_ids_still_deduplicate(tmp_path):
    stamp = datetime.now(UTC).isoformat()
    folder = tmp_path / ".codex" / "sessions"
    folder.mkdir(parents=True)
    record = {
        "type": "response_item",
        "timestamp": stamp,
        "payload": {"type": "function_call", "call_id": "same", "name": "exec_command"},
    }
    (folder / "rollout.jsonl").write_text(
        "\n".join(json.dumps(record) for _ in range(2)) + "\n", encoding="utf-8"
    )
    summary = collect_accounts(tmp_path)
    assert summary["details"]["codex"]["tool_calls"] == 1

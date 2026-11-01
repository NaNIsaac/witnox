"""Synthetic fixtures for multiple account stores and agent formats."""

import json
from datetime import UTC, datetime

from witnox.cli import main
from witnox.providers import collect_accounts


def test_provider_fixtures(tmp_path, capsys):
    stamp = datetime.now(UTC).isoformat()
    for store in (".claude", ".claude-alt"):
        p = tmp_path / store / "projects" / "p"
        p.mkdir(parents=True)
        record = {"type": "assistant", "timestamp": stamp, "message": {
            "id": "msg", "content": [{"type": "tool_use", "id": "tool", "name": "Read"}],
        }}
        (p / "session.jsonl").write_text(json.dumps(record), encoding="utf-8")

    codex = tmp_path / ".codex" / "sessions" / "2026" / "11"
    codex.mkdir(parents=True)
    event = {"type": "response_item", "timestamp": stamp,
             "payload": {"type": "function_call", "call_id": "one",
                         "name": "exec_command", "arguments": "SECRET"}}
    (codex / "rollout.jsonl").write_text(
        json.dumps(event) + "\n" + json.dumps(event), encoding="utf-8"
    )
    gemini = tmp_path / ".gemini" / "tmp" / "hash" / "chats"
    gemini.mkdir(parents=True)
    (gemini / "session.json").write_text(json.dumps({"messages": [
        {"type": "gemini", "timestamp": stamp, "toolCalls": [
            {"id": "one", "name": "run_shell_command", "args": {"command": "SECRET"}},
        ]},
    ]}), encoding="utf-8")

    result = collect_accounts(tmp_path)
    assert [x["tool_calls"] for x in result["providers"]] == [2, 1, 1]
    assert len(result["claude_stores"]) == 2
    assert result["details"]["codex"]["tools"] == {"exec_command": 1}
    assert result["details"]["gemini"]["tools"] == {"run_shell_command": 1}
    assert "SECRET" not in json.dumps(result)
    assert str(tmp_path) not in json.dumps(result)

    assert main(["agents", "--root", str(tmp_path), "--json"]) == 0
    output = capsys.readouterr().out
    assert json.loads(output)["providers"][0]["tool_calls"] == 2
    assert "SECRET" not in output


def test_unknown_codex_tool_name_not_exported(tmp_path):
    stamp = datetime.now(UTC).isoformat()
    folder = tmp_path / ".codex" / "sessions"
    folder.mkdir(parents=True)
    (folder / "x.jsonl").write_text(json.dumps({
        "type": "response_item", "timestamp": stamp,
        "payload": {"type": "custom_tool_call", "call_id": "1",
                    "name": "private_name_SECRET"},
    }), encoding="utf-8")
    result = collect_accounts(tmp_path)
    assert result["details"]["codex"]["tools"] == {"other": 1}
    assert "SECRET" not in json.dumps(result)

from datetime import datetime, timezone
from pathlib import Path
import pytest
import json

from witnox.collector import collect_claude
from witnox.cli import main


def test_deduplicates_snapshots_but_preserves_distinct_tools(tmp_path: Path):
    project = tmp_path / ".claude" / "projects" / "example"
    project.mkdir(parents=True)
    event = {
        "type": "assistant", "timestamp": "2026-10-31T00:00:00Z",
        "message": {"id": "msg_1", "content": [
            {"type": "tool_use", "id": "tool_a", "name": "Bash",
             "input": {"command": "secret-command --token=abc"}},
            {"type": "tool_use", "id": "tool_b", "name": "Read", "input": {"file_path": "PRIVATE"}},
        ]},
    }
    (project / "x.jsonl").write_text(
        "\n".join([json.dumps(event), json.dumps(event), "not-json"]), encoding="utf-8"
    )
    result = collect_claude(tmp_path, now=datetime(2026, 10, 31, tzinfo=timezone.utc))
    assert result["tool_calls"] == 2
    assert result["tools"] == {"Bash": 1, "Read": 1}
    assert "secret" not in json.dumps(result)
    assert "PRIVATE" not in json.dumps(result)


def test_skips_old_events(tmp_path: Path):
    project = tmp_path / ".claude-alt" / "projects" / "p"
    project.mkdir(parents=True)
    event = {
        "type": "assistant", "timestamp": "2026-01-01T00:00:00Z",
        "message": {"id": "a", "content": [{"type": "tool_use", "id": "b", "name": "Bash"}]},
    }
    (project / "x.jsonl").write_text(json.dumps(event), encoding="utf-8")
    result = collect_claude(tmp_path, now=datetime(2026, 10, 31, tzinfo=timezone.utc))
    assert result["tool_calls"] == 0


def test_cli_version(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    assert "0.0.1" in capsys.readouterr().out

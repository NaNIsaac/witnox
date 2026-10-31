import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from witnox.cli import main
from witnox.collector import collect_claude


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
    result = collect_claude(tmp_path, now=datetime(2026, 10, 31, tzinfo=UTC))
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
    result = collect_claude(tmp_path, now=datetime(2026, 10, 31, tzinfo=UTC))
    assert result["tool_calls"] == 0


def test_cli_version(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    assert "0.0.1" in capsys.readouterr().out


def test_progress_stderr_preserves_json_stdout(tmp_path: Path, capsys):
    project = tmp_path / ".claude" / "projects" / "p"
    project.mkdir(parents=True)
    (project / "x.jsonl").write_text(
        json.dumps({
            "type": "assistant",
            "timestamp": datetime.now(UTC).isoformat(),
            "message": {
                "id": "message_test",
                "content": [{"type": "tool_use", "id": "tool_test", "name": "Read"}],
            },
        }),
        encoding="utf-8",
    )
    assert main(["report", "--root", str(tmp_path), "--json", "--progress"]) == 0
    out = capsys.readouterr()
    assert json.loads(out.out)["tools"] == {"Read": 1}
    assert "Scanning Claude logs" in out.err
    assert "Scanning Claude logs" not in out.out


def test_no_progress_suppresses_stderr(tmp_path: Path, capsys):
    assert main(["report", "--root", str(tmp_path), "--no-progress"]) == 0
    assert capsys.readouterr().err == ""

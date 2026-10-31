"""The parser favors precision over recall; raw shell arguments are never emitted."""

import json
from datetime import UTC, datetime

from witnox.cli import main
from witnox.commands import parse_shell


def test_simple_subcommands_and_pipeline():
    assert parse_shell("git status && gh pr list | grep ready", "Bash") == [
        ("git", "status"),
        ("gh", "pr"),
        ("grep", None),
    ]


def test_skips_script_body_and_unknown_commands():
    for command in ["for x in a b; do git status; done",
                    "python - <<'PY'\nimport os\nPY",
                    "def demo():\n  git status",
                    "echo git status"]:
        assert parse_shell(command, "Bash") == []


def test_does_not_echo_untrusted_arguments(tmp_path, capsys):
    p = tmp_path / ".claude" / "projects" / "project"
    p.mkdir(parents=True)
    record = {
        "type": "assistant",
        "timestamp": datetime.now(UTC).isoformat(),
        "message": {
            "id": "m",
            "content": [
                {"type": "tool_use", "id": "a", "name": "Bash",
                 "input": {"command": "git status && gh pr list --repo PRIVATE_TOKEN"}},
                {"type": "tool_use", "id": "b", "name": "PowerShell",
                 "input": {"command": "git diff; Get-Content PRIVATE_SECRET"}},
            ],
        },
    }
    (p / "session.jsonl").write_text(json.dumps(record) + "\n" + json.dumps(record))
    assert main(["commands", "--root", str(tmp_path), "--json", "--no-progress"]) == 0
    output = capsys.readouterr()
    data = json.loads(output.out)
    assert data["shell_tool_calls"] == 2
    assert data["subcommands"]["git status"] == 1
    assert data["subcommands"]["gh pr"] == 1
    assert data["subcommands"]["git diff"] == 1
    assert data["executables"]["Get-Content"] == 1
    assert "PRIVATE_TOKEN" not in output.out
    assert "PRIVATE_SECRET" not in output.out
    assert output.err == ""

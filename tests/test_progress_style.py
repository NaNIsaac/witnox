from witnox.cli import main


def test_ssh_fallback(tmp_path, monkeypatch, capsys):
    project = tmp_path / ".claude" / "projects" / "demo"
    project.mkdir(parents=True)
    for index in range(25):
        (project / f"{index}.jsonl").write_text("", encoding="utf-8")
    monkeypatch.setenv("SSH_CONNECTION", "ssh-terminal")
    assert main(["report", "--root", str(tmp_path), "--progress"]) == 0
    output = capsys.readouterr()
    messages = output.err.strip().splitlines()
    assert len(messages) <= 11
    assert "100%" in messages[-1]


def test_ssh_explicit_bar(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("SSH_CONNECTION", "ssh-terminal")
    assert main(["commands", "--root", str(tmp_path), "--progress",
                 "--progress-style", "bar"]) == 0
    assert "Scanning Claude logs" in capsys.readouterr().err

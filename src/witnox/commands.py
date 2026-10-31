"""Conservative shell executable/subcommand estimates from Claude tool inputs.

This is NOT an execution trace: commands may be nested, conditional, or never run.
Skip heredocs, multiline scripts and shell control constructs to minimize false positives.
Only fixed command names and subcommand allowlists leave this module.
"""

from __future__ import annotations

import re
import shlex
from collections import Counter

EXECUTABLES = frozenset({
    "git", "gh", "uv", "uvx", "python", "python3", "pytest", "ruff",
    "grep", "rg", "sed", "cat", "ls", "tail", "head", "find", "wc",
    "curl", "node", "npm", "npx", "cargo", "herdr", "courier", "cdg",
    "witnox", "codex", "claude", "agy", "pwsh", "powershell",
    "Get-ChildItem", "Get-Content", "Set-Content", "Select-String",
    "Get-Command", "Test-Path", "Copy-Item", "Remove-Item",
    "New-Item", "Where-Object", "Select-Object",
})
SUBCOMMANDS = {
    "git": frozenset({"status", "diff", "log", "add", "commit", "push", "pull",
                      "fetch", "switch", "checkout", "branch", "stash", "show",
                      "merge", "rebase", "clone", "restore", "reset", "tag",
                      "remote", "rev-parse", "worktree", "ls-files", "grep",
                      "config", "describe", "cherry-pick"}),
    "gh": frozenset({"pr", "issue", "repo", "run", "workflow", "release", "api",
                     "auth", "extension", "search", "gist", "project"}),
    "uv": frozenset({"run", "sync", "add", "remove", "lock", "build", "publish",
                     "tool", "pip", "venv", "python", "cache", "self", "tree"}),
    "cargo": frozenset({"build", "test", "check", "clippy", "fmt", "run",
                        "install", "update", "publish"}),
    "npm": frozenset({"install", "run", "test", "ci", "exec", "view", "publish"}),
    "herdr": frozenset({"workspace", "session", "agent", "pane", "tab", "integration"}),
    "courier": frozenset({"send", "serve", "doctor", "status"}),
    "cdg": frozenset({"pack", "digest", "scan", "term", "cap", "semdiff", "tree"}),
    "witnox": frozenset({"report", "commands"}),
    "ruff": frozenset({"check", "format", "rule", "config"}),
    "gh-garden": frozenset(),
}
SKIP_PREFIX = frozenset({
    "if", "then", "else", "elif", "fi", "for", "while", "do", "done",
    "function", "def", "class", "import", "from", "return", "assert",
    "echo", "printf", "export", "set", "source", "cd", "exit",
})
SEPARATOR = re.compile(r"\s*(?:\|\||&&|[|;])\s*")
ENV_ASSIGNMENT = re.compile(r"[A-Za-z_][A-Za-z_0-9]*=.*")
WINDOWS_PATH = re.compile(r"[/\\]")
MAX_COMMAND_LENGTH = 4000


def _canonical(token: str) -> str:
    name = WINDOWS_PATH.split(token.strip('"\' '))[-1]
    if name.lower().endswith((".exe", ".cmd", ".bat")):
        name = name.rsplit(".", 1)[0]
    if name.lower() == "gh-garden":
        return "gh"
    if name.startswith(("Get-", "Set-", "Select-", "Test-", "Copy-", "Remove-", "New-", "Where-")):
        return name
    return name.lower()


def _estimate_segment(segment: str) -> tuple[str, str | None] | None:
    segment = segment.strip()
    if not segment or segment.startswith(("#", "$", "{", "}", "//")):
        return None
    try:
        tokens = shlex.split(segment, posix=True)
    except ValueError:
        return None
    while tokens and ENV_ASSIGNMENT.fullmatch(tokens[0]):
        tokens.pop(0)
    if not tokens:
        return None
    cmd = _canonical(tokens[0])
    if cmd in SKIP_PREFIX or cmd not in EXECUTABLES:
        return None
    if len(tokens) < 2:
        return cmd, None
    # Never expose arbitrary arguments, paths, flags or repository names.
    options_with_values = {"-C", "-c", "--repo", "--dir", "--cwd", "--git-dir", "-R"}
    i = 1
    while i < len(tokens):
        token = tokens[i]
        if token in options_with_values:
            i += 2
            continue
        if token.startswith("-"):
            i += 1
            continue
        candidate = token.lower()
        return cmd, candidate if candidate in SUBCOMMANDS.get(cmd, ()) else None
    return cmd, None


def parse_shell(command: str, shell: str) -> list[tuple[str, str | None]]:
    """Estimate simple shell command invocations, never emit raw command content."""
    if not isinstance(command, str) or len(command) > MAX_COMMAND_LENGTH:
        return []
    if "\n" in command or "\r" in command or "<<" in command or "@'" in command or '@"' in command:
        return []
    # Do not attempt to parse nested scripts, substitutions or complex control flow.
    if any(s in command for s in ("$(", "`", "{", "}")):
        return []
    if shell not in {"Bash", "PowerShell"}:
        return []
    found = []
    for segment in SEPARATOR.split(command):
        estimated = _estimate_segment(segment)
        if estimated:
            found.append(estimated)
    return found


def count_commands(items: list[tuple[str, str | None]]) -> dict:
    executables = Counter(exe for exe, _ in items)
    subcommands = Counter(f"{exe} {sub}" for exe, sub in items if sub)
    return {
        "recognized_invocations": len(items),
        "executables": dict(executables.most_common()),
        "subcommands": dict(subcommands.most_common()),
    }

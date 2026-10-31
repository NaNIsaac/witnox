# Witnox

**Local-first observability and behavioral analytics for AI coding agents.**

Witnox is an independent, read-only project for understanding how coding agents use tools, time and tokens. It does not require Herdr or ORC. Early builds focus on safe local aggregation of Claude Code JSONL sessions; other agents, full shell parsing, token attribution and cross-agent comparisons are planned, **not implemented yet**.

## Development status

**v0.1.0 initial release.** The supported command aggregates Claude Code tool-use counts; a conservative shell executable/subcommand estimator is available in development, but automatic monitoring is not implemented.

## Quick start

```sh
uv sync --extra dev
uv run witnox --version
uv run witnox report --days 7 --top 30
uv run witnox report --root /path/to/user-home --days 7 --json
uv run pytest -q
```

Windows PowerShell:

```powershell
uv run witnox report --root $HOME --days 7 --top 30
```

Progress is shown with tqdm when stderr is an interactive terminal. Use `--progress` to force it or `--no-progress` to suppress it. Progress is written only to stderr, so `--json` stdout remains machine-readable.

## Shell command estimates (development branch)

```powershell
uv run witnox commands --root $HOME --days 7 --top 40
uv run witnox commands --group-by executable --days 7
uv run witnox commands --days 7 --json --no-progress
```

Counts represent recognizable commands in submitted Bash/PowerShell tool inputs,
**not confirmed process executions**. Complex scripts, heredocs and unknown commands
are skipped to reduce false positives. Only allowlisted executable and subcommand names
are reported, never file paths or command arguments.

## Privacy and boundaries

- Local-first; no network requests, background services, or runtime telemetry.
- Reads `.claude*/projects/**/*.jsonl` but does not modify it.
- Only counts tool names. Does **not** save or print user prompts, raw commands, file paths, tool arguments, or tokens.
- CLI JSON contains aggregates only. Consider aggregate information potentially sensitive before sharing publicly.
- Repeated snapshots are deduplicated by tool-use ID within a file. Logs without stable identifiers may be skipped.
- No claims that a tool call equals a task, a successful result, or an actual subprocess execution.

## Roadmap

1. Validated tool-call aggregation with fixture tests.
2. Separate Claude Bash and PowerShell parser with conservative counting and measurable uncertainty.
3. Codex and Gemini adapters with documented schema and coverage limits.
4. Optional incremental local SQLite index and reproducible cross-agent efficiency comparisons.
5. Post-v0.1.0: add verified shell metrics and cross-agent comparison.

## Publishing

PyPI deployment is triggered by publishing a GitHub Release tagged exactly `v0.1.0` (matching `pyproject.toml`). The `.github/workflows/publish.yml` workflow tests with uv, builds distributions, and uploads using PyPI Trusted Publishing (OIDC). Configure the pending PyPI publisher for owner `NaNIsaac`, repository `witnox`, workflow `publish.yml`, and GitHub environment `release` (create it in the repository's Settings → Environments). The publish job references this environment. For a failed initial publication from an older release tag, use the manual `workflow_dispatch` on `main` after this change is merged; re-running an old release job would continue using the workflow stored at the old tag. No API token is required.

MIT licensed. See [LICENSE](LICENSE).

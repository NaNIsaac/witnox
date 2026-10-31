# Witnox

**Local-first observability and behavioral analytics for AI coding agents.**

Witnox is an independent, read-only project for understanding how coding agents use tools, time and tokens. It does not require Herdr or ORC. Early builds focus on safe local aggregation of Claude Code JSONL sessions; other agents, shell subcommand parsing, token attribution and cross-agent comparisons are planned, **not implemented yet**.

## Development status

**0.0.1 scaffold (pre-alpha), not a v0.1.0 release.** Initial command: aggregate tool-use counts; no command parsing or automatic monitoring yet.

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
5. `v0.1.0`: complete tested minimal CLI, build artifacts and publishing checklist; release only after owner review.

## Publishing

PyPI name availability is **not guaranteed** by search results. Before first release, verify registration, create a trusted publisher (GitHub Actions OIDC) in PyPI and test wheel/sdist and installation. No upload credential or publishing workflow is bundled in this scaffold.

MIT licensed. See [LICENSE](LICENSE).

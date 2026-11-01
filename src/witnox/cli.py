"""Witnox CLI."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from . import __version__
from .collector import collect_claude
from .providers import collect_accounts


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="witnox", description="Local-first AI agent analytics")
    parser.add_argument("--version", action="version", version=f"witnox {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)
    report = sub.add_parser("report", help="Read-only aggregate Claude Code report")
    report.add_argument("--root", type=Path, default=Path.home())
    report.add_argument("--days", type=int, default=7)
    report.add_argument("--top", type=int, default=30)
    report.add_argument("--json", action="store_true")
    group = report.add_mutually_exclusive_group()
    group.add_argument(
        "--progress",
        dest="progress",
        action="store_true",
        default=None,
        help="Always show a progress bar on stderr",
    )
    group.add_argument(
        "--no-progress",
        dest="progress",
        action="store_false",
        help="Disable progress output",
    )
    commands = sub.add_parser("commands", help="Estimate shell executables and subcommands")
    commands.add_argument("--root", type=Path, default=Path.home())
    commands.add_argument("--days", type=int, default=7)
    commands.add_argument("--top", type=int, default=30)
    commands.add_argument("--group-by", choices=["executable", "subcommand"],
                          default="subcommand")
    commands.add_argument("--json", action="store_true")
    group2 = commands.add_mutually_exclusive_group()
    group2.add_argument("--progress", dest="progress", action="store_true", default=None)
    group2.add_argument("--no-progress", dest="progress", action="store_false")
    agents = sub.add_parser("agents", help="Compare Claude stores, Codex and Gemini locally")
    agents.add_argument("--root", type=Path, default=Path.home())
    agents.add_argument("--days", type=int, default=7)
    agents.add_argument("--top", type=int, default=10)
    agents.add_argument("--json", action="store_true")
    for target in (report, commands):
        target.add_argument("--progress-style", choices=["auto", "bar", "lines"],
                            default="auto", help="Progress display mode (auto is SSH-safe)")
    args = parser.parse_args(argv)
    if args.command == "report":
        if args.days < 1 or args.top < 1:
            parser.error("--days and --top must be positive")
        result = collect_claude(args.root, days=args.days, progress=args.progress,
                                progress_style=args.progress_style)
        if args.json:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print(
                f"Claude Code | {args.days} days | "
                f"files: {result['files_scanned']} | tool calls: {result['tool_calls']}"
            )
            for name, count in list(result["tools"].items())[: args.top]:
                print(f"{name:36} {count:>8}")
            print("Read-only aggregates; no prompts, paths or command arguments emitted.")
    if args.command == "commands":
        if args.days < 1 or args.top < 1:
            parser.error("--days and --top must be positive")
        result = collect_claude(args.root, days=args.days, progress=args.progress,
                                include_commands=True, progress_style=args.progress_style)
        metrics = result["commands"]
        if args.json:
            print(json.dumps(metrics, ensure_ascii=False, indent=2))
        else:
            key = "executables" if args.group_by == "executable" else "subcommands"
            print(
                f"Claude commands | {args.days} days | "
                f"recognized: {metrics['recognized_invocations']} | "
                f"shell calls: {metrics['shell_tool_calls']}"
            )
            for name, count in list(metrics[key].items())[:args.top]:
                print(f"{name:36} {count:>8}")
            print("Conservative estimates, not executions; complex scripts may be skipped.")
    if args.command == "agents":
        if args.days < 1 or args.top < 1:
            parser.error("--days and --top must be positive")
        result = collect_accounts(args.root, days=args.days)
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(f"Witnox providers | last {args.days} days")
            for item in result["providers"]:
                print(f"{item['provider']:12} files={item['files_scanned']:>6} "
                      f"tool calls={item['tool_calls']:>8}")
            print("Claude stores (pseudonyms; not verified distinct accounts):")
            for item in result["claude_stores"]:
                print(f"  {item['store']:12} files={item['files_scanned']:>6} "
                      f"tool calls={item['tool_calls']:>8}")
            for name in ("codex", "gemini"):
                print(f"{name} tools:")
                for tool, count in list(result["details"][name]["tools"].items())[:args.top]:
                    print(f"  {tool:32} {count:>8}")
            print(result["note"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

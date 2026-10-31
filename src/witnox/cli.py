"""Witnox CLI."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from . import __version__
from .collector import collect_claude


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
    args = parser.parse_args(argv)
    if args.command == "report":
        if args.days < 1 or args.top < 1:
            parser.error("--days and --top must be positive")
        result = collect_claude(args.root, days=args.days, progress=args.progress)
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
                                include_commands=True)
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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

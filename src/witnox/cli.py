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
    args = parser.parse_args(argv)
    if args.command == "report":
        if args.days < 1 or args.top < 1:
            parser.error("--days and --top must be positive")
        result = collect_claude(args.root, days=args.days)
        if args.json:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print(
                f"Claude Code | {args.days} days | "
                f"files: {result['files_scanned']} | tool calls: {result['tool_calls']}"
            )
            for name, count in list(result["tools"].items())[:args.top]:
                print(f"{name:36} {count:>8}")
            print("Read-only aggregates; no prompts, paths or command arguments emitted.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

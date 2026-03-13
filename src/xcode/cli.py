"""CLI entry point for xcode."""

import argparse
import sys


def main() -> None:
    parser = argparse.ArgumentParser(
        description="xCode: run coding tasks with codebase knowledge graph and agents (like Claude Code)."
    )
    parser.add_argument("task", nargs="?", help="Task description for the agent")
    args = parser.parse_args()
    if not args.task:
        parser.print_help()
        sys.exit(0)
    print(f"Task: {args.task}")
    print("(xCode scaffold: full implementation in progress)")


if __name__ == "__main__":
    main()

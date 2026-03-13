"""CLI entry point for xcode."""

import argparse
import os
import sys


def main() -> None:
    parser = argparse.ArgumentParser(
        description="xCode: run coding tasks with codebase knowledge graph and agents (like Claude Code)."
    )
    parser.add_argument(
        "task",
        nargs="?",
        help="Task description for the agent",
    )
    parser.add_argument(
        "--path",
        "-p",
        type=str,
        default=os.getcwd(),
        help="Path to the repository (default: current directory)",
    )
    parser.add_argument(
        "--language",
        "-l",
        type=str,
        choices=["python", "csharp"],
        default="python",
        help="Language of the codebase (default: python)",
    )
    parser.add_argument(
        "--project-name",
        type=str,
        default=None,
        help="Project name for the knowledge graph (default: basename of --path)",
    )
    parser.add_argument(
        "--no-build-graph",
        action="store_true",
        help="Skip building/updating the knowledge graph (use existing graph)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Verbose output",
    )
    args = parser.parse_args()

    if not args.task:
        parser.print_help()
        sys.exit(0)

    project_path = os.path.abspath(args.path)
    if not os.path.isdir(project_path):
        print(f"Error: not a directory: {project_path}", file=sys.stderr)
        sys.exit(1)

    project_name = args.project_name or os.path.basename(project_path.rstrip(os.sep))

    if args.verbose:
        print(f"Task: {args.task}")
        print(f"Path: {project_path}")
        print(f"Language: {args.language}")
        print(f"Project name: {project_name}")
        print(f"Build graph: {not args.no_build_graph}")

    # Orchestration will be wired in later (ensure-graph, spawn agent)
    print(f"Task: {args.task}")
    print("(ensure-graph and agent spawn will run here)")


if __name__ == "__main__":
    main()

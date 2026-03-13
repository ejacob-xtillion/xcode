"""CLI entry point for xcode."""

import argparse
import os
import sys

from xcode.ensure_graph import ensure_knowledge_graph
from xcode.llm_config import LLMConfig, DEFAULT_OLLAMA_ENDPOINT


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
    parser.add_argument(
        "--model",
        "-m",
        type=str,
        default=None,
        help="Model name (e.g. llama3.2, gpt-4o). Default from XCODE_MODEL or cloud default.",
    )
    parser.add_argument(
        "--llm-endpoint",
        type=str,
        default=None,
        help="LLM API base URL for local inference (e.g. http://localhost:11434/v1 for Ollama). Overrides XCODE_LLM_ENDPOINT.",
    )
    parser.add_argument(
        "--local",
        action="store_true",
        help="Use local LLM (default: Ollama at http://localhost:11434/v1). Implies --llm-endpoint if not set.",
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

    # Resolve LLM config (local or cloud)
    llm_config = LLMConfig.from_env()
    if args.local:
        llm_config = LLMConfig.for_local(
            base_url=args.llm_endpoint or llm_config.base_url or DEFAULT_OLLAMA_ENDPOINT,
            model=args.model or llm_config.model or "llama3.2",
        )
    else:
        if args.llm_endpoint is not None:
            llm_config.base_url = args.llm_endpoint
        if args.model is not None:
            llm_config.model = args.model

    if args.verbose:
        print(f"Task: {args.task}")
        print(f"Path: {project_path}")
        print(f"Language: {args.language}")
        print(f"Project name: {project_name}")
        print(f"Build graph: {not args.no_build_graph}")
        print(f"LLM: model={llm_config.model}, base_url={llm_config.base_url or 'cloud'}")

    if not args.no_build_graph:
        try:
            ensure_knowledge_graph(
                project_path=project_path,
                language=args.language,
                project_name=project_name,
                keep_existing=False,
                verbose=args.verbose,
            )
        except Exception as e:
            print(f"Error building knowledge graph: {e}", file=sys.stderr)
            sys.exit(1)

    # Agent spawn will receive llm_config (base_url, model) for local or cloud
    print(f"Task: {args.task}")
    print("(agent spawn will run here)")


if __name__ == "__main__":
    main()

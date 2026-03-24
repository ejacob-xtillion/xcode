"""
xCode CLI - Main entry point

Provides a Claude Code-like experience for running AI agents with codebase knowledge graphs.
"""

import os
import sys
from pathlib import Path

import click
from dotenv import load_dotenv
from rich.console import Console
from rich.text import Text

from xcode.banner import render_compact_header
from xcode.container import create_container
from xcode.models import XCodeConfig
from xcode.requests import CLIRequestHandler, InteractiveHandler
from xcode.startup import StartupOrchestrator

# Load environment variables
load_dotenv()

console = Console()


@click.command()
@click.argument("task", required=False)
@click.option(
    "--path",
    "-p",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, resolve_path=True),
    default=os.getcwd(),
    help="Path to the repository (default: current directory)",
)
@click.option(
    "--language",
    "-l",
    type=click.Choice(["python", "csharp"], case_sensitive=False),
    default="python",
    help="Programming language of the repository",
)
@click.option(
    "--project-name",
    type=str,
    default=None,
    help="Project name for the knowledge graph (default: directory name)",
)
@click.option(
    "--no-build-graph",
    is_flag=True,
    help="Skip building the knowledge graph (assume it already exists)",
)
@click.option(
    "--model",
    type=str,
    default=None,
    help="LLM model name (e.g., gpt-4, llama3.2, codellama)",
)
@click.option(
    "--llm-endpoint",
    type=str,
    default=None,
    help="Base URL for local LLM API (e.g., http://localhost:11434 for Ollama)",
)
@click.option(
    "--local",
    is_flag=True,
    help="Use local LLM with default endpoint (Ollama at http://localhost:11434)",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Enable verbose output",
)
@click.option(
    "--no-agent-stream",
    is_flag=True,
    help="Do not print the agent's live token stream (draft reasoning) from SSE",
)
@click.option(
    "--agent-trace-recap",
    is_flag=True,
    help="After each agent task, print a chronological trace panel (tools, stream summary)",
)
@click.option(
    "--no-verify",
    is_flag=True,
    help="Skip automatic verification (tests/linters) after changes",
)
@click.option(
    "--no-test-generation",
    is_flag=True,
    help="Skip automatic test generation for untested code",
)
@click.option(
    "--max-fix-attempts",
    type=int,
    default=2,
    help="Maximum retry attempts when tests fail (default: 2)",
)
@click.option(
    "--interactive",
    "-i",
    is_flag=True,
    help="Start in interactive mode (default if no task provided)",
)
@click.version_option(version="0.1.0", prog_name="xcode")
def main(
    task: str | None,
    path: str,
    language: str,
    project_name: str | None,
    no_build_graph: bool,
    model: str | None,
    llm_endpoint: str | None,
    local: bool,
    verbose: bool,
    no_agent_stream: bool,
    agent_trace_recap: bool,
    no_verify: bool,
    no_test_generation: bool,
    max_fix_attempts: int,
    interactive: bool,
) -> None:
    """
    xCode: AI-powered coding assistant with codebase knowledge graphs.

    TASK: The coding task to accomplish (optional - if not provided, starts interactive mode)

    Examples:
        xcode                                           # Start interactive mode
        xcode -i                                        # Start interactive mode explicitly
        xcode "add type hints to all functions"        # Single-shot execution
        xcode --path /path/to/repo "fix flaky tests"   # Single-shot with custom path
        xcode --local --model llama3.2 "refactor code" # Single-shot with local LLM
    """
    try:
        use_interactive = interactive or task is None

        config = XCodeConfig(
            task=task or "",
            repo_path=Path(path),
            language=language,
            project_name=project_name,
            build_graph=not no_build_graph,
            model=model,
            llm_endpoint=llm_endpoint,
            use_local_llm=local,
            verbose=verbose,
            agent_stream_tokens=not no_agent_stream,
            agent_trace_recap=agent_trace_recap,
            verify_changes=not no_verify,
            generate_missing_tests=not no_test_generation,
            max_fix_attempts=max_fix_attempts,
        )

        if use_interactive:
            # ── Interactive mode ──────────────────────────────────────────────
            # Show startup experience with background graph building
            _llm_cfg = config.get_llm_config()
            orchestrator = StartupOrchestrator(
                project_name=config.project_name,
                repo_path=config.repo_path,
                language=config.language,
                console=console,
                verbose=verbose,
                enable_descriptions=config.xgraph_enable_descriptions,
                openai_base_url=_llm_cfg.get("base_url"),
            )
            orchestrator.start_with_welcome(build_graph=config.build_graph)
            
            # Create DI container and start interactive session
            container = create_container(config, console)
            handler = InteractiveHandler(
                config=config,
                task_service=container.task_service,
                agent_service=container.agent_service,
                console=console,
            )
            handler.run()
            sys.exit(0)

        # ── Single-shot mode ──────────────────────────────────────────────
        render_compact_header(
            console,
            task=task,
            repo_path=config.repo_path,
            model=config.model,
        )

        if verbose:
            console.print(Text("  Configuration", style="dim"))
            console.print(Text(f"    language  {config.language}", style="dim"))
            console.print(Text(f"    project   {config.project_name}", style="dim"))
            console.print(
                Text(f"    graph     {'skip' if not config.build_graph else 'build'}", style="dim")
            )
            if config.llm_endpoint:
                console.print(Text(f"    endpoint  {config.llm_endpoint}", style="dim"))
                eff = config.get_llm_config().get("base_url")
                if eff and eff != config.llm_endpoint:
                    console.print(Text(f"    openai_api {eff}", style="dim"))
            console.print()

        # Create DI container and handler
        container = create_container(config, console)
        handler = CLIRequestHandler(container)
        
        # Execute task
        result = handler.handle(
            task_description=task,
            repo_path=config.repo_path,
            language=config.language,
            project_name=config.project_name,
            build_graph=config.build_graph,
            verbose=verbose,
        )

        sys.exit(0 if result.success else 1)

    except KeyboardInterrupt:
        console.print(Text("\n  ⚠  Interrupted", style="yellow"))
        sys.exit(130)
    except Exception as e:
        console.print(Text(f"\n  ✗  {e}", style="bold red"))
        if verbose:
            console.print_exception()
        sys.exit(1)


if __name__ == "__main__":
    main()

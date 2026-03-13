"""
xCode CLI - Main entry point

Provides a Claude Code-like experience for running AI agents with codebase knowledge graphs.
"""
import os
import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.panel import Panel
from dotenv import load_dotenv

from xcode.config import XCodeConfig
from xcode.orchestrator import XCodeOrchestrator

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
    "--interactive",
    "-i",
    is_flag=True,
    help="Start in interactive mode (default if no task provided)",
)
@click.version_option(version="0.1.0", prog_name="xcode")
def main(
    task: Optional[str],
    path: str,
    language: str,
    project_name: Optional[str],
    no_build_graph: bool,
    model: Optional[str],
    llm_endpoint: Optional[str],
    local: bool,
    verbose: bool,
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
        # Determine mode: interactive if no task provided or --interactive flag
        use_interactive = interactive or task is None
        
        # Build configuration
        config = XCodeConfig(
            task=task or "",  # Empty task for interactive mode
            repo_path=Path(path),
            language=language,
            project_name=project_name,
            build_graph=not no_build_graph,
            model=model,
            llm_endpoint=llm_endpoint,
            use_local_llm=local,
            verbose=verbose,
        )
        
        if use_interactive:
            # Import here to avoid slow startup for single-shot mode
            from xcode.interactive import InteractiveSession
            
            # Build graph first if needed
            if config.build_graph:
                orchestrator = XCodeOrchestrator(config, console)
                orchestrator._ensure_knowledge_graph()
            
            # Start interactive session
            session = InteractiveSession(config, console)
            session.run()
            sys.exit(0)
        
        # Single-shot mode (existing behavior)
        if not verbose:
            console.print(
                Panel.fit(
                    "[bold cyan]xCode[/bold cyan] - AI Coding Assistant\n"
                    f"[dim]Task: {task}[/dim]",
                    border_style="cyan",
                )
            )


        if verbose:
            console.print(f"[dim]Configuration:[/dim]")
            console.print(f"  Repository: {config.repo_path}")
            console.print(f"  Language: {config.language}")
            console.print(f"  Project: {config.project_name}")
            console.print(f"  Build graph: {config.build_graph}")
            console.print(f"  Model: {config.model or 'default'}")
            if config.llm_endpoint:
                console.print(f"  LLM endpoint: {config.llm_endpoint}")
            console.print()

        # Run orchestrator
        orchestrator = XCodeOrchestrator(config, console)
        result = orchestrator.run()

        if result.success:
            console.print("\n[bold green]✓[/bold green] Task completed successfully!")
            sys.exit(0)
        else:
            console.print(f"\n[bold red]✗[/bold red] Task failed: {result.error}")
            sys.exit(1)

    except KeyboardInterrupt:
        console.print("\n[yellow]⚠[/yellow] Interrupted by user")
        sys.exit(130)
    except Exception as e:
        console.print(f"\n[bold red]Error:[/bold red] {e}")
        if verbose:
            console.print_exception()
        sys.exit(1)


if __name__ == "__main__":
    main()

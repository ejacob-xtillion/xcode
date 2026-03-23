"""
Elegant startup experience for xCode.

Shows an informative intro message that streams in while the knowledge graph builds silently in the background.
"""

import io
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.spinner import Spinner
from rich.text import Text


@dataclass
class StartupState:
    """Tracks the state of the startup process."""

    graph_building: bool = False
    graph_complete: bool = False
    graph_error: Optional[str] = None


class StartupOrchestrator:
    """
    Orchestrates the startup experience with intro message and background graph building.
    
    Shows an informative intro about xCode while silently building the knowledge graph
    in the background, providing a smooth, educational UX.
    """

    INTRO_MESSAGE = """
# Welcome to xCode! ✨

**xCode** is an AI-powered coding assistant that understands your entire codebase through knowledge graphs.

## What xCode Does

- 🔍 **Deep Code Understanding**: Analyzes your codebase structure, relationships, and dependencies
- 🤖 **Intelligent Assistance**: Provides context-aware help for coding tasks
- 🚀 **Fast Execution**: Leverages knowledge graphs for quick, accurate responses
- 💡 **Smart Suggestions**: Understands your code architecture to give better recommendations

## Getting Started

1. **Ask Questions**: Type any coding task or question about your codebase
2. **Use Commands**: Type `/help` to see available commands
3. **Interactive Mode**: You're now in interactive mode - just start typing!

## Example Tasks

- "Add error handling to the API endpoints"
- "Refactor the authentication module"
- "Find all unused imports"
- "Explain how the database layer works"

---

*Preparing your workspace...*
"""

    def __init__(
        self,
        console: Console,
        project_name: str,
        repo_path: Path,
        language: str,
        verbose: bool = False,
        enable_descriptions: bool = False,
    ):
        self.console = console
        self.project_name = project_name
        self.repo_path = repo_path
        self.language = language
        self.verbose = verbose
        self.enable_descriptions = enable_descriptions
        self.state = StartupState()
        self._build_thread: Optional[threading.Thread] = None

    def start_with_welcome(self, build_graph: bool = True) -> None:
        """
        Show intro message and build graph silently in background.
        
        Args:
            build_graph: Whether to build the knowledge graph during startup
        """
        # Show intro message first (always completes fully)
        self._show_intro_message()
        
        if build_graph:
            self.state.graph_building = True
            
            # Start graph building in background thread (silent)
            self._build_thread = threading.Thread(
                target=self._build_graph_background,
                daemon=True,
            )
            self._build_thread.start()

            # Show loading state while graph builds
            self._show_loading_state()

            if self.state.graph_error and self.verbose:
                self.console.print(
                    f"\n[dim yellow]Note: Graph build encountered an issue: {self.state.graph_error}[/dim yellow]"
                )
            elif not self.state.graph_complete and self.verbose:
                self.console.print(
                    "\n[dim yellow]Note: Graph build is continuing in the background...[/dim yellow]"
                )

    def _show_intro_message(self) -> None:
        """Show informative intro message about xCode with streaming effect."""
        # Add project context to the intro
        context = f"\n**Current Project**: {self.project_name}\n"
        context += f"**Path**: `{self.repo_path}`\n"
        context += f"**Language**: {self.language}\n"
        
        full_message = self.INTRO_MESSAGE.replace(
            "*Preparing your workspace...*",
            f"{context}\n*Preparing your workspace...*"
        )
        
        # Stream the message line by line with markdown rendering
        lines = full_message.split('\n')
        current_text = ""
        
        with Live(
            Panel(
                Markdown(""),
                border_style="bright_blue",
                padding=(1, 2),
                title="[bold cyan]xCode[/bold cyan]",
            ),
            console=self.console,
            refresh_per_second=10,
        ) as live:
            for line in lines:
                current_text += line + "\n"
                live.update(
                    Panel(
                        Markdown(current_text),
                        border_style="bright_blue",
                        padding=(1, 2),
                        title="[bold cyan]xCode[/bold cyan]",
                    )
                )
                time.sleep(0.15)  # 150ms per line for smooth streaming
        
        self.console.print()

    def _show_loading_state(self) -> None:
        """Show loading spinner while graph builds."""
        spinner = Spinner("dots", text="[cyan]Preparing your workspace...[/cyan]")
        
        with Live(spinner, console=self.console, refresh_per_second=10) as live:
            # Keep spinner alive while thread is running
            if self._build_thread:
                while self._build_thread.is_alive():
                    time.sleep(0.1)  # Check every 100ms
                    # Update spinner to keep it animated
                    live.update(spinner)
        
        # Show completion
        if self.state.graph_complete:
            self.console.print("[green]✓[/green] [dim]Workspace ready![/dim]")
        elif self.state.graph_error:
            self.console.print("[yellow]⚠[/yellow] [dim]Graph build skipped[/dim]")
        self.console.print()

    def _build_graph_background(self) -> None:
        """Build the knowledge graph silently in a background thread."""
        try:
            # Build the graph (output suppressed)
            self._build_via_subprocess()
            self.state.graph_complete = True

        except Exception as e:
            self.state.graph_error = str(e)
            if self.verbose:
                self.console.print_exception()
        finally:
            self.state.graph_building = False
    
    def _build_via_subprocess(self) -> None:
        """Build graph using subprocess with real-time progress parsing."""
        try:
            # Try library import first
            from xgraph.knowledge_graph.build_graph import build_knowledge_graph
            use_library = True
        except ImportError:
            use_library = False
        
        if use_library:
            self._build_via_library()
        else:
            self._build_via_cli()
    
    def _build_via_library(self) -> None:
        """Build using xgraph library with output suppressed."""
        from xgraph.knowledge_graph.build_graph import build_knowledge_graph
        
        # Redirect stdout/stderr to suppress all output
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        
        try:
            sys.stdout = io.StringIO()
            sys.stderr = io.StringIO()
            
            build_knowledge_graph(
                project_path=str(self.repo_path),
                language=self.language,
                project_name=self.project_name,
                enable_descriptions=self.enable_descriptions,
                keep_existing_graph=True,
                graph_db_type="neo4j",
            )
            
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr
    
    def _build_via_cli(self) -> None:
        """Build using xgraph CLI with output suppressed."""
        cmd = [
            "build-graph",
            "--project-path", str(self.repo_path),
            "--language", self.language,
            "--project-name", self.project_name,
            "--keep-existing-graph",
        ]
        
        if self.enable_descriptions:
            cmd.append("--enable-descriptions")
        
        subprocess.run(
            cmd,
            capture_output=True,  # Suppress output
            text=True,
            check=True,
        )

"""
Elegant startup experience for xCode.

Provides a seamless welcome screen while the knowledge graph builds in the background.
"""

import io
import re
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from rich.align import Align
from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.text import Text


@dataclass
class StartupState:
    """Tracks the state of the startup process."""

    graph_building: bool = False
    graph_complete: bool = False
    graph_error: Optional[str] = None
    files_processed: int = 0
    total_files: int = 0


class StartupOrchestrator:
    """
    Orchestrates the startup experience with welcome screen and background graph building.
    
    Shows a beautiful welcome screen while seamlessly building the knowledge graph
    in the background, providing a smooth UX without blocking the user.
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
        Show welcome screen and optionally build graph in background.
        
        Args:
            build_graph: Whether to build the knowledge graph during startup
        """
        if not build_graph:
            self._show_simple_welcome()
            return

        self.state.graph_building = True
        
        # Start graph building in background thread
        self._build_thread = threading.Thread(
            target=self._build_graph_background,
            daemon=True,
        )
        self._build_thread.start()

        # Show welcome screen with live progress
        self._show_welcome_with_progress()

        # Wait for graph to complete (with timeout)
        if self._build_thread:
            self._build_thread.join(timeout=300)  # 5 minute max

        if self.state.graph_error:
            self.console.print(
                Panel(
                    f"[yellow]⚠ Graph build encountered an issue:[/yellow]\n{self.state.graph_error}\n\n"
                    "[dim]You can continue, but some features may be limited.[/dim]",
                    border_style="yellow",
                )
            )
        elif not self.state.graph_complete:
            self.console.print(
                Panel(
                    "[yellow]⚠ Graph build is taking longer than expected.[/yellow]\n\n"
                    "[dim]Continuing in the background...[/dim]",
                    border_style="yellow",
                )
            )

    def _show_simple_welcome(self) -> None:
        """Show simple welcome without graph building."""
        welcome_text = Text()
        welcome_text.append("✨ Welcome to ", style="bold cyan")
        welcome_text.append("xCode", style="bold magenta")
        welcome_text.append(" ✨\n\n", style="bold cyan")
        welcome_text.append(f"Project: ", style="dim")
        welcome_text.append(f"{self.project_name}\n", style="cyan")
        welcome_text.append(f"Path: ", style="dim")
        welcome_text.append(f"{self.repo_path}\n", style="cyan")
        welcome_text.append(f"Language: ", style="dim")
        welcome_text.append(f"{self.language}\n\n", style="cyan")
        welcome_text.append("Type ", style="dim")
        welcome_text.append("/help", style="bold")
        welcome_text.append(" for commands or start coding!\n", style="dim")

        self.console.print(
            Panel(
                Align.center(welcome_text),
                border_style="bright_blue",
                padding=(1, 2),
            )
        )
        self.console.print()

    def _show_welcome_with_progress(self) -> None:
        """Show welcome screen with live progress updates."""
        layout = Layout()
        layout.split_column(
            Layout(name="welcome", size=10),
            Layout(name="progress", size=5),
        )

        # Welcome section
        welcome_text = Text()
        welcome_text.append("✨ Welcome to ", style="bold cyan")
        welcome_text.append("xCode", style="bold magenta")
        welcome_text.append(" ✨\n\n", style="bold cyan")
        welcome_text.append(f"Project: ", style="dim")
        welcome_text.append(f"{self.project_name}\n", style="cyan")
        welcome_text.append(f"Path: ", style="dim")
        welcome_text.append(f"{self.repo_path}\n", style="cyan")
        welcome_text.append(f"Language: ", style="dim")
        welcome_text.append(f"{self.language}\n\n", style="cyan")
        welcome_text.append("Preparing your workspace...", style="dim italic")

        layout["welcome"].update(
            Panel(
                Align.center(welcome_text),
                border_style="bright_blue",
                padding=(1, 2),
            )
        )

        # Progress section
        progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(complete_style="cyan", finished_style="green"),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=self.console,
        )
        
        task_id = progress.add_task(
            f"Indexing codebase ({self.state.files_processed}/{self.state.total_files} files)...",
            total=100,
        )

        layout["progress"].update(
            Panel(
                progress,
                border_style="dim",
                padding=(0, 1),
            )
        )

        # Live update loop - keep running until build completes or times out
        with Live(layout, console=self.console, refresh_per_second=4):
            max_wait = 300  # 5 minutes
            elapsed = 0
            
            while elapsed < max_wait:
                # Update progress if we have file counts
                if self.state.total_files > 0:
                    percentage = (self.state.files_processed / self.state.total_files) * 100
                    progress.update(
                        task_id,
                        completed=percentage,
                        description=f"Indexing codebase ({self.state.files_processed}/{self.state.total_files} files)...",
                    )
                
                if self.state.graph_error:
                    progress.update(task_id, description="[yellow]Graph build encountered issues[/yellow]")
                    time.sleep(1)  # Show error briefly
                    break
                
                if self.state.graph_complete:
                    progress.update(
                        task_id,
                        completed=100,
                        description="[green]✓ Knowledge graph ready![/green]",
                    )
                    time.sleep(0.5)  # Show completion briefly
                    break
                
                time.sleep(0.25)
                elapsed += 0.25

        self.console.print()

    def _build_graph_background(self) -> None:
        """Build the knowledge graph in a background thread."""
        try:
            # Estimate total files for progress tracking
            self.state.total_files = self._estimate_file_count()
            
            # Simulate progress during build (since we can't get real-time updates from xgraph)
            # We'll update the counter smoothly to give visual feedback
            import threading
            
            def simulate_progress():
                """Smoothly increment progress while build is running."""
                while not self.state.graph_complete and not self.state.graph_error:
                    if self.state.files_processed < self.state.total_files:
                        # Increment slowly to show activity
                        self.state.files_processed = min(
                            self.state.files_processed + 1,
                            self.state.total_files - 1  # Leave last file for actual completion
                        )
                    time.sleep(0.5)  # Update every 0.5 seconds
            
            progress_thread = threading.Thread(target=simulate_progress, daemon=True)
            progress_thread.start()
            
            # Use subprocess to capture and parse xgraph output
            self._build_via_subprocess()

            self.state.graph_complete = True
            self.state.files_processed = self.state.total_files

        except Exception as e:
            self.state.graph_error = str(e)
            if self.verbose:
                # Restore console for error printing
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
        """Build using xgraph library with output capture and progress tracking."""
        from xgraph.knowledge_graph.build_graph import build_knowledge_graph
        
        # Redirect stdout/stderr to capture progress
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        
        # Use a custom StringIO that updates progress as it writes
        class ProgressCapture(io.StringIO):
            def __init__(self, parent):
                super().__init__()
                self.parent = parent
                self.buffer = ""
            
            def write(self, s):
                super().write(s)
                self.buffer += s
                # Parse progress from the buffer
                self.parent._parse_progress_incremental(self.buffer)
                return len(s)
        
        captured_output = ProgressCapture(self)
        
        try:
            sys.stdout = captured_output
            sys.stderr = captured_output
            
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
        """Build using xgraph CLI."""
        cmd = [
            "build-graph",
            "--project-path", str(self.repo_path),
            "--language", self.language,
            "--project-name", self.project_name,
            "--keep-existing-graph",
        ]
        
        if self.enable_descriptions:
            cmd.append("--enable-descriptions")
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
        )
        
        if self.verbose and result.stdout:
            self._parse_progress(result.stdout)
    
    def _parse_progress(self, output: str) -> None:
        """Parse xgraph output to update progress."""
        # Look for processed file count
        matches = re.findall(r'processed=(\d+)', output)
        if matches:
            self.state.files_processed = int(matches[-1])
    
    def _parse_progress_incremental(self, output: str) -> None:
        """Parse xgraph output incrementally to update progress in real-time."""
        # Look for the most recent processed count
        matches = re.findall(r'processed=(\d+)', output)
        if matches:
            processed = int(matches[-1])
            if processed > self.state.files_processed:
                self.state.files_processed = processed

    def _estimate_file_count(self) -> int:
        """Estimate the number of files to process."""
        try:
            extensions = {".py", ".cs"} if self.language == "csharp" else {".py"}
            count = sum(
                1
                for ext in extensions
                for _ in self.repo_path.rglob(f"*{ext}")
                if not any(
                    part.startswith(".")
                    or part in {"__pycache__", "node_modules", "venv", ".venv", "bin", "obj"}
                    for part in _.parts
                )
            )
            return max(count, 1)  # At least 1 to avoid division by zero
        except Exception:
            return 50  # Reasonable default

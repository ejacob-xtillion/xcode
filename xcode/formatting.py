"""
Rich formatting utilities for xCode CLI output.

Provides consistent, beautiful formatting for various output types including:
- Task summaries
- Refactoring reports
- Verification results
- Error messages
- Progress indicators
"""

from pathlib import Path
from typing import Any

from rich import box
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text
from rich.tree import Tree


class OutputFormatter:
    """Centralized formatter for all CLI output."""

    def __init__(self, console: Console):
        self.console = console

    def section_header(self, title: str, style: str = "bold cyan") -> None:
        """Print a section header with separator."""
        self.console.print(f"\n[{style}]{title}[/{style}]")
        self.console.print(Text("─" * 60, style="bright_black"))

    def subsection(self, title: str, style: str = "bold") -> None:
        """Print a subsection header."""
        self.console.print(f"\n[{style}]• {title}[/{style}]")

    def bullet(self, text: str, indent: int = 2, style: str = "") -> None:
        """Print a bullet point with optional indentation."""
        prefix = " " * indent
        if style:
            self.console.print(f"{prefix}• [{style}]{text}[/{style}]")
        else:
            self.console.print(f"{prefix}• {text}")

    def nested_bullet(self, text: str, indent: int = 4, style: str = "dim") -> None:
        """Print a nested bullet point."""
        prefix = " " * indent
        if style:
            self.console.print(f"{prefix}├─ [{style}]{text}[/{style}]")
        else:
            self.console.print(f"{prefix}├─ {text}")

    def key_value(self, key: str, value: str, indent: int = 4, key_style: str = "cyan") -> None:
        """Print a key-value pair."""
        prefix = " " * indent
        self.console.print(f"{prefix}[{key_style}]{key}[/{key_style}]  {value}")

    def success(self, message: str, prefix: str = "✓") -> None:
        """Print a success message."""
        self.console.print(f"[green]{prefix} {message}[/green]")

    def warning(self, message: str, prefix: str = "⚠") -> None:
        """Print a warning message."""
        self.console.print(f"[yellow]{prefix} {message}[/yellow]")

    def error(self, message: str, prefix: str = "✗") -> None:
        """Print an error message."""
        self.console.print(f"[red]{prefix} {message}[/red]")

    def info(self, message: str, prefix: str = "ℹ") -> None:
        """Print an info message."""
        self.console.print(f"[blue]{prefix} {message}[/blue]")

    def code_block(
        self,
        code: str,
        language: str = "python",
        title: str | None = None,
        line_numbers: bool = False,
    ) -> None:
        """Print a syntax-highlighted code block."""
        syntax = Syntax(code, language, theme="monokai", line_numbers=line_numbers)
        if title:
            self.console.print(Panel(syntax, title=f"[bold]{title}[/bold]", border_style="blue"))
        else:
            self.console.print(syntax)

    def panel(
        self,
        content: str | Text,
        title: str | None = None,
        border_style: str = "blue",
        padding: tuple[int, int] = (1, 2),
    ) -> None:
        """Print content in a panel."""
        self.console.print(
            Panel(
                content,
                title=f"[bold]{title}[/bold]" if title else None,
                border_style=border_style,
                padding=padding,
                box=box.ROUNDED,
            )
        )

    def table(
        self,
        title: str | None = None,
        headers: list[str] | None = None,
        rows: list[list[str]] | None = None,
        show_header: bool = True,
    ) -> Table:
        """Create and return a Rich table (call console.print to display)."""
        table = Table(
            title=title,
            box=box.ROUNDED,
            border_style="bright_black",
            show_header=show_header,
            padding=(0, 1),
        )

        if headers:
            for header in headers:
                table.add_column(header, style="bold cyan")

        if rows:
            for row in rows:
                table.add_row(*row)

        return table

    def file_tree(self, files: list[str | Path], title: str = "Modified Files") -> None:
        """Display a tree of files grouped by directory."""
        tree = Tree(f"[bold cyan]{title}[/bold cyan]")

        # Group files by directory
        dirs: dict[str, list[str]] = {}
        for file in files:
            file_path = Path(file)
            dir_name = str(file_path.parent) if file_path.parent != Path(".") else "."
            if dir_name not in dirs:
                dirs[dir_name] = []
            dirs[dir_name].append(file_path.name)

        # Build tree
        for dir_name, file_names in sorted(dirs.items()):
            if dir_name == ".":
                for file_name in sorted(file_names):
                    tree.add(f"[yellow]{file_name}[/yellow]")
            else:
                dir_branch = tree.add(f"[blue]{dir_name}/[/blue]")
                for file_name in sorted(file_names):
                    dir_branch.add(f"[yellow]{file_name}[/yellow]")

        self.console.print(tree)

    def separator(self, char: str = "─", length: int = 60, style: str = "bright_black") -> None:
        """Print a separator line."""
        self.console.print(Text(char * length, style=style))

    def markdown(self, content: str) -> None:
        """Render markdown content."""
        md = Markdown(content)
        self.console.print(md)


class RefactoringFormatter(OutputFormatter):
    """Specialized formatter for refactoring summaries."""

    def print_refactoring_summary(
        self,
        title: str,
        changes: dict[str, list[str]],
        usage_guide: dict[str, Any] | None = None,
        example_code: str | None = None,
        notes: list[dict[str, str]] | None = None,
        verification: dict[str, Any] | None = None,
        modified_files: list[str] | None = None,
    ) -> None:
        """
        Print a comprehensive refactoring summary.

        Args:
            title: Main title of the refactoring
            changes: Dict mapping file names to list of change descriptions
            usage_guide: Optional usage guide with 'title' and 'steps' keys
            example_code: Optional example code snippet
            notes: Optional list of notes with 'type' ('warning', 'info', 'success') and 'message'
            verification: Optional verification results with 'passed', 'duration', 'details'
            modified_files: Optional list of modified file paths
        """
        # Header
        self.console.print()
        self.panel(
            Text(title, style="bold white", justify="center"),
            border_style="cyan",
            padding=(1, 4),
        )

        # What Changed
        self.section_header("What I changed")
        for file_name, change_list in changes.items():
            self.subsection(file_name)
            for change in change_list:
                if change.startswith("  "):
                    # Nested item
                    self.nested_bullet(change.strip())
                else:
                    self.bullet(change)

        # Usage Guide
        if usage_guide:
            self.section_header(usage_guide.get("title", "How to use"))
            for step in usage_guide.get("steps", []):
                self.bullet(step)

        # Example Code
        if example_code:
            self.console.print()
            self.code_block(example_code, language="python", title="Example")

        # Notes
        if notes:
            for note in notes:
                note_type = note.get("type", "info")
                message = note.get("message", "")
                title = note.get("title", "")

                self.console.print()
                if note_type == "warning":
                    self.warning(f"{title}: {message}" if title else message)
                elif note_type == "success":
                    self.success(f"{title}: {message}" if title else message)
                elif note_type == "error":
                    self.error(f"{title}: {message}" if title else message)
                else:
                    self.info(f"{title}: {message}" if title else message)

        # Verification
        if verification:
            self.section_header("Verification")
            passed = verification.get("passed", 0)
            duration = verification.get("duration", "")
            details = verification.get("details", [])

            if passed > 0:
                self.success("Ran the full test suite after the refactor:")
                self.bullet(
                    f"[green]{passed} passed in {duration}[/green]", indent=4
                )

            for detail in details:
                self.bullet(detail, indent=4, style="dim")

        # Modified Files
        if modified_files:
            self.section_header("Files modified")
            self.file_tree(modified_files)

        self.console.print()


class TaskFormatter(OutputFormatter):
    """Specialized formatter for task execution output."""

    def print_task_start(self, task: str, repo_path: Path, model: str | None = None) -> None:
        """Print task start banner."""
        self.section_header("Task", style="bold cyan")
        self.console.print(f"  [bold]{task}[/bold]")
        self.console.print()
        self.key_value("Repository", str(repo_path), indent=2, key_style="dim")
        if model:
            self.key_value("Model", model, indent=2, key_style="dim")
        self.console.print()

    def print_task_complete(
        self,
        success: bool,
        duration: str | None = None,
        iterations: int | None = None,
        modified_files: list[str] | None = None,
    ) -> None:
        """Print task completion summary."""
        self.console.print()
        self.separator("━", length=60, style="cyan")

        if success:
            self.success("Task completed successfully")
        else:
            self.error("Task failed")

        if duration:
            self.key_value("Duration", duration, indent=2, key_style="dim")
        if iterations is not None:
            self.key_value("Iterations", str(iterations), indent=2, key_style="dim")

        if modified_files:
            self.console.print()
            self.file_tree(modified_files, title="Modified Files")

        self.console.print()


class VerificationFormatter(OutputFormatter):
    """Specialized formatter for verification output."""

    def print_verification_start(self) -> None:
        """Print verification start message."""
        self.section_header("Running verification", style="bold cyan")

    def print_test_discovery(
        self, related_tests: int, untested_callables: int, modified_files: list[str]
    ) -> None:
        """Print test discovery results."""
        files_str = ", ".join(modified_files)
        self.console.print(f"[dim]Modified files: {files_str}[/dim]")
        self.console.print(
            f"[dim]Found {related_tests} related tests, "
            f"{untested_callables} untested callables[/dim]"
        )

    def print_test_generation(self, count: int) -> None:
        """Print test generation message."""
        self.info(f"Generating tests for {count} untested callables...")

    def print_verification_result(
        self,
        success: bool,
        checks_run: list[str],
        output: str | None = None,
        fix_attempts: int = 0,
    ) -> None:
        """Print verification result."""
        self.console.print()

        if success:
            self.success("Verification passed")
        else:
            if fix_attempts > 0:
                self.error(f"Verification failed after {fix_attempts} fix attempts")
            else:
                self.error("Verification failed")

        if checks_run:
            self.console.print(f"[dim]Checks run: {', '.join(checks_run)}[/dim]")

        if output and not success:
            self.console.print()
            self.panel(output, title="Verification Output", border_style="red")


class ErrorFormatter(OutputFormatter):
    """Specialized formatter for error messages."""

    def print_error(
        self,
        error: str | Exception,
        context: str | None = None,
        suggestions: list[str] | None = None,
        verbose: bool = False,
    ) -> None:
        """Print a formatted error message with optional context and suggestions."""
        self.console.print()
        self.error(f"Error: {error}")

        if context:
            self.console.print(f"[dim]{context}[/dim]")

        if suggestions:
            self.console.print()
            self.console.print("[bold yellow]Suggestions:[/bold yellow]")
            for suggestion in suggestions:
                self.bullet(suggestion, style="yellow")

        if verbose and isinstance(error, Exception):
            self.console.print()
            self.console.print_exception()


def normalize_agent_markdown(text: str) -> str:
    """
    Light cleanup so model prose renders better as Rich Markdown:
    - Turn Unicode bullet lines into '-' list items (inside fenced blocks unchanged).
    """
    lines = text.splitlines()
    out: list[str] = []
    in_fence = False
    for line in lines:
        stripped_left = line.lstrip()
        if stripped_left.startswith("```"):
            in_fence = not in_fence
            out.append(line)
            continue
        if not in_fence and stripped_left.startswith(("•", "\u2022")):
            indent = line[: len(line) - len(stripped_left)]
            rest = stripped_left[1:].lstrip()
            out.append(f"{indent}- {rest}")
        else:
            out.append(line)
    return "\n".join(out)


def final_answer_panel(content: str, console: Console) -> Panel:
    """
    Build a Panel around Markdown so answers wrap (max width on wide terminals).
    expand=False avoids stretching the border to the full console with empty padding.
    """
    term_w = console.size.width or 80
    if term_w < 1:
        term_w = 80
    panel_width = min(term_w, 102)
    md_source = normalize_agent_markdown(content.strip())
    body = Markdown(
        md_source,
        code_theme="default",
        hyperlinks=True,
    )
    return Panel(
        body,
        box=box.ROUNDED,
        title="[bold green]Final answer[/bold green]",
        title_align="left",
        border_style="green",
        width=panel_width,
        padding=(1, 2),
        expand=False,
    )


def print_final_answer(console: Console, content: str) -> None:
    """Print an agent final answer with Markdown rendering and bounded width."""
    if not content or not content.strip():
        return
    console.print()
    console.print(final_answer_panel(content, console))
    console.print()


# Convenience function for creating formatters
def create_formatter(
    console: Console, formatter_type: str = "default"
) -> OutputFormatter:
    """
    Create a formatter instance.

    Args:
        console: Rich console instance
        formatter_type: Type of formatter
            ('default', 'refactoring', 'task', 'verification', 'error')

    Returns:
        Appropriate formatter instance
    """
    formatters = {
        "default": OutputFormatter,
        "refactoring": RefactoringFormatter,
        "task": TaskFormatter,
        "verification": VerificationFormatter,
        "error": ErrorFormatter,
    }

    formatter_class = formatters.get(formatter_type, OutputFormatter)
    return formatter_class(console)

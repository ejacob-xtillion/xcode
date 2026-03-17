"""
xCode welcome banner — pixel art logo rendered with Rich.
"""

from pathlib import Path

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

VERSION = "0.1.0"

# 5×5 pixel font — each string is one row (top → bottom)
_PIXEL: dict[str, list[str]] = {
    "x": ["█   █", " █ █ ", "  █  ", " █ █ ", "█   █"],
    "C": [" ████", "█    ", "█    ", "█    ", " ████"],
    "o": [" ███ ", "█   █", "█   █", "█   █", " ███ "],
    "d": ["   ██", "  █ █", " █  █", " █  █", "  ███"],
    "e": [" ███ ", "█   █", "█████", "█    ", " ████"],
}

# "x" → warm amber, "Code" → cool cyan
_WORD = ["x", "C", "o", "d", "e"]
_COLORS = ["yellow", "bright_cyan", "bright_cyan", "bright_cyan", "bright_cyan"]


def _build_logo() -> Text:
    """Assemble the 5-row pixel-art logo as a Rich Text block."""
    logo = Text()
    for row in range(5):
        for i, (ch, color) in enumerate(zip(_WORD, _COLORS)):
            if i > 0:
                logo.append("  ")
            logo.append(_PIXEL[ch][row], style=f"bold {color}")
        logo.append("\n")
    return logo


def render_banner(
    console: Console,
    *,
    repo_path: Path | None = None,
    model: str | None = None,
) -> None:
    """Print the full xCode welcome banner (interactive startup)."""
    logo = _build_logo()

    meta = Text("\n")
    meta.append(f"  v{VERSION}", style="dim")
    meta.append("  ·  ", style="dim")
    meta.append("AI coding assistant with codebase knowledge graphs", style="dim italic")

    if repo_path or model:
        meta.append("\n")
        if repo_path:
            meta.append("  repo   ", style="dim")
            meta.append(str(repo_path), style="cyan")
        if model:
            meta.append("   model  " if repo_path else "  model  ", style="dim")
            meta.append(model, style="cyan")

    content = Text()
    content.append_text(logo)
    content.append_text(meta)

    console.print(
        Panel(
            content,
            box=box.ROUNDED,
            border_style="bright_black",
            padding=(1, 3),
        )
    )

    # Keyboard hint bar
    hints = Text("  ")
    pairs = [
        ("/help", "commands"),
        ("ctrl+r", "history search"),
        ("ctrl+c", "interrupt"),
        ("ctrl+d", "exit"),
    ]
    for i, (key, label) in enumerate(pairs):
        if i > 0:
            hints.append("  ·  ", style="dim")
        hints.append(key, style="bold cyan")
        hints.append(f" {label}", style="dim")
    console.print(hints)
    console.print()


def render_compact_header(
    console: Console,
    *,
    task: str,
    repo_path: Path | None = None,
    model: str | None = None,
) -> None:
    """Print a compact single-line header for single-shot mode."""
    line = Text()
    line.append(" xCode ", style="bold cyan reverse")
    line.append(f"  v{VERSION}", style="dim")

    if repo_path:
        line.append("  ·  ", style="dim")
        line.append(str(repo_path), style="dim cyan")
    if model:
        line.append("  ·  ", style="dim")
        line.append(model, style="dim cyan")

    console.print(line)
    console.print(Text("─" * 60, style="bright_black"))

    task_line = Text()
    task_line.append("  ◆ ", style="bold cyan")
    task_line.append(task, style="bold")
    console.print(task_line)
    console.print()


def render_help_table(console: Console) -> None:
    """Print the commands + shortcuts reference table."""
    table = Table(
        box=box.ROUNDED,
        border_style="bright_black",
        show_header=False,
        padding=(0, 2),
        expand=False,
    )
    table.add_column(style="bold cyan", no_wrap=True)
    table.add_column(style="dim")

    table.add_row("[bold dim]Commands[/bold dim]", "")
    table.add_row("/help", "Show this help")
    table.add_row("/clear", "Clear history and screen")
    table.add_row("/history", "Show conversation history")
    table.add_row("/status", "Show current configuration")
    table.add_row("/model", "Switch model  · /model gpt-4")
    table.add_row("/verbose", "Toggle verbose output")
    table.add_row("/exit", "Exit xCode")
    table.add_row("", "")
    table.add_row("[bold dim]Shortcuts[/bold dim]", "")
    table.add_row("ctrl+r", "Search command history")
    table.add_row("ctrl+c", "Interrupt current task")
    table.add_row("ctrl+d", "Exit")
    table.add_row("\\ + enter", "Multi-line input")

    console.print(table)
    console.print()

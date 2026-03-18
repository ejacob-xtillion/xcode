"""
Interactive session manager for xCode — Claude Code-style REPL experience.
"""

import asyncio
from pathlib import Path

from prompt_toolkit import PromptSession
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.history import FileHistory
from prompt_toolkit.styles import Style
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from xcode.agent_runner import AgentRunner
from xcode.banner import render_banner, render_help_table
from xcode.domain.models import XCodeConfig

# Slash commands available for tab-completion
_COMMANDS = [
    "/help",
    "/clear",
    "/exit",
    "/quit",
    "/history",
    "/status",
    "/model",
    "/verbose",
]


class InteractiveSession:
    """Manages an interactive xCode session with conversation history."""

    def __init__(self, config: XCodeConfig, console: Console):
        self.config = config
        self.console = console
        self.conversation_history: list[dict] = []
        self.session_active = True

        history_file = Path.home() / ".xcode" / "history.txt"
        history_file.parent.mkdir(parents=True, exist_ok=True)

        self.prompt_session = PromptSession(
            history=FileHistory(str(history_file)),
            auto_suggest=AutoSuggestFromHistory(),
            completer=WordCompleter(_COMMANDS, ignore_case=True),
            style=Style.from_dict(
                {
                    "prompt": "ansicyan bold",
                    "": "ansiwhite",
                }
            ),
            multiline=False,
            enable_history_search=True,
        )

        self.agent_runner = AgentRunner(config, console)

    # ── Lifecycle ────────────────────────────────────────────────────────────

    def run(self) -> None:
        """Run the interactive session loop."""
        # Banner is now shown by StartupOrchestrator during graph build
        # Only show it here if we're resuming or if graph wasn't built
        
        while self.session_active:
            try:
                user_input = self.prompt_session.prompt(
                    [("class:prompt", "> ")],
                    multiline=False,
                )

                if not user_input.strip():
                    continue

                self._handle_input(user_input.strip())

            except KeyboardInterrupt:
                self.console.print(Text("\n  ctrl+d to exit  ·  /help for commands", style="dim"))
            except EOFError:
                self._handle_exit()
                break
            except Exception as e:
                self.console.print(Text(f"  ✗  {e}", style="red"))
                if self.config.verbose:
                    self.console.print_exception()

    # ── Input routing ────────────────────────────────────────────────────────

    def _handle_input(self, user_input: str) -> None:
        """Route input to command handler or task executor."""
        if user_input.startswith("/"):
            self._handle_command(user_input)
            return

        if user_input.endswith("\\"):
            user_input = self._get_multiline_input(user_input[:-1])

        self.conversation_history.append({"role": "user", "content": user_input})
        self._execute_task(user_input)

    def _get_multiline_input(self, initial: str) -> str:
        """Collect continuation lines until the user submits an empty line."""
        lines = [initial]
        self.console.print(Text("  multi-line · empty line to finish", style="dim"))
        while True:
            try:
                line = self.prompt_session.prompt([("class:prompt", "… ")], multiline=False)
                if not line.strip():
                    break
                lines.append(line)
            except (KeyboardInterrupt, EOFError):
                break
        return "\n".join(lines)

    # ── Slash commands ───────────────────────────────────────────────────────

    def _handle_command(self, command: str) -> None:
        parts = command.split(maxsplit=1)
        cmd = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        dispatch = {
            "/exit": lambda: self._handle_exit(),
            "/quit": lambda: self._handle_exit(),
            "/help": lambda: render_help_table(self.console),
            "/clear": lambda: self._handle_clear(),
            "/history": lambda: self._handle_history(),
            "/status": lambda: self._handle_status(),
            "/model": lambda: self._handle_model(args),
            "/verbose": lambda: self._handle_verbose(),
        }

        handler = dispatch.get(cmd)
        if handler:
            handler()
        else:
            self.console.print(Text(f"  Unknown command: {cmd}", style="red"))
            self.console.print(Text("  /help for available commands", style="dim"))

    def _handle_exit(self) -> None:
        self.console.print(Text("\n  Bye!\n", style="dim cyan"))
        self.session_active = False

    def _handle_clear(self) -> None:
        self.conversation_history.clear()
        self.console.clear()
        render_banner(
            self.console,
            repo_path=self.config.repo_path,
            model=self.config.model,
        )

    def _handle_history(self) -> None:
        if not self.conversation_history:
            self.console.print(Text("  No history yet", style="dim"))
            return

        lines = Text()
        user_msgs = [m for m in self.conversation_history if m["role"] == "user"]
        for i, msg in enumerate(user_msgs, 1):
            snippet = msg["content"]
            if len(snippet) > 80:
                snippet = snippet[:77] + "…"
            lines.append(f"  {i:>2}  ", style="dim")
            lines.append(snippet)
            lines.append("\n")

        self.console.print(
            Panel(
                lines,
                title="[bold]History[/bold]",
                border_style="bright_black",
                box=box.ROUNDED,
                padding=(0, 1),
            )
        )

    def _handle_status(self) -> None:
        lines = Text()
        fields = [
            ("repo", str(self.config.repo_path)),
            ("project", self.config.project_name),
            ("language", self.config.language),
            ("model", self.config.model or "default"),
            ("verbose", str(self.config.verbose)),
        ]
        for key, val in fields:
            lines.append(f"  {key:<10}", style="dim")
            lines.append(f"{val}\n", style="cyan")

        self.console.print(
            Panel(
                lines,
                title="[bold]Status[/bold]",
                border_style="bright_black",
                box=box.ROUNDED,
                padding=(0, 1),
            )
        )

    def _handle_model(self, model_name: str) -> None:
        if not model_name:
            self.console.print(
                Text(f"  current model  {self.config.model or 'default'}", style="dim")
            )
            self.console.print(Text("  usage: /model gpt-4", style="dim"))
            return
        self.config.model = model_name
        self.console.print(Text(f"  ✓  model → {model_name}", style="green"))

    def _handle_verbose(self) -> None:
        self.config.verbose = not self.config.verbose
        state = "on" if self.config.verbose else "off"
        self.console.print(Text(f"  ✓  verbose {state}", style="green"))

    # ── Task execution ───────────────────────────────────────────────────────

    def _execute_task(self, task: str) -> None:
        self.console.print()
        self.config.task = task

        result = asyncio.run(
            self.agent_runner._run_agent_async(conversation_context=self._build_context())
        )

        role_entry = (
            {"role": "assistant", "content": "Task completed successfully", "logs": result.logs}
            if result.success
            else {"role": "assistant", "content": f"Error: {result.error}"}
        )
        self.conversation_history.append(role_entry)
        self.console.print()

    def _build_context(self) -> str:
        """Summarise the last 5 exchanges for the agent."""
        if not self.conversation_history:
            return ""
        parts = ["## Previous Conversation\n"]
        for msg in self.conversation_history[-5:]:
            parts.append(f"**{msg['role'].title()}:** {msg['content']}\n")
        return "\n".join(parts)

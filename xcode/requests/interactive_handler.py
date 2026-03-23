"""
Interactive request handler for xCode.

Handles interactive REPL sessions following the RCSR pattern:
- Request: Parse user input from interactive prompt
- Command: Create and execute commands based on input
- Service: Commands orchestrate services
- Repository: Services use repositories for external operations
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

from xcode.banner import render_banner, render_help_table
from xcode.domain.models import Task, XCodeConfig
from xcode.schema import get_schema
from xcode.services.agent_service import AgentService
from xcode.services.task_service import TaskService

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
    "/trace",
]


class InteractiveHandler:
    """Handles interactive REPL session requests."""

    def __init__(
        self,
        config: XCodeConfig,
        task_service: TaskService,
        agent_service: AgentService,
        console: Console,
    ):
        """
        Initialize interactive handler.

        Args:
            config: xCode configuration
            task_service: Service for task operations
            agent_service: Service for agent execution
            console: Rich console for output
        """
        self.config = config
        self.task_service = task_service
        self.agent_service = agent_service
        self.console = console
        self.conversation_history: list[dict] = []
        self.session_active = True

        # Set up prompt session with history and completion
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

    # ── Lifecycle ────────────────────────────────────────────────────────────

    def run(self) -> None:
        """
        Run the interactive session loop.

        This is the main entry point for interactive mode.
        Handles user input, commands, and task execution.
        """
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
                self.console.print(
                    Text("\n  ctrl+d to exit  ·  /help for commands", style="dim")
                )
            except EOFError:
                self._handle_exit()
                break
            except Exception as e:
                self.console.print(Text(f"  ✗  {e}", style="red"))
                if self.config.verbose:
                    self.console.print_exception()

    # ── Input routing ────────────────────────────────────────────────────────

    def _handle_input(self, user_input: str) -> None:
        """
        Route input to command handler or task executor.

        Args:
            user_input: User's input string
        """
        # Handle slash commands
        if user_input.startswith("/"):
            self._handle_command(user_input)
            return

        # Handle multiline input (ending with backslash)
        if user_input.endswith("\\"):
            user_input = self._get_multiline_input(user_input[:-1])

        # Validate task
        is_valid, error_msg = self.task_service.validate_task(user_input)
        if not is_valid:
            self.console.print(Text(f"  ✗  {error_msg}", style="red"))
            return

        # Add to conversation history
        self.conversation_history.append({"role": "user", "content": user_input})

        # Execute task
        self._execute_task(user_input)

    def _get_multiline_input(self, initial: str) -> str:
        """
        Collect continuation lines until the user submits an empty line.

        Args:
            initial: Initial line of input

        Returns:
            Complete multiline input string
        """
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
        """
        Handle slash commands.

        Args:
            command: The command string (starting with /)
        """
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
            "/trace": lambda: self._handle_trace_recap(),
        }

        handler = dispatch.get(cmd)
        if handler:
            handler()
        else:
            self.console.print(Text(f"  Unknown command: {cmd}", style="red"))
            self.console.print(Text("  /help for available commands", style="dim"))

    def _handle_exit(self) -> None:
        """Handle exit command."""
        self.console.print(Text("\n  Bye!\n", style="dim cyan"))
        self.session_active = False

    def _handle_clear(self) -> None:
        """Handle clear command - clear history and screen."""
        self.conversation_history.clear()
        self.console.clear()
        render_banner(
            self.console,
            repo_path=self.config.repo_path,
            model=self.config.model,
        )

    def _handle_history(self) -> None:
        """Handle history command - show conversation history."""
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
        """Handle status command - show current configuration."""
        lines = Text()
        fields = [
            ("repo", str(self.config.repo_path)),
            ("project", self.config.project_name),
            ("language", self.config.language),
            ("model", self.config.model or "default"),
            ("verbose", str(self.config.verbose)),
            ("agent_stream", str(self.config.agent_stream_tokens)),
            ("trace_recap", str(self.config.agent_trace_recap)),
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
        """
        Handle model command - change the active model.

        Args:
            model_name: Name of the model to switch to
        """
        if not model_name:
            self.console.print(
                Text(f"  current model  {self.config.model or 'default'}", style="dim")
            )
            self.console.print(Text("  usage: /model gpt-4", style="dim"))
            return
        self.config.model = model_name
        self.console.print(Text(f"  ✓  model → {model_name}", style="green"))

    def _handle_verbose(self) -> None:
        """Handle verbose command - toggle verbose mode."""
        self.config.verbose = not self.config.verbose
        state = "on" if self.config.verbose else "off"
        self.console.print(Text(f"  ✓  verbose {state}", style="green"))

    def _handle_trace_recap(self) -> None:
        """Toggle post-task chronological trace panel (same as --agent-trace-recap)."""
        self.config.agent_trace_recap = not self.config.agent_trace_recap
        state = "on" if self.config.agent_trace_recap else "off"
        self.console.print(Text(f"  ✓  trace recap {state}", style="green"))

    # ── Task execution ───────────────────────────────────────────────────────

    def _execute_task(self, task_description: str) -> None:
        """
        Execute a task using the agent service.

        Args:
            task_description: The task to execute
        """
        self.console.print()

        try:
            # Create task with full context
            task = Task(
                description=task_description,
                repo_path=self.config.repo_path,
                project_name=self.config.project_name,
                language=self.config.language,
            )

            # Get schema for Neo4j context
            schema = get_schema()

            # Build conversation context
            conversation_context = self._build_context()

            # Execute task asynchronously
            result = asyncio.run(
                self.agent_service.execute_task(
                    task=task,
                    config=self.config,
                    schema=schema,
                    conversation_context=conversation_context,
                )
            )

            # Add result to conversation history
            if result.success:
                role_entry = {
                    "role": "assistant",
                    "content": "Task completed successfully",
                    "logs": result.logs,
                }
            else:
                role_entry = {
                    "role": "assistant",
                    "content": f"Error: {result.error}",
                }
            self.conversation_history.append(role_entry)

            # Display result
            self._format_result(result)

        except Exception as e:
            error_msg = f"Task execution failed: {e}"
            self.console.print(Text(f"  ✗  {error_msg}", style="bold red"))
            if self.config.verbose:
                self.console.print_exception()

            # Add error to history
            self.conversation_history.append(
                {
                    "role": "assistant",
                    "content": f"Error: {error_msg}",
                }
            )

        self.console.print()

    def _build_context(self) -> str:
        """
        Build conversation context from history.

        Summarizes the last 5 exchanges for the agent.

        Returns:
            Formatted conversation context string
        """
        if not self.conversation_history:
            return ""

        parts = ["## Previous Conversation\n"]
        for msg in self.conversation_history[-5:]:
            parts.append(f"**{msg['role'].title()}:** {msg['content']}\n")
        return "\n".join(parts)

    def _format_result(self, result) -> None:
        """
        Format and display the execution result.

        Args:
            result: The agent execution result
        """
        if result.success:
            self.console.print(Text("  ✓  Task completed", style="bold green"))
            if result.iterations > 0:
                self.console.print(
                    Text(f"  Completed in {result.iterations} iteration(s)", style="dim")
                )
        else:
            self.console.print(Text("  ✗  Task failed", style="bold red"))
            if result.error:
                self.console.print(Text(f"  Error: {result.error}", style="red"))

        # Footer trace only when verbose and repo did not already print trace recap panel
        if result.logs and self.config.verbose and not self.config.agent_trace_recap:
            self.console.print(Text("\n  Execution trace:", style="dim"))
            for log in result.logs:
                self.console.print(Text(f"    {log}", style="dim"))

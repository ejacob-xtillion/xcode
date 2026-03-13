"""
Interactive session manager for xCode - provides a Claude Code-like REPL experience
"""
import asyncio
import sys
from pathlib import Path
from typing import Optional

from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.styles import Style
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.live import Live
from rich.text import Text

from xcode.config import XCodeConfig
from xcode.agent_runner import AgentRunner


class InteractiveSession:
    """Manages an interactive xCode session with conversation history."""

    def __init__(self, config: XCodeConfig, console: Console):
        self.config = config
        self.console = console
        self.conversation_history: list[dict] = []
        self.session_active = True
        
        # Setup prompt toolkit
        history_file = Path.home() / ".xcode" / "history.txt"
        history_file.parent.mkdir(parents=True, exist_ok=True)
        
        self.prompt_session = PromptSession(
            history=FileHistory(str(history_file)),
            auto_suggest=AutoSuggestFromHistory(),
            completer=self._create_completer(),
            style=self._create_style(),
            multiline=False,  # Start with single-line, use \ for continuation
            enable_history_search=True,
        )
        
        self.agent_runner = AgentRunner(config, console)
    
    def _create_completer(self) -> WordCompleter:
        """Create command completer."""
        commands = [
            "/help",
            "/clear", 
            "/exit",
            "/quit",
            "/history",
            "/model",
            "/verbose",
        ]
        return WordCompleter(commands, ignore_case=True)
    
    def _create_style(self) -> Style:
        """Create prompt style."""
        return Style.from_dict({
            'prompt': 'cyan bold',
            'command': 'yellow',
        })
    
    def run(self) -> None:
        """Run the interactive session."""
        self._show_welcome()
        
        while self.session_active:
            try:
                # Get user input
                user_input = self.prompt_session.prompt(
                    [('class:prompt', 'xcode> ')],
                    multiline=False,
                )
                
                if not user_input.strip():
                    continue
                
                # Handle input
                self._handle_input(user_input)
                
            except KeyboardInterrupt:
                self.console.print("\n[yellow]Use /exit or Ctrl+D to quit[/yellow]")
                continue
            except EOFError:
                self._handle_exit()
                break
            except Exception as e:
                self.console.print(f"[red]Error: {e}[/red]")
                if self.config.verbose:
                    self.console.print_exception()
    
    def _show_welcome(self) -> None:
        """Show welcome message."""
        welcome_text = """
# Welcome to xCode Interactive Mode

Type your coding task and press Enter. Available commands:
- `/help` - Show this help
- `/clear` - Clear conversation history
- `/history` - Show conversation history  
- `/model <name>` - Switch LLM model
- `/verbose` - Toggle verbose output
- `/exit` or `/quit` - Exit interactive mode
- `Ctrl+D` - Exit
- `Ctrl+R` - Search command history

Press `\\` then `Enter` for multi-line input.
        """
        self.console.print(Panel(
            Markdown(welcome_text.strip()),
            title="[bold cyan]xCode Interactive[/bold cyan]",
            border_style="cyan"
        ))
    
    def _handle_input(self, user_input: str) -> None:
        """Handle user input - commands or tasks."""
        # Handle commands
        if user_input.startswith("/"):
            self._handle_command(user_input)
            return
        
        # Handle multi-line continuation
        if user_input.endswith("\\"):
            user_input = self._get_multiline_input(user_input[:-1])
        
        # Add to conversation history
        self.conversation_history.append({
            "role": "user",
            "content": user_input
        })
        
        # Execute task with agent
        self._execute_task(user_input)
    
    def _get_multiline_input(self, initial: str) -> str:
        """Get multi-line input."""
        lines = [initial]
        self.console.print("[dim]Multi-line mode (empty line to finish)[/dim]")
        
        while True:
            try:
                line = self.prompt_session.prompt([('class:prompt', '... ')], multiline=False)
                if not line.strip():
                    break
                lines.append(line)
            except (KeyboardInterrupt, EOFError):
                break
        
        return "\n".join(lines)
    
    def _handle_command(self, command: str) -> None:
        """Handle slash commands."""
        parts = command.split(maxsplit=1)
        cmd = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""
        
        if cmd in ["/exit", "/quit"]:
            self._handle_exit()
        elif cmd == "/help":
            self._show_welcome()
        elif cmd == "/clear":
            self._handle_clear()
        elif cmd == "/history":
            self._handle_history()
        elif cmd == "/model":
            self._handle_model(args)
        elif cmd == "/verbose":
            self._handle_verbose()
        else:
            self.console.print(f"[red]Unknown command: {cmd}[/red]")
            self.console.print("[dim]Type /help for available commands[/dim]")
    
    def _handle_exit(self) -> None:
        """Handle exit command."""
        self.console.print("\n[cyan]Goodbye! 👋[/cyan]")
        self.session_active = False
    
    def _handle_clear(self) -> None:
        """Clear conversation history."""
        self.conversation_history.clear()
        self.console.clear()
        self.console.print("[green]✓[/green] Conversation history cleared")
        self._show_welcome()
    
    def _handle_history(self) -> None:
        """Show conversation history."""
        if not self.conversation_history:
            self.console.print("[yellow]No conversation history yet[/yellow]")
            return
        
        self.console.print(Panel(
            "\n".join([
                f"[cyan]User:[/cyan] {msg['content'][:100]}..." if len(msg['content']) > 100 
                else f"[cyan]User:[/cyan] {msg['content']}"
                for msg in self.conversation_history if msg['role'] == 'user'
            ]),
            title="[bold]Conversation History[/bold]",
            border_style="blue"
        ))
    
    def _handle_model(self, model_name: str) -> None:
        """Switch model."""
        if not model_name:
            self.console.print(f"[cyan]Current model:[/cyan] {self.config.model}")
            self.console.print("[dim]Usage: /model <model-name>[/dim]")
            return
        
        self.config.model = model_name
        self.console.print(f"[green]✓[/green] Switched to model: {model_name}")
    
    def _handle_verbose(self) -> None:
        """Toggle verbose mode."""
        self.config.verbose = not self.config.verbose
        status = "enabled" if self.config.verbose else "disabled"
        self.console.print(f"[green]✓[/green] Verbose mode {status}")
    
    def _execute_task(self, task: str) -> None:
        """Execute a task with the agent."""
        self.console.print()
        
        # Update config with current task
        self.config.task = task
        
        # Build context from conversation history
        context = self._build_context()
        
        # Run agent (this will stream output)
        result = asyncio.run(self.agent_runner._run_agent_async(conversation_context=context))
        
        # Add response to history
        if result.success:
            self.conversation_history.append({
                "role": "assistant",
                "content": "Task completed successfully",
                "logs": result.logs
            })
        else:
            self.conversation_history.append({
                "role": "assistant", 
                "content": f"Error: {result.error}",
            })
        
        self.console.print()
    
    def _build_context(self) -> str:
        """Build context from conversation history for agent."""
        if not self.conversation_history:
            return ""
        
        context_parts = ["## Previous Conversation\n"]
        for msg in self.conversation_history[-5:]:  # Last 5 messages
            role = msg['role'].title()
            content = msg['content']
            context_parts.append(f"**{role}:** {content}\n")
        
        return "\n".join(context_parts)

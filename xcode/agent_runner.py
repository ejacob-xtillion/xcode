"""
Agent runner - spawns and manages la-factoria agents
"""
import subprocess
import sys
from typing import Optional
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.text import Text

from xcode.config import XCodeConfig
from xcode.result import XCodeResult
from xcode.schema import get_schema


class AgentRunner:
    """Runs la-factoria agents with task and context."""

    def __init__(self, config: XCodeConfig, console: Console):
        self.config = config
        self.console = console
        self.max_iterations = 10
        self.current_iteration = 0

    def run(self) -> XCodeResult:
        """
        Run the agent with the given task.
        
        Returns:
            XCodeResult with success status and logs
        """
        try:
            # For now, implement a stub that shows the integration points
            # In production, this would call la-factoria API/CLI
            return self._run_agent_stub()
            
        except Exception as e:
            return XCodeResult(
                success=False,
                task=self.config.task,
                iterations=self.current_iteration,
                error=str(e),
            )

    def _run_agent_stub(self) -> XCodeResult:
        """
        Stub implementation showing agent integration structure.
        
        In production, this would:
        1. Call la-factoria to spawn an agent
        2. Pass task, repo path, project name
        3. Configure Neo4j MCP
        4. Provide schema context
        5. Configure LLM (local or cloud)
        6. Stream agent output
        7. Capture logs and close the loop
        """
        self.console.print("[dim]Agent runner stub - integration points:[/dim]\n")
        
        # Show what would be passed to la-factoria
        agent_config = {
            "task": self.config.task,
            "repo_path": str(self.config.repo_path),
            "project_name": self.config.project_name,
            "language": self.config.language,
            "neo4j": {
                "uri": self.config.neo4j_uri,
                "user": self.config.neo4j_user,
                "password": "***",  # Don't show password
            },
            "llm": self.config.get_llm_config(),
            "schema": "Neo4j schema provided",
            "max_iterations": self.max_iterations,
        }
        
        self.console.print(Panel(
            Text.from_markup(
                f"[cyan]Task:[/cyan] {agent_config['task']}\n"
                f"[cyan]Repository:[/cyan] {agent_config['repo_path']}\n"
                f"[cyan]Project:[/cyan] {agent_config['project_name']}\n"
                f"[cyan]Language:[/cyan] {agent_config['language']}\n"
                f"[cyan]LLM Model:[/cyan] {agent_config['llm']['model']}\n"
                f"[cyan]LLM Endpoint:[/cyan] {agent_config['llm'].get('base_url', 'cloud (OpenAI)')}\n"
                f"[cyan]Neo4j:[/cyan] {agent_config['neo4j']['uri']}\n"
                f"[cyan]Max Iterations:[/cyan] {agent_config['max_iterations']}"
            ),
            title="[bold]Agent Configuration[/bold]",
            border_style="cyan"
        ))
        
        self.console.print("\n[yellow]Note:[/yellow] This is a stub. In production:")
        self.console.print("  1. Spawn la-factoria agent with above config")
        self.console.print("  2. Provide Neo4j schema as context")
        self.console.print("  3. Stream agent actions and output")
        self.console.print("  4. Capture tool outputs (tests, linter, commands)")
        self.console.print("  5. Pass logs back to agent for verification")
        self.console.print("  6. Iterate until success or max iterations")
        self.console.print("  7. Return final result\n")
        
        # Simulate success for now
        return XCodeResult(
            success=True,
            task=self.config.task,
            iterations=1,
            logs=[
                "Agent would execute task here",
                "Logs would be captured and passed back",
                "Verification would check success criteria",
            ],
        )

    def _get_agent_context(self) -> dict:
        """
        Build context to pass to the agent.
        
        Returns:
            Dict with schema, project info, and tools
        """
        return {
            "schema": get_schema(),
            "project_name": self.config.project_name,
            "repo_path": str(self.config.repo_path),
            "language": self.config.language,
            "neo4j_uri": self.config.neo4j_uri,
            "tools": [
                "neo4j_query",  # Query the knowledge graph
                "read_file",    # Read source files
                "write_file",   # Edit source files
                "run_shell",    # Run commands (returns stdout/stderr/exit_code)
                "run_tests",    # Run tests (returns results)
                "run_linter",   # Run linter (returns issues)
            ],
        }

    def _verify_result(self, logs: list[str]) -> tuple[bool, Optional[str]]:
        """
        Verify if the task was completed successfully.
        
        Args:
            logs: Logs from agent execution
            
        Returns:
            Tuple of (success, error_message)
        """
        # In production, this would:
        # 1. Run tests if applicable
        # 2. Run linter if applicable
        # 3. Check for specific success criteria
        # 4. Return whether verification passed
        
        # For now, always return success in stub
        return True, None

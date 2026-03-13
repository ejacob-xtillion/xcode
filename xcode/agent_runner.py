"""
Agent runner - spawns and manages la-factoria agents
"""
import asyncio
import json
import subprocess
import sys
from typing import Optional
import httpx
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.text import Text
from rich.status import Status

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
        self.lf_base_url = "http://localhost:8000"
        self.agent_name = "xcode_coding_agent"

    def run(self) -> XCodeResult:
        """
        Run the agent with the given task.
        
        Returns:
            XCodeResult with success status and logs
        """
        try:
            # Run async agent call
            return asyncio.run(self._run_agent_async())
            
        except Exception as e:
            return XCodeResult(
                success=False,
                task=self.config.task,
                iterations=self.current_iteration,
                error=str(e),
            )

    async def _run_agent_async(self) -> XCodeResult:
        """
        Run the agent via la-factoria API with streaming.
        
        Returns:
            XCodeResult with success status and logs
        """
        # Build the context-rich query for the agent
        schema_text = get_schema()
        query = self._build_agent_query(schema_text)
        
        # Show configuration
        self._show_config()
        
        # Prepare request
        request_data = {
            "agent_name": self.agent_name,
            "query": query
        }
        
        logs = []
        session_id = None
        final_status = "unknown"
        execution_time_ms = 0
        
        try:
            self.console.print(f"\n[bold cyan]🤖 Connecting to la-factoria agent...[/bold cyan]")
            
            async with httpx.AsyncClient(timeout=300.0) as client:
                # Stream agent execution
                async with client.stream(
                    "POST",
                    f"{self.lf_base_url}/agents",
                    json=request_data,
                    headers={"Accept": "text/event-stream"}
                ) as response:
                    if response.status_code != 200:
                        error_text = await response.aread()
                        raise Exception(f"La-factoria API error: {response.status_code} - {error_text.decode()}")
                    
                    self.console.print("[green]✓[/green] Connected to agent\n")
                    
                    # Process streaming events
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            event_data = line[6:]  # Remove "data: " prefix
                            try:
                                event = json.loads(event_data)
                                result = self._handle_event(event, logs)
                                
                                # Extract session info from events
                                if event.get("type") == "session_created":
                                    session_id = event.get("session_id")
                                elif event.get("type") == "complete":
                                    session_id = event.get("session_id")
                                    final_status = event.get("status", "completed")
                                    execution_time_ms = event.get("execution_time_ms", 0)
                                    
                            except json.JSONDecodeError as e:
                                self.console.print(f"[yellow]Warning: Failed to parse event: {e}[/yellow]")
            
            # Determine success based on final status
            success = final_status in ["completed", "interrupted"]
            
            self.console.print(f"\n[bold]Agent execution {final_status}[/bold]")
            self.console.print(f"Execution time: {execution_time_ms / 1000:.2f}s")
            if session_id:
                self.console.print(f"Session ID: {session_id}")
            
            return XCodeResult(
                success=success,
                task=self.config.task,
                iterations=1,
                logs=logs,
            )
            
        except httpx.ConnectError:
            self.console.print("[red]✗[/red] Failed to connect to la-factoria")
            self.console.print("[yellow]Make sure la-factoria is running at http://localhost:8000[/yellow]")
            self.console.print("[dim]Start it with: cd /path/to/la-factoria && python -m app.main[/dim]")
            return XCodeResult(
                success=False,
                task=self.config.task,
                iterations=0,
                error="Failed to connect to la-factoria API",
            )
        except Exception as e:
            self.console.print(f"[red]✗[/red] Error: {str(e)}")
            return XCodeResult(
                success=False,
                task=self.config.task,
                iterations=self.current_iteration,
                error=str(e),
            )
    
    def _build_agent_query(self, schema_text: str) -> str:
        """Build a context-rich query for the agent."""
        return f"""You are a coding assistant working on a codebase.

**Task:** {self.config.task}

**Repository Information:**
- Path: {self.config.repo_path}
- Project: {self.config.project_name}
- Language: {self.config.language}

**Knowledge Graph:**
You have access to a Neo4j knowledge graph containing the complete codebase structure.
Use the neo4j_query tool to understand code relationships, find dependencies, and locate relevant code.

**Neo4j Connection:**
- URI: {self.config.neo4j_uri}
- Database: neo4j
- Project: {self.config.project_name}

**Schema:**
{schema_text}

**Available Tools:**
- neo4j_query: Query the knowledge graph to understand code structure
- read_file: Read files from the repository
- write_file: Modify files in the repository
- run_shell: Execute shell commands (tests, linters, etc.)

**Instructions:**
1. First, use neo4j_query to understand the codebase structure relevant to the task
2. Read the necessary files
3. Make the required changes
4. Run tests/linters to verify your changes
5. Iterate if needed

Please complete the task now."""
    
    def _show_config(self):
        """Show agent configuration."""
        llm_config = self.config.get_llm_config()
        self.console.print(Panel(
            Text.from_markup(
                f"[cyan]Task:[/cyan] {self.config.task}\n"
                f"[cyan]Repository:[/cyan] {self.config.repo_path}\n"
                f"[cyan]Project:[/cyan] {self.config.project_name}\n"
                f"[cyan]Language:[/cyan] {self.config.language}\n"
                f"[cyan]Agent:[/cyan] {self.agent_name}\n"
                f"[cyan]LF API:[/cyan] {self.lf_base_url}\n"
                f"[cyan]LLM Model:[/cyan] {llm_config['model']}\n"
                f"[cyan]Neo4j:[/cyan] {self.config.neo4j_uri}"
            ),
            title="[bold]Agent Configuration[/bold]",
            border_style="cyan"
        ))
    
    def _handle_event(self, event: dict, logs: list[str]) -> None:
        """Handle streaming event from la-factoria."""
        event_type = event.get("type")
        
        if event_type == "session_created":
            session_id = event.get("session_id")
            self.console.print(f"[dim]Session created: {session_id}[/dim]")
            
        elif event_type == "token":
            # Stream tokens to console
            content = event.get("content", "")
            self.console.print(content, end="")
            logs.append(content)
            
        elif event_type == "tool_call":
            tool = event.get("tool", "unknown")
            args = event.get("args", {})
            self.console.print(f"\n[yellow]🔧 Tool:[/yellow] {tool}")
            if self.config.verbose:
                self.console.print(f"[dim]Args: {json.dumps(args, indent=2)}[/dim]")
            logs.append(f"Tool call: {tool}")
            
        elif event_type == "tool_result":
            content = event.get("content", "")
            if self.config.verbose:
                self.console.print(f"[dim]Result: {content[:200]}...[/dim]" if len(content) > 200 else f"[dim]Result: {content}[/dim]")
            
        elif event_type == "answer":
            content = event.get("content", "")
            self.console.print(f"\n[green]✓[/green] {content}")
            logs.append(f"Answer: {content}")
            
        elif event_type == "error":
            content = event.get("content", "")
            self.console.print(f"\n[red]✗ Error:[/red] {content}")
            logs.append(f"Error: {content}")
            
        elif event_type == "interrupt":
            prompt = event.get("prompt", "")
            self.console.print(f"\n[yellow]⚠ Interrupt:[/yellow] {prompt}")
            logs.append(f"Interrupt: {prompt}")
            
        elif event_type == "complete":
            status = event.get("status", "unknown")
            self.console.print(f"\n[dim]Status: {status}[/dim]")

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

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
from rich.syntax import Syntax
from rich.tree import Tree
from rich.table import Table

from xcode.config import XCodeConfig
from xcode.result import XCodeResult
from xcode.schema import get_schema
from xcode.task_classifier import TaskClassifier, TaskClassification


class AgentRunner:
    """Runs la-factoria agents with task and context."""

    def __init__(self, config: XCodeConfig, console: Console):
        self.config = config
        self.console = console
        self.max_iterations = 10
        self.current_iteration = 0
        self.lf_base_url = "http://localhost:8000"
        self.agent_name = "xcode_coding_agent"
        self.tool_call_counter = 0  # Track tool calls for better display

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

    def _validate_task(self) -> tuple[bool, str]:
        """
        Validate the task before sending to the agent.
        
        Returns:
            tuple[bool, str]: (is_valid, error_message)
        """
        import re
        
        task = self.config.task.strip()
        
        # Check minimum length
        if len(task) < 3:
            return False, "Task is too short. Please provide a meaningful coding task."
        
        # Check for common invalid patterns
        invalid_patterns = [
            (r'^[^a-zA-Z0-9\s]+$', "Task contains only special characters"),
            (r'^(hi|hello|hey|test)[\]!.]*$', "Please provide a specific coding task instead of a greeting"),
        ]
        
        for pattern, message in invalid_patterns:
            if re.match(pattern, task, re.IGNORECASE):
                return False, message
        
        return True, ""
    
    async def _run_agent_async(self, conversation_context: str = "") -> XCodeResult:
        """
        Run the agent via la-factoria API with streaming.

        Args:
            conversation_context: Previous conversation history for interactive mode
        
        Returns:
            XCodeResult with success status and logs
        """
        # Validate task first
        is_valid, error_msg = self._validate_task()
        if not is_valid:
            self.console.print(f"[yellow]⚠[/yellow] Invalid task: {error_msg}")
            self.console.print(f"[dim]Example: 'Add a function to calculate fibonacci numbers'[/dim]")
            return XCodeResult(
                success=False,
                task=self.config.task,
                iterations=0,
                error=error_msg,
            )

        # Classify task and adjust execution parameters
        classification = TaskClassifier().classify(self.config.task)
        self.max_iterations = classification.max_iterations
        self._show_classification(classification)

        # Build the context-rich query for the agent
        schema_text = get_schema()
        query = self._build_agent_query(schema_text, conversation_context)

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
        tool_calls = []  # Track all tool calls for summary
        
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
                                
                                # Track tool calls for summary
                                if event.get("type") == "tool_call":
                                    tool_calls.append({
                                        "tool": event.get("tool"),
                                        "args": event.get("args", {}),
                                    })
                                
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
            
            # Show tool call summary
            if tool_calls and self.config.verbose:
                self._show_tool_summary(tool_calls)
            
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
    
    def _build_agent_query(self, schema_text: str, conversation_context: str = "") -> str:
        """Build a context-rich query for the agent."""
        query_parts = []
        
        # Add conversation context if available (for interactive mode)
        if conversation_context:
            query_parts.append(conversation_context)
            query_parts.append("\n---\n")
        
        # Add current task
        query_parts.append(f"""You are a coding assistant working on a codebase.

**Current Task:** {self.config.task}

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

**Important Guidelines:**
- If the task is unclear, ambiguous, or not a valid coding request, respond immediately without using tools
- Only use tools when the task requires actual code inspection or modification
- For greetings, questions, or non-coding requests, respond directly

**Instructions:**
1. Evaluate if the task requires code changes or inspection
2. If yes: Use neo4j_query to understand the codebase structure relevant to the task
3. Read the necessary files
4. Make the required changes
5. Run tests/linters to verify your changes
6. Iterate if needed

Please complete the task now.""")
        
        return "\n".join(query_parts)
    
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
    
    def _show_classification(self, classification: TaskClassification):
        """Show task classification information."""
        self.console.print(Panel(
            Text.from_markup(
                f"[yellow]Task Type:[/yellow] {classification.task_type.value}\n"
                f"[yellow]Confidence:[/yellow] {classification.confidence:.0%}\n"
                f"[yellow]Max Files:[/yellow] {classification.max_files_to_read}\n"
                f"[yellow]Needs Neo4j:[/yellow] {classification.needs_neo4j}\n"
                f"[yellow]Max Iterations:[/yellow] {classification.max_iterations}\n"
                f"[yellow]Strategy:[/yellow] {classification.suggested_strategy}"
            ),
            title="[bold]Task Classification[/bold]",
            border_style="yellow"
        ))
    
    def _handle_event(self, event: dict, logs: list[str]) -> None:
        """Handle streaming event from la-factoria with rich formatting."""
        event_type = event.get("type")
        
        if event_type == "session_created":
            session_id = event.get("session_id")
            self.console.print(f"[dim]Session created: {session_id}[/dim]\n")
            
        elif event_type == "token":
            # Stream tokens to console
            content = event.get("content", "")
            self.console.print(content, end="")
            logs.append(content)
            
        elif event_type == "tool_call":
            self.tool_call_counter += 1
            tool = event.get("tool", "unknown")
            args = event.get("args", {})
            tool_id = event.get("tool_call_id", "")
            
            # Create a visually distinct tool call display
            self.console.print("\n")
            
            # Build the tool call panel content
            tool_info = Text()
            tool_info.append(f"🔧 Tool Call #{self.tool_call_counter}\n", style="bold yellow")
            tool_info.append(f"Tool: ", style="cyan")
            tool_info.append(f"{tool}\n", style="bold white")
            
            if tool_id:
                tool_info.append(f"ID: ", style="dim cyan")
                tool_info.append(f"{tool_id}\n", style="dim")
            
            # Format arguments based on verbosity and size
            if args:
                tool_info.append(f"\nArguments:\n", style="cyan")
                args_str = json.dumps(args, indent=2)
                
                # Always show some args, but truncate if too long and not verbose
                if len(args_str) > 500 and not self.config.verbose:
                    # Show compact version for large args
                    arg_keys = list(args.keys())
                    tool_info.append(f"  {', '.join(arg_keys)}\n", style="yellow")
                    tool_info.append(f"  [dim](use --verbose to see full args)[/dim]\n", style="dim")
                else:
                    # Show full args with syntax highlighting
                    try:
                        syntax = Syntax(args_str, "json", theme="monokai", line_numbers=False)
                        self.console.print(syntax)
                    except:
                        tool_info.append(f"{args_str}\n", style="yellow")
            
            # Show the panel only if we didn't already print syntax
            if not (args and (len(json.dumps(args, indent=2)) <= 500 or self.config.verbose)):
                self.console.print(Panel(
                    tool_info,
                    border_style="yellow",
                    padding=(0, 1)
                ))
            else:
                # Just show the header if we printed syntax separately
                self.console.print(tool_info)
            
            logs.append(f"Tool call #{self.tool_call_counter}: {tool}")
            
        elif event_type == "tool_result":
            content = event.get("content", "")
            tool_call_id = event.get("tool_call_id", "")
            is_error = event.get("is_error", False)
            
            # Create tool result display
            result_info = Text()
            
            if is_error:
                result_info.append("❌ Tool Error\n", style="bold red")
                border_style = "red"
            else:
                result_info.append("✓ Tool Result\n", style="bold green")
                border_style = "green"
            
            if tool_call_id:
                result_info.append(f"ID: ", style="dim cyan")
                result_info.append(f"{tool_call_id}\n", style="dim")
            
            # Format the result content
            if content:
                result_info.append(f"\nOutput:\n", style="cyan")
                
                # Intelligently display based on content type and size
                content_str = str(content)
                
                if len(content_str) > 1000 and not self.config.verbose:
                    # Truncate long results
                    result_info.append(f"{content_str[:500]}\n", style="white")
                    result_info.append(f"... [dim]({len(content_str) - 500} more chars, use --verbose to see all)[/dim]\n", style="dim")
                else:
                    # Try to detect if it's JSON and format accordingly
                    if content_str.strip().startswith(("{", "[")):
                        try:
                            parsed = json.loads(content_str)
                            formatted = json.dumps(parsed, indent=2)
                            if len(formatted) < 1000 or self.config.verbose:
                                syntax = Syntax(formatted, "json", theme="monokai", line_numbers=False)
                                self.console.print(Panel(
                                    syntax,
                                    title="[bold green]✓ Tool Result[/bold green]",
                                    border_style=border_style,
                                    padding=(0, 1)
                                ))
                                logs.append(f"Tool result: {formatted[:200]}...")
                                return
                        except:
                            pass
                    
                    result_info.append(f"{content_str}\n", style="white")
            
            self.console.print(Panel(
                result_info,
                border_style=border_style,
                padding=(0, 1)
            ))
            
            logs.append(f"Tool result: {content_str[:200] if content else 'empty'}...")
            self.console.print()  # Add spacing after tool result
            
        elif event_type == "answer":
            content = event.get("content", "")
            self.console.print(f"\n[bold green]✓ Agent Response:[/bold green]")
            self.console.print(f"{content}")
            logs.append(f"Answer: {content}")
            
        elif event_type == "error":
            content = event.get("content", "")
            self.console.print(Panel(
                f"[bold red]Error:[/bold red]\n{content}",
                border_style="red",
                padding=(1, 2)
            ))
            logs.append(f"Error: {content}")
            
        elif event_type == "interrupt":
            prompt = event.get("prompt", "")
            self.console.print(Panel(
                f"[bold yellow]⚠ Interrupt:[/bold yellow]\n{prompt}",
                border_style="yellow",
                padding=(1, 2)
            ))
            logs.append(f"Interrupt: {prompt}")
            
        elif event_type == "complete":
            status = event.get("status", "unknown")
            self.console.print(f"\n[dim]Status: {status}[/dim]")
            
            # Show summary of tool calls
            if self.tool_call_counter > 0:
                self.console.print(f"[dim]Total tool calls: {self.tool_call_counter}[/dim]")

    def _show_tool_summary(self, tool_calls: list[dict]) -> None:
        """Show a summary of all tool calls made during execution."""
        self.console.print("\n")
        
        # Create a tree view of tool calls
        tree = Tree("🔧 [bold cyan]Tool Call Summary[/bold cyan]")
        
        # Group by tool type
        tool_groups = {}
        for tc in tool_calls:
            tool_name = tc["tool"]
            if tool_name not in tool_groups:
                tool_groups[tool_name] = []
            tool_groups[tool_name].append(tc)
        
        # Add to tree
        for tool_name, calls in tool_groups.items():
            tool_branch = tree.add(f"[yellow]{tool_name}[/yellow] ({len(calls)} calls)")
            
            for i, call in enumerate(calls[:3], 1):  # Show first 3 of each type
                args = call["args"]
                # Show key arguments
                arg_summary = []
                for key, value in list(args.items())[:2]:  # First 2 args
                    val_str = str(value)
                    if len(val_str) > 50:
                        val_str = val_str[:47] + "..."
                    arg_summary.append(f"{key}={val_str}")
                
                tool_branch.add(f"[dim]Call {i}: {', '.join(arg_summary)}[/dim]")
            
            if len(calls) > 3:
                tool_branch.add(f"[dim]... and {len(calls) - 3} more[/dim]")
        
        self.console.print(tree)
    
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

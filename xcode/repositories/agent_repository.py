"""
Agent repository for la-factoria integration.
"""
import json
from typing import Optional

import httpx
from rich.console import Console

from xcode.domain.interfaces import AgentRepository
from xcode.models import Task, TaskClassification, AgentResult, FileTreeCache, TaskType


class LaFactoriaRepository(AgentRepository):
    """
    La-factoria implementation of agent repository.

    Communicates with la-factoria API to execute agent tasks via HTTP streaming.
    """

    def __init__(
        self,
        base_url: str,
        console: Console,
        agent_name: str = "xcode_coding_agent",
        verbose: bool = False,
    ):
        """
        Initialize the la-factoria repository.

        Args:
            base_url: Base URL for la-factoria API
            console: Rich console for output
            agent_name: Name of the agent to use
            verbose: Whether to show verbose output
        """
        self.base_url = base_url
        self.console = console
        self.agent_name = agent_name
        self.verbose = verbose
        self.tool_call_counter = 0

    async def execute_task(
        self,
        task: Task,
        config: dict,
        schema: str,
        conversation_context: str = "",
    ) -> AgentResult:
        """
        Execute a task using an AI agent.
        
        Args:
            task: Task to execute
            config: LLM configuration dict
            schema: Neo4j schema documentation
            conversation_context: Previous conversation history
            
        Returns:
            AgentResult with execution status
        """
        # Extract parameters from task and config
        classification = task.classification if hasattr(task, 'classification') else None
        file_tree = task.file_tree if hasattr(task, 'file_tree') else None
        neo4j_uri = config.get('neo4j_uri', 'bolt://localhost:7687')
        
        return await self._run_agent_internal(
            task=task,
            classification=classification,
            file_tree=file_tree,
            schema_text=schema,
            neo4j_uri=neo4j_uri,
            conversation_context=conversation_context,
        )
    
    async def _run_agent_internal(
        self,
        task: Task,
        classification: Optional[TaskClassification],
        file_tree: Optional[FileTreeCache],
        schema_text: str,
        neo4j_uri: str,
        conversation_context: str = "",
    ) -> AgentResult:
        """
        Internal method to run the agent via la-factoria API with streaming.

        Args:
            task: Task to execute
            classification: Task classification
            file_tree: Optional file tree cache
            schema_text: Neo4j schema documentation
            neo4j_uri: Neo4j connection URI
            conversation_context: Previous conversation history

        Returns:
            AgentResult with execution status
        """
        query = self._build_agent_query(
            task, classification, file_tree, schema_text, neo4j_uri, conversation_context
        )

        request_data = {"agent_name": self.agent_name, "query": query}

        logs = []
        session_id = None
        final_status = "unknown"
        execution_time_ms = 0
        tool_calls = []

        try:
            self.console.print("\n[bold cyan]🤖 Connecting to la-factoria agent...[/bold cyan]")

            async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/agents",
                    json=request_data,
                    headers={"Accept": "text/event-stream"},
                ) as response:
                    if response.status_code != 200:
                        error_text = await response.aread()
                        raise Exception(
                            f"La-factoria API error: {response.status_code} - {error_text.decode()}"
                        )

                    self.console.print("[green]✓[/green] Connected to agent\n")

                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            event_data = line[6:]
                            try:
                                event = json.loads(event_data)

                                if event.get("type") == "tool_call":
                                    tool_calls.append(
                                        {
                                            "tool": event.get("tool"),
                                            "args": event.get("args", {}),
                                        }
                                    )

                                self._handle_event(event, logs)

                                if event.get("type") == "session_created":
                                    session_id = event.get("session_id")
                                elif event.get("type") == "complete":
                                    session_id = event.get("session_id")
                                    final_status = event.get("status", "completed")
                                    execution_time_ms = event.get("execution_time_ms", 0)

                            except json.JSONDecodeError as e:
                                self.console.print(
                                    f"[yellow]Warning: Failed to parse event: {e}[/yellow]"
                                )

            success = final_status in ["completed", "interrupted"]

            self.console.print(f"\n[bold]Agent execution {final_status}[/bold]")
            self.console.print(f"Execution time: {execution_time_ms / 1000:.2f}s")
            if session_id:
                self.console.print(f"Session ID: {session_id}")

            if tool_calls and self.verbose:
                self._show_tool_summary(tool_calls)

            return AgentResult(
                success=success,
                task=task.description,
                iterations=1,
                logs=logs,
            )

        except httpx.ConnectError:
            self.console.print("[red]✗[/red] Failed to connect to la-factoria")
            self.console.print(
                "[yellow]Make sure la-factoria is running at http://localhost:8000[/yellow]"
            )
            self.console.print(
                "[dim]Start it with: cd /path/to/la-factoria && python -m app.main[/dim]"
            )
            return AgentResult(
                success=False,
                task=task.description,
                iterations=0,
                error="Failed to connect to la-factoria API",
            )
        except Exception as e:
            self.console.print(f"[red]✗[/red] Error: {str(e)}")
            return AgentResult(
                success=False,
                task=task.description,
                iterations=0,
                error=str(e),
            )

    def _build_agent_query(
        self,
        task: Task,
        classification: TaskClassification,
        file_tree: Optional[FileTreeCache],
        schema_text: str,
        neo4j_uri: str,
        conversation_context: str = "",
    ) -> str:
        """Build a context-rich query for the agent."""
        query_parts = []

        if conversation_context:
            query_parts.append(conversation_context)
            query_parts.append("\n---\n")

        query_parts.append(
            f"""You are a coding assistant working on a codebase.

**Current Task:** {task.description}

**Repository Information:**
- Path: {task.repo_path}
- Project: {task.project_name}
- Language: {task.language}
"""
        )

        file_operation_tasks = [
            TaskType.CREATE_NEW_FILE,
            TaskType.MODIFY_EXISTING,
            TaskType.DELETE_FILES,
            TaskType.REFACTOR,
        ]

        if classification.task_type in file_operation_tasks and file_tree:
            file_list = self._format_file_tree(file_tree)
            query_parts.append(
                f"""
**Available files in repository:**
{file_list}
"""
            )

        query_parts.append(
            f"""
**Knowledge Graph:**
You have access to a Neo4j knowledge graph containing the complete codebase
structure. Use the neo4j_query tool to understand code relationships, find
dependencies, and locate relevant code.

**Neo4j Connection:**
- URI: {neo4j_uri}
- Database: neo4j
- Project: {task.project_name}

**Schema:**
{schema_text}

**Available Tools:**
- neo4j_query: Query the knowledge graph to understand code structure
- read_file: Read files from the repository
- write_file: Modify files in the repository
- run_shell: Execute shell commands (tests, linters, etc.)

**Instructions:**
1. Use Neo4j queries to understand the codebase structure
2. Read only the files you need to complete the task
3. Make focused, precise changes
4. Run tests after making changes
5. Iterate if tests fail

Complete the task efficiently and accurately.
"""
        )

        return "\n".join(query_parts)

    def _format_file_tree(self, file_tree: FileTreeCache) -> str:
        """Format file tree for display."""
        files = file_tree.list_all_files()
        if not files:
            return "(no files found)"

        by_ext = {}
        for file_info in files:
            ext = file_info.extension or "(no ext)"
            if ext not in by_ext:
                by_ext[ext] = []
            by_ext[ext].append(file_info.path)

        lines = []
        for ext, paths in sorted(by_ext.items()):
            lines.append(f"{ext}: {len(paths)} files")
            if len(paths) <= 10:
                for path in sorted(paths):
                    lines.append(f"  - {path}")
            else:
                for path in sorted(paths)[:5]:
                    lines.append(f"  - {path}")
                lines.append(f"  ... and {len(paths) - 5} more")

        return "\n".join(lines)

    def _handle_event(self, event: dict, logs: list) -> None:
        """Handle a streaming event from la-factoria."""
        event_type = event.get("type")

        if event_type == "session_created":
            session_id = event.get("session_id")
            if self.verbose:
                self.console.print(f"[dim]Session created: {session_id}[/dim]")

        elif event_type == "token":
            content = event.get("content", "")
            self.console.print(content, end="")
            logs.append(content)

        elif event_type == "tool_call":
            self.tool_call_counter += 1
            tool = event.get("tool", "unknown")
            args = event.get("args", {})

            if not self.verbose:
                self.console.print(f"[dim cyan]→ {tool}[/dim cyan]", end=" ")
            else:
                self.console.print(f"\n[yellow]🔧 Tool Call #{self.tool_call_counter}: {tool}[/yellow]")
                if args:
                    args_str = json.dumps(args, indent=2)
                    self.console.print(f"[dim]{args_str}[/dim]")

            logs.append(f"Tool call #{self.tool_call_counter}: {tool}")

        elif event_type == "tool_result":
            is_error = event.get("is_error", False)

            if not self.verbose:
                if is_error:
                    self.console.print("[red]✗[/red]")
                else:
                    self.console.print("[green]✓[/green]")
            else:
                content = event.get("content", "")
                if content:
                    content_str = str(content)
                    if len(content_str) > 200:
                        content_str = content_str[:200] + "..."
                    status = "✗ Error" if is_error else "✓ Result"
                    self.console.print(f"[{'red' if is_error else 'green'}]{status}:[/] [dim]{content_str}[/dim]")

        elif event_type == "answer":
            content = event.get("content", "")
            if content:
                if not self.verbose:
                    self.console.print(f"\n{content}")
                else:
                    self.console.print(f"\n[bold green]✓ Agent Response:[/bold green]\n{content}")
                logs.append(f"Answer: {content}")

        elif event_type == "error":
            content = event.get("content", "")
            self.console.print(f"[red]✗ Error:[/red] {content}")
            logs.append(f"Error: {content}")

        elif event_type == "interrupt":
            prompt = event.get("prompt", "")
            self.console.print(f"[yellow]⚠ Interrupt:[/yellow] {prompt}")
            logs.append(f"Interrupt: {prompt}")

        elif event_type == "complete":
            status = event.get("status", "unknown")
            if self.verbose:
                self.console.print(f"\n[dim]Status: {status}[/dim]")

    def _show_tool_summary(self, tool_calls: list) -> None:
        """Show summary of tool calls."""
        from collections import Counter

        tool_counts = Counter(tc["tool"] for tc in tool_calls)

        self.console.print("\n[bold]Tool Usage Summary:[/bold]")
        for tool, count in tool_counts.most_common():
            self.console.print(f"  {tool}: {count} calls")

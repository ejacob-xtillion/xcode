"""
Agent repository for la-factoria integration.
"""
import json
from typing import Optional

import httpx
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

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
        self.stream_tokens = True
        self.trace_recap = False
        self.tool_call_counter = 0
        self._trace_seq = 0
        self._token_chunks: list[str] = []
        self._stream_printed = False

    def configure_display(
        self,
        *,
        verbose: bool,
        stream_tokens: bool = True,
        trace_recap: bool = False,
    ) -> None:
        """Sync console behavior from CLI / interactive toggles (call before each task)."""
        self.verbose = verbose
        self.stream_tokens = stream_tokens
        self.trace_recap = trace_recap

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
            config: LLM configuration dict (includes classification, file_tree, neo4j_uri)
            schema: Neo4j schema documentation
            conversation_context: Previous conversation history
            
        Returns:
            AgentResult with execution status
        """
        # Extract parameters from config
        classification = config.get('classification')
        file_tree = config.get('file_tree')
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

        logs: list[str] = []
        session_id = None
        final_status = "unknown"
        execution_time_ms = 0
        tool_calls = []
        self.tool_call_counter = 0
        self._trace_seq = 0
        self._token_chunks = []
        self._stream_printed = False

        try:
            self.console.print("\n[bold cyan]🤖 Connecting to la-factoria agent...[/bold cyan]")

            async with httpx.AsyncClient(timeout=httpx.Timeout(300.0)) as client:
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
                    self.console.print(
                        "[bold magenta]━━ Agent trace (chronological) ━━[/bold magenta]"
                    )

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

                    self._flush_token_buffer(logs)

            if self.trace_recap and logs:
                self.console.print(
                    Panel(
                        Text("\n".join(logs), style="dim"),
                        title="[bold]Trace recap (chronological)[/bold]",
                        border_style="bright_magenta",
                    )
                )

            success = final_status in ["completed", "interrupted"]

            if self.verbose or not success:
                self.console.print(f"\n[bold]Agent execution {final_status}[/bold]")
                self.console.print(f"Execution time: {execution_time_ms / 1000:.2f}s")
                if session_id:
                    self.console.print(f"Session ID: {session_id}")

            if tool_calls and self.verbose:
                self._show_tool_summary(tool_calls)

            # Extract error from logs if task failed
            error_msg = None
            if not success:
                # Look for error in logs
                for log in logs:
                    if "error" in log.lower() or "failed" in log.lower():
                        error_msg = log
                        break
                if not error_msg and logs:
                    error_msg = logs[-1] if logs else "Unknown error"

            return AgentResult(
                success=success,
                task=task.description,
                iterations=1,
                logs=logs,
                error=error_msg if not success else None,
            )

        except httpx.ConnectError:
            self.console.print("[red]✗[/red] Failed to connect to la-factoria")
            self.console.print(
                f"[yellow]Make sure the agent API is running at {self.base_url}[/yellow]"
            )
            self.console.print(
                "[dim]If running via Docker Compose, start `xcode-agent` first.[/dim]"
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
structure. Use the read_neo4j_cypher tool to understand code relationships, find
dependencies, and locate relevant code.

**Neo4j Connection:**
- URI: {neo4j_uri}
- Database: neo4j
- Project: {task.project_name}

**Schema:**
{schema_text}

**Available Tools:**
- read_neo4j_cypher: Query the knowledge graph (Cypher)
- read_text_file / write_file / edit_file (and related): Filesystem MCP tools — use absolute paths under the repo
- run_shell_command: Run tests/linters; pass command string and working_directory (absolute repo path)

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

    def _append_trace_line(self, logs: list[str], kind: str, summary: str) -> None:
        """Numbered chronological entry for DX and optional recap."""
        self._trace_seq += 1
        line = f"{self._trace_seq:>2}. [{kind}] {summary}"
        logs.append(line)

    def _flush_token_buffer(self, logs: list[str]) -> None:
        """Fold streamed tokens into one trace line before answer / complete."""
        if not self._token_chunks:
            return
        full = "".join(self._token_chunks)
        self._token_chunks.clear()
        preview = self._truncate(full.replace("\n", " "), 220)
        self._append_trace_line(logs, "stream", f"{len(full)} chars — {preview}")

    def _handle_event(self, event: dict, logs: list) -> None:
        """Handle a streaming event from la-factoria."""
        event_type = event.get("type")

        if event_type == "session_created":
            session_id = event.get("session_id")
            sid = session_id or "?"
            self._append_trace_line(logs, "session", f"created ({sid})")
            self.console.print(
                f"\n[dim]{self._trace_seq:>2}. [session][/dim] [cyan]{sid}[/cyan]"
            )

        elif event_type == "reasoning":
            # Show agent's reasoning/thinking process
            content = event.get("content", "")
            if content:
                preview = self._truncate(content.replace("\n", " "), 160)
                self._append_trace_line(logs, "reasoning", preview)
                self.console.print(
                    f"\n[bold blue]💭 Reasoning[/bold blue] [dim](trace {self._trace_seq})[/dim]"
                )
                self.console.print(f"[dim italic]{content}[/dim italic]")

        elif event_type == "token":
            content = event.get("content", "")
            if not content:
                return
            self._token_chunks.append(content)
            if self.stream_tokens:
                self.console.print(content, end="", style="dim")
                self._stream_printed = True

        elif event_type == "tool_call":
            self.tool_call_counter += 1
            tool = event.get("tool", "unknown")
            args = event.get("args", {})

            # Always show tool calls with context
            tool_display = self._format_tool_call(tool, args)
            self._append_trace_line(logs, "tool_call", f"{tool} — {tool_display}")
            self.console.print(
                f"\n[yellow]🔧 Step {self.tool_call_counter}:[/yellow] [white]{tool}[/white] — {tool_display}"
            )

            if self.verbose and args:
                args_str = json.dumps(args, indent=2)
                self.console.print(f"[dim]{args_str}[/dim]")

        elif event_type == "tool_result":
            is_error = event.get("is_error", False)
            content = event.get("content", "")

            if is_error:
                err_bit = self._truncate(str(content), 300)
                self._append_trace_line(logs, "tool_error", err_bit)
                self.console.print(f"  [red]✗ Error:[/red] {err_bit}")
            else:
                result_summary = self._summarize_tool_result(content)
                self._append_trace_line(logs, "tool_result", result_summary)
                self.console.print(f"  [green]✓[/green] {result_summary}")
                if self.verbose and content:
                    content_str = self._truncate(str(content), 500)
                    self.console.print(f"  [dim]{content_str}[/dim]")

        elif event_type == "answer":
            content = event.get("content", "")
            if content:
                self._flush_token_buffer(logs)
                if self._stream_printed:
                    self.console.print()
                    self._stream_printed = False
                self._append_trace_line(logs, "answer", f"{len(content)} chars")
                self.console.print(f"\n[bold green]━━━ Final answer ━━━[/bold green]")
                self.console.print(f"{content}")
                self.console.print(f"[bold green]━━━━━━━━━━━━━━━━━━━━━━[/bold green]\n")

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
            self._flush_token_buffer(logs)
            self._append_trace_line(logs, "complete", status)
            if self.verbose:
                self.console.print(f"\n[dim]Status: {status}[/dim]")

    def _format_tool_call(self, tool: str, args: dict) -> str:
        """Format tool call for display with context."""
        if tool == "read_neo4j_cypher":
            query = args.get("query", "")
            # Extract the main action from the query
            if "MATCH" in query:
                if "File" in query:
                    return "Querying knowledge graph for files..."
                elif "Class" in query:
                    return "Querying knowledge graph for classes..."
                elif "Callable" in query or "Function" in query:
                    return "Querying knowledge graph for functions..."
                elif "Test" in query:
                    return "Querying knowledge graph for tests..."
                elif "count" in query.lower():
                    return "Counting elements in knowledge graph..."
                else:
                    return "Querying knowledge graph..."
            return f"Running Cypher query..."
        elif tool in ("read_file", "read_text_file"):
            path = args.get("path", args.get("file_path", ""))
            return f"Reading file: {path}"
        elif tool in ("write_file", "write_text_file"):
            path = args.get("path", args.get("file_path", ""))
            return f"Writing file: {path}"
        elif tool == "edit_file":
            path = args.get("path", args.get("file_path", ""))
            return f"Editing file: {path}"
        elif tool == "list_directory":
            path = args.get("path", ".")
            return f"Listing directory: {path}"
        elif tool == "search_files":
            pattern = args.get("pattern", args.get("query", ""))
            return f"Searching files for: {pattern}"
        elif tool in ("run_shell_command", "run_shell", "execute_command"):
            cmd = args.get("command", "")
            cwd = args.get("working_directory", "")
            base = f"Running command: {self._truncate(cmd, 50)}"
            if cwd:
                return f"{base} (cwd: {self._truncate(cwd, 40)})"
            return base
        else:
            return f"{tool}"

    def _summarize_tool_result(self, content: str) -> str:
        """Summarize tool result for display."""
        if not content:
            return "Done"
        
        content_str = str(content)
        
        # Count items if it looks like a list/array result
        if content_str.startswith("[") and content_str.endswith("]"):
            try:
                import ast
                items = ast.literal_eval(content_str)
                if isinstance(items, list):
                    return f"Found {len(items)} items"
            except:
                pass
        
        # Check for common result patterns
        if "path" in content_str.lower() and content_str.count("\n") > 0:
            lines = content_str.strip().split("\n")
            return f"Found {len(lines)} files/paths"
        
        # Default: show truncated content
        if len(content_str) > 100:
            return f"{content_str[:100]}..."
        return content_str

    def _truncate(self, text: str, max_len: int) -> str:
        """Truncate text to max length."""
        if not text:
            return ""
        text = str(text)
        if len(text) <= max_len:
            return text
        return text[:max_len] + "..."

    def _show_tool_summary(self, tool_calls: list) -> None:
        """Show summary of tool calls."""
        from collections import Counter

        tool_counts = Counter(tc["tool"] for tc in tool_calls)

        self.console.print("\n[bold]Tool Usage Summary:[/bold]")
        for tool, count in tool_counts.most_common():
            self.console.print(f"  {tool}: {count} calls")

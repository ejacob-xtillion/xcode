"""
La-factoria agent repository implementation.
"""

import asyncio
import json

import httpx
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.text import Text
from rich.tree import Tree

from xcode.domain.interfaces import AgentRepository
from xcode.domain.models import AgentResult, Task


class LaFactoriaAgentRepository(AgentRepository):
    """La-factoria API implementation of AgentRepository."""

    def __init__(
        self,
        console: Console,
        base_url: str = "http://localhost:8000",
        agent_name: str = "xcode_coding_agent",
        max_iterations: int = 10,
    ):
        self.console = console
        self.base_url = base_url
        self.agent_name = agent_name
        self.max_iterations = max_iterations
        self.tool_call_counter = 0

    async def execute_task(
        self,
        task: Task,
        config: dict,
        schema: str,
        conversation_context: str = "",
    ) -> AgentResult:
        """
        Execute a task using la-factoria agent.

        Args:
            task: Task to execute
            config: LLM configuration
            schema: Neo4j schema documentation
            conversation_context: Previous conversation history

        Returns:
            AgentResult with execution outcome
        """
        logs = []
        iterations = 0

        try:
            system_prompt = self._build_system_prompt(schema)
            user_message = self._build_user_message(task, conversation_context)

            async with httpx.AsyncClient(timeout=300.0) as client:
                response = await client.post(
                    f"{self.base_url}/agent/stream",
                    json={
                        "agent_name": self.agent_name,
                        "system_prompt": system_prompt,
                        "user_message": user_message,
                        "config": config,
                    },
                    headers={"Accept": "text/event-stream"},
                )

                if response.status_code != 200:
                    error_msg = f"Agent API error: {response.status_code}"
                    if response.text:
                        error_msg += f"\n{response.text}"
                    return AgentResult(
                        success=False,
                        task=task.description,
                        iterations=iterations,
                        error=error_msg,
                        logs=logs,
                    )

                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        if data == "[DONE]":
                            break

                        try:
                            event = json.loads(data)
                            self._handle_event(event, logs)
                            iterations += 1
                        except json.JSONDecodeError:
                            continue

            return AgentResult(
                success=True,
                task=task.description,
                iterations=iterations,
                logs=logs,
            )

        except Exception as e:
            return AgentResult(
                success=False,
                task=task.description,
                iterations=iterations,
                error=str(e),
                logs=logs,
            )

    def _build_system_prompt(self, schema: str) -> str:
        """Build system prompt with Neo4j schema."""
        return f"""You are a coding agent with access to a Neo4j knowledge graph.

{schema}

Use the knowledge graph to understand the codebase structure and relationships.
Make targeted, efficient changes based on the task requirements.
"""

    def _build_user_message(self, task: Task, conversation_context: str) -> str:
        """Build user message with task and context."""
        message = task.description

        if task.context:
            message += f"\n\nContext:\n{task.context}"

        if conversation_context:
            message += f"\n\nPrevious conversation:\n{conversation_context}"

        return message

    def _handle_event(self, event: dict, logs: list[str]) -> None:
        """Handle streaming event from agent."""
        event_type = event.get("type")

        if event_type == "tool_call":
            self._display_tool_call(event)
            logs.append(f"Tool: {event.get('tool_name')}")

        elif event_type == "tool_result":
            self._display_tool_result(event)

        elif event_type == "message":
            content = event.get("content", "")
            if content.strip():
                self.console.print(content)
                logs.append(content)

        elif event_type == "error":
            error_msg = event.get("error", "Unknown error")
            self.console.print(f"[red]Error:[/red] {error_msg}")
            logs.append(f"Error: {error_msg}")

    def _display_tool_call(self, event: dict) -> None:
        """Display tool call in a formatted way."""
        self.tool_call_counter += 1
        tool_name = event.get("tool_name", "unknown")
        args = event.get("arguments", {})

        tree = Tree(f"[bold cyan]Tool Call #{self.tool_call_counter}: {tool_name}[/bold cyan]")

        for key, value in args.items():
            if isinstance(value, str) and len(value) > 100:
                value = value[:100] + "..."
            tree.add(f"[dim]{key}:[/dim] {value}")

        self.console.print(tree)

    def _display_tool_result(self, event: dict) -> None:
        """Display tool result in a formatted way."""
        result = event.get("result", "")

        if isinstance(result, str) and len(result) > 500:
            result_preview = result[:500] + "..."
        else:
            result_preview = str(result)

        if result_preview.strip():
            self.console.print(
                Panel(
                    result_preview,
                    title="[dim]Tool Result[/dim]",
                    border_style="dim",
                )
            )

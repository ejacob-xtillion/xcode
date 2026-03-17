"""
Agent service for AI agent execution.
"""

from rich.console import Console

from xcode.domain.interfaces import AgentRepository
from xcode.domain.models import AgentResult, Task, XCodeConfig


class AgentService:
    """Service for agent execution operations."""

    def __init__(self, agent_repo: AgentRepository, console: Console):
        self.agent_repo = agent_repo
        self.console = console

    async def execute_task(
        self,
        task: Task,
        config: XCodeConfig,
        schema: str,
        conversation_context: str = "",
    ) -> AgentResult:
        """
        Execute a task using an AI agent.

        Args:
            task: Task to execute
            config: Configuration
            schema: Neo4j schema documentation
            conversation_context: Previous conversation history

        Returns:
            AgentResult with execution outcome
        """
        self.console.print(f"\n[bold]Starting agent for task:[/bold] {task.description}\n")

        llm_config = config.get_llm_config()

        result = await self.agent_repo.execute_task(
            task=task,
            config=llm_config,
            schema=schema,
            conversation_context=conversation_context,
        )

        return result

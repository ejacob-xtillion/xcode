"""
Agent service for AI agent execution.
"""

from rich.console import Console

from xcode.domain.interfaces import AgentRepository
from xcode.domain.models import AgentResult, Task, XCodeConfig
from xcode.repositories.agent_repository import AgentHttpRepository
from xcode.repositories.cache_repository import InMemoryCacheRepository
from xcode.services.classification_service import ClassificationService


class AgentService:
    """Service for agent execution operations."""

    def __init__(
        self, 
        agent_repo: AgentRepository, 
        console: Console,
        classification_service: ClassificationService = None,
        cache_repo: InMemoryCacheRepository = None,
    ):
        self.agent_repo = agent_repo
        self.console = console
        self.classification_service = classification_service or ClassificationService()
        self.cache_repo = cache_repo or InMemoryCacheRepository()

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

        # Classify the task
        classification = self.classification_service.classify(task.description)
        
        # Get file tree for file operation tasks
        file_tree = None
        from xcode.models import TaskType
        file_operation_tasks = {
            TaskType.CREATE_NEW_FILE,
            TaskType.DELETE_FILES,
            TaskType.MODIFY_EXISTING,
        }
        if classification.task_type in file_operation_tasks:
            file_tree = self.cache_repo.get_or_create_cache(
                project_name=config.project_name,
                repo_path=config.repo_path,
            )

        # Build config dict with all needed parameters
        llm_config = config.get_llm_config()
        llm_config['neo4j_uri'] = config.neo4j_uri
        llm_config['classification'] = classification
        llm_config['file_tree'] = file_tree

        if isinstance(self.agent_repo, AgentHttpRepository):
            self.agent_repo.configure_display(
                verbose=config.verbose,
                stream_tokens=config.agent_stream_tokens,
                trace_recap=config.agent_trace_recap,
            )

        result = await self.agent_repo.execute_task(
            task=task,
            config=llm_config,
            schema=schema,
            conversation_context=conversation_context,
        )

        # Extract modified files from agent logs
        result.modified_files = self._extract_modified_files_from_logs(result.logs)

        return result

    def _extract_modified_files_from_logs(self, logs: list[str]) -> list[str]:
        """
        Parse agent logs to identify which files were modified.

        Looks for tool_call log entries with write_file or edit_file tools
        and extracts the file paths.

        Args:
            logs: List of log entries from agent execution

        Returns:
            List of relative file paths that were modified
        """
        import re

        modified = set()

        for log in logs:
            # Look for tool_call entries
            if "[tool_call]" not in log:
                continue

            # Check for write_file or edit_file
            if "write_file" in log or "edit_file" in log:
                # Try to extract file path from log
                # Format: "N. [tool_call] write_file — Writing file: /path/to/file"
                # or JSON args in verbose mode
                
                # Pattern 1: "Writing file: /path" or "Editing file: /path"
                match = re.search(r"(?:Writing|Editing) file: (.+?)(?:\s|$)", log)
                if match:
                    file_path = match.group(1).strip()
                    modified.add(file_path)
                    continue

                # Pattern 2: JSON args with "path" or "file_path" key
                # This is a simplified extraction - actual JSON parsing would be more robust
                path_match = re.search(r'"(?:path|file_path)":\s*"([^"]+)"', log)
                if path_match:
                    file_path = path_match.group(1).strip()
                    modified.add(file_path)

        return list(modified)

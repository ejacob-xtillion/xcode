"""
Domain interfaces (ports) for dependency inversion.

These interfaces define contracts that infrastructure adapters must implement.
"""

from abc import ABC, abstractmethod
from pathlib import Path

from xcode.domain.models import AgentResult, FileInfo, FileTreeCache, Task


class GraphRepository(ABC):
    """Interface for knowledge graph operations."""

    @abstractmethod
    def build_graph(self, project_name: str, repo_path: Path, language: str) -> None:
        """Build knowledge graph for a repository."""
        pass

    @abstractmethod
    def query(self, cypher: str, params: dict | None = None) -> list[dict]:
        """Execute a Cypher query and return results."""
        pass

    @abstractmethod
    def close(self) -> None:
        """Close connection to graph database."""
        pass


class FileRepository(ABC):
    """Interface for file system operations."""

    @abstractmethod
    def get_file_tree(self, repo_path: Path) -> FileTreeCache:
        """Get cached file tree for a repository."""
        pass

    @abstractmethod
    def read_file(self, file_path: Path) -> str:
        """Read contents of a file."""
        pass

    @abstractmethod
    def write_file(self, file_path: Path, content: str) -> None:
        """Write contents to a file."""
        pass

    @abstractmethod
    def file_exists(self, file_path: Path) -> bool:
        """Check if a file exists."""
        pass

    @abstractmethod
    def list_files(self, directory: Path, pattern: str = "*") -> list[FileInfo]:
        """List files in a directory matching a pattern."""
        pass


class AgentRepository(ABC):
    """Interface for agent execution."""

    @abstractmethod
    async def execute_task(
        self,
        task: Task,
        config: dict,
        schema: str,
        conversation_context: str = "",
    ) -> AgentResult:
        """Execute a task using an AI agent."""
        pass


class TaskRepository(ABC):
    """Interface for task persistence and retrieval."""

    @abstractmethod
    def save_task(self, task: Task) -> str:
        """Save a task and return its ID."""
        pass

    @abstractmethod
    def get_task(self, task_id: str) -> Task | None:
        """Retrieve a task by ID."""
        pass

    @abstractmethod
    def list_tasks(self) -> list[Task]:
        """List all tasks."""
        pass

"""
Task classification models.
"""

from dataclasses import dataclass
from enum import Enum


class TaskType(Enum):
    """Types of tasks the agent can handle."""

    CREATE_NEW_FILE = "create_new_file"
    DELETE_FILES = "delete_files"
    MODIFY_EXISTING = "modify_existing"
    ADD_FEATURE = "add_feature"
    FIX_BUG = "fix_bug"
    REFACTOR = "refactor"
    ARCHITECTURE_CHANGE = "architecture_change"
    DOCUMENTATION = "documentation"
    GREETING = "greeting"
    QUESTION = "question"
    UNKNOWN = "unknown"


@dataclass
class TaskClassification:
    """Result of task classification."""

    task_type: TaskType
    max_files_to_read: int
    needs_neo4j: bool
    max_iterations: int
    suggested_strategy: str
    confidence: float

    @property
    def should_use_tools(self) -> bool:
        """Whether this task requires any tools."""
        return self.task_type not in {TaskType.GREETING, TaskType.QUESTION}

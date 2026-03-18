"""
Task classification models.
"""
from dataclasses import dataclass
from enum import Enum


class TaskType(Enum):
    """Types of tasks the agent can handle."""
    
    # Simple operations (1-3 files, no Neo4j needed)
    CREATE_NEW_FILE = "create_new_file"
    DELETE_FILES = "delete_files"

    # Medium operations (3-10 files, limited Neo4j)
    MODIFY_EXISTING = "modify_existing"
    ADD_FEATURE = "add_feature"
    FIX_BUG = "fix_bug"
    
    # Complex operations (10+ files, full Neo4j access)
    REFACTOR = "refactor"
    ARCHITECTURE_CHANGE = "architecture_change"
    
    # Documentation operations (read-only, selective files)
    DOCUMENTATION = "documentation"
    
    # Non-coding operations (no tools needed)
    GREETING = "greeting"
    QUESTION = "question"
    
    # Unknown (use conservative defaults)
    UNKNOWN = "unknown"


@dataclass
class TaskClassification:
    """Result of task classification."""
    
    task_type: TaskType
    max_files_to_read: int
    needs_neo4j: bool
    max_iterations: int
    suggested_strategy: str
    confidence: float  # 0.0 to 1.0
    
    @property
    def should_use_tools(self) -> bool:
        """Whether this task requires any tools."""
        return self.task_type != TaskType.GREETING

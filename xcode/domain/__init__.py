"""
Domain layer for xCode.

This layer contains pure business logic, domain models, and interfaces.
No external dependencies - only Python standard library.
"""

from xcode.domain.interfaces import (
    AgentRepository,
    FileRepository,
    GraphRepository,
    TaskRepository,
)
from xcode.domain.models import (
    AgentResult,
    FileInfo,
    FileTreeCache,
    Task,
    TaskClassification,
    TaskType,
    VerificationResult,
    XCodeConfig,
)

__all__ = [
    "Task",
    "AgentResult",
    "VerificationResult",
    "TaskType",
    "TaskClassification",
    "FileInfo",
    "FileTreeCache",
    "XCodeConfig",
    "AgentRepository",
    "FileRepository",
    "GraphRepository",
    "TaskRepository",
]

"""
Domain models for xCode.

Pure domain models with validation and business rules.
No external dependencies.
"""

from xcode.models.classification import TaskClassification, TaskType
from xcode.models.config import XCodeConfig
from xcode.models.file_info import FileInfo, FileTreeCache
from xcode.models.result import AgentResult, VerificationResult
from xcode.models.task import Task

__all__ = [
    "Task",
    "AgentResult",
    "VerificationResult",
    "TaskType",
    "TaskClassification",
    "FileInfo",
    "FileTreeCache",
    "XCodeConfig",
]

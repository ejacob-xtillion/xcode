"""
Domain models for xCode.

This package contains pure domain models with validation and business rules.
Models have no external dependencies and represent core business concepts.
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

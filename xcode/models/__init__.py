"""
Domain models for xCode.

Pure data models with validation and business rules.
No external dependencies.
"""
from xcode.models.result import AgentResult, VerificationResult
from xcode.models.classification import TaskType, TaskClassification
from xcode.models.file_info import FileInfo, FileTreeCache
from xcode.models.config import XCodeConfig
from xcode.models.task import Task, TaskValidationError
from xcode.models.test_info import TestInfo, CallableInfo

__all__ = [
    "AgentResult",
    "VerificationResult",
    "TaskType",
    "TaskClassification",
    "FileInfo",
    "FileTreeCache",
    "XCodeConfig",
    "Task",
    "TaskValidationError",
    "TestInfo",
    "CallableInfo",
]

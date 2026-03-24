"""
Data models for test discovery and generation.
"""

from dataclasses import dataclass


@dataclass
class TestInfo:
    """Information about a test in the codebase."""

    name: str
    path: str
    line_number: int
    tests_callable: str | None = None


@dataclass
class CallableInfo:
    """Information about a callable (function/method) in the codebase."""

    name: str
    signature: str
    file_path: str
    line_number: int
    is_tested: bool = False

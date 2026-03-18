"""
Result models for xCode execution.
"""
from dataclasses import dataclass
from typing import Optional, List


@dataclass
class AgentResult:
    """Result of agent execution."""

    success: bool
    task: str
    iterations: int
    error: Optional[str] = None
    logs: List[str] = None

    def __post_init__(self) -> None:
        if self.logs is None:
            self.logs = []


@dataclass
class VerificationResult:
    """Result of running verification checks."""

    success: bool
    checks_run: List[str]
    output: str
    error: Optional[str] = None

"""
Result models for xCode execution.
"""

from dataclasses import dataclass


@dataclass
class AgentResult:
    """Result of agent execution."""

    success: bool
    task: str
    iterations: int
    error: str | None = None
    logs: list[str] | None = None

    def __post_init__(self) -> None:
        if self.logs is None:
            self.logs = []


@dataclass
class VerificationResult:
    """Result of running verification checks."""

    success: bool
    checks_run: list[str]
    output: str
    error: str | None = None

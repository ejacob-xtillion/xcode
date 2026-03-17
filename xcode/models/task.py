"""
Task model for xCode.
"""

from dataclasses import dataclass


@dataclass
class Task:
    """Represents a coding task to be executed."""

    description: str
    context: str | None = None
    constraints: list[str] | None = None

    def __post_init__(self) -> None:
        if self.constraints is None:
            self.constraints = []

"""
Result object for xCode execution
"""

from dataclasses import dataclass


@dataclass
class XCodeResult:
    """Result of xCode execution."""

    success: bool
    task: str
    iterations: int
    error: str | None = None
    logs: list[str] = None

    def __post_init__(self) -> None:
        if self.logs is None:
            self.logs = []

"""
Result object for xCode execution
"""
from dataclasses import dataclass
from typing import Optional, List


@dataclass
class XCodeResult:
    """Result of xCode execution."""

    success: bool
    task: str
    iterations: int
    error: Optional[str] = None
    logs: List[str] = None

    def __post_init__(self) -> None:
        if self.logs is None:
            self.logs = []

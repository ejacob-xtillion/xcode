"""
Base command interface for xCode commands.
"""

from abc import ABC, abstractmethod
from typing import Any


class BaseCommand(ABC):
    """Base interface for all commands."""

    @abstractmethod
    def execute(self) -> Any:
        """Execute the command and return result."""
        pass

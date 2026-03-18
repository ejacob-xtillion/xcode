"""
Task model with validation.
"""
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


class TaskValidationError(Exception):
    """Raised when task validation fails."""
    pass


@dataclass
class Task:
    """
    Task entity with validation.
    
    Represents a coding task to be executed by the agent.
    """
    
    description: str
    repo_path: Path
    project_name: str
    language: str = "python"
    
    def __post_init__(self) -> None:
        """Validate task after initialization."""
        self.validate()
    
    def validate(self) -> None:
        """
        Validate the task description.
        
        Raises:
            TaskValidationError: If validation fails
        """
        task = self.description.strip()
        
        # Check minimum length
        if len(task) < 3:
            raise TaskValidationError("Task is too short. Please provide a meaningful coding task.")
        
        # Check for common invalid patterns
        invalid_patterns = [
            (r"^[^a-zA-Z0-9\s]+$", "Task contains only special characters"),
            (
                r"^(hi|hello|hey|test)[\]!.]*$",
                "Please provide a specific coding task instead of a greeting",
            ),
        ]
        
        for pattern, message in invalid_patterns:
            if re.match(pattern, task, re.IGNORECASE):
                raise TaskValidationError(message)
    
    def is_valid_coding_task(self) -> bool:
        """
        Check if this is a valid coding task.
        
        Returns:
            bool: True if valid, False otherwise
        """
        try:
            self.validate()
            return True
        except TaskValidationError:
            return False
    
    @property
    def is_simple(self) -> bool:
        """
        Check if this is a simple task.
        
        Simple tasks typically involve:
        - Single file operations
        - Basic modifications
        - Quick fixes
        
        Returns:
            bool: True if task is simple
        """
        simple_indicators = ["simple", "basic", "quick", "small", "single", "just", "only", "one"]
        task_lower = self.description.lower()
        return any(indicator in task_lower for indicator in simple_indicators)
    
    @property
    def is_complex(self) -> bool:
        """
        Check if this is a complex task.
        
        Complex tasks typically involve:
        - Multiple files
        - Refactoring
        - Architecture changes
        - Comprehensive modifications
        
        Returns:
            bool: True if task is complex
        """
        complex_indicators = [
            "complex",
            "entire",
            "all",
            "multiple",
            "refactor",
            "migrate",
            "overhaul",
            "redesign",
            "comprehensive",
        ]
        task_lower = self.description.lower()
        return any(indicator in task_lower for indicator in complex_indicators)

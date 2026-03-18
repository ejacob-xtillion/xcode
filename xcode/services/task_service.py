"""
Task service for task classification and management.
"""

from pathlib import Path

from xcode.domain.models import Task, TaskClassification
from xcode.task_classifier import TaskClassifier


class TaskService:
    """Service for task-related operations."""

    def __init__(self):
        self.classifier = TaskClassifier()

    def classify_task(self, task_description: str) -> TaskClassification:
        """
        Classify a task to determine execution strategy.

        Args:
            task_description: The task description to classify

        Returns:
            TaskClassification with execution parameters
        """
        return self.classifier.classify(task_description)

    def create_task(
        self,
        description: str,
        repo_path: Path,
        project_name: str,
        language: str = "python",
    ) -> Task:
        """
        Create a new task instance.

        Args:
            description: Task description
            repo_path: Path to the repository
            project_name: Name of the project
            language: Programming language (default: python)

        Returns:
            Task instance
        """
        return Task(
            description=description,
            repo_path=repo_path,
            project_name=project_name,
            language=language,
        )

    def validate_task(self, task_description: str) -> tuple[bool, str]:
        """
        Validate a task description.

        Args:
            task_description: The task to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        import re

        task = task_description.strip()

        if len(task) < 3:
            return False, "Task is too short. Please provide a meaningful coding task."

        invalid_patterns = [
            (r"^[^a-zA-Z0-9\s]+$", "Task contains only special characters"),
            (
                r"^(hi|hello|hey|test)[\]!.]*$",
                "Please provide a specific coding task instead of a greeting",
            ),
        ]

        for pattern, message in invalid_patterns:
            if re.match(pattern, task, re.IGNORECASE):
                return False, message

        return True, ""

"""
Task classification system to optimize agent tool usage.

This module classifies tasks to determine:
- What type of operation is needed
- How many files should be read
- Whether Neo4j queries are needed
- Maximum iteration limits
"""

import re

from xcode.domain.models import TaskClassification, TaskType
from xcode.task_config import (
    TASK_TYPE_CONFIGS,
    TASK_TYPE_CONTEXT_HINTS,
    TASK_TYPE_PATTERNS,
)


class TaskClassifier:
    """Classifies tasks to optimize agent execution."""

    def classify(self, task: str) -> TaskClassification:
        """
        Classify a task to determine optimal execution strategy.

        Args:
            task: The task description

        Returns:
            TaskClassification with execution parameters
        """
        task_lower = task.lower().strip()

        # Try to match patterns in priority order
        # Check specific patterns before general ones
        priority_order = [
            TaskType.GREETING,  # Check greetings first (before questions)
            TaskType.FIX_BUG,  # Check bug fixes before general modifications
            TaskType.DELETE_FILES,
            TaskType.REFACTOR,
            TaskType.ARCHITECTURE_CHANGE,
            TaskType.DOCUMENTATION,
            TaskType.CREATE_NEW_FILE,
            TaskType.ADD_FEATURE,
            TaskType.MODIFY_EXISTING,
            TaskType.QUESTION,  # Check questions last (most general)
        ]

        best_match = TaskType.UNKNOWN
        best_confidence = 0.0

        for task_type in priority_order:
            if task_type not in TASK_TYPE_PATTERNS:
                continue
            patterns = TASK_TYPE_PATTERNS[task_type]
            for pattern in patterns:
                if re.search(pattern, task_lower, re.IGNORECASE):
                    # Calculate confidence based on pattern specificity
                    confidence = self._calculate_confidence(pattern, task_lower)
                    if confidence > best_confidence:
                        best_match = task_type
                        best_confidence = confidence

        # Get configuration for the matched type
        config = TASK_TYPE_CONFIGS[best_match]

        # Adjust based on task length and complexity
        complexity_multiplier = self._assess_complexity(task)

        return TaskClassification(
            task_type=best_match,
            max_files_to_read=int(config.max_files * complexity_multiplier),
            needs_neo4j=config.needs_neo4j,
            max_iterations=int(config.max_iterations * complexity_multiplier),
            suggested_strategy=config.strategy,
            confidence=best_confidence,
        )

    def _calculate_confidence(self, pattern: str, task: str) -> float:
        """
        Calculate confidence score for a pattern match.

        Higher confidence for:
        - More specific patterns
        - Matches at the start of the task
        - Longer matches
        - Exact matches (pattern with ^ and $)
        """
        match = re.search(pattern, task, re.IGNORECASE)
        if not match:
            return 0.0

        # Base confidence
        confidence = 0.7

        # Bonus for match at start
        if match.start() == 0:
            confidence += 0.15

        # Bonus for exact match patterns (^ and $)
        if pattern.startswith("^") and pattern.endswith("$"):
            confidence += 0.15

        # Bonus for longer patterns
        pattern_length = len(pattern)
        if pattern_length > 30:
            confidence += 0.1
        elif pattern_length > 20:
            confidence += 0.05

        return min(confidence, 1.0)

    def _assess_complexity(self, task: str) -> float:
        """
        Assess task complexity to adjust limits.

        Returns multiplier (0.5 to 2.0)
        """
        # Simple tasks
        simple_indicators = ["simple", "basic", "quick", "small", "single", "just", "only", "one"]

        # Complex tasks
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

        task_lower = task.lower()

        # Count indicators
        simple_count = sum(1 for word in simple_indicators if word in task_lower)
        complex_count = sum(1 for word in complex_indicators if word in task_lower)

        # Calculate multiplier
        if simple_count > complex_count:
            return 0.7
        elif complex_count > simple_count:
            return 1.5
        else:
            return 1.0

    def get_context_hint(self, classification: TaskClassification) -> str:
        """
        Get a hint for what context to gather.

        Args:
            classification: The task classification

        Returns:
            String hint for context gathering
        """
        return TASK_TYPE_CONTEXT_HINTS.get(
            classification.task_type, "Gather context as needed"
        )

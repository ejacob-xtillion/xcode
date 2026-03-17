"""
Task classification configuration.

Separates configuration data from classification logic for better maintainability.
"""

from dataclasses import dataclass

from xcode.models.classification import TaskType


@dataclass
class TaskTypeConfig:
    """Configuration for a specific task type."""

    max_files: int
    needs_neo4j: bool
    max_iterations: int
    strategy: str


# Configuration for each task type
TASK_TYPE_CONFIGS: dict[TaskType, TaskTypeConfig] = {
    TaskType.GREETING: TaskTypeConfig(
        max_files=0,
        needs_neo4j=False,
        max_iterations=1,
        strategy="Respond directly without using any tools",
    ),
    TaskType.QUESTION: TaskTypeConfig(
        max_files=5,
        needs_neo4j=True,
        max_iterations=3,
        strategy="Use Neo4j to find relevant code, read minimal files to answer",
    ),
    TaskType.CREATE_NEW_FILE: TaskTypeConfig(
        max_files=3,
        needs_neo4j=False,
        max_iterations=5,
        strategy="Read similar files as templates, create new file, verify",
    ),
    TaskType.DELETE_FILES: TaskTypeConfig(
        max_files=0,
        needs_neo4j=False,
        max_iterations=3,
        strategy="Search for files, delete them, confirm",
    ),
    TaskType.MODIFY_EXISTING: TaskTypeConfig(
        max_files=5,
        needs_neo4j=True,
        max_iterations=8,
        strategy="Find target files via Neo4j, read them, modify, test",
    ),
    TaskType.ADD_FEATURE: TaskTypeConfig(
        max_files=10,
        needs_neo4j=True,
        max_iterations=15,
        strategy="Understand codebase via Neo4j, read related files, implement, test",
    ),
    TaskType.FIX_BUG: TaskTypeConfig(
        max_files=8,
        needs_neo4j=True,
        max_iterations=12,
        strategy="Locate bug via Neo4j, read affected files, fix, verify with tests",
    ),
    TaskType.REFACTOR: TaskTypeConfig(
        max_files=20,
        needs_neo4j=True,
        max_iterations=25,
        strategy="Map dependencies via Neo4j, read affected files, refactor, test thoroughly",
    ),
    TaskType.ARCHITECTURE_CHANGE: TaskTypeConfig(
        max_files=30,
        needs_neo4j=True,
        max_iterations=30,
        strategy="Full codebase analysis via Neo4j, systematic changes, extensive testing",
    ),
    TaskType.DOCUMENTATION: TaskTypeConfig(
        max_files=10,
        needs_neo4j=True,
        max_iterations=8,
        strategy="Query Neo4j for structure, read main modules, create docs",
    ),
    TaskType.UNKNOWN: TaskTypeConfig(
        max_files=15,
        needs_neo4j=True,
        max_iterations=20,
        strategy="Conservative approach: use all available tools as needed",
    ),
}

# Regex patterns for task type detection
TASK_TYPE_PATTERNS: dict[TaskType, list[str]] = {
    TaskType.GREETING: [
        r"^(hi|hello|hey|greetings)(\s+\w+)?[\s!.]*$",
        r"^good\s+(morning|afternoon|evening)[\s!.]*$",
        r"^how\s+are\s+you[\s?!.]*$",
        r"^what\'?s\s+up[\s?!.]*$",
    ],
    TaskType.FIX_BUG: [
        r"\bfix\s+(the\s+)?(bug|issue|error|problem)",
        r"\b(resolve|address)\s+(the\s+)?(\w+\s+)?(\w+\s+)?(issue|error|problem)",
        r"\bdebug\s+",
    ],
    TaskType.DELETE_FILES: [
        r"\b(delete|remove|clean\s*up|purge)\s+.*files?",
        r"\bremove\s+the\s+.*\.(json|md|txt|log)",
    ],
    TaskType.REFACTOR: [
        r"\brefactor\s+",
        r"\brestructure\s+",
        r"\breorganize\s+",
        r"\bclean\s+up\s+the\s+code",
    ],
    TaskType.ARCHITECTURE_CHANGE: [
        r"\b(migrate|convert|transform)\s+.*\s+to\s+",
        r"\breplace\s+\w+\s+with\s+",
        r"\bchange\s+the\s+architecture",
    ],
    TaskType.DOCUMENTATION: [
        r"\b(add|create|write|update)\s+.*\b(documentation|docs?|readme|guide)",
        r"\bdocument\s+(the\s+)?(code|api|codebase)",
    ],
    TaskType.CREATE_NEW_FILE: [
        r"\b(create|add|make|write)\s+(a\s+)?(new\s+)?file",
        r"\b(add|write|create)\s+a\s+(class|function|module|component)",
        r"\bwrite\s+a\s+new\s+",
        r"\bimplement\s+a\s+(simple|basic|new)\s+",
    ],
    TaskType.ADD_FEATURE: [
        r"\badd\s+(feature|functionality|capability|support\s+for)",
        r"\bimplement\s+\w+\s+(feature|functionality)",
        r"\benable\s+\w+",
    ],
    TaskType.MODIFY_EXISTING: [
        r"\b(update|modify|change|edit)\s+.*\.(py|js|ts|go|java)",
        r"\b(update|modify|change|edit)\s+(the\s+)?(\w+\s+)?(\w+\s+)?(function|class|method|file|settings?|config)",
    ],
    TaskType.QUESTION: [
        r"^(what|how|why|when|where|who)\s+",
        r"^(can|could|would|should)\s+you\s+",
        r"^(is|are|does|do)\s+",
        r"\?$",
    ],
}

# Context hints for each task type
TASK_TYPE_CONTEXT_HINTS: dict[TaskType, str] = {
    TaskType.CREATE_NEW_FILE: "Look for similar files as templates",
    TaskType.DELETE_FILES: "Search for files matching the pattern",
    TaskType.MODIFY_EXISTING: "Find and read only the target file(s)",
    TaskType.ADD_FEATURE: "Find related modules and their dependencies",
    TaskType.FIX_BUG: "Locate the buggy code and its test files",
    TaskType.REFACTOR: "Map all dependencies and affected files",
    TaskType.DOCUMENTATION: "Read main entry points and public APIs",
    TaskType.QUESTION: "Find relevant code sections to answer the question",
}

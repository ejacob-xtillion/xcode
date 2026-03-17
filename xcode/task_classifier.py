"""
Task classification system to optimize agent tool usage.

This module classifies tasks to determine:
- What type of operation is needed
- How many files should be read
- Whether Neo4j queries are needed
- Maximum iteration limits
"""
import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class TaskType(Enum):
    """Types of tasks the agent can handle."""
    
    # Simple operations (1-3 files, no Neo4j needed)
    CREATE_NEW_FILE = "create_new_file"
    DELETE_FILES = "delete_files"
    READ_FILE = "read_file"
    
    # Medium operations (3-10 files, limited Neo4j)
    MODIFY_EXISTING = "modify_existing"
    ADD_FEATURE = "add_feature"
    FIX_BUG = "fix_bug"
    
    # Complex operations (10+ files, full Neo4j access)
    REFACTOR = "refactor"
    ARCHITECTURE_CHANGE = "architecture_change"
    
    # Documentation operations (read-only, selective files)
    DOCUMENTATION = "documentation"
    
    # Non-coding operations (no tools needed)
    GREETING = "greeting"
    QUESTION = "question"
    CLARIFICATION = "clarification"
    
    # Unknown (use conservative defaults)
    UNKNOWN = "unknown"


@dataclass
class TaskClassification:
    """Result of task classification."""
    
    task_type: TaskType
    max_files_to_read: int
    needs_neo4j: bool
    max_iterations: int
    suggested_strategy: str
    confidence: float  # 0.0 to 1.0
    
    @property
    def should_use_tools(self) -> bool:
        """Whether this task requires any tools."""
        return self.task_type not in [
            TaskType.GREETING,
            TaskType.CLARIFICATION,
        ]


class TaskClassifier:
    """Classifies tasks to optimize agent execution."""
    
    # Patterns for different task types
    # Ordered by specificity (most specific first)
    PATTERNS = {
        TaskType.GREETING: [
            r'^(hi|hello|hey|greetings)(\s+\w+)?[\s!.]*$',
            r'^good\s+(morning|afternoon|evening)[\s!.]*$',
            r'^how\s+are\s+you[\s?!.]*$',
            r'^what\'?s\s+up[\s?!.]*$',
        ],
        TaskType.FIX_BUG: [
            r'\bfix\s+(the\s+)?(bug|issue|error|problem)',
            r'\b(resolve|address)\s+(the\s+)?(\w+\s+)?(\w+\s+)?(issue|error|problem)',
            r'\bdebug\s+',
        ],
        TaskType.DELETE_FILES: [
            r'\b(delete|remove|clean\s*up|purge)\s+.*files?',
            r'\bremove\s+the\s+.*\.(json|md|txt|log)',
        ],
        TaskType.REFACTOR: [
            r'\brefactor\s+',
            r'\brestructure\s+',
            r'\breorganize\s+',
            r'\bclean\s+up\s+the\s+code',
        ],
        TaskType.ARCHITECTURE_CHANGE: [
            r'\b(migrate|convert|transform)\s+.*\s+to\s+',
            r'\breplace\s+\w+\s+with\s+',
            r'\bchange\s+the\s+architecture',
        ],
        TaskType.DOCUMENTATION: [
            r'\b(add|create|write|update)\s+.*\b(documentation|docs?|readme|guide)',
            r'\bdocument\s+(the\s+)?(code|api|codebase)',
        ],
        TaskType.CREATE_NEW_FILE: [
            r'\b(create|add|make|write)\s+(a\s+)?(new\s+)?file',
            r'\b(add|write|create)\s+a\s+(class|function|module|component)',
            r'\bwrite\s+a\s+new\s+',
            r'\bimplement\s+a\s+(simple|basic|new)\s+',
        ],
        TaskType.ADD_FEATURE: [
            r'\badd\s+(feature|functionality|capability|support\s+for)',
            r'\bimplement\s+\w+\s+(feature|functionality)',
            r'\benable\s+\w+',
        ],
        TaskType.MODIFY_EXISTING: [
            r'\b(update|modify|change|edit)\s+.*\.(py|js|ts|go|java)',
            r'\b(update|modify|change|edit)\s+(the\s+)?(\w+\s+)?(\w+\s+)?(function|class|method|file|settings?|config)',
        ],
        TaskType.QUESTION: [
            r'^(what|how|why|when|where|who)\s+',
            r'^(can|could|would|should)\s+you\s+',
            r'^(is|are|does|do)\s+',
            r'\?$',
        ],
    }
    
    # Configuration for each task type
    TASK_CONFIG = {
        TaskType.GREETING: {
            "max_files": 0,
            "needs_neo4j": False,
            "max_iterations": 1,
            "strategy": "Respond directly without using any tools",
        },
        TaskType.QUESTION: {
            "max_files": 5,
            "needs_neo4j": True,
            "max_iterations": 3,
            "strategy": "Use Neo4j to find relevant code, read minimal files to answer",
        },
        TaskType.CREATE_NEW_FILE: {
            "max_files": 3,
            "needs_neo4j": False,
            "max_iterations": 5,
            "strategy": "Read similar files as templates, create new file, verify",
        },
        TaskType.DELETE_FILES: {
            "max_files": 0,
            "needs_neo4j": False,
            "max_iterations": 3,
            "strategy": "Search for files, delete them, confirm",
        },
        TaskType.MODIFY_EXISTING: {
            "max_files": 5,
            "needs_neo4j": True,
            "max_iterations": 8,
            "strategy": "Find target files via Neo4j, read them, modify, test",
        },
        TaskType.ADD_FEATURE: {
            "max_files": 10,
            "needs_neo4j": True,
            "max_iterations": 15,
            "strategy": "Understand codebase via Neo4j, read related files, implement, test",
        },
        TaskType.FIX_BUG: {
            "max_files": 8,
            "needs_neo4j": True,
            "max_iterations": 12,
            "strategy": "Locate bug via Neo4j, read affected files, fix, verify with tests",
        },
        TaskType.REFACTOR: {
            "max_files": 20,
            "needs_neo4j": True,
            "max_iterations": 25,
            "strategy": "Map dependencies via Neo4j, read affected files, refactor, test thoroughly",
        },
        TaskType.ARCHITECTURE_CHANGE: {
            "max_files": 30,
            "needs_neo4j": True,
            "max_iterations": 30,
            "strategy": "Full codebase analysis via Neo4j, systematic changes, extensive testing",
        },
        TaskType.DOCUMENTATION: {
            "max_files": 10,
            "needs_neo4j": True,
            "max_iterations": 8,
            "strategy": "Query Neo4j for structure, read main modules, create docs",
        },
        TaskType.UNKNOWN: {
            "max_files": 15,
            "needs_neo4j": True,
            "max_iterations": 20,
            "strategy": "Conservative approach: use all available tools as needed",
        },
    }
    
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
            if task_type not in self.PATTERNS:
                continue
            patterns = self.PATTERNS[task_type]
            for pattern in patterns:
                if re.search(pattern, task_lower, re.IGNORECASE):
                    # Calculate confidence based on pattern specificity
                    confidence = self._calculate_confidence(pattern, task_lower)
                    if confidence > best_confidence:
                        best_match = task_type
                        best_confidence = confidence
        
        # Get configuration for the matched type
        config = self.TASK_CONFIG[best_match]
        
        # Adjust based on task length and complexity
        complexity_multiplier = self._assess_complexity(task)
        
        return TaskClassification(
            task_type=best_match,
            max_files_to_read=int(config["max_files"] * complexity_multiplier),
            needs_neo4j=config["needs_neo4j"],
            max_iterations=int(config["max_iterations"] * complexity_multiplier),
            suggested_strategy=config["strategy"],
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
        if pattern.startswith('^') and pattern.endswith('$'):
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
        simple_indicators = [
            "simple", "basic", "quick", "small", "single",
            "just", "only", "one"
        ]
        
        # Complex tasks
        complex_indicators = [
            "complex", "entire", "all", "multiple", "refactor",
            "migrate", "overhaul", "redesign", "comprehensive"
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
        hints = {
            TaskType.CREATE_NEW_FILE: "Look for similar files as templates",
            TaskType.DELETE_FILES: "Search for files matching the pattern",
            TaskType.MODIFY_EXISTING: "Find and read only the target file(s)",
            TaskType.ADD_FEATURE: "Find related modules and their dependencies",
            TaskType.FIX_BUG: "Locate the buggy code and its test files",
            TaskType.REFACTOR: "Map all dependencies and affected files",
            TaskType.DOCUMENTATION: "Read main entry points and public APIs",
            TaskType.QUESTION: "Find relevant code sections to answer the question",
        }
        
        return hints.get(classification.task_type, "Gather context as needed")

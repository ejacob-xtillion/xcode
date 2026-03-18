"""
Classification service for task analysis.
"""
import re

from xcode.models import Task, TaskClassification, TaskType


class ClassificationService:
    """Service for classifying tasks to optimize agent execution."""
    
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
    
    def classify(self, task: Task) -> TaskClassification:
        """
        Classify a task to determine optimal execution strategy.
        
        Args:
            task: The task to classify
            
        Returns:
            TaskClassification with execution parameters
        """
        task_lower = task.description.lower().strip()
        
        # Try to match patterns in priority order
        priority_order = [
            TaskType.GREETING,
            TaskType.FIX_BUG,
            TaskType.DELETE_FILES,
            TaskType.REFACTOR,
            TaskType.ARCHITECTURE_CHANGE,
            TaskType.DOCUMENTATION,
            TaskType.CREATE_NEW_FILE,
            TaskType.ADD_FEATURE,
            TaskType.MODIFY_EXISTING,
            TaskType.QUESTION,
        ]
        
        best_match = TaskType.UNKNOWN
        best_confidence = 0.0
        
        for task_type in priority_order:
            if task_type not in self.PATTERNS:
                continue
            patterns = self.PATTERNS[task_type]
            for pattern in patterns:
                if re.search(pattern, task_lower, re.IGNORECASE):
                    confidence = self._calculate_confidence(pattern, task_lower)
                    if confidence > best_confidence:
                        best_match = task_type
                        best_confidence = confidence
        
        # Get configuration for the matched type
        config = self.TASK_CONFIG[best_match]
        
        # Adjust based on task length and complexity
        complexity_multiplier = self._assess_complexity(task.description)
        
        return TaskClassification(
            task_type=best_match,
            max_files_to_read=int(config["max_files"] * complexity_multiplier),
            needs_neo4j=config["needs_neo4j"],
            max_iterations=int(config["max_iterations"] * complexity_multiplier),
            suggested_strategy=config["strategy"],
            confidence=best_confidence,
        )
    
    def _calculate_confidence(self, pattern: str, task: str) -> float:
        """Calculate confidence score for a pattern match."""
        match = re.search(pattern, task, re.IGNORECASE)
        if not match:
            return 0.0
        
        confidence = 0.7
        
        if match.start() == 0:
            confidence += 0.15
        
        if pattern.startswith('^') and pattern.endswith('$'):
            confidence += 0.15
        
        pattern_length = len(pattern)
        if pattern_length > 30:
            confidence += 0.1
        elif pattern_length > 20:
            confidence += 0.05
        
        return min(confidence, 1.0)
    
    def _assess_complexity(self, task_description: str) -> float:
        """Assess task complexity to adjust limits."""
        simple_indicators = [
            "simple", "basic", "quick", "small", "single",
            "just", "only", "one"
        ]
        
        complex_indicators = [
            "complex", "entire", "all", "multiple", "refactor",
            "migrate", "overhaul", "redesign", "comprehensive"
        ]
        
        task_lower = task_description.lower()
        
        simple_count = sum(1 for word in simple_indicators if word in task_lower)
        complex_count = sum(1 for word in complex_indicators if word in task_lower)
        
        if simple_count > complex_count:
            return 0.7
        elif complex_count > simple_count:
            return 1.5
        else:
            return 1.0
    
    def get_context_hint(self, classification: TaskClassification) -> str:
        """Get a hint for what context to gather."""
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

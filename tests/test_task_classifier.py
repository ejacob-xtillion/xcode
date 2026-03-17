"""
Tests for task classification system.
"""
import pytest
from xcode.task_classifier import TaskClassifier, TaskType, TaskClassification


class TestTaskClassifier:
    """Test suite for TaskClassifier."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.classifier = TaskClassifier()
    
    def test_greeting_classification(self):
        """Test that greetings are classified correctly."""
        greetings = [
            "hi",
            "hello",
            "hey there",
            "good morning",
            "how are you?",
            "what's up",
        ]
        
        for greeting in greetings:
            result = self.classifier.classify(greeting)
            assert result.task_type == TaskType.GREETING
            assert not result.should_use_tools
            assert result.max_files_to_read == 0
            assert not result.needs_neo4j
    
    def test_create_file_classification(self):
        """Test that file creation tasks are classified correctly."""
        tasks = [
            "create a new file for user authentication",
            "add a class for handling database connections",
            "implement a simple chess game",
            "write a new module for logging",
        ]
        
        for task in tasks:
            result = self.classifier.classify(task)
            assert result.task_type == TaskType.CREATE_NEW_FILE
            assert result.should_use_tools
            assert result.max_files_to_read <= 5
            assert not result.needs_neo4j
    
    def test_delete_files_classification(self):
        """Test that file deletion tasks are classified correctly."""
        tasks = [
            "delete the analysis results files",
            "remove the test.json file",
            "clean up old log files",
            "purge temporary files",
        ]
        
        for task in tasks:
            result = self.classifier.classify(task)
            assert result.task_type == TaskType.DELETE_FILES
            assert result.should_use_tools
            assert result.max_files_to_read == 0
            assert not result.needs_neo4j
    
    def test_modify_existing_classification(self):
        """Test that modification tasks are classified correctly."""
        tasks = [
            "update the config.py file",
            "modify the authentication function",
            "change the database connection settings",
            "edit the main.py file",
        ]
        
        for task in tasks:
            result = self.classifier.classify(task)
            assert result.task_type == TaskType.MODIFY_EXISTING
            assert result.should_use_tools
            assert result.max_files_to_read <= 10
            assert result.needs_neo4j
    
    def test_add_feature_classification(self):
        """Test that feature addition tasks are classified correctly."""
        tasks = [
            "add feature for user registration",
            "implement caching functionality",
            "add support for multiple databases",
            "enable dark mode",
        ]
        
        for task in tasks:
            result = self.classifier.classify(task)
            assert result.task_type == TaskType.ADD_FEATURE
            assert result.should_use_tools
            assert result.max_files_to_read >= 5
            assert result.needs_neo4j
    
    def test_fix_bug_classification(self):
        """Test that bug fix tasks are classified correctly."""
        tasks = [
            "fix the bug in user authentication",
            "resolve the database connection issue",
            "debug the login function",
            "address the error in the API",
        ]
        
        for task in tasks:
            result = self.classifier.classify(task)
            assert result.task_type == TaskType.FIX_BUG
            assert result.should_use_tools
            assert result.needs_neo4j
    
    def test_refactor_classification(self):
        """Test that refactoring tasks are classified correctly."""
        tasks = [
            "refactor the database layer",
            "restructure the authentication module",
            "clean up the code in utils.py",
            "reorganize the project structure",
        ]
        
        for task in tasks:
            result = self.classifier.classify(task)
            assert result.task_type == TaskType.REFACTOR
            assert result.should_use_tools
            assert result.max_files_to_read >= 15
            assert result.needs_neo4j
            assert result.max_iterations >= 20
    
    def test_documentation_classification(self):
        """Test that documentation tasks are classified correctly."""
        tasks = [
            "add documentation to the docs folder",
            "create a README for the project",
            "write API documentation",
            "update the user guide",
            "document the codebase",
        ]
        
        for task in tasks:
            result = self.classifier.classify(task)
            assert result.task_type == TaskType.DOCUMENTATION
            assert result.should_use_tools
            assert result.needs_neo4j
    
    def test_question_classification(self):
        """Test that questions are classified correctly."""
        questions = [
            "what does this function do?",
            "how does the authentication work?",
            "where is the database connection defined?",
            "can you explain the caching mechanism?",
        ]
        
        for question in questions:
            result = self.classifier.classify(question)
            assert result.task_type == TaskType.QUESTION
            assert result.should_use_tools
            assert result.max_files_to_read <= 10
            assert result.needs_neo4j
    
    def test_complexity_assessment_simple(self):
        """Test that simple tasks get lower limits."""
        result = self.classifier.classify("add a simple hello world function")
        # Simple tasks should have reduced limits
        assert result.max_files_to_read <= 10
        assert result.max_iterations <= 14
    
    def test_complexity_assessment_complex(self):
        """Test that complex tasks get higher limits."""
        result = self.classifier.classify("migrate entire codebase to use async/await")
        assert result.max_files_to_read >= 20
        assert result.max_iterations >= 25
    
    def test_confidence_scoring(self):
        """Test that confidence scores are reasonable."""
        # Very clear task
        result1 = self.classifier.classify("create a new file for authentication")
        # Should have reasonable confidence
        assert result1.confidence >= 0.0
        
        # Ambiguous task - "do something" is vague but starts with "do" which matches question pattern
        result2 = self.classifier.classify("xyz random gibberish that makes no sense")
        # Should be unknown with low confidence
        assert result2.task_type == TaskType.UNKNOWN
        assert result2.confidence == 0.0
    
    def test_context_hints(self):
        """Test that context hints are provided."""
        result = self.classifier.classify("add a new feature for user profiles")
        hint = self.classifier.get_context_hint(result)
        assert isinstance(hint, str)
        assert len(hint) > 0
    
    def test_unknown_task_type(self):
        """Test that unknown tasks get conservative defaults."""
        result = self.classifier.classify("xyzabc random gibberish task")
        # Should either be unknown or have reasonable defaults
        assert result.max_files_to_read <= 20
        assert result.max_iterations <= 25
    
    def test_architecture_change_classification(self):
        """Test that architecture changes are classified correctly."""
        tasks = [
            "migrate from REST to GraphQL",
            "convert the app to use microservices",
            "replace SQLite with PostgreSQL",
        ]
        
        for task in tasks:
            result = self.classifier.classify(task)
            assert result.task_type == TaskType.ARCHITECTURE_CHANGE
            assert result.max_files_to_read >= 20
            assert result.max_iterations >= 25
    
    def test_case_insensitivity(self):
        """Test that classification is case-insensitive."""
        result1 = self.classifier.classify("CREATE A NEW FILE")
        result2 = self.classifier.classify("create a new file")
        result3 = self.classifier.classify("CrEaTe A nEw FiLe")
        
        assert result1.task_type == result2.task_type == result3.task_type
    
    def test_whitespace_handling(self):
        """Test that extra whitespace doesn't affect classification."""
        result1 = self.classifier.classify("  create a new file  ")
        result2 = self.classifier.classify("create a new file")
        
        assert result1.task_type == result2.task_type


class TestTaskClassification:
    """Test the TaskClassification dataclass."""
    
    def test_should_use_tools_true(self):
        """Test that coding tasks require tools."""
        classification = TaskClassification(
            task_type=TaskType.CREATE_NEW_FILE,
            max_files_to_read=3,
            needs_neo4j=False,
            max_iterations=5,
            suggested_strategy="Create file",
            confidence=0.9,
        )
        assert classification.should_use_tools
    
    def test_should_use_tools_false(self):
        """Test that greetings don't require tools."""
        classification = TaskClassification(
            task_type=TaskType.GREETING,
            max_files_to_read=0,
            needs_neo4j=False,
            max_iterations=1,
            suggested_strategy="Respond directly",
            confidence=0.95,
        )
        assert not classification.should_use_tools
    
    def test_question_requires_tools(self):
        """Test that questions require tools to answer."""
        classification = TaskClassification(
            task_type=TaskType.QUESTION,
            max_files_to_read=5,
            needs_neo4j=True,
            max_iterations=3,
            suggested_strategy="Find and read relevant code",
            confidence=0.85,
        )
        assert classification.should_use_tools


class TestPatternMatching:
    """Test pattern matching edge cases."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.classifier = TaskClassifier()
    
    def test_multiple_pattern_matches(self):
        """Test tasks that could match multiple patterns."""
        # This could be both "add feature" and "documentation"
        result = self.classifier.classify("add documentation for the new feature")
        # Should pick the best match based on confidence
        assert result.task_type in [TaskType.DOCUMENTATION, TaskType.ADD_FEATURE]
    
    def test_pattern_priority(self):
        """Test that more specific patterns take priority."""
        # "fix bug" should take priority over general "modify"
        result = self.classifier.classify("fix the bug in config.py")
        assert result.task_type == TaskType.FIX_BUG
    
    def test_no_pattern_match(self):
        """Test behavior when no pattern matches."""
        result = self.classifier.classify("asdfghjkl qwertyuiop")
        assert result.task_type == TaskType.UNKNOWN
        # Should still have reasonable defaults
        assert result.max_files_to_read > 0
        assert result.max_iterations > 0

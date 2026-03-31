"""
Tests for the formatting module.
"""

from io import StringIO
from pathlib import Path
from types import SimpleNamespace

import pytest
from rich.console import Console

from xcode.formatting import (
    ErrorFormatter,
    OutputFormatter,
    RefactoringFormatter,
    TaskFormatter,
    VerificationFormatter,
    create_formatter,
    final_answer_panel,
    print_final_answer,
)


@pytest.fixture
def console():
    """Create a console that writes to a string buffer for testing."""
    string_io = StringIO()
    return Console(file=string_io, force_terminal=True, width=80)


@pytest.fixture
def output_formatter(console):
    """Create an OutputFormatter instance."""
    return OutputFormatter(console)


@pytest.fixture
def refactoring_formatter(console):
    """Create a RefactoringFormatter instance."""
    return RefactoringFormatter(console)


@pytest.fixture
def task_formatter(console):
    """Create a TaskFormatter instance."""
    return TaskFormatter(console)


@pytest.fixture
def verification_formatter(console):
    """Create a VerificationFormatter instance."""
    return VerificationFormatter(console)


@pytest.fixture
def error_formatter(console):
    """Create an ErrorFormatter instance."""
    return ErrorFormatter(console)


class TestOutputFormatter:
    """Tests for the base OutputFormatter class."""

    def test_section_header(self, output_formatter, console):
        """Test section header formatting."""
        output_formatter.section_header("Test Section")
        output = console.file.getvalue()
        assert "Test Section" in output
        assert "─" in output

    def test_subsection(self, output_formatter, console):
        """Test subsection formatting."""
        output_formatter.subsection("Test Subsection")
        output = console.file.getvalue()
        assert "Test Subsection" in output
        assert "•" in output

    def test_bullet(self, output_formatter, console):
        """Test bullet point formatting."""
        output_formatter.bullet("Test bullet")
        output = console.file.getvalue()
        assert "Test bullet" in output
        assert "•" in output

    def test_nested_bullet(self, output_formatter, console):
        """Test nested bullet formatting."""
        output_formatter.nested_bullet("Nested item")
        output = console.file.getvalue()
        assert "Nested item" in output
        assert "├─" in output

    def test_key_value(self, output_formatter, console):
        """Test key-value pair formatting."""
        output_formatter.key_value("Key", "Value")
        output = console.file.getvalue()
        assert "Key" in output
        assert "Value" in output

    def test_success(self, output_formatter, console):
        """Test success message formatting."""
        output_formatter.success("Success message")
        output = console.file.getvalue()
        assert "Success message" in output
        assert "✓" in output

    def test_warning(self, output_formatter, console):
        """Test warning message formatting."""
        output_formatter.warning("Warning message")
        output = console.file.getvalue()
        assert "Warning message" in output
        assert "⚠" in output

    def test_error(self, output_formatter, console):
        """Test error message formatting."""
        output_formatter.error("Error message")
        output = console.file.getvalue()
        assert "Error message" in output
        assert "✗" in output

    def test_info(self, output_formatter, console):
        """Test info message formatting."""
        output_formatter.info("Info message")
        output = console.file.getvalue()
        assert "Info message" in output
        assert "ℹ" in output

    def test_code_block(self, output_formatter, console):
        """Test code block formatting."""
        output_formatter.code_block('print("hello")', language="python")
        output = console.file.getvalue()
        assert "print" in output
        assert "hello" in output

    def test_panel(self, output_formatter, console):
        """Test panel formatting."""
        output_formatter.panel("Panel content", title="Test Panel")
        output = console.file.getvalue()
        assert "Panel content" in output
        assert "Test Panel" in output

    def test_table(self, output_formatter, console):
        """Test table creation."""
        table = output_formatter.table(
            title="Test Table",
            headers=["Col1", "Col2"],
            rows=[["A", "B"], ["C", "D"]],
        )
        console.print(table)
        output = console.file.getvalue()
        assert "Test Table" in output
        assert "Col1" in output
        assert "Col2" in output
        assert "A" in output
        assert "B" in output

    def test_file_tree(self, output_formatter, console):
        """Test file tree formatting."""
        files = ["dir1/file1.py", "dir1/file2.py", "dir2/file3.py"]
        output_formatter.file_tree(files, title="Files")
        output = console.file.getvalue()
        assert "Files" in output
        assert "file1.py" in output
        assert "file2.py" in output
        assert "file3.py" in output

    def test_separator(self, output_formatter, console):
        """Test separator formatting."""
        output_formatter.separator()
        output = console.file.getvalue()
        assert "─" in output

    def test_markdown(self, output_formatter, console):
        """Test markdown rendering."""
        output_formatter.markdown("# Heading\n\n**Bold text**")
        output = console.file.getvalue()
        assert "Heading" in output
        assert "Bold text" in output


class TestRefactoringFormatter:
    """Tests for the RefactoringFormatter class."""

    def test_print_refactoring_summary_basic(self, refactoring_formatter, console):
        """Test basic refactoring summary."""
        refactoring_formatter.print_refactoring_summary(
            title="Test Refactoring",
            changes={
                "file1.py": ["Change 1", "Change 2"],
                "file2.py": ["Change 3"],
            },
        )
        output = console.file.getvalue()
        assert "Test Refactoring" in output
        assert "file1.py" in output
        assert "file2.py" in output
        assert "Change 1" in output
        assert "Change 2" in output
        assert "Change 3" in output

    def test_print_refactoring_summary_with_usage(self, refactoring_formatter, console):
        """Test refactoring summary with usage guide."""
        refactoring_formatter.print_refactoring_summary(
            title="Test Refactoring",
            changes={"file1.py": ["Change 1"]},
            usage_guide={"title": "How to use", "steps": ["Step 1", "Step 2"]},
        )
        output = console.file.getvalue()
        assert "How to use" in output
        assert "Step 1" in output
        assert "Step 2" in output

    def test_print_refactoring_summary_with_example(self, refactoring_formatter, console):
        """Test refactoring summary with example code."""
        refactoring_formatter.print_refactoring_summary(
            title="Test Refactoring",
            changes={"file1.py": ["Change 1"]},
            example_code='print("example")',
        )
        output = console.file.getvalue()
        assert "example" in output

    def test_print_refactoring_summary_with_notes(self, refactoring_formatter, console):
        """Test refactoring summary with notes."""
        refactoring_formatter.print_refactoring_summary(
            title="Test Refactoring",
            changes={"file1.py": ["Change 1"]},
            notes=[
                {"type": "warning", "message": "Warning note"},
                {"type": "info", "message": "Info note"},
            ],
        )
        output = console.file.getvalue()
        assert "Warning note" in output
        assert "Info note" in output

    def test_print_refactoring_summary_with_verification(self, refactoring_formatter, console):
        """Test refactoring summary with verification."""
        refactoring_formatter.print_refactoring_summary(
            title="Test Refactoring",
            changes={"file1.py": ["Change 1"]},
            verification={"passed": 10, "duration": "1.5s", "details": ["Detail 1"]},
        )
        output = console.file.getvalue()
        assert "10 passed" in output
        assert "1.5s" in output
        assert "Detail 1" in output


class TestTaskFormatter:
    """Tests for the TaskFormatter class."""

    def test_print_task_start(self, task_formatter, console):
        """Test task start formatting."""
        task_formatter.print_task_start(
            task="Test task", repo_path=Path("/test/repo"), model="gpt-4"
        )
        output = console.file.getvalue()
        assert "Test task" in output
        assert "/test/repo" in output
        assert "gpt-4" in output

    def test_print_task_complete_success(self, task_formatter, console):
        """Test task completion formatting (success)."""
        task_formatter.print_task_complete(
            success=True, duration="2.5s", iterations=3, modified_files=["file1.py", "file2.py"]
        )
        output = console.file.getvalue()
        assert "completed successfully" in output or "✓" in output
        assert "2.5s" in output
        assert "3" in output
        assert "file1.py" in output

    def test_print_task_complete_failure(self, task_formatter, console):
        """Test task completion formatting (failure)."""
        task_formatter.print_task_complete(success=False)
        output = console.file.getvalue()
        assert "failed" in output or "✗" in output


class TestVerificationFormatter:
    """Tests for the VerificationFormatter class."""

    def test_print_verification_start(self, verification_formatter, console):
        """Test verification start formatting."""
        verification_formatter.print_verification_start()
        output = console.file.getvalue()
        assert "verification" in output.lower()

    def test_print_test_discovery(self, verification_formatter, console):
        """Test test discovery formatting."""
        verification_formatter.print_test_discovery(
            related_tests=5, untested_callables=2, modified_files=["file1.py"]
        )
        output = console.file.getvalue()
        assert "5" in output
        assert "2" in output
        assert "file1.py" in output

    def test_print_test_generation(self, verification_formatter, console):
        """Test test generation formatting."""
        verification_formatter.print_test_generation(count=3)
        output = console.file.getvalue()
        assert "3" in output
        assert "test" in output.lower()

    def test_print_verification_result_success(self, verification_formatter, console):
        """Test verification result formatting (success)."""
        verification_formatter.print_verification_result(
            success=True, checks_run=["pytest", "ruff"]
        )
        output = console.file.getvalue()
        assert "passed" in output.lower() or "✓" in output
        assert "pytest" in output
        assert "ruff" in output

    def test_print_verification_result_failure(self, verification_formatter, console):
        """Test verification result formatting (failure)."""
        verification_formatter.print_verification_result(
            success=False, checks_run=["pytest"], output="Test failed", fix_attempts=2
        )
        output = console.file.getvalue()
        assert "failed" in output.lower() or "✗" in output
        assert "2" in output


class TestErrorFormatter:
    """Tests for the ErrorFormatter class."""

    def test_print_error_basic(self, error_formatter, console):
        """Test basic error formatting."""
        error_formatter.print_error(error="Test error")
        output = console.file.getvalue()
        assert "Test error" in output
        assert "Error" in output

    def test_print_error_with_context(self, error_formatter, console):
        """Test error formatting with context."""
        error_formatter.print_error(error="Test error", context="Additional context")
        output = console.file.getvalue()
        assert "Test error" in output
        assert "Additional context" in output

    def test_print_error_with_suggestions(self, error_formatter, console):
        """Test error formatting with suggestions."""
        error_formatter.print_error(
            error="Test error", suggestions=["Suggestion 1", "Suggestion 2"]
        )
        output = console.file.getvalue()
        assert "Test error" in output
        assert "Suggestion 1" in output
        assert "Suggestion 2" in output


class TestCreateFormatter:
    """Tests for the create_formatter factory function."""

    def test_create_default_formatter(self, console):
        """Test creating default formatter."""
        formatter = create_formatter(console, "default")
        assert isinstance(formatter, OutputFormatter)

    def test_create_refactoring_formatter(self, console):
        """Test creating refactoring formatter."""
        formatter = create_formatter(console, "refactoring")
        assert isinstance(formatter, RefactoringFormatter)

    def test_create_task_formatter(self, console):
        """Test creating task formatter."""
        formatter = create_formatter(console, "task")
        assert isinstance(formatter, TaskFormatter)

    def test_create_verification_formatter(self, console):
        """Test creating verification formatter."""
        formatter = create_formatter(console, "verification")
        assert isinstance(formatter, VerificationFormatter)

    def test_create_error_formatter(self, console):
        """Test creating error formatter."""
        formatter = create_formatter(console, "error")
        assert isinstance(formatter, ErrorFormatter)

    def test_create_unknown_formatter_returns_default(self, console):
        """Test creating unknown formatter returns default."""
        formatter = create_formatter(console, "unknown")
        assert isinstance(formatter, OutputFormatter)


class TestFinalAnswerFormatting:
    """Tests for agent final-answer Panel/Markdown output."""

    def test_final_answer_panel_narrow_terminal(self):
        # Only `console.size.width` is used; avoid relying on StringIO Console sizing.
        c = SimpleNamespace(size=SimpleNamespace(width=60))
        p = final_answer_panel("Line one\n\nLine **two**", c)
        assert p.width == 60

    def test_final_answer_panel_wide_terminal_capped(self):
        c = SimpleNamespace(size=SimpleNamespace(width=200))
        p = final_answer_panel("Hi", c)
        assert p.width == 102

    def test_print_final_answer_renders_markdown(self):
        buf = StringIO()
        c = Console(file=buf, force_terminal=True, width=80)
        print_final_answer(c, "# Title\n\nSome **bold** text.")
        out = buf.getvalue()
        assert "Title" in out
        assert "bold" in out

    def test_print_final_answer_whitespace_only_is_silent(self):
        buf = StringIO()
        c = Console(file=buf, force_terminal=True, width=80)
        print_final_answer(c, "   \n  ")
        assert buf.getvalue() == ""

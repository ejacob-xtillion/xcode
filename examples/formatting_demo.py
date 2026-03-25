"""
Demo script showing rich CLI formatting capabilities.

Run this to see examples of all formatting options.
"""

from pathlib import Path

from rich.console import Console

from xcode.formatting import (
    ErrorFormatter,
    RefactoringFormatter,
    TaskFormatter,
    VerificationFormatter,
    create_formatter,
)


def demo_refactoring_summary():
    """Demonstrate refactoring summary formatting."""
    console = Console()
    formatter = RefactoringFormatter(console)

    formatter.print_refactoring_summary(
        title="Polars Backend Support Added",
        changes={
            "restricted_pandas.py": [
                "Added optional Polars backend with a single class interface",
                "New constructor signature: RestrictedDataFrame(data, *, backend=\"pandas\")",
                "  backend=\"pandas\" (default): stores data as pandas.DataFrame",
                "  backend=\"polars\": stores data as polars.DataFrame",
                "Accepts pandas.DataFrame, polars.DataFrame, dict (column → list), or CSV path",
                "Implemented filter/select/sort/aggregate paths for both backends",
                "Public return types are consistent with original pandas expectations",
                "Polars is optional at runtime; import guarded with clear RuntimeError",
            ],
            "analytics.py": [
                "Kept using pandas types in signatures and return types",
                "No behavioral change needed since RestrictedDataFrame abstracts backend",
            ],
            "records.py": [
                "Kept using pandas for DataFrame builders "
                "(employees_to_dataframe, sales_to_dataframe)",
                "Ensures zero extra dependencies for tests and normal pandas workflows",
            ],
        },
        usage_guide={
            "title": "How to use Polars now",
            "steps": [
                "Keep your existing code as-is (it will use pandas by default)",
                "To run analytics on a Polars backend:",
                "  Pass backend=\"polars\" when constructing the RestrictedDataFrame",
                "  Downstream code can remain unchanged "
                "(RestrictedDataFrame returns pandas objects)",
            ],
        },
        example_code="""from records import employees_to_dataframe, sample_employees
from restricted_pandas import RestrictedDataFrame
from analytics import SalaryAnalyzer

# Build pandas DataFrame
df = employees_to_dataframe(sample_employees())

# Use Polars backend internally
rdf = RestrictedDataFrame(df, backend="polars")

# Existing analytics works the same; results are pandas objects
analyzer = SalaryAnalyzer(rdf)
mean_by_dept = analyzer.mean_salary_by_department()  # pandas.Series
top3 = analyzer.top_salaries(3)                      # pandas.DataFrame""",
        notes=[
            {
                "type": "warning",
                "title": "Note about pyarrow",
                "message": (
                    "If you pass a Polars DataFrame into RestrictedDataFrame "
                    'with backend="pandas", Polars may require pyarrow for '
                    'efficient conversion. Install pyarrow or use backend="polars" '
                    "to avoid this."
                ),
            }
        ],
        verification={
            "passed": 11,
            "duration": "0.71s",
            "details": ["All existing tests pass with pandas backend", "New Polars tests added"],
        },
        modified_files=[
            "restricted_pandas.py",
            "analytics.py",
            "records.py",
            "tests/test_restricted_pandas.py",
        ],
    )


def demo_task_execution():
    """Demonstrate task execution formatting."""
    console = Console()
    formatter = TaskFormatter(console)

    formatter.print_task_start(
        task="Add logging to main.py",
        repo_path=Path("/Users/elijahgjacob/xcode"),
        model="gpt-4",
    )

    # Simulate some work
    console.print("[dim]Analyzing codebase...[/dim]")
    console.print("[dim]Generating changes...[/dim]")
    console.print("[dim]Applying modifications...[/dim]")

    formatter.print_task_complete(
        success=True,
        duration="2.3s",
        iterations=3,
        modified_files=["xcode/main.py", "xcode/utils/logger.py"],
    )


def demo_verification():
    """Demonstrate verification formatting."""
    console = Console()
    formatter = VerificationFormatter(console)

    formatter.print_verification_start()
    formatter.print_test_discovery(
        related_tests=5,
        untested_callables=2,
        modified_files=["xcode/main.py", "xcode/utils/logger.py"],
    )
    formatter.print_test_generation(count=2)

    console.print("[dim]Running pytest...[/dim]")
    console.print("[dim]Running ruff...[/dim]")

    formatter.print_verification_result(
        success=True, checks_run=["pytest", "ruff"], output=None, fix_attempts=0
    )


def demo_error_handling():
    """Demonstrate error formatting."""
    console = Console()
    formatter = ErrorFormatter(console)

    formatter.print_error(
        error="Neo4j connection failed",
        context="Attempted to connect to bolt://localhost:7687",
        suggestions=[
            "Check that Neo4j is running: docker-compose ps",
            "Verify NEO4J_URI in .env file",
            "Try restarting Neo4j: docker-compose restart neo4j",
        ],
        verbose=False,
    )


def demo_basic_formatting():
    """Demonstrate basic formatting utilities."""
    console = Console()
    formatter = create_formatter(console, "default")

    formatter.section_header("Basic Formatting Demo")

    formatter.subsection("Success Messages")
    formatter.success("Operation completed successfully")
    formatter.success("All tests passed", prefix="✓")

    formatter.subsection("Warning Messages")
    formatter.warning("Deprecated API usage detected")
    formatter.warning("Missing optional dependency", prefix="⚠")

    formatter.subsection("Error Messages")
    formatter.error("File not found")
    formatter.error("Invalid configuration", prefix="✗")

    formatter.subsection("Info Messages")
    formatter.info("Processing 10 files...")
    formatter.info("Using default configuration", prefix="ℹ")

    formatter.subsection("Bullet Lists")
    formatter.bullet("First item")
    formatter.bullet("Second item")
    formatter.nested_bullet("Nested item 1")
    formatter.nested_bullet("Nested item 2")
    formatter.bullet("Third item")

    formatter.subsection("Key-Value Pairs")
    formatter.key_value("Repository", "/Users/elijahgjacob/xcode")
    formatter.key_value("Language", "Python")
    formatter.key_value("Model", "gpt-4")

    formatter.subsection("Code Block")
    formatter.code_block(
        code='def hello():\n    print("Hello, World!")',
        language="python",
        title="Example Function",
        line_numbers=True,
    )

    formatter.subsection("Panel")
    formatter.panel(
        "This is important information displayed in a panel.",
        title="Important",
        border_style="yellow",
    )

    formatter.subsection("Table")
    table = formatter.table(
        title="Test Results",
        headers=["Test", "Status", "Duration"],
        rows=[
            ["test_login", "✓ Passed", "0.12s"],
            ["test_logout", "✓ Passed", "0.08s"],
            ["test_register", "✗ Failed", "0.15s"],
        ],
    )
    console.print(table)

    formatter.subsection("File Tree")
    formatter.file_tree(
        files=[
            "xcode/cli.py",
            "xcode/orchestrator.py",
            "xcode/services/agent_service.py",
            "xcode/services/graph_service.py",
            "tests/test_cli.py",
        ],
        title="Modified Files",
    )

    formatter.subsection("Markdown")
    formatter.markdown(
        """
# Markdown Support

You can use **bold**, *italic*, and `code` formatting.

- Bullet points
- Are supported
- Too

1. As well as
2. Numbered lists
"""
    )


def main():
    """Run all formatting demos."""
    console = Console()

    demos = [
        ("Refactoring Summary", demo_refactoring_summary),
        ("Task Execution", demo_task_execution),
        ("Verification", demo_verification),
        ("Error Handling", demo_error_handling),
        ("Basic Formatting", demo_basic_formatting),
    ]

    for i, (name, demo_func) in enumerate(demos):
        if i > 0:
            console.print("\n" + "=" * 80 + "\n")

        console.print(f"[bold cyan]Demo {i + 1}: {name}[/bold cyan]\n")
        demo_func()


if __name__ == "__main__":
    main()

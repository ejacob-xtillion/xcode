"""
Test discovery service - finds tests related to modified code using Neo4j.
"""

from pathlib import Path

from rich.console import Console

from xcode.domain.interfaces import GraphRepository
from xcode.models.test_info import CallableInfo, TestInfo


class TestDiscoveryService:
    """Discovers tests related to modified code using Neo4j knowledge graph."""

    def __init__(self, graph_repo: GraphRepository, console: Console):
        self.graph_repo = graph_repo
        self.console = console

    def find_tests_for_files(
        self, file_paths: list[str], project_name: str
    ) -> dict[str, list[TestInfo]]:
        """
        Find all tests related to modified files.

        Uses multiple Neo4j queries:
        1. Find tests that directly test callables in modified files
        2. Find test files that import the modified files

        Args:
            file_paths: List of relative file paths that were modified
            project_name: Name of the project in Neo4j

        Returns:
            Dict mapping file_path -> list of related TestInfo objects
        """
        if not file_paths:
            return {}

        tests_by_file = {}

        for file_path in file_paths:
            related_tests = []

            # Query 1: Find tests for callables in this file
            try:
                cypher = """
                MATCH (p:Project {name: $project_name})
                MATCH (p)<-[:INCLUDED_IN*]-(f:File)
                WHERE f.path = $file_path
                MATCH (f)<-[:DECLARED_IN]-(c:Callable)
                MATCH (c)<-[:TESTS]-(t:Test)
                RETURN DISTINCT t.name as name, t.path as path, 
                       coalesce(t.line_number, 0) as line_number,
                       c.name as tests_callable
                """
                results = self.graph_repo.query(
                    cypher, {"project_name": project_name, "file_path": file_path}
                )

                for record in results:
                    related_tests.append(
                        TestInfo(
                            name=record["name"],
                            path=record["path"],
                            line_number=record["line_number"],
                            tests_callable=record.get("tests_callable"),
                        )
                    )
            except Exception as e:
                self.console.print(
                    f"[yellow]Warning: Failed to query tests for {file_path}: {e}[/yellow]"
                )

            # Query 2: Find test files that import this module
            try:
                module_name = Path(file_path).stem
                cypher = """
                MATCH (p:Project {name: $project_name})
                MATCH (p)<-[:INCLUDED_IN*]-(f:File)
                WHERE f.path CONTAINS 'test'
                MATCH (f)-[:IMPORTS]->(m:Module)
                WHERE m.name = $module_name OR m.name CONTAINS $module_name
                MATCH (f)<-[:DECLARED_IN]-(t:Test)
                RETURN DISTINCT t.name as name, t.path as path,
                       coalesce(t.line_number, 0) as line_number
                """
                results = self.graph_repo.query(
                    cypher, {"project_name": project_name, "module_name": module_name}
                )

                for record in results:
                    test_info = TestInfo(
                        name=record["name"],
                        path=record["path"],
                        line_number=record["line_number"],
                        tests_callable=None,
                    )
                    if test_info not in related_tests:
                        related_tests.append(test_info)
            except Exception as e:
                self.console.print(
                    f"[yellow]Warning: Failed to query test imports for {file_path}: {e}[/yellow]"
                )

            tests_by_file[file_path] = related_tests

        return tests_by_file

    def find_untested_callables(
        self, file_paths: list[str], project_name: str
    ) -> list[CallableInfo]:
        """
        Find callables in modified files that have no test coverage.

        Args:
            file_paths: List of relative file paths that were modified
            project_name: Name of the project in Neo4j

        Returns:
            List of CallableInfo objects for untested callables
        """
        if not file_paths:
            return []

        untested = []

        for file_path in file_paths:
            try:
                cypher = """
                MATCH (p:Project {name: $project_name})
                MATCH (p)<-[:INCLUDED_IN*]-(f:File)
                WHERE f.path = $file_path
                MATCH (f)<-[:DECLARED_IN]-(c:Callable)
                WHERE NOT (c:Test) 
                  AND NOT EXISTS((c)<-[:TESTS]-())
                RETURN c.name as name, 
                       coalesce(c.signature, c.name) as signature,
                       f.path as file_path,
                       coalesce(c.line_number, 0) as line_number
                LIMIT 50
                """
                results = self.graph_repo.query(
                    cypher, {"project_name": project_name, "file_path": file_path}
                )

                for record in results:
                    untested.append(
                        CallableInfo(
                            name=record["name"],
                            signature=record["signature"],
                            file_path=record["file_path"],
                            line_number=record["line_number"],
                            is_tested=False,
                        )
                    )
            except Exception as e:
                self.console.print(
                    f"[yellow]Warning: Failed to query untested callables for {file_path}: {e}[/yellow]"
                )

        return untested

    def get_test_summary(
        self, file_paths: list[str], project_name: str
    ) -> dict[str, any]:
        """
        Get a summary of test coverage for modified files.

        Args:
            file_paths: List of relative file paths
            project_name: Name of the project

        Returns:
            Dict with coverage statistics
        """
        tests_by_file = self.find_tests_for_files(file_paths, project_name)
        untested = self.find_untested_callables(file_paths, project_name)

        total_tests = sum(len(tests) for tests in tests_by_file.values())
        files_with_tests = sum(1 for tests in tests_by_file.values() if tests)
        files_without_tests = len(file_paths) - files_with_tests

        return {
            "total_modified_files": len(file_paths),
            "files_with_tests": files_with_tests,
            "files_without_tests": files_without_tests,
            "total_related_tests": total_tests,
            "untested_callables": len(untested),
            "tests_by_file": tests_by_file,
            "untested_callables_list": untested,
        }

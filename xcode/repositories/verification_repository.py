"""
Verification repository for running tests and linters.
"""

import subprocess
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Tuple

from xcode.models import VerificationResult


class VerificationRepository(ABC):
    """Abstract interface for verification operations."""

    @abstractmethod
    def run_tests(self, repo_path: Path, language: str) -> Tuple[bool, str, str]:
        """
        Run tests and capture output.

        Args:
            repo_path: Path to the repository
            language: Programming language (python, csharp, etc.)

        Returns:
            Tuple of (success, stdout, stderr)
        """
        pass

    @abstractmethod
    def run_linter(self, repo_path: Path, language: str) -> Tuple[bool, str, str]:
        """
        Run linter and capture output.

        Args:
            repo_path: Path to the repository
            language: Programming language (python, csharp, etc.)

        Returns:
            Tuple of (success, stdout, stderr)
        """
        pass

    @abstractmethod
    def run_command(self, repo_path: Path, command: list[str]) -> Tuple[bool, str, str, int]:
        """
        Run arbitrary command and capture output.

        Args:
            repo_path: Path to the repository
            command: Command to run as list of strings

        Returns:
            Tuple of (success, stdout, stderr, exit_code)
        """
        pass

    @abstractmethod
    def verify(
        self, repo_path: Path, language: str, run_tests: bool = True, run_linter: bool = True
    ) -> VerificationResult:
        """
        Run verification checks and return consolidated result.

        Args:
            repo_path: Path to the repository
            language: Programming language
            run_tests: Whether to run tests
            run_linter: Whether to run linter

        Returns:
            VerificationResult with all check outputs
        """
        pass


class SubprocessVerificationRepository(VerificationRepository):
    """
    Subprocess-based implementation of VerificationRepository.

    Runs tests and linters using subprocess execution.
    """

    def __init__(self):
        """Initialize the subprocess verification repository."""
        pass

    def run_tests(self, repo_path: Path, language: str) -> Tuple[bool, str, str]:
        """
        Run tests and capture output.

        Args:
            repo_path: Path to the repository
            language: Programming language (python, csharp, etc.)

        Returns:
            Tuple of (success, stdout, stderr)
        """
        try:
            if language == "python":
                return self._run_pytest(repo_path)
            elif language == "csharp":
                return self._run_dotnet_test(repo_path)
            else:
                return False, "", f"Unsupported language: {language}"
        except Exception as e:
            return False, "", str(e)

    def _run_pytest(self, repo_path: Path) -> Tuple[bool, str, str]:
        """
        Run pytest and return results.

        Args:
            repo_path: Path to the repository

        Returns:
            Tuple of (success, stdout, stderr)
        """
        try:
            result = subprocess.run(
                ["pytest", "-v", "--tb=short"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=300,
            )

            success = result.returncode == 0
            return success, result.stdout, result.stderr

        except FileNotFoundError:
            return False, "", "pytest not found - please install pytest"
        except subprocess.TimeoutExpired:
            return False, "", "Test execution timed out (5 minutes)"

    def _run_dotnet_test(self, repo_path: Path) -> Tuple[bool, str, str]:
        """
        Run dotnet test and return results.

        Args:
            repo_path: Path to the repository

        Returns:
            Tuple of (success, stdout, stderr)
        """
        try:
            result = subprocess.run(
                ["dotnet", "test", "--verbosity", "normal"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=300,
            )

            success = result.returncode == 0
            return success, result.stdout, result.stderr

        except FileNotFoundError:
            return False, "", "dotnet not found - please install .NET SDK"
        except subprocess.TimeoutExpired:
            return False, "", "Test execution timed out (5 minutes)"

    def run_linter(self, repo_path: Path, language: str) -> Tuple[bool, str, str]:
        """
        Run linter and capture output.

        Args:
            repo_path: Path to the repository
            language: Programming language (python, csharp, etc.)

        Returns:
            Tuple of (success, stdout, stderr)
        """
        try:
            if language == "python":
                return self._run_ruff(repo_path)
            elif language == "csharp":
                return self._run_dotnet_format(repo_path)
            else:
                return False, "", f"Unsupported language: {language}"
        except Exception as e:
            return False, "", str(e)

    def _run_ruff(self, repo_path: Path) -> Tuple[bool, str, str]:
        """
        Run ruff linter for Python.

        Args:
            repo_path: Path to the repository

        Returns:
            Tuple of (success, stdout, stderr)
        """
        try:
            result = subprocess.run(
                ["ruff", "check", "."],
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=60,
            )

            success = result.returncode == 0
            return success, result.stdout, result.stderr

        except FileNotFoundError:
            return True, "ruff not installed - skipping linting", ""
        except subprocess.TimeoutExpired:
            return False, "", "Linter execution timed out"

    def _run_dotnet_format(self, repo_path: Path) -> Tuple[bool, str, str]:
        """
        Run dotnet format for C#.

        Args:
            repo_path: Path to the repository

        Returns:
            Tuple of (success, stdout, stderr)
        """
        try:
            result = subprocess.run(
                ["dotnet", "format", "--verify-no-changes", "--verbosity", "normal"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=60,
            )

            success = result.returncode == 0
            return success, result.stdout, result.stderr

        except FileNotFoundError:
            return True, "dotnet format not available - skipping", ""
        except subprocess.TimeoutExpired:
            return False, "", "Format check timed out"

    def run_command(self, repo_path: Path, command: list[str]) -> Tuple[bool, str, str, int]:
        """
        Run arbitrary command and capture output.

        Args:
            repo_path: Path to the repository
            command: Command to run as list of strings

        Returns:
            Tuple of (success, stdout, stderr, exit_code)
        """
        try:
            result = subprocess.run(
                command,
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=60,
            )

            success = result.returncode == 0
            return success, result.stdout, result.stderr, result.returncode

        except subprocess.TimeoutExpired:
            return False, "", "Command timed out", -1
        except Exception as e:
            return False, "", str(e), -1

    def verify(
        self, repo_path: Path, language: str, run_tests: bool = True, run_linter: bool = True
    ) -> VerificationResult:
        """
        Run verification checks and return consolidated result.

        Args:
            repo_path: Path to the repository
            language: Programming language
            run_tests: Whether to run tests
            run_linter: Whether to run linter

        Returns:
            VerificationResult with all check outputs
        """
        checks = []
        outputs = []
        all_success = True
        error = None

        try:
            if run_tests:
                test_success, test_stdout, test_stderr = self.run_tests(repo_path, language)
                checks.append("tests")
                outputs.append(f"=== Tests ===\n{test_stdout}\n{test_stderr}")
                all_success = all_success and test_success

            if run_linter:
                lint_success, lint_stdout, lint_stderr = self.run_linter(repo_path, language)
                checks.append("linter")
                outputs.append(f"=== Linter ===\n{lint_stdout}\n{lint_stderr}")
                all_success = all_success and lint_success

        except Exception as e:
            error = str(e)
            all_success = False

        combined_output = "\n\n".join(outputs)

        return VerificationResult(
            success=all_success,
            checks_run=checks,
            output=combined_output,
            error=error,
        )

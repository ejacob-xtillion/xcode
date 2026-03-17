"""
Verification loop - captures logs and passes them back to the agent
"""

import subprocess
from pathlib import Path

from rich.console import Console

from xcode.domain.models import VerificationResult


class VerificationLoop:
    """
    Handles verification loop for agent task completion.

    Captures logs from tests, linter, and commands and passes them
    back into the agent for verification and iteration.
    """

    def __init__(self, repo_path: Path, language: str, console: Console):
        self.repo_path = repo_path
        self.language = language
        self.console = console

    def run_tests(self) -> tuple[bool, str, str]:
        """
        Run tests and capture output.

        Returns:
            Tuple of (success, stdout, stderr)
        """
        try:
            if self.language == "python":
                return self._run_pytest()
            elif self.language == "csharp":
                return self._run_dotnet_test()
            else:
                return False, "", f"Unsupported language: {self.language}"
        except Exception as e:
            return False, "", str(e)

    def _run_pytest(self) -> tuple[bool, str, str]:
        """Run pytest and return results."""
        try:
            result = subprocess.run(
                ["pytest", "-v", "--tb=short"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
            )

            success = result.returncode == 0
            return success, result.stdout, result.stderr

        except FileNotFoundError:
            return False, "", "pytest not found - please install pytest"
        except subprocess.TimeoutExpired:
            return False, "", "Test execution timed out (5 minutes)"

    def _run_dotnet_test(self) -> tuple[bool, str, str]:
        """Run dotnet test and return results."""
        try:
            result = subprocess.run(
                ["dotnet", "test", "--verbosity", "normal"],
                cwd=self.repo_path,
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

    def run_linter(self) -> tuple[bool, str, str]:
        """
        Run linter and capture output.

        Returns:
            Tuple of (success, stdout, stderr)
        """
        try:
            if self.language == "python":
                return self._run_ruff()
            elif self.language == "csharp":
                return self._run_dotnet_format()
            else:
                return False, "", f"Unsupported language: {self.language}"
        except Exception as e:
            return False, "", str(e)

    def _run_ruff(self) -> tuple[bool, str, str]:
        """Run ruff linter for Python."""
        try:
            result = subprocess.run(
                ["ruff", "check", "."],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=60,
            )

            # Ruff returns 0 if no issues, 1 if issues found
            success = result.returncode == 0
            return success, result.stdout, result.stderr

        except FileNotFoundError:
            # ruff not installed, skip linting
            return True, "ruff not installed - skipping linting", ""
        except subprocess.TimeoutExpired:
            return False, "", "Linter execution timed out"

    def _run_dotnet_format(self) -> tuple[bool, str, str]:
        """Run dotnet format for C#."""
        try:
            result = subprocess.run(
                ["dotnet", "format", "--verify-no-changes", "--verbosity", "normal"],
                cwd=self.repo_path,
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

    def run_command(self, command: list[str]) -> tuple[bool, str, str, int]:
        """
        Run arbitrary command and capture output.

        Args:
            command: Command to run as list of strings

        Returns:
            Tuple of (success, stdout, stderr, exit_code)
        """
        try:
            result = subprocess.run(
                command,
                cwd=self.repo_path,
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

    def verify(self, run_tests: bool = True, run_linter: bool = True) -> VerificationResult:
        """
        Run verification checks and return consolidated result.

        Args:
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
                test_success, test_stdout, test_stderr = self.run_tests()
                checks.append("tests")
                outputs.append(f"=== Tests ===\n{test_stdout}\n{test_stderr}")
                all_success = all_success and test_success

            if run_linter:
                lint_success, lint_stdout, lint_stderr = self.run_linter()
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

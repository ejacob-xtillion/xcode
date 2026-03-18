"""
Verify changes command - runs tests and linters.
"""

from pathlib import Path

from rich.console import Console

from xcode.commands.base_command import BaseCommand
from xcode.domain.models import VerificationResult
from xcode.services.verification_service import VerificationService


class VerifyChangesCommand(BaseCommand):
    """Command to verify code changes."""

    def __init__(
        self,
        repo_path: Path,
        language: str,
        verification_service: VerificationService,
        console: Console,
        run_tests: bool = True,
        run_linter: bool = True,
    ):
        self.repo_path = repo_path
        self.language = language
        self.verification_service = verification_service
        self.console = console
        self.run_tests = run_tests
        self.run_linter = run_linter

    def execute(self) -> VerificationResult:
        """Run verification checks."""
        return self.verification_service.run_verification(
            repo_path=self.repo_path,
            language=self.language,
        )

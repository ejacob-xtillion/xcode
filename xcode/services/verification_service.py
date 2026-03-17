"""
Verification service for running tests and checks.
"""

from pathlib import Path

from rich.console import Console

from xcode.domain.models import VerificationResult


class VerificationService:
    """Service for verification operations."""

    def __init__(self, console: Console):
        self.console = console

    def run_verification(
        self,
        repo_path: Path,
        language: str,
    ) -> VerificationResult:
        """
        Run verification checks (tests, linting).

        Args:
            repo_path: Path to repository
            language: Programming language

        Returns:
            VerificationResult with check outcomes
        """
        from xcode.verification import VerificationLoop

        verification = VerificationLoop(repo_path, language, self.console)
        return verification.verify()

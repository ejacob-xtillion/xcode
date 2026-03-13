"""
Tests for verification module
"""
import pytest
from pathlib import Path
from unittest.mock import Mock, patch
from rich.console import Console

from xcode.verification import VerificationLoop, VerificationResult


@pytest.fixture
def mock_console():
    """Create a mock console."""
    return Mock(spec=Console)


@pytest.fixture
def verification_loop(tmp_path, mock_console):
    """Create a VerificationLoop instance."""
    return VerificationLoop(tmp_path, "python", mock_console)


class TestVerificationResult:
    """Tests for VerificationResult dataclass."""

    def test_verification_result_creation(self):
        """Test VerificationResult creation."""
        result = VerificationResult(
            success=True,
            checks_run=["tests", "linter"],
            output="All checks passed",
        )
        
        assert result.success is True
        assert result.checks_run == ["tests", "linter"]
        assert result.output == "All checks passed"
        assert result.error is None

    def test_verification_result_with_error(self):
        """Test VerificationResult with error."""
        result = VerificationResult(
            success=False,
            checks_run=["tests"],
            output="Test output",
            error="Tests failed",
        )
        
        assert result.success is False
        assert result.error == "Tests failed"


class TestVerificationLoop:
    """Tests for VerificationLoop."""

    def test_init(self, tmp_path, mock_console):
        """Test VerificationLoop initialization."""
        loop = VerificationLoop(tmp_path, "python", mock_console)
        
        assert loop.repo_path == tmp_path
        assert loop.language == "python"
        assert loop.console == mock_console

    @patch("xcode.verification.subprocess.run")
    def test_run_pytest_success(self, mock_run, verification_loop):
        """Test successful pytest execution."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout="test_example.py::test_foo PASSED",
            stderr="",
        )
        
        success, stdout, stderr = verification_loop._run_pytest()
        
        assert success is True
        assert "PASSED" in stdout
        assert stderr == ""
        mock_run.assert_called_once()

    @patch("xcode.verification.subprocess.run")
    def test_run_pytest_failure(self, mock_run, verification_loop):
        """Test failed pytest execution."""
        mock_run.return_value = Mock(
            returncode=1,
            stdout="test_example.py::test_foo FAILED",
            stderr="AssertionError",
        )
        
        success, stdout, stderr = verification_loop._run_pytest()
        
        assert success is False
        assert "FAILED" in stdout

    @patch("xcode.verification.subprocess.run")
    def test_run_pytest_not_found(self, mock_run, verification_loop):
        """Test pytest not installed."""
        mock_run.side_effect = FileNotFoundError()
        
        success, stdout, stderr = verification_loop._run_pytest()
        
        assert success is False
        assert "pytest not found" in stderr

    @patch("xcode.verification.subprocess.run")
    def test_run_ruff_success(self, mock_run, verification_loop):
        """Test successful ruff execution."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout="All checks passed!",
            stderr="",
        )
        
        success, stdout, stderr = verification_loop._run_ruff()
        
        assert success is True
        assert stderr == ""

    @patch("xcode.verification.subprocess.run")
    def test_run_ruff_with_issues(self, mock_run, verification_loop):
        """Test ruff finding issues."""
        mock_run.return_value = Mock(
            returncode=1,
            stdout="file.py:10:5: E501 line too long",
            stderr="",
        )
        
        success, stdout, stderr = verification_loop._run_ruff()
        
        assert success is False
        assert "E501" in stdout

    @patch("xcode.verification.subprocess.run")
    def test_run_command(self, mock_run, verification_loop):
        """Test running arbitrary command."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout="command output",
            stderr="",
        )
        
        success, stdout, stderr, exit_code = verification_loop.run_command(["echo", "test"])
        
        assert success is True
        assert exit_code == 0
        mock_run.assert_called_once()

    @patch("xcode.verification.subprocess.run")
    def test_run_command_failure(self, mock_run, verification_loop):
        """Test command failure."""
        mock_run.return_value = Mock(
            returncode=1,
            stdout="",
            stderr="error",
        )
        
        success, stdout, stderr, exit_code = verification_loop.run_command(["false"])
        
        assert success is False
        assert exit_code == 1

    @patch.object(VerificationLoop, "run_tests")
    @patch.object(VerificationLoop, "run_linter")
    def test_verify_all_checks(self, mock_linter, mock_tests, verification_loop):
        """Test running all verification checks."""
        mock_tests.return_value = (True, "Tests passed", "")
        mock_linter.return_value = (True, "Lint passed", "")
        
        result = verification_loop.verify(run_tests=True, run_linter=True)
        
        assert result.success is True
        assert "tests" in result.checks_run
        assert "linter" in result.checks_run
        assert "Tests passed" in result.output
        assert "Lint passed" in result.output

    @patch.object(VerificationLoop, "run_tests")
    @patch.object(VerificationLoop, "run_linter")
    def test_verify_tests_fail(self, mock_linter, mock_tests, verification_loop):
        """Test verification with test failures."""
        mock_tests.return_value = (False, "Tests failed", "error")
        mock_linter.return_value = (True, "Lint passed", "")
        
        result = verification_loop.verify(run_tests=True, run_linter=True)
        
        assert result.success is False
        assert "tests" in result.checks_run

    @patch.object(VerificationLoop, "run_tests")
    def test_verify_only_tests(self, mock_tests, verification_loop):
        """Test running only tests."""
        mock_tests.return_value = (True, "Tests passed", "")
        
        result = verification_loop.verify(run_tests=True, run_linter=False)
        
        assert result.success is True
        assert "tests" in result.checks_run
        assert "linter" not in result.checks_run

    def test_run_tests_delegates_by_language(self, tmp_path, mock_console):
        """Test that run_tests delegates to language-specific method."""
        loop_python = VerificationLoop(tmp_path, "python", mock_console)
        loop_csharp = VerificationLoop(tmp_path, "csharp", mock_console)
        
        with patch.object(loop_python, "_run_pytest") as mock_pytest:
            mock_pytest.return_value = (True, "", "")
            loop_python.run_tests()
            mock_pytest.assert_called_once()
        
        with patch.object(loop_csharp, "_run_dotnet_test") as mock_dotnet:
            mock_dotnet.return_value = (True, "", "")
            loop_csharp.run_tests()
            mock_dotnet.assert_called_once()

    def test_run_linter_delegates_by_language(self, tmp_path, mock_console):
        """Test that run_linter delegates to language-specific method."""
        loop_python = VerificationLoop(tmp_path, "python", mock_console)
        loop_csharp = VerificationLoop(tmp_path, "csharp", mock_console)
        
        with patch.object(loop_python, "_run_ruff") as mock_ruff:
            mock_ruff.return_value = (True, "", "")
            loop_python.run_linter()
            mock_ruff.assert_called_once()
        
        with patch.object(loop_csharp, "_run_dotnet_format") as mock_format:
            mock_format.return_value = (True, "", "")
            loop_csharp.run_linter()
            mock_format.assert_called_once()

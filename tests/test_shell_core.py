"""Unit tests for agent shell sandbox (stdlib-only shell_core).

Loads shell_core by file path to avoid ``app`` namespace clashes with unrelated
packages on PYTHONPATH.
"""

import importlib.util
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent
_SHELL_CORE = _REPO_ROOT / "agent/app/engine/xcode_coding_agent/shell_core.py"


def _load_shell_core():
    spec = importlib.util.spec_from_file_location("xcode_agent_shell_core", _SHELL_CORE)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["xcode_agent_shell_core"] = mod
    spec.loader.exec_module(mod)
    return mod


_sc = _load_shell_core()
ShellCommandError = _sc.ShellCommandError
clear_requirements_install_cache = _sc.clear_requirements_install_cache
resolve_working_directory = _sc.resolve_working_directory
run_shell_command_impl = _sc.run_shell_command_impl
truncate_output = _sc.truncate_output


@pytest.fixture(autouse=True)
def _reset_requirements_install_cache():
    """Isolate tests that touch the in-process requirements install dedupe cache."""
    clear_requirements_install_cache()
    yield
    clear_requirements_install_cache()


def test_resolve_working_directory_accepts_subdirectory(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    sub = root / "pkg"
    sub.mkdir()
    assert resolve_working_directory(str(sub), [str(root)]) == str(sub.resolve())


def test_resolve_working_directory_rejects_outside_root(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    other = tmp_path / "other"
    other.mkdir()
    with pytest.raises(ShellCommandError, match="not under allowed roots"):
        resolve_working_directory(str(other), [str(root)])


def test_resolve_working_directory_rejects_symlink_escape(tmp_path):
    safe = tmp_path / "safe"
    safe.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    link = safe / "evil"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("symlink not supported")
    with pytest.raises(ShellCommandError, match="not under allowed roots"):
        resolve_working_directory(str(link), [str(safe)])


def test_run_shell_command_impl_echo(tmp_path):
    root = tmp_path / "r"
    root.mkdir()
    out = run_shell_command_impl(
        'echo hello',
        str(root),
        allowed_roots=[str(root)],
        timeout=10,
        max_output_bytes=4096,
    )
    assert "exit_code=0" in out
    assert "hello" in out


def test_run_shell_command_impl_timeout(tmp_path):
    root = tmp_path / "r"
    root.mkdir()
    with pytest.raises(ShellCommandError, match="timed out"):
        run_shell_command_impl(
            "sleep 30",
            str(root),
            allowed_roots=[str(root)],
            timeout=1,
            max_output_bytes=4096,
        )


def test_truncate_output():
    long = "x" * 1000
    t = truncate_output(long, max_bytes=50)
    assert "truncated" in t
    assert len(t.encode("utf-8")) <= 55


def test_run_shell_command_impl_empty_command(tmp_path):
    root = tmp_path / "r"
    root.mkdir()
    with pytest.raises(ShellCommandError, match="non-empty"):
        run_shell_command_impl(
            "   ",
            str(root),
            allowed_roots=[str(root)],
            timeout=10,
            max_output_bytes=4096,
        )


def test_run_shell_command_impl_nonzero_exit(tmp_path):
    root = tmp_path / "r"
    root.mkdir()
    out = run_shell_command_impl(
        "false",
        str(root),
        allowed_roots=[str(root)],
        timeout=10,
        max_output_bytes=4096,
    )
    assert "exit_code=1" in out


def test_auto_install_skipped_without_requirements_txt(tmp_path):
    root = tmp_path / "r"
    root.mkdir()
    with patch.object(_sc.subprocess, "run") as mock_run:
        mock_run.side_effect = AssertionError("pip should not run")
        with patch.object(_sc.subprocess, "Popen") as mock_popen:
            proc = MagicMock()
            proc.returncode = 0
            proc.communicate.return_value = ("ok\n", "")
            mock_popen.return_value = proc
            out = run_shell_command_impl(
                "python -m pytest -q",
                str(root),
                allowed_roots=[str(root)],
                timeout=10,
                max_output_bytes=4096,
                auto_install_requirements=True,
            )
    assert "exit_code=0" in out
    assert "ok" in out
    mock_popen.assert_called_once()


def test_auto_install_runs_pip_before_pytest_when_requirements_present(tmp_path):
    root = tmp_path / "r"
    root.mkdir()
    (root / "requirements.txt").write_text("# deps\n")

    def fake_run(argv, **kwargs):
        assert argv == [
            sys.executable,
            "-m",
            "pip",
            "install",
            "-q",
            "-r",
            "requirements.txt",
        ]
        return subprocess.CompletedProcess(argv, 0, stdout="installed\n", stderr="")

    with patch.object(_sc.shutil, "which", return_value=None):
        with patch.object(_sc.subprocess, "run", side_effect=fake_run):
            with patch.object(_sc.subprocess, "Popen") as mock_popen:
                proc = MagicMock()
                proc.returncode = 0
                proc.communicate.return_value = ("tests passed\n", "")
                mock_popen.return_value = proc
                out = run_shell_command_impl(
                    "python -m pytest -q",
                    str(root),
                    allowed_roots=[str(root)],
                    timeout=10,
                    max_output_bytes=4096,
                    auto_install_requirements=True,
                    pip_install_timeout=60,
                )
    assert "install_exit_code=0" in out
    assert "installed" in out
    assert "tests passed" in out
    mock_popen.assert_called_once()


def test_auto_install_uses_uv_when_on_path(tmp_path):
    root = tmp_path / "r"
    root.mkdir()
    (root / "requirements.txt").write_text("# deps\n")

    def fake_run(argv, **kwargs):
        assert argv == [
            "/bin/uv",
            "pip",
            "install",
            "-q",
            "-r",
            "requirements.txt",
            "--python",
            sys.executable,
        ]
        return subprocess.CompletedProcess(argv, 0, stdout="uv ok\n", stderr="")

    with patch.object(_sc.shutil, "which", return_value="/bin/uv"):
        with patch.object(_sc.subprocess, "run", side_effect=fake_run):
            with patch.object(_sc.subprocess, "Popen") as mock_popen:
                proc = MagicMock()
                proc.returncode = 0
                proc.communicate.return_value = ("done\n", "")
                mock_popen.return_value = proc
                out = run_shell_command_impl(
                    "pytest -q",
                    str(root),
                    allowed_roots=[str(root)],
                    timeout=10,
                    max_output_bytes=4096,
                    auto_install_requirements=True,
                )
    assert "uv pip install" in out
    assert "uv ok" in out
    assert "done" in out


def test_auto_install_pip_failure_raises(tmp_path):
    root = tmp_path / "r"
    root.mkdir()
    (root / "requirements.txt").write_text("badpkg===nope\n")

    def fake_run(argv, **kwargs):
        return subprocess.CompletedProcess(argv, 1, stdout="", stderr="pip error\n")

    with patch.object(_sc.shutil, "which", return_value=None):
        with patch.object(_sc.subprocess, "run", side_effect=fake_run):
            with patch.object(_sc.subprocess, "Popen") as mock_popen:
                with pytest.raises(ShellCommandError, match="requirements.txt install failed"):
                    run_shell_command_impl(
                        "pytest -q",
                        str(root),
                        allowed_roots=[str(root)],
                        timeout=10,
                        max_output_bytes=4096,
                        auto_install_requirements=True,
                    )
    mock_popen.assert_not_called()


def test_requirements_txt_exceeds_max_size_raises(tmp_path):
    root = tmp_path / "r"
    root.mkdir()
    limit = _sc._MAX_REQUIREMENTS_TXT_BYTES
    (root / "requirements.txt").write_bytes(b"#\n" + b"x" * limit)
    with pytest.raises(ShellCommandError, match="larger than"):
        run_shell_command_impl(
            "pytest -q",
            str(root),
            allowed_roots=[str(root)],
            timeout=10,
            max_output_bytes=4096,
            auto_install_requirements=True,
        )


def test_auto_install_second_pytest_skips_install_when_cached(tmp_path):
    root = tmp_path / "r"
    root.mkdir()
    (root / "requirements.txt").write_text("pandas\n")

    runs = []

    def fake_run(argv, **kwargs):
        runs.append(list(argv))
        return subprocess.CompletedProcess(argv, 0, stdout="ok\n", stderr="")

    with patch.object(_sc.shutil, "which", return_value=None):
        with patch.object(_sc.subprocess, "run", side_effect=fake_run):
            with patch.object(_sc.subprocess, "Popen") as mock_popen:
                proc = MagicMock()
                proc.returncode = 0
                proc.communicate.return_value = ("out\n", "")
                mock_popen.return_value = proc
                run_shell_command_impl(
                    "pytest -q",
                    str(root),
                    allowed_roots=[str(root)],
                    timeout=10,
                    max_output_bytes=4096,
                    auto_install_requirements=True,
                )
                run_shell_command_impl(
                    "pytest -q",
                    str(root),
                    allowed_roots=[str(root)],
                    timeout=10,
                    max_output_bytes=4096,
                    auto_install_requirements=True,
                )
    assert len(runs) == 1
    assert mock_popen.call_count == 2


def test_skip_redundant_requirements_install_false_runs_pip_twice(tmp_path):
    root = tmp_path / "r"
    root.mkdir()
    (root / "requirements.txt").write_text("x\n")

    runs = []

    def fake_run(argv, **kwargs):
        runs.append(argv)
        return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")

    with patch.object(_sc.shutil, "which", return_value=None):
        with patch.object(_sc.subprocess, "run", side_effect=fake_run):
            with patch.object(_sc.subprocess, "Popen") as mock_popen:
                proc = MagicMock()
                proc.returncode = 0
                proc.communicate.return_value = ("", "")
                mock_popen.return_value = proc
                for _ in range(2):
                    run_shell_command_impl(
                        "pytest -q",
                        str(root),
                        allowed_roots=[str(root)],
                        timeout=10,
                        max_output_bytes=4096,
                        auto_install_requirements=True,
                        skip_redundant_requirements_install=False,
                    )
    assert len(runs) == 2

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
    assert "exit_code=" not in out
    assert "hello" in out
    assert "$ echo hello" in out or "echo hello" in out


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


def test_auto_install_skipped_without_requirements_or_pyproject(tmp_path):
    """No auto-install when neither requirements.txt nor pyproject.toml exists."""
    root = tmp_path / "r"
    root.mkdir()
    with patch.object(_sc.subprocess, "run") as mock_run:
        mock_run.side_effect = AssertionError("pip/uv should not run")
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
    assert "exit_code=" not in out
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
    assert "install_exit_code" not in out
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


# --------------------------------------------------------------------------
# pyproject.toml + uv tests
# --------------------------------------------------------------------------


def test_pyproject_uv_sync_and_uv_run_before_pytest(tmp_path):
    """When pyproject.toml exists (no requirements.txt) and uv on PATH, run uv sync then uv run."""
    root = tmp_path / "r"
    root.mkdir()
    (root / "pyproject.toml").write_text('[project]\nname = "foo"\n')

    sync_calls = []

    def fake_run(argv, **kwargs):
        sync_calls.append(list(argv))
        return subprocess.CompletedProcess(argv, 0, stdout="synced\n", stderr="")

    with patch.object(_sc.shutil, "which", return_value="/bin/uv"):
        with patch.object(_sc.subprocess, "run", side_effect=fake_run):
            with patch.object(_sc.subprocess, "Popen") as mock_popen:
                proc = MagicMock()
                proc.returncode = 0
                proc.communicate.return_value = ("tests passed\n", "")
                mock_popen.return_value = proc
                out = run_shell_command_impl(
                    "pytest -q",
                    str(root),
                    allowed_roots=[str(root)],
                    timeout=10,
                    max_output_bytes=4096,
                    auto_install_requirements=True,
                )

    # uv sync was called
    assert len(sync_calls) == 1
    assert sync_calls[0] == ["/bin/uv", "sync"]

    # Popen was called with uv run -- pytest -q
    mock_popen.assert_called_once()
    popen_argv = mock_popen.call_args[0][0]
    assert popen_argv == ["/bin/uv", "run", "--", "pytest", "-q"]

    # Output includes sync preamble and test result
    assert "uv sync" in out
    assert "synced" in out
    assert "tests passed" in out
    assert "(via uv run)" in out


def test_pyproject_uv_sync_failure_raises(tmp_path):
    """uv sync failure raises ShellCommandError with preamble."""
    root = tmp_path / "r"
    root.mkdir()
    (root / "pyproject.toml").write_text('[project]\nname = "foo"\n')

    def fake_run(argv, **kwargs):
        return subprocess.CompletedProcess(argv, 1, stdout="", stderr="sync error\n")

    with patch.object(_sc.shutil, "which", return_value="/bin/uv"):
        with patch.object(_sc.subprocess, "run", side_effect=fake_run):
            with patch.object(_sc.subprocess, "Popen") as mock_popen:
                with pytest.raises(ShellCommandError, match="uv sync failed"):
                    run_shell_command_impl(
                        "pytest -q",
                        str(root),
                        allowed_roots=[str(root)],
                        timeout=10,
                        max_output_bytes=4096,
                        auto_install_requirements=True,
                    )
    mock_popen.assert_not_called()


def test_pyproject_second_pytest_skips_sync_when_cached(tmp_path):
    """Second pytest in same process skips uv sync when pyproject unchanged."""
    root = tmp_path / "r"
    root.mkdir()
    (root / "pyproject.toml").write_text('[project]\nname = "foo"\n')

    sync_calls = []

    def fake_run(argv, **kwargs):
        sync_calls.append(list(argv))
        return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")

    with patch.object(_sc.shutil, "which", return_value="/bin/uv"):
        with patch.object(_sc.subprocess, "run", side_effect=fake_run):
            with patch.object(_sc.subprocess, "Popen") as mock_popen:
                proc = MagicMock()
                proc.returncode = 0
                proc.communicate.return_value = ("ok\n", "")
                mock_popen.return_value = proc
                run_shell_command_impl(
                    "pytest -q",
                    str(root),
                    allowed_roots=[str(root)],
                    timeout=10,
                    max_output_bytes=4096,
                    auto_install_requirements=True,
                )
                out2 = run_shell_command_impl(
                    "pytest -q",
                    str(root),
                    allowed_roots=[str(root)],
                    timeout=10,
                    max_output_bytes=4096,
                    auto_install_requirements=True,
                )

    # uv sync only called once
    assert len(sync_calls) == 1
    # Popen called twice (both pytest runs via uv run)
    assert mock_popen.call_count == 2
    # Second run shows skipped message
    assert "skipped uv sync" in out2


def test_pyproject_with_uv_lock_fingerprint_includes_lock(tmp_path):
    """Fingerprint includes uv.lock when present; change triggers re-sync."""
    root = tmp_path / "r"
    root.mkdir()
    (root / "pyproject.toml").write_text('[project]\nname = "foo"\n')
    (root / "uv.lock").write_text("# lock v1\n")

    sync_calls = []

    def fake_run(argv, **kwargs):
        sync_calls.append(list(argv))
        return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")

    with patch.object(_sc.shutil, "which", return_value="/bin/uv"):
        with patch.object(_sc.subprocess, "run", side_effect=fake_run):
            with patch.object(_sc.subprocess, "Popen") as mock_popen:
                proc = MagicMock()
                proc.returncode = 0
                proc.communicate.return_value = ("ok\n", "")
                mock_popen.return_value = proc

                # First run
                run_shell_command_impl(
                    "pytest -q",
                    str(root),
                    allowed_roots=[str(root)],
                    timeout=10,
                    max_output_bytes=4096,
                    auto_install_requirements=True,
                )
                # Modify uv.lock
                (root / "uv.lock").write_text("# lock v2\n")
                # Second run should re-sync
                run_shell_command_impl(
                    "pytest -q",
                    str(root),
                    allowed_roots=[str(root)],
                    timeout=10,
                    max_output_bytes=4096,
                    auto_install_requirements=True,
                )

    # uv sync called twice (fingerprint changed)
    assert len(sync_calls) == 2


def test_pyproject_skipped_when_uv_not_on_path(tmp_path):
    """pyproject.toml exists but uv not on PATH: no sync, run command directly."""
    root = tmp_path / "r"
    root.mkdir()
    (root / "pyproject.toml").write_text('[project]\nname = "foo"\n')

    with patch.object(_sc.subprocess, "run") as mock_run:
        mock_run.side_effect = AssertionError("uv sync should not run")
        with patch.object(_sc.shutil, "which", return_value=None):
            with patch.object(_sc.subprocess, "Popen") as mock_popen:
                proc = MagicMock()
                proc.returncode = 0
                proc.communicate.return_value = ("ok\n", "")
                mock_popen.return_value = proc
                out = run_shell_command_impl(
                    "pytest -q",
                    str(root),
                    allowed_roots=[str(root)],
                    timeout=10,
                    max_output_bytes=4096,
                    auto_install_requirements=True,
                )

    # Command run directly (no uv run wrapper)
    mock_popen.assert_called_once()
    popen_argv = mock_popen.call_args[0][0]
    assert popen_argv == ["pytest", "-q"]
    # No uv sync preamble or "(via uv run)" in output
    assert "uv sync" not in out
    assert "(via uv run)" not in out


def test_requirements_txt_takes_precedence_over_pyproject(tmp_path):
    """When both requirements.txt and pyproject.toml exist, use requirements.txt path."""
    root = tmp_path / "r"
    root.mkdir()
    (root / "requirements.txt").write_text("pandas\n")
    (root / "pyproject.toml").write_text('[project]\nname = "foo"\n')

    run_calls = []

    def fake_run(argv, **kwargs):
        run_calls.append(list(argv))
        return subprocess.CompletedProcess(argv, 0, stdout="installed\n", stderr="")

    with patch.object(_sc.shutil, "which", return_value="/bin/uv"):
        with patch.object(_sc.subprocess, "run", side_effect=fake_run):
            with patch.object(_sc.subprocess, "Popen") as mock_popen:
                proc = MagicMock()
                proc.returncode = 0
                proc.communicate.return_value = ("ok\n", "")
                mock_popen.return_value = proc
                out = run_shell_command_impl(
                    "pytest -q",
                    str(root),
                    allowed_roots=[str(root)],
                    timeout=10,
                    max_output_bytes=4096,
                    auto_install_requirements=True,
                )

    # Should use uv pip install (requirements.txt path), not uv sync
    assert len(run_calls) == 1
    assert "pip" in run_calls[0]
    assert "uv pip install" in out

    # Popen runs pytest directly (not via uv run)
    popen_argv = mock_popen.call_args[0][0]
    assert popen_argv == ["pytest", "-q"]


def test_pyproject_exceeds_max_size_raises(tmp_path):
    """pyproject.toml larger than limit raises ShellCommandError."""
    root = tmp_path / "r"
    root.mkdir()
    limit = _sc._MAX_PYPROJECT_BYTES
    (root / "pyproject.toml").write_bytes(b"#\n" + b"x" * limit)

    with patch.object(_sc.shutil, "which", return_value="/bin/uv"):
        with pytest.raises(ShellCommandError, match="larger than"):
            run_shell_command_impl(
                "pytest -q",
                str(root),
                allowed_roots=[str(root)],
                timeout=10,
                max_output_bytes=4096,
                auto_install_requirements=True,
            )

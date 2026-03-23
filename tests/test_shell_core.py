"""Unit tests for agent shell sandbox (stdlib-only shell_core).

Loads shell_core by file path to avoid ``app`` namespace clashes with unrelated
packages on PYTHONPATH.
"""

import importlib.util
import sys
from pathlib import Path

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
resolve_working_directory = _sc.resolve_working_directory
run_shell_command_impl = _sc.run_shell_command_impl
truncate_output = _sc.truncate_output


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

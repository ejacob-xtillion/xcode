"""Tests for shell/pytest-oriented tool result summaries in AgentHttpRepository."""

from xcode.repositories.agent_repository import AgentHttpRepository


def test_shell_like_summary_pytest_passed():
    text = """cwd
$ pytest -q

stdout:
some noise
=== 3 passed in 1.23s ===
"""
    s = AgentHttpRepository._shell_like_summary(text)
    assert s is not None
    assert "passed" in s


def test_shell_like_summary_exit_code():
    text = """exit_code=1
/tmp
$ pytest

stdout:
oops
"""
    s = AgentHttpRepository._shell_like_summary(text)
    assert s is not None
    assert "exit_code=" in s


def test_shell_like_summary_none_for_plain_text():
    s = AgentHttpRepository._shell_like_summary("just some log\nlines here\n")
    assert s is None

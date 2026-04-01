from app.api.agents.shell_stream_multiplex import is_shell_tool_name


def test_is_shell_tool_name():
    assert is_shell_tool_name("run_shell_command")
    assert is_shell_tool_name("custom.run_shell_command")
    assert not is_shell_tool_name("read_file")

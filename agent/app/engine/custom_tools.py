"""Custom LangChain tools mixed with MCP-discovered tools."""

from app.core.settings import get_settings
from app.engine.xcode_coding_agent.shell_tool import get_shell_tools_for_agent


def get_all_tools() -> list:
    """Return custom tools for agents (currently shell only when enabled)."""
    return get_shell_tools_for_agent(get_settings())


__all__ = ["get_all_tools"]

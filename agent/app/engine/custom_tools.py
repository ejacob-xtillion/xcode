"""Custom tools that can be mixed with MCP-discovered tools.

This module demonstrates a simple, self-contained tool that returns a static
hello string. It follows the guidance in CUSTOM_TOOLS.md:

- Use `@tool` from LangChain
- Provide a clear docstring that explains when to use the tool
- Expose a `get_all_tools()` helper so agents can import and combine tools

Note: This tool is local to the agent and does not require an MCP server.
You can verify availability via the `/tools` API or by asking the agent for
hello-world output.
"""

from langchain.tools import tool

from app.core.logger import get_logger

logger = get_logger()


@tool
def get_hello_world() -> str:
    """
    Return a friendly hello-world message.

    Use this when the user asks for a basic greeting or to confirm custom tools
    are available without calling an MCP server.
    """
    message = "Hello from the custom tool!"
    logger.info("custom_tool_hello_requested", message=message)
    return message


def get_all_tools() -> list:
    """Return all custom tools defined in this module."""
    return [get_hello_world]


__all__ = ["get_hello_world", "get_all_tools"]

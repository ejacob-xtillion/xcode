"""MCP Client wrapper for fastmcp.Client initialization.

Handles initialization of fastmcp.Client instances for multiple MCP servers
with different transport types (stdio, http, sse), header forwarding, and cleanup.
"""

import os
import sys
from pathlib import Path
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastmcp import Client
from fastmcp.client.transports import (
    SSETransport,
    StdioTransport,
    StreamableHttpTransport,
)

from app.core.settings import AppSettings
from app.core.logger import logger


class MCPClient:
    """Wrapper class for fastmcp.Client

    Example:
        client = MCPClient(settings)

        async with client.connect("my_server", headers=req.headers) as mcp:
            tools = await mcp.list_tools()
            result = await mcp.call_tool("my_tool", {"arg": "value"})
    """

    def __init__(self, settings: AppSettings) -> None:
        self.settings = settings
        self._servers = settings.mcp_servers

    @property
    def server_names(self) -> list[str]:
        """Get list of configured server names."""
        return list(self._servers.keys())

    def _get_auth_header(self, server_config: dict) -> str | None:
        """Build auth header from config or environment.

        Args:
            server_config: Server configuration dict

        Returns:
            Formatted Authorization header value or None
        """
        auth_type = server_config.get("authType")
        auth_env_var = server_config.get("authEnvVar")

        if not auth_type or not auth_env_var:
            return None

        # Check server config env dict first
        env_dict = server_config.get("env") or {}
        credential = None
        if auth_env_var in env_dict:
            token_value = env_dict[auth_env_var]
            # Handle ${VAR} expansion
            if isinstance(token_value, str) and token_value.startswith("${") and token_value.endswith("}"):
                var_name = token_value[2:-1]
                credential = self.settings.get_env(var_name)
            else:
                credential = token_value
        else:
            # Fall back to environment lookup
            credential = self.settings.get_env(auth_env_var)

        if not credential:
            return None

        # Format header based on auth type
        if auth_type.lower() in ("jwt", "bearer"):
            return f"Bearer {credential}"
        elif auth_type.lower() == "token":
            return f"Token {credential}"
        return credential

    def _create_transport(self, server_config: dict, headers: dict[str, str] | None):
        """Create the appropriate transport based on server config."""
        fwd_headers = dict(headers) if headers else {}

        # Add auth if not already present
        auth = self._get_auth_header(server_config)
        if auth and "Authorization" not in fwd_headers:
            fwd_headers["Authorization"] = auth

        transport_type = server_config.get("formOfTransport", "stdio")
        url = server_config.get("url")
        timeout = server_config.get("timeout", 30)

        if transport_type == "stdio":
            command = server_config.get("command")
            args = server_config.get("args", [])
            env = server_config.get("env")

            # If no explicit command, parse from URL
            if not command:
                if url and url.startswith("stdio://"):
                    # Parse stdio:// URLs: stdio:///path/to/script.py
                    script_path = url.replace("stdio://", "")

                    # Convert to absolute path if relative
                    if not os.path.isabs(script_path):
                        # Try relative to current working directory
                        abs_path = Path.cwd() / script_path
                        if abs_path.exists():
                            script_path = str(abs_path)

                    # For Python scripts, use the current Python interpreter
                    if script_path.endswith(".py"):
                        command = sys.executable
                        args = [script_path] + args
                    else:
                        command = script_path
                else:
                    # Fall back to using URL as command
                    command = url

            return StdioTransport(
                command=command,
                args=args,
                env=env or None,
            )
        elif transport_type == "sse":
            return SSETransport(
                url=url,
                headers=fwd_headers or None,
                sse_read_timeout=timeout,
            )
        elif transport_type == "http":
            return StreamableHttpTransport(
                url=url,
                headers=fwd_headers or None,
                sse_read_timeout=timeout,
            )
        else:
            raise ValueError(f"Unsupported transport: {transport_type}")

    @asynccontextmanager
    async def connect(
        self,
        server_name: str,
        headers: dict[str, str] | None = None,
    ) -> AsyncIterator[Client]:
        """Connect to an MCP server.

        Args:
            server_name: Name of the server in settings.mcp_servers
            headers: Optional headers to forward (auth, tenant, correlation id)

        Yields:
            Connected fastmcp.Client instance

        Raises:
            KeyError: If server not found
            ConnectionError: If connection fails
        """
        if server_name not in self._servers:
            raise KeyError(f"MCP server '{server_name}' not found")

        server_config = self._servers[server_name]
        transport = self._create_transport(server_config, headers)
        timeout = server_config.get("timeout", 30)

        client = Client(transport=transport, timeout=timeout)

        try:
            async with client:
                logger.info(f"Connected to MCP server '{server_name}'")
                yield client
        except (ConnectionError, TimeoutError) as e:
            logger.error(f"Connection failed for '{server_name}': {e}")
            raise
        except (FileNotFoundError, OSError) as e:
            logger.error(f"Subprocess failed for '{server_name}': {e}")
            raise

        finally:
            logger.info(f"Disconnected from '{server_name}'")


__all__ = ["MCPClient"]

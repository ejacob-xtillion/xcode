"""Global MCP tool discovery service.

Discovers tools from all configured MCP servers and converts them to LangChain BaseTool objects.
Uses langchain-mcp-adapters for tool conversion and caching for performance.

MCP server configurations are validated using app.core.mcp.models (StdioServerConfig,
SSEServerConfig, HTTPServerConfig) to ensure type safety and proper validation.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from langchain_core.tools import BaseTool
from langchain_mcp_adapters.tools import load_mcp_tools
from langchain_mcp_adapters.sessions import (
    StdioConnection,
    SSEConnection,
    StreamableHttpConnection,
    create_session,
)

from app.core.settings import AppSettings, get_settings
from app.core.logger import get_logger
from app.engine.mcp_tool_call_cache import build_tool_call_cache_interceptors

logger = get_logger()


class GlobalToolDiscovery:
    """Discovers and caches tools from all configured MCP servers.

    This service:
    - Iterates all MCP servers from settings
    - Fetches tools using langchain-mcp-adapters
    - Converts to LangChain BaseTool objects
    - Caches results with TTL to avoid redundant fetches
    - Handles partial failures gracefully

    Example:
        discovery = GlobalToolDiscovery(settings)

        # Get all tools from all servers
        all_tools = await discovery.discover_all_tools(headers=request.headers)
        # Returns: {"server1": [BaseTool, ...], "server2": [BaseTool, ...]}

        # Get tools from specific server
        server_tools = await discovery.discover_server_tools("my_server", headers=request.headers)
    """

    def __init__(self, cache_ttl_seconds: int = 300):
        """Initialize the tool discovery service.

        Args:
            settings: Application settings containing mcp_servers config (defaults to get_settings())
            cache_ttl_seconds: How long to cache discovered tools (default: 5 minutes)
        """
        self.settings = get_settings()
        self.cache_ttl = timedelta(seconds=cache_ttl_seconds)
        self._cache: Dict[str, tuple[datetime, List[BaseTool]]] = {}
        # Per-server locks to avoid duplicate concurrent fetches for the same server
        self._locks: Dict[str, asyncio.Lock] = {}

    def _resolve_auth_token(self, server_config: dict, auth_env_var: str) -> Optional[str]:
        """Resolve authentication token from config or environment.

        Args:
            server_config: Server configuration dict
            auth_env_var: Name of environment variable containing token

        Returns:
            Resolved token value or None
        """
        # Check server config env dict first
        env_dict = server_config.get("env") or {}
        if auth_env_var in env_dict:
            token_value = env_dict[auth_env_var]
            # Handle ${VAR} expansion
            if isinstance(token_value, str) and token_value.startswith("${") and token_value.endswith("}"):
                var_name = token_value[2:-1]
                return self.settings.get_env(var_name)
            return token_value

        # Fall back to environment lookup
        return self.settings.get_env(auth_env_var)

    def _format_auth_header(self, auth_type: str, token: str) -> str:
        """Format Authorization header value based on auth type.

        Args:
            auth_type: Type of authentication (jwt, bearer, api_key, etc.)
            token: Authentication token

        Returns:
            Formatted Authorization header value
        """
        return f"Bearer {token}"

    def _prepare_headers(self, server_config: dict, headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """Prepare headers including authentication for HTTP-based transports.

        Args:
            server_config: Server configuration dict
            headers: Optional base headers to include

        Returns:
            Dict of headers with authentication injected if configured
        """
        prepared = dict(headers) if headers else {}

        auth_type = server_config.get("authType")
        auth_env_var = server_config.get("authEnvVar")

        if not (auth_type and auth_env_var):
            return prepared

        token = self._resolve_auth_token(server_config, auth_env_var)

        if token:
            prepared["Authorization"] = self._format_auth_header(auth_type, token)
            logger.debug(
                "auth_token_injected",
                auth_type=auth_type,
                auth_env_var=auth_env_var,
                transport=server_config.get("formOfTransport"),
            )

        return prepared

    def _build_stdio_connection(self, server_config: dict, headers: Dict[str, str]) -> StdioConnection:
        """Build stdio transport connection.

        Args:
            server_config: Server configuration dict
            headers: Prepared headers (unused for stdio)

        Returns:
            StdioConnection configuration

        Raises:
            ValueError: If required 'command' is missing
        """
        command = server_config.get("command")
        if not command:
            raise ValueError("stdio transport requires 'command' in server config")

        connection: StdioConnection = {
            "transport": "stdio",
            "command": command,
            "args": server_config.get("args", []),
        }

        if env := server_config.get("env"):
            resolved_env = {}
            for key, value in env.items():
                if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
                    resolved_env[key] = self.settings.get_env(value[2:-1])
                else:
                    resolved_env[key] = value
            connection["env"] = resolved_env

        return connection

    def _build_sse_connection(self, server_config: dict, headers: Dict[str, str]) -> SSEConnection:
        """Build SSE transport connection.

        Args:
            server_config: Server configuration dict
            headers: Prepared headers with authentication

        Returns:
            SSEConnection configuration

        Raises:
            ValueError: If required 'url' is missing
        """
        url = server_config.get("url")
        if not url:
            raise ValueError("sse transport requires 'url' in server config")

        connection: SSEConnection = {
            "transport": "sse",
            "url": url,
            "headers": headers,
            "sse_read_timeout": float(server_config.get("timeout", 300)),
        }

        return connection

    def _build_http_connection(self, server_config: dict, headers: Dict[str, str]) -> StreamableHttpConnection:
        """Build HTTP transport connection.

        Args:
            server_config: Server configuration dict
            headers: Prepared headers with authentication

        Returns:
            StreamableHttpConnection configuration

        Raises:
            ValueError: If required 'url' is missing
        """
        url = server_config.get("url")
        if not url:
            raise ValueError("http transport requires 'url' in server config")

        connection: StreamableHttpConnection = {
            "transport": "streamable_http",
            "url": url,
            "headers": headers,
            "timeout": timedelta(seconds=server_config.get("timeout", 30)),
        }

        return connection

    def _build_connection(
        self, server_config: dict, headers: Optional[Dict[str, str]] = None
    ) -> StdioConnection | SSEConnection | StreamableHttpConnection:
        """Build a langchain-mcp-adapters Connection config from server settings.

        Args:
            server_config: Server configuration dict from settings.mcp_servers
            headers: Optional headers to forward (for auth, tenant extraction)

        Returns:
            Connection TypedDict for langchain-mcp-adapters

        Raises:
            ValueError: If transport type is unsupported
        """
        transport_type = server_config.get("formOfTransport", "streamable_http")

        # Prepare headers with authentication
        prepared_headers = self._prepare_headers(server_config, headers)

        # Dispatch to transport-specific builders
        builders = {
            "stdio": self._build_stdio_connection,
            "sse": self._build_sse_connection,
            "http": self._build_http_connection,
        }

        builder = builders.get(transport_type)
        if not builder:
            raise ValueError(f"Unsupported transport type: {transport_type}")

        return builder(server_config, prepared_headers)

    def _is_cache_valid(self, server_name: str) -> bool:
        """Check if cached tools for a server are still valid.

        Args:
            server_name: Name of the MCP server

        Returns:
            True if cache exists and is not expired
        """
        if server_name not in self._cache:
            return False

        cached_time, _ = self._cache[server_name]
        return datetime.now() - cached_time < self.cache_ttl

    async def discover_server_tools(
        self, server_name: str, headers: Optional[Dict[str, str]] = None, request: Optional[object] = None
    ) -> List[BaseTool]:
        """Discover tools from a specific MCP server.

        Args:
            server_name: Name of the server in settings.mcp_servers
            headers: Optional pre-built headers to forward (auth, tenant, correlation id)
            request: Optional FastAPI request object (for building headers if not provided)

        Returns:
            List of LangChain BaseTool objects from this server

        Raises:
            KeyError: If server not found in settings
        """
        # Per-server lock to prevent duplicate concurrent fetches
        lock = self._locks.setdefault(server_name, asyncio.Lock())

        async with lock:
            # Re-check cache under lock
            if self._is_cache_valid(server_name):
                logger.debug("mcp_tools_cache_hit", server=server_name)
                _, cached_tools = self._cache[server_name]
                return cached_tools

        server_config = self.settings.mcp_servers[server_name]

        # Build headers from request if provided but headers not
        if request and not headers:
            from app.core.middleware.mcp_headers import get_forwarded_headers

            headers = get_forwarded_headers(request)

        try:
            # Build connection config
            connection = self._build_connection(server_config, headers)

            # Use langchain-mcp-adapters to discover and convert tools
            logger.debug("mcp_tools_discovering", server=server_name)

            tool_interceptors = build_tool_call_cache_interceptors(self.settings)

            # For HTTP/SSE connections, create a session first
            # For stdio connections, we can pass connection directly
            transport_type = server_config.get("formOfTransport", "streamable_http")
            if transport_type in ("http", "sse"):
                # Create session from connection for HTTP/SSE transports
                async with create_session(connection) as session:
                    tools = await load_mcp_tools(
                        session=session,
                        connection=None,
                        tool_interceptors=tool_interceptors,
                        server_name=server_name,
                    )
            else:
                # For stdio, pass connection directly
                tools = await load_mcp_tools(
                    session=None,
                    connection=connection,
                    tool_interceptors=tool_interceptors,
                    server_name=server_name,
                )

            # Cache the results
            self._cache[server_name] = (datetime.now(), tools)

            logger.debug(
                "mcp_tools_discovered", server=server_name, tool_count=len(tools), tool_names=[t.name for t in tools]
            )
            return tools

        except Exception as e:
            logger.error("mcp_tools_discovery_failed", server=server_name, error=str(e), error_type=type(e).__name__)
            # Return empty list on failure (graceful degradation)
            return []

    async def discover_all_tools(
        self, headers: Optional[Dict[str, str]] = None, request: Optional[object] = None
    ) -> Dict[str, List[BaseTool]]:
        """Discover tools from all configured MCP servers.

        Args:
            headers: Optional pre-built headers to forward to all servers
            request: Optional FastAPI request object (for building per-server headers)

        Returns:
            Dict mapping server names to their discovered tools.
            Example: {"server1": [BaseTool, ...], "server2": [BaseTool, ...]}

        Note:
            - Handles partial failures gracefully (failed servers return empty list)
            - Returns empty dict if no MCP servers configured
            - Uses caching to avoid redundant fetches within TTL window
            - If request is provided, builds headers per-server with server-level auth
        """
        if not self.settings.mcp_servers:
            logger.warning("mcp_no_servers_configured")
            return {}

        server_names = list(self.settings.mcp_servers.keys())

        # Fetch from all servers concurrently for better latency when multiple servers are configured.
        tools_results = await asyncio.gather(
            *(self.discover_server_tools(server_name, headers, request) for server_name in server_names)
        )

        result: Dict[str, List[BaseTool]] = {name: tools for name, tools in zip(server_names, tools_results)}

        total_tools = sum(len(tools) for tools in result.values())
        logger.debug("mcp_tools_discovery_complete", server_count=len(result), total_tools=total_tools)

        return result

    def clear_cache(self, server_name: Optional[str] = None) -> None:
        """Clear the tool cache.

        Args:
            server_name: If provided, clear cache for specific server only.
                        If None, clear entire cache.
        """
        if server_name:
            self._cache.pop(server_name, None)
            logger.debug("mcp_cache_cleared", server=server_name)
        else:
            self._cache.clear()
            logger.debug("mcp_cache_cleared_all")


# Module-level singleton instance for shared caching across all agent invocations
_global_tool_discovery_instance: Optional[GlobalToolDiscovery] = None


def get_tool_discovery() -> GlobalToolDiscovery:
    """Get or create the global tool discovery singleton instance.

    This ensures that the tool cache is shared across all agent invocations,
    avoiding redundant MCP server connections and tool discovery.

    Returns:
        GlobalToolDiscovery: Shared singleton instance
    """
    global _global_tool_discovery_instance
    if _global_tool_discovery_instance is None:
        _global_tool_discovery_instance = GlobalToolDiscovery()
        logger.debug("global_tool_discovery_initialized")
    return _global_tool_discovery_instance


def build_agent_tool_map(
    agent_configs: Dict[str, Dict[str, list]],
    all_tools_by_server: Dict[str, List[BaseTool]],
) -> Dict[str, List[BaseTool]]:
    """Build agent name -> tools mapping with proper isolation.

    Supervisor agents: only get subagents from tools.subagents (no MCP tools).
    Simple agents: only get tools from their configured mcpServers.
    """
    agent_tool_map: Dict[str, List[BaseTool]] = {}

    for agent_name, config in agent_configs.items():
        agent_type = config.get("agent_type", "")
        explicit_tools = config.get("tools", {})
        mcp_servers = config.get("mcpServers") or []

        if agent_type == "supervisor_agent":
            agent_tool_map[agent_name] = []
            continue

        if isinstance(explicit_tools, dict) and explicit_tools:
            resolved: List[BaseTool] = []
            allowed_servers = set(mcp_servers) if mcp_servers else set(all_tools_by_server.keys())
            for server, names in explicit_tools.items():
                if server != "subagents" and server in allowed_servers:
                    for name in names or []:
                        tool = {t.name: t for t in all_tools_by_server.get(server, [])}.get(name)
                        if tool:
                            resolved.append(tool)
            agent_tool_map[agent_name] = resolved
            continue

        tools: List[BaseTool] = []
        for server in mcp_servers:
            tools.extend(all_tools_by_server.get(server, []))
        agent_tool_map[agent_name] = tools

    return agent_tool_map


__all__ = ["GlobalToolDiscovery", "get_tool_discovery", "build_agent_tool_map"]

"""Pydantic models for MCP server configuration.

Provides type-safe configuration models for MCP servers with validation.
Supports stdio, SSE, and HTTP transport types with their respective configuration options.
"""

from typing import Dict, List, Literal, Optional, Union
from pydantic import BaseModel, Field, field_validator


class StdioServerConfig(BaseModel):
    """Configuration for stdio-based MCP servers.

    Stdio servers run as local processes and communicate via stdin/stdout.
    """

    formOfTransport: Literal["stdio"] = Field(default="stdio", description="Transport type for stdio-based servers")
    command: str = Field(..., description="Command to execute (e.g., 'python', 'node', or path to executable)")
    args: List[str] = Field(default_factory=list, description="Command-line arguments to pass to the command")
    env: Optional[Dict[str, str]] = Field(default=None, description="Environment variables to set for the process")
    authType: Optional[Literal["bearer", "jwt", "api_key"]] = Field(
        default=None, description="Authentication type if auth is required"
    )
    authEnvVar: Optional[str] = Field(
        default=None, description="Environment variable name containing the auth credential"
    )


class SSEServerConfig(BaseModel):
    """Configuration for SSE (Server-Sent Events) based MCP servers.

    SSE servers communicate via HTTP with server-sent events for streaming.
    """

    formOfTransport: Literal["sse"] = Field(default="sse", description="Transport type for SSE-based servers")
    url: str = Field(..., description="URL endpoint for the SSE server")
    timeout: int = Field(default=300, description="SSE read timeout in seconds", gt=0)
    authType: Optional[Literal["bearer", "jwt", "api_key"]] = Field(
        default=None, description="Authentication type if auth is required"
    )
    authEnvVar: Optional[str] = Field(
        default=None, description="Environment variable name containing the auth credential"
    )


class HTTPServerConfig(BaseModel):
    """Configuration for HTTP-based MCP servers.

    HTTP servers communicate via standard HTTP requests/responses.
    """

    formOfTransport: Literal["http"] = Field(default="http", description="Transport type for HTTP-based servers")
    url: str = Field(..., description="URL endpoint for the HTTP server")
    timeout: int = Field(default=30, description="HTTP request timeout in seconds", gt=0)
    authType: Optional[Literal["bearer", "jwt", "api_key"]] = Field(
        default=None, description="Authentication type if auth is required"
    )
    authEnvVar: Optional[str] = Field(
        default=None, description="Environment variable name containing the auth credential"
    )


# Union type for any MCP server configuration
MCPServerConfig = Union[StdioServerConfig, SSEServerConfig, HTTPServerConfig]


class MCPServersConfig(BaseModel):
    """Container for all MCP server configurations.

    Maps server names to their respective configurations.
    """

    servers: Dict[str, MCPServerConfig] = Field(
        default_factory=dict, description="Dictionary mapping server names to their configurations"
    )

    @field_validator("servers", mode="before")
    @classmethod
    def validate_servers(cls, v: Dict[str, dict]) -> Dict[str, MCPServerConfig]:
        """Validate and convert server configs to appropriate typed models.

        Args:
            v: Dictionary of server configurations

        Returns:
            Dictionary with validated typed server configs

        Raises:
            ValueError: If transport type is invalid or required fields are missing
        """
        if not isinstance(v, dict):
            return v

        validated = {}
        for server_name, config in v.items():
            if not isinstance(config, dict):
                # Already a model instance
                validated[server_name] = config
                continue

            transport = config.get("formOfTransport", "stdio")

            try:
                if transport == "stdio":
                    validated[server_name] = StdioServerConfig(**config)
                elif transport == "sse":
                    validated[server_name] = SSEServerConfig(**config)
                elif transport == "http":
                    validated[server_name] = HTTPServerConfig(**config)
                else:
                    raise ValueError(
                        f"Invalid transport type '{transport}' for server '{server_name}'. "
                        f"Must be one of: stdio, sse, http"
                    )
            except Exception as e:
                raise ValueError(f"Invalid configuration for MCP server '{server_name}': {str(e)}") from e

        return validated

    def get_server(self, server_name: str) -> Optional[MCPServerConfig]:
        """Get configuration for a specific server.

        Args:
            server_name: Name of the server

        Returns:
            Server configuration or None if not found
        """
        return self.servers.get(server_name)

    def list_servers(self) -> List[str]:
        """Get list of all configured server names.

        Returns:
            List of server names
        """
        return list(self.servers.keys())


__all__ = [
    "StdioServerConfig",
    "SSEServerConfig",
    "HTTPServerConfig",
    "MCPServerConfig",
    "MCPServersConfig",
]

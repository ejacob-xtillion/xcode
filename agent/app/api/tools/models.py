from typing import Dict, List, Optional

from pydantic import BaseModel


class ToolInfo(BaseModel):
    """Minimal MCP tool representation returned by discovery endpoints."""

    name: str
    description: Optional[str] = None


class ToolsResponse(BaseModel):
    """Response model for listing tools from all servers."""

    servers: List[str]
    tools: Dict[str, List[ToolInfo]]


class ServerToolsResponse(BaseModel):
    """Response model for listing tools from a single server."""

    server: str
    tools: List[ToolInfo]


__all__ = ["ToolInfo", "ToolsResponse", "ServerToolsResponse"]

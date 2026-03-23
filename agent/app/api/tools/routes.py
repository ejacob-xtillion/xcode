from fastapi import APIRouter, HTTPException, Request

from app.core.middleware.mcp_headers import get_forwarded_headers
from app.engine.custom_tools import get_all_tools as get_custom_tools
from app.engine.mcp_tools import get_tool_discovery

from .models import ServerToolsResponse, ToolsResponse, ToolInfo

router = APIRouter()


@router.get("", response_model=ToolsResponse)
async def list_all_tools(request: Request) -> ToolsResponse:
    """List tools from all configured MCP servers."""
    discovery = get_tool_discovery()

    # Pass request to discovery so it can build headers per-server with server-level auth
    tools_by_server = await discovery.discover_all_tools(request=request)
    servers = list(tools_by_server.keys())

    # Add custom tools as a logical "custom" server entry
    custom_tools = get_custom_tools()
    tools_by_server["custom"] = custom_tools
    servers.append("custom")

    # Normalize into response model shape
    tools_response = {
        server: [ToolInfo(name=t.name, description=getattr(t, "description", None)) for t in tools]
        for server, tools in tools_by_server.items()
    }

    return ToolsResponse(servers=servers, tools=tools_response)


@router.get("/{server_name}", response_model=ServerToolsResponse)
async def list_server_tools(server_name: str, request: Request) -> ServerToolsResponse:
    """List tools from a specific MCP server."""
    discovery = get_tool_discovery()
    if server_name not in discovery.settings.mcp_servers:
        raise HTTPException(status_code=404, detail=f"MCP server '{server_name}' not found")
    # Build headers from request
    headers = get_forwarded_headers(request)

    tools = await discovery.discover_server_tools(server_name, headers)
    tool_infos = [ToolInfo(name=t.name, description=getattr(t, "description", None)) for t in tools]

    return ServerToolsResponse(server=server_name, tools=tool_infos)

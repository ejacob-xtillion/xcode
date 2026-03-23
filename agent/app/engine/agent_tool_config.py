"""Single source of truth for which MCP servers the xcode_coding_agent uses."""

# Order is preserved for discovery; names must match keys in AppSettings.mcp_servers.
XCODE_CODING_AGENT_MCP_SERVERS: tuple[str, ...] = ("neo4j", "filesystem")

# Simple Agent Instructions
## Getting Started 
* Read important LangChain Documentation on [LangGraph Agents](https://docs.langchain.com/oss/python/langchain/langgraph)
* Simple agents are single-purpose agents that can use MCP servers and custom tools to accomplish tasks.
* They are the foundation for all other agent patterns (supervisor sub-agents, HITL agents).
* Config example:
```yaml
---
# Simple Agent Configuration
# Single agent with MCP servers and custom tools

agents: 1
typeOfGraph: simple

# LLM configuration
LLMType: openai

# MCP Server Configuration (optional)
MCPServers:
  github:
    formOfTransport: http
    url: "https://api.githubcopilot.com/mcp/"
    port: 443
    authType: bearer
    authEnvVar: "GITHUB_TOKEN"

  web_search:
    url: "ws://localhost:8080"
    formOfTransport: websocket
    port: 8080
    authType: api_key
    authEnvVar: "MCP_WEBSEARCH_API_KEY"

AgentConfigs:
  research_agent:
    prompt: "You are a research assistant that helps find and summarize information from various sources."
    type: simple_agent
    mcpServers:
      - github
      - web_search
    ModelName: "gpt-4-turbo"
    temperature: 0.7  # Optional: temperature for model inference (0.0-2.0)
    reasoning_effort: "medium"  # Optional: reasoning effort for GPT-5 models ('low', 'medium', 'high')
```
* This configuration creates a simple agent that can use tools from both GitHub and web search MCP servers.
* The agent will automatically discover available tools from configured MCP servers at runtime.

## Minimal Configuration
* The simplest possible configuration requires only:
  - `type: simple_agent`
  - `prompt` (system prompt for the agent)
  - `ModelName` (optional, uses default if not specified)

```yaml
AgentConfigs:
  my_agent:
    prompt: "You are a helpful assistant."
    type: simple_agent
    ModelName: "gpt-4o-mini"
```

## Invocation
* Simple agents can be invoked using the streaming or completion endpoints.
* The following is an example requesting the agent to perform a research task:
```bash
curl -X 'POST' \
  'http://localhost:8000/agents' \
  -H 'accept: */*' \
  -H 'Content-Type: application/json' \
  -d '{
  "query": "Search for information about LangChain agents and summarize the key concepts.",
  "agent_name": "research_agent"
}'
```

* Streaming response example:
```bash
curl -X 'POST' \
  'http://localhost:8000/agents/stream' \
  -H 'accept: text/event-stream' \
  -H 'Content-Type: application/json' \
  -d '{
  "query": "Search for information about LangChain agents.",
  "agent_name": "research_agent"
}'
```

## Adding Functionality

### MCP Servers
* MCP servers provide standardized, reusable tools that can be shared across multiple agents.
* Tools from MCP servers are automatically discovered at runtime.
* Configure MCP servers in your YAML config:
```yaml
MCPServers:
  my_server:
    url: "http://localhost:8080"
    formOfTransport: http
    authType: bearer
    authEnvVar: MCP_SERVER_TOKEN

AgentConfigs:
  my_agent:
    type: simple_agent
    prompt: "You are a helpful assistant."
    mcpServers: ["my_server"]  # Connect agent to MCP server
```

### Custom Tools
* Add Python functions directly to your agent for agent-specific logic.
* Custom tools are best for:
  - Simple utilities (calculators, formatters, validators)
  - Agent-specific business logic
  - Rapid prototyping without server setup
  - Tools that don't need to be shared

* See the [Custom Tools Guide](CUSTOM_TOOLS.md) for detailed instructions on adding custom tools.

* Quick example:
```python
# In app/engine/<agent_name>/tools.py
from langchain.tools import tool

@tool
def calculate_tip(bill_amount: float, tip_percentage: float = 15.0) -> str:
    """Calculate tip amount for a restaurant bill."""
    tip = bill_amount * (tip_percentage / 100)
    return f"Tip: ${tip:.2f}"

def get_all_tools() -> list:
    return [calculate_tip]
```

### Combining MCP and Custom Tools
* You can use both MCP tools and custom tools in the same agent.
* The generated agent code automatically combines tools from both sources.
* Custom tools are loaded from `app/engine/<agent_name>/tools.py` if it exists.
* MCP tools are discovered from configured MCP servers at runtime.

## Tool Discovery
* Tools are automatically discovered and made available to your agent:
  - MCP tools: Discovered from configured MCP servers at runtime
  - Custom tools: Loaded from `app/engine/<agent_name>/tools.py` if present
* The agent uses tool docstrings to understand when and how to use each tool.
* Clear, descriptive docstrings are critical for proper tool usage.

## Modifying Agent Behavior

### Updating the Prompt
* Edit the agent's prompt in your YAML configuration file and regenerate the repository.
* Or modify `app/engine/<agent_name>/agent.py` directly in the generated repository.

### Changing Models
* Update `ModelName` in your YAML configuration:
```yaml
AgentConfigs:
  my_agent:
    type: simple_agent
    prompt: "You are a helpful assistant."
    ModelName: "gpt-4-turbo"  # Change model here
    temperature: 0.7  # Optional: adjust temperature
```

### Adjusting Temperature
* Set `temperature` in your YAML configuration (0.0-2.0).
* GPT-5 models always use temperature=1.0 regardless of configuration.

### Adding/Removing MCP Servers
* Add or remove MCP servers from the `mcpServers` list:
```yaml
AgentConfigs:
  my_agent:
    type: simple_agent
    prompt: "You are a helpful assistant."
    mcpServers: 
      - github
      - web_search
      # Add or remove servers as needed
```

### Specifying Specific Tools
* Optionally specify which tools to use from each MCP server:
```yaml
AgentConfigs:
  my_agent:
    type: simple_agent
    prompt: "You are a helpful assistant."
    mcpServers: ["github"]
    tools:  # Optional: Specify specific tools
      github:
        - search_code
        - get_file_contents
        # Only these tools will be available
```

## Best Practices

### Prompt Design
* Write clear, specific prompts that describe the agent's role and capabilities
* Include examples of when to use available tools
* Specify output format expectations
* Mention any constraints or safety considerations

### Tool Selection
* Use MCP servers for:
  - Complex integrations (databases, APIs, external services)
  - Tools shared across multiple agents
  - Standardized tool discovery protocol

* Use custom tools for:
  - Simple utilities specific to one agent
  - Rapid prototyping
  - Agent-specific business logic

### Error Handling
* Tools should handle errors gracefully and return helpful error messages
* Use structured logging to track tool usage and errors
* Validate inputs before processing in custom tools

### Performance
* Keep custom tools lightweight and focused
* Avoid blocking operations in custom tools
* Use async operations when possible for I/O-bound tasks


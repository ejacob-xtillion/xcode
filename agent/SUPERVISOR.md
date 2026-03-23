# Supervisor Agent Instructions
## Getting Started 
* Read important LangChain Documentation on [Multi-Agent Systems](https://docs.langchain.com/oss/python/langchain/multi-agent)
* Supervisor agents coordinate multiple specialized sub-agents by delegating tasks to the appropriate sub-agent based on their expertise.
* The supervisor receives queries and delegates to sub-agents (wrapped as tools), then synthesizes results from multiple sub-agents when needed.
* Config example:
```yaml
---
# Supervisor Pattern Configuration
# Supervisor coordinates multiple specialized sub-agents

agents: 3
typeOfGraph: simple

# LLM configuration
LLMType: openai

# MCP Servers Configuration
# These are used by subagents, NOT by supervisor_agent
# Supported transport types: stdio, http, sse
MCPServers:
  # HTTP transport example
  github:
    formOfTransport: http
    url: "https://api.githubcopilot.com/mcp/"
    port: 443
    authType: bearer
    authEnvVar: "GITHUB_TOKEN"

  # Stdio transport example
  neo4j:
    formOfTransport: stdio
    command: "uvx"
    args:
      - "mcp-neo4j-cypher"
      - "--transport"
      - "stdio"
    env:
      NEO4J_URI: "bolt://host.docker.internal:7687"
      NEO4J_USERNAME: "neo4j"
      NEO4J_PASSWORD: "password"
    authType: jwt
    authEnvVar: "MCP_NEO4J_JWT_TOKEN"

AgentConfigs:
  # Supervisor Agent - coordinates subagents
  # NOTE: supervisor_agent does NOT have mcpServers or MCP tool configs
  research_supervisor:
    type: "supervisor_agent"
    prompt: |
      You are a research supervisor coordinating a team of specialized research agents.
      
      Your role is to:
      - Understand the user's research question or task
      - Delegate work to the appropriate subagent based on their expertise
      - Synthesize results from multiple subagents when needed
      - Provide clear, comprehensive answers to the user
      
      Available subagents:
      - github_researcher: Specialized in GitHub repository analysis, code search, and issue tracking
      - data_analyst: Specialized in data analysis, Neo4j graph queries, and data insights
      
      IMPORTANT: Output only the final synthesized answer to the user. Do not show your internal reasoning, delegation steps, or thinking process. Present the result directly and clearly.
      
      When a user asks a question, determine which subagent(s) should handle the task, delegate appropriately, and present only the final synthesized answer. If a task requires multiple subagents, coordinate them and present a unified result.
    ModelName: "gpt-5-mini"
    # supervisor_agent ONLY has tools.subagents - no mcpServers or other tool configs
    tools:
      subagents:
        - github_researcher
        - data_analyst

  # Subagent 1: GitHub Researcher
  # This is a simple_agent that CAN have mcpServers and tools
  github_researcher:
    type: "simple_agent"
    prompt: "GitHub code search specialist. Help users find code, analyze repositories, and track issues."
    mcpServers: 
      - github
    ModelName: "gpt-5-mini"

  # Subagent 2: Data Analyst
  # This is a simple_agent that CAN have mcpServers and tools
  data_analyst:
    type: "simple_agent"
    prompt: "Data analysis specialist. Help users query Neo4j graph databases and analyze data patterns."
    mcpServers: ["neo4j"]
    ModelName: "gpt-5-mini"
```
* This configuration creates a supervisor agent that coordinates two sub-agents: `github_researcher` and `data_analyst`.
* The supervisor receives queries and delegates to the appropriate sub-agent based on the task.
* Sub-agents are `simple_agent` or `hitl_agent` instances that can use MCP servers and custom tools.

## Important Configuration Rules

### Supervisor Agent Requirements
* **MUST** have `type: supervisor_agent`
* **MUST** define `tools.subagents` as a list of sub-agent names
* **CANNOT** have `mcpServers` or MCP tool configurations
* **CANNOT** use custom tools directly (only delegates to sub-agents)

### Sub-Agent Requirements
* **MUST** be `type: simple_agent` or `hitl_agent`
* **CAN** have `mcpServers` and MCP tool configurations
* **CAN** use custom tools
* **MUST** be defined in `AgentConfigs` with the names listed in `tools.subagents`

## Invocation
* Supervisor agents are invoked using the same streaming or completion endpoints as simple agents.
* The following is an example requesting the supervisor to coordinate a research task:
```bash
curl -X 'POST' \
  'http://localhost:8000/agents' \
  -H 'accept: */*' \
  -H 'Content-Type: application/json' \
  -d '{
  "query": "Find all open issues in the organization/repo repository and analyze the data patterns in our Neo4j database related to those issues.",
  "agent_name": "research_supervisor"
}'
```
* The supervisor will:
  1. Analyze the query and determine which sub-agents are needed
  2. Delegate to `github_researcher` to find GitHub issues
  3. Delegate to `data_analyst` to query Neo4j for related data
  4. Synthesize the results and present a unified answer

## How Delegation Works

### Automatic Header Forwarding
* Headers (authentication, correlation IDs) are automatically forwarded from the supervisor to sub-agents
* This ensures sub-agents have the necessary context and authentication

### Sub-Agent Tool Access
* Sub-agents appear as tools to the supervisor
* The supervisor can call sub-agents by name (e.g., `github_researcher`, `data_analyst`)
* Sub-agents execute their tasks independently and return results to the supervisor

### Result Synthesis
* The supervisor receives results from all delegated sub-agents
* It synthesizes these results into a coherent response for the user
* The supervisor should present only the final synthesized answer, not the internal delegation steps

## Modifying Sub-Agents
* To modify sub-agents, edit their configuration in the YAML file and regenerate the repository
* To add new sub-agents:
  1. Add the sub-agent configuration to `AgentConfigs` with `type: simple_agent` or `type: hitl_agent`
  2. Add the sub-agent name to `tools.subagents` in the supervisor configuration
  3. Regenerate the repository

* To modify sub-agent behavior, edit the agent's prompt or tool configuration:
```yaml
AgentConfigs:
  github_researcher:
    type: "simple_agent"  # or "hitl_agent" for human oversight
    prompt: "Your updated prompt here"
    mcpServers: ["github"]
    # Optional: Specify specific tools to use
    tools:
      github:
        - search_code
        - get_file_contents
    ModelName: "gpt-5-mini"
```

## Best Practices

### Supervisor Prompt Design
* Clearly describe the supervisor's coordination role
* List all available sub-agents and their expertise
* Specify when to delegate to each sub-agent
* Emphasize synthesizing results rather than showing delegation steps

### Sub-Agent Design
* Make sub-agents focused on specific domains
* Use clear, descriptive prompts that explain the sub-agent's expertise
* Configure appropriate MCP servers and tools for each sub-agent's domain

### Coordination Strategy
* Design the supervisor to handle multi-step tasks that require multiple sub-agents
* Ensure sub-agents can work independently without conflicting with each other
* Consider the order of delegation when tasks depend on previous results


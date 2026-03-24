# CLAUDE.md — xCode Project Guide

## Project Overview

xCode is a **monorepo** containing:
1. **CLI tool** (`xcode/`) - Builds a Neo4j knowledge graph and orchestrates coding tasks
2. **AI Agent** (`agent/`) - FastAPI server with LangGraph-based coding agent

The CLI spawns the agent via Docker, which uses MCP tools (Neo4j, filesystem) to understand and modify code.

---

## Repository Structure

```
xcode/
├── xcode/                    # CLI package
│   ├── cli.py               # Click CLI entry point
│   ├── orchestrator.py      # Main orchestrator
│   ├── repositories/        # External adapters (agent API, Neo4j, etc.)
│   └── services/            # Business logic
├── agent/                    # AI Agent (FastAPI + LangGraph)
│   ├── app/
│   │   ├── api/agents/      # Agent API routes and service
│   │   ├── engine/          # Agent implementation
│   │   │   ├── xcode_coding_agent/  # The coding agent
│   │   │   │   ├── agent.py         # Agent creation
│   │   │   │   └── prompt.py        # System prompt
│   │   │   ├── stream_processor.py  # SSE event processing
│   │   │   └── mcp_tools.py         # MCP tool integration
│   │   └── core/            # Settings, DB, middleware
│   ├── Dockerfile           # Agent container
│   └── pyproject.toml       # Agent dependencies
├── docker-compose.yml       # Full stack (Neo4j, Postgres, Agent, CLI)
├── tests/                   # CLI tests
└── pyproject.toml          # CLI dependencies
```

---

## Architecture

```
CLI (xcode/cli.py)
    ↓
Orchestrator (xcode/orchestrator.py)
    ↓
Agent Repository (xcode/repositories/agent_repository.py)
    ↓ HTTP/SSE
Agent API (agent/app/api/agents/)
    ↓
LangGraph Agent (agent/app/engine/xcode_coding_agent/)
    ↓ MCP
Tools: Neo4j (knowledge graph), Filesystem (read/write files)
```

### Key Files

| File | Role |
|------|------|
| `xcode/cli.py` | Click CLI entry point |
| `xcode/orchestrator.py` | Main orchestrator |
| `xcode/repositories/agent_repository.py` | Agent HTTP client (SSE streaming) |
| `agent/app/api/agents/service.py` | Agent session management |
| `agent/app/engine/xcode_coding_agent/agent.py` | LangGraph agent creation |
| `agent/app/engine/xcode_coding_agent/prompt.py` | System prompt (Cypher rules, file handling) |
| `agent/app/engine/stream_processor.py` | Converts LangGraph events to SSE |

---

## Agent Integration

- **URL**: `http://localhost:8000` (or `http://xcode-agent:8000` in Docker)
- **Agent name**: `xcode_coding_agent`
- **Endpoint**: `POST /agents`
- **Request**: `{"agent_name": "xcode_coding_agent", "query": "<task description>"}`
- **Response**: Server-Sent Events (SSE)
- **Event types**: `session_created`, `tool_call`, `tool_result`, `token`, `answer`, `error`, `complete`

### MCP Tools Available to Agent

1. **Neo4j** (`read_neo4j_cypher`) - Query the knowledge graph
2. **Filesystem** (`read_file`, `write_file`, `edit_file`, `list_directory`) - File operations

---

## Running

### With Docker (recommended)

```bash
# Start all services
docker-compose up -d

# Run a task
docker-compose exec xcode xcode "add logging to main.py"

# Interactive mode
docker-compose exec -it xcode xcode -i
```

### Local Development

```bash
# Start dependencies
docker-compose up -d neo4j postgres xcode-agent

# Run CLI locally
xcode --local "your task here"
```

### CLI Flags

```bash
xcode "task"                    # Run task
xcode -i                        # Interactive mode
xcode --verbose "task"          # Verbose output
xcode --no-build-graph "task"   # Skip graph rebuild
xcode --local "task"            # Ollama for xgraph (normalizes to http://localhost:11434/v1)
xcode --no-verify "task"        # Skip automatic verification
xcode --no-test-generation "task"  # Skip automatic test generation
xcode --max-fix-attempts 3 "task"  # Allow 3 fix attempts on test failures
```

### Verification Loop

xCode automatically verifies changes after task completion:

1. **Test Discovery**: Queries Neo4j to find tests related to modified code
2. **Coverage Analysis**: Identifies untested callables using graph relationships
3. **Test Generation**: Generates pytest tests for untested code (if enabled)
4. **Verification**: Runs tests and linters
5. **Auto-Fix**: Retries with agent fixes if verification fails (max 2 attempts by default)

The loop uses Neo4j queries like:
```cypher
// Find tests for a callable
MATCH (c:Callable {name: 'my_function'})<-[:TESTS]-(t:Test)
RETURN t.name, t.path

// Find untested callables
MATCH (f:File {path: 'myfile.py'})<-[:DECLARED_IN]-(c:Callable)
WHERE NOT (c:Test) AND NOT EXISTS((c)<-[:TESTS]-())
RETURN c.name, c.signature
```

### Local LLM (Ollama)

- **`--local` / `XCODE_LLM_ENDPOINT`**: Used for **knowledge graph (xgraph)**. `get_llm_config()` normalizes port `11434` to an OpenAI-compatible base URL with `/v1`. xgraph runs with temporary `OPENAI_BASE_URL` / `OPENAI_API_KEY=ollama` during graph build (including interactive startup).
- **La-factoria agent**: Uses **`agent/.env`** (`LLM_BASE_URL`, `LLM_MODEL`, etc.), not the CLI flags. For Ollama set e.g. `LLM_BASE_URL=http://localhost:11434/v1` (or `host.docker.internal` from containers).

---

## Tests & Code Quality

```bash
# CLI tests
pytest tests/ -v
pytest --cov=xcode --cov-report=html

# Formatting & linting
black xcode tests
ruff check xcode tests
mypy xcode
```

---

## Environment Variables

### CLI (.env)
```bash
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password
LA_FACTORIA_URL=http://localhost:8000
```

### Agent (agent/.env)
```bash
OPENAI_API_KEY=your-key
NEO4J_URI=bolt://neo4j:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=password
DATABASE_URL=postgresql://user:pass@postgres:5432/db
```

---

## Common Issues

### Agent returns "Access denied - path outside allowed directories"
The filesystem MCP only allows access to `/Users/elijahgjacob`. Ensure:
1. The repo path is under this directory
2. The Docker volume mount is correct: `/Users/elijahgjacob:/Users/elijahgjacob`

### Neo4j Cypher syntax errors
The agent's prompt has strict Cypher rules. Key points:
- Use simple, separate queries (not complex CALL {} blocks)
- Never use UNION ALL
- Neo4j stores relative paths; agent must prepend repo path

### Recursion limit reached
The agent has a 100-step limit. If hit, the task is too complex or the agent is looping. Check the prompt's "STOP CONDITIONS" section.

---

## Development Notes

- Agent runs in its own container with separate Python environment
- Agent imports stay as `app.*` (not `agent.app.*`)
- CLI communicates with agent via HTTP/SSE only
- Agent's LLM is configured in `agent/.env`, not via CLI flags

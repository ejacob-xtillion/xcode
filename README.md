# xCode

> AI-powered coding assistant with codebase knowledge graphs

xCode is a monorepo containing:
- **CLI** (`xcode/`): Command-line interface for coding tasks
- **Agent** (`agent/`): FastAPI + LangGraph AI agent with MCP tools

## Features

- 🔍 **Knowledge Graph Integration**: Understands your codebase structure via Neo4j
- 🤖 **AI Agent**: LangGraph-based agent with MCP tools (Neo4j, filesystem)
- 💻 **Local LLM Support**: Works with Ollama, LM Studio, or cloud APIs
- ✅ **Automatic Verification Loop**: Runs tests/linters after changes, generates missing tests
- 🧪 **Smart Test Discovery**: Uses Neo4j to find related tests and untested code
- 🔄 **Auto-Fix Retry**: Agent automatically fixes test failures (configurable attempts)
- 📊 **Rich CLI**: Beautiful terminal UI with progress indicators
- 🏗️ **Clean Architecture**: Modular design with clear separation of concerns

## Quick Start

### Docker (Recommended)

```bash
# Configure agent
cp agent/.env.example agent/.env
# Edit agent/.env and set OPENAI_API_KEY

# Start all services
docker-compose up -d

# Run xCode interactively
docker-compose exec xcode xcode -i

# Or run a single task
docker-compose exec xcode xcode "add type hints to all functions"
```

### Local Development

```bash
# Start backend services
docker-compose up -d neo4j postgres xcode-agent

# Install CLI locally
pip install -e .

# Run xCode
xcode --local "your task here"
```

## CLI Options

```
Options:
  --path, -p PATH          Repository path (default: current directory)
  --language, -l LANG      Language: python or csharp (default: python)
  --project-name NAME      Project name for knowledge graph
  --no-build-graph         Skip building knowledge graph
  --model NAME             LLM model for graph building
  --llm-endpoint URL       Base URL for local LLM API
  --local                  Use local LLM (Ollama at localhost:11434)
  --verbose, -v            Enable verbose output
  --no-verify              Skip automatic verification after changes
  --no-test-generation     Skip automatic test generation for untested code
  --max-fix-attempts N     Maximum retry attempts on test failures (default: 2)
  -i, --interactive        Interactive mode
  --help                   Show this message and exit
```

### Verification Loop

By default, xCode automatically verifies changes after the agent completes a task:

1. **Test Discovery**: Uses Neo4j to find tests related to modified code
2. **Coverage Check**: Identifies untested callables in modified files
3. **Test Generation**: Automatically generates tests for untested code
4. **Verification**: Runs pytest and linters
5. **Auto-Fix**: If tests fail, agent gets 2 attempts to fix issues

Disable with `--no-verify` or `--no-test-generation` flags.

## Repository Structure

```
xcode/
├── xcode/                    # CLI package
│   ├── cli.py               # Click CLI entry point
│   ├── orchestrator.py      # Main orchestrator
│   ├── services/            # Business logic
│   ├── repositories/        # External adapters
│   └── domain/              # Models & interfaces
├── agent/                    # AI Agent (FastAPI + LangGraph)
│   ├── app/
│   │   ├── api/agents/      # Agent API
│   │   ├── engine/          # Agent implementation
│   │   └── core/            # Settings, DB, middleware
│   └── Dockerfile
├── docker-compose.yml       # Full stack orchestration
├── tests/                   # CLI tests
└── pyproject.toml          # CLI dependencies
```

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

## Local LLM (Ollama)

- **Knowledge graph (`xgraph`)**: `xcode --local` (or `XCODE_LLM_ENDPOINT`) normalizes Ollama to an OpenAI-compatible base URL (`http://localhost:11434/v1`) and sets `OPENAI_*` for xgraph while the graph builds. Start Ollama and pull a model (e.g. `ollama pull llama3.2`).
- **Coding agent (la-factoria)**: The agent HTTP API uses the **agent server's** LLM env (`agent/.env`). For Ollama, set `LLM_BASE_URL` to `http://localhost:11434/v1` (or `http://host.docker.internal:11434/v1` from Docker) and `LLM_API_KEY=ollama` (or any non-empty placeholder Ollama accepts).

## Neo4j Knowledge Graph

The agent queries a Neo4j knowledge graph containing:

**Node Types:**
- `Project`, `Folder`, `File`, `Class`, `Callable`, `Test`, `Module`, `Variable`

**Relationship Types:**
- `DECLARED_IN`, `IMPORTS`, `INHERITS_FROM`, `USES`, `TESTS`, `INCLUDED_IN`

**Example Query:**
```cypher
MATCH (f:File)<-[:DECLARED_IN]-(c:Callable)
WHERE NOT EXISTS((c)<-[:TESTS]-())
RETURN c.name, f.path
```

## Development

### Running Tests

```bash
pytest tests/ -v
pytest --cov=xcode --cov-report=html
```

### Code Quality

```bash
black xcode tests
ruff check xcode tests
mypy xcode
```

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
```

## Documentation

- [CLAUDE.md](CLAUDE.md) - Project guide for AI assistants
- [DOCKER.md](DOCKER.md) - Docker setup instructions
- [ARCHITECTURE.md](ARCHITECTURE.md) - Clean architecture details
- [agent/README.md](agent/README.md) - Agent documentation

## License

MIT License - see LICENSE file for details

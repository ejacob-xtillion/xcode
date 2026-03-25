# Contributing to xCode

Thank you for your interest in contributing to xCode! This document provides guidelines and instructions for development.

## Development Setup

### Prerequisites

- Python 3.11+
- Docker and Docker Compose
- Git

### Local Development

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd xcode
   ```

2. **Set up environment variables:**
   ```bash
   # CLI environment
   cp .env.docker.example .env
   # Edit .env with your settings
   
   # Agent environment
   cp agent/.env.example agent/.env
   # Edit agent/.env and set OPENAI_API_KEY
   ```

3. **Start backend services:**
   ```bash
   docker-compose up -d neo4j postgres xcode-agent
   ```

4. **Install CLI locally:**
   ```bash
   pip install -e .
   ```

5. **Run xCode:**
   ```bash
   xcode --local "your task here"
   ```

## Project Structure

This is a monorepo with two main packages:

### CLI Package (`xcode/`)

The CLI orchestrates coding tasks and manages the knowledge graph:

```
xcode/
├── cli.py              # Click CLI entry point
├── orchestrator.py     # Main orchestrator
├── services/           # Business logic
│   ├── graph_service.py
│   ├── verification_service.py
│   └── task_classifier.py
├── repositories/       # External adapters
│   ├── agent_repository.py
│   ├── neo4j_repository.py
│   └── filesystem_repository.py
└── domain/            # Models & interfaces
```

### Agent Package (`agent/`)

The FastAPI + LangGraph agent that executes coding tasks:

```
agent/
├── app/
│   ├── api/agents/           # Agent API routes
│   ├── engine/
│   │   ├── xcode_coding_agent/  # Main coding agent
│   │   ├── stream_processor.py  # SSE event handling
│   │   └── mcp_tools.py         # MCP tool integration
│   └── core/                 # Settings, DB, middleware
├── Dockerfile
└── pyproject.toml
```

## Testing

### Running Tests

```bash
# Run all CLI tests
pytest tests/ -v

# Run with coverage
pytest --cov=xcode --cov-report=html

# Run specific test file
pytest tests/test_orchestrator.py -v
```

### Writing Tests

- Place tests in the `tests/` directory
- Mirror the structure of the `xcode/` package
- Use pytest fixtures for common setup
- Mock external dependencies (Neo4j, agent API)

## Code Quality

### Formatting and Linting

```bash
# Format code
black xcode tests

# Lint code
ruff check xcode tests

# Type checking
mypy xcode
```

### Pre-commit Checks

Before committing, ensure:
1. All tests pass
2. Code is formatted with `black`
3. No linting errors from `ruff`
4. Type checking passes with `mypy`

## Architecture Principles

xCode follows **Clean Architecture** principles:

1. **Domain Layer**: Core business logic, no external dependencies
2. **Service Layer**: Use cases and business workflows
3. **Repository Layer**: External adapters (Neo4j, HTTP, filesystem)
4. **Interface Layer**: CLI, API endpoints

### Key Rules

- **Dependencies flow inward**: CLI → Services → Domain
- **No circular dependencies**: Use dependency injection
- **Interface segregation**: Small, focused interfaces
- **Testability**: Mock external dependencies

## Agent Development

### Agent Architecture

The agent uses LangGraph with MCP tools:

```python
# Agent flow
User Query → LangGraph Agent → MCP Tools → Response
                    ↓
            (Neo4j, Filesystem)
```

### Adding New MCP Tools

1. Define tool in `agent/app/engine/mcp_tools.py`
2. Register tool in agent creation (`agent/app/engine/xcode_coding_agent/agent.py`)
3. Update system prompt if needed (`agent/app/engine/xcode_coding_agent/prompt.py`)

### Testing the Agent

```bash
# Start agent locally
cd agent
uvicorn app.main:app --reload

# Test via HTTP
curl -X POST http://localhost:8000/agents \
  -H "Content-Type: application/json" \
  -d '{"agent_name": "xcode_coding_agent", "query": "test query"}'
```

## Git Workflow

### Branch Naming

- `feature/` - New features
- `fix/` - Bug fixes
- `chore/` - Maintenance tasks
- `docs/` - Documentation updates
- `hotfix/` - Urgent production fixes

### Commit Messages

Follow conventional commits:

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

Types: `feat`, `fix`, `docs`, `chore`, `test`, `refactor`, `perf`

Examples:
- `feat(agent): add retry logic for failed tool calls`
- `fix(cli): handle empty Neo4j query results`
- `docs: update README with verification loop details`

### Pull Request Process

1. Create a feature branch from `main`
2. Make your changes with clear commits
3. Ensure all tests pass
4. Update documentation if needed
5. Create a PR with a clear description
6. Address review feedback

## Common Development Tasks

### Rebuilding the Knowledge Graph

```bash
# Force rebuild
xcode --local "list all files"

# Skip rebuild for testing
xcode --no-build-graph "your task"
```

### Debugging the Agent

```bash
# Enable verbose output
xcode --verbose "your task"

# Check agent logs
docker-compose logs xcode-agent -f
```

### Working with Neo4j

```bash
# Access Neo4j browser
open http://localhost:7474

# Run Cypher queries
docker-compose exec neo4j cypher-shell -u neo4j -p password
```

## Documentation

### Documentation Structure

- `README.md` - Quick start and overview
- `CLAUDE.md` - AI assistant guide (always keep up-to-date)
- `docs/ARCHITECTURE.md` - Clean architecture details
- `docs/DOCKER.md` - Docker setup and troubleshooting
- `CONTRIBUTING.md` - This file
- `agent/README.md` - Agent-specific documentation

### Updating Documentation

When making significant changes:
1. Update relevant documentation files
2. Keep `CLAUDE.md` in sync (critical for AI assistants)
3. Add examples where helpful
4. Update architecture diagrams if structure changes

## Getting Help

- Check existing documentation in `docs/`
- Review test files for usage examples
- Open an issue for bugs or feature requests
- Ask questions in discussions

## License

By contributing to xCode, you agree that your contributions will be licensed under the MIT License.

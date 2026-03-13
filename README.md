# xCode

> AI-powered coding assistant with codebase knowledge graphs

xCode is a CLI tool inspired by Claude Code that integrates:
- **xgraph**: Codebase knowledge graphs in Neo4j
- **la-factoria**: On-the-fly agent spawning
- **Local LLM support**: Run with Ollama, LM Studio, or any OpenAI-compatible endpoint

## Features

- 🔍 **Knowledge Graph Integration**: Understands your codebase structure via Neo4j
- 🤖 **AI Agents**: Spawns agents to complete coding tasks
- 💻 **Local LLM Support**: Works with Ollama, LM Studio, llama.cpp, or cloud APIs
- 🔄 **Verification Loop**: Automatically runs tests and linters, iterates until success
- 🎯 **Multi-Language**: Supports Python and C#
- 📊 **Rich CLI**: Beautiful terminal UI with progress indicators

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/xcode.git
cd xcode

# Install in development mode
pip install -e .

# Or install from PyPI (when published)
pip install xcode-cli
```

### Prerequisites

1. **Neo4j**: Running instance for knowledge graphs
   ```bash
   # Using Docker
   docker run -p 7687:7687 -p 7474:7474 -e NEO4J_AUTH=neo4j/password neo4j
   ```

2. **xgraph**: For building knowledge graphs
   ```bash
   pip install xgraph
   ```

3. **LLM** (choose one):
   - **Ollama** (local): `brew install ollama && ollama pull llama3.2`
   - **LM Studio** (local): Download from lmstudio.ai
   - **OpenAI** (cloud): Set `OPENAI_API_KEY` environment variable

### Environment Variables

Create a `.env` file:

```bash
# Neo4j Configuration
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password

# Optional: LLM Configuration
XCODE_MODEL=llama3.2                    # Default model name
XCODE_LLM_ENDPOINT=http://localhost:11434  # For local LLM

# Optional: xgraph Configuration
XGRAPH_ENABLE_DESCRIPTIONS=false  # Enable LLM-generated descriptions in graph
```

## Usage

### Basic Usage

```bash
# Run with cloud LLM (OpenAI)
xcode "add type hints to all functions"

# Specify repository path
xcode --path /path/to/repo "refactor database client"

# Use local LLM (Ollama)
xcode --local "fix flaky tests in auth module"

# Custom local endpoint and model
xcode --llm-endpoint http://localhost:1234 --model codellama "optimize query performance"
```

### CLI Options

```
Options:
  --path, -p PATH          Repository path (default: current directory)
  --language, -l LANG      Language: python or csharp (default: python)
  --project-name NAME      Project name for knowledge graph
  --no-build-graph         Skip building knowledge graph
  --model NAME             LLM model (e.g., gpt-4, llama3.2, codellama)
  --llm-endpoint URL       Base URL for local LLM API
  --local                  Use local LLM (Ollama at localhost:11434)
  --verbose, -v            Enable verbose output
  --help                   Show this message and exit
```

### Examples

```bash
# Add retry logic with exponential backoff
xcode "add retry logic with exponential backoff to API client"

# Find and fix type errors
xcode --verbose "find and fix all mypy type errors"

# Refactor with specific model
xcode --model gpt-4-turbo "refactor user authentication to use JWT"

# Local LLM with custom endpoint (LM Studio)
xcode --llm-endpoint http://localhost:1234/v1 --model mistral "optimize database queries"

# C# project
xcode --path /path/to/csharp/project --language csharp "add logging to all controllers"

# Skip graph rebuild (graph already exists)
xcode --no-build-graph "update API documentation"
```

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                         xCode CLI                        │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  1. Ensure Knowledge Graph Exists (xgraph)              │
│     ├─ Parse codebase AST                               │
│     ├─ Build nodes and relationships                    │
│     └─ Write to Neo4j                                   │
│                                                          │
│  2. Spawn Agent (la-factoria stub)                      │
│     ├─ Pass task description                            │
│     ├─ Configure Neo4j MCP                              │
│     ├─ Provide graph schema                             │
│     ├─ Configure LLM (local or cloud)                   │
│     └─ Provide tools (read, write, run, query)          │
│                                                          │
│  3. Verification Loop                                   │
│     ├─ Run tests (pytest / dotnet test)                 │
│     ├─ Run linter (ruff / dotnet format)                │
│     ├─ Capture stdout, stderr, exit codes               │
│     ├─ Pass logs back to agent                          │
│     └─ Iterate until success or max iterations          │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

## Project Structure

```
xcode/
├── xcode/
│   ├── __init__.py           # Package initialization
│   ├── cli.py                # CLI entry point
│   ├── config.py             # Configuration management
│   ├── orchestrator.py       # Main orchestration logic
│   ├── graph_builder.py      # xgraph integration
│   ├── agent_runner.py       # Agent spawning (stub)
│   ├── schema.py             # Neo4j schema for agents
│   ├── verification.py       # Test/linter verification loop
│   └── result.py             # Result dataclass
├── tests/
│   ├── test_config.py
│   ├── test_graph_builder.py
│   ├── test_agent_runner.py
│   ├── test_schema.py
│   └── test_verification.py
├── pyproject.toml            # Package configuration
└── README.md                 # This file
```

## Neo4j Schema

The knowledge graph contains:

**Node Types:**
- `Project`: Root project container
- `Folder`: Directory structure
- `File`: Source code files
- `Class`: Class definitions
- `Callable`: Functions and methods
- `Test`: Test functions
- `Module`: Imported modules
- `Variable`: Variable declarations

**Relationship Types:**
- `DECLARED_IN`: Element declared in File/Class
- `IMPORTS`: File imports Module
- `INHERITS_FROM`: Class inheritance
- `USES`: Code element uses another
- `TESTS`: Test covers code element
- `INCLUDED_IN`: Containment hierarchy

**Example Queries:**
```cypher
// Find callables that use a specific class
MATCH (c:Callable)-[:USES]->(target)
WHERE target.name CONTAINS 'PaymentClient'
RETURN c.name, c.path, c.line_number

// Find tests for a callable
MATCH (t:Test)-[:TESTS]->(c:Callable {name: 'process_payment'})
RETURN t.name, t.path

// Find untested code
MATCH (p:Project {name: $projectName})
MATCH (p)<-[:INCLUDED_IN*]-(f:File)<-[:DECLARED_IN]-(c:Callable)
WHERE NOT (c:Test) AND NOT EXISTS((c)<-[:TESTS]-())
RETURN c.name, c.path
```

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run specific test module
pytest tests/test_config.py -v

# Run with coverage
pytest --cov=xcode --cov-report=html

# Run tests in parallel
pytest -n auto
```

### Code Quality

```bash
# Format code
black xcode tests

# Lint
ruff check xcode tests

# Type check
mypy xcode
```

### Git Workflow

This project follows a structured SDLC with feature branches:

```bash
# Feature branches
feature/orchestrator-module    # Core orchestration
feature/agent-integration      # Agent runner and schema
feature/verification-loop      # Verification and testing

# All merged to main via structured commits
```

## Integration with la-factoria

The current implementation includes a **stub** for la-factoria integration that shows all the integration points. To integrate with a real la-factoria instance:

1. **Replace the stub** in `xcode/agent_runner.py` with actual la-factoria API calls
2. **Ensure la-factoria** accepts:
   - Task description
   - Repository path and project name
   - Neo4j MCP configuration
   - LLM configuration (model, base_url)
   - Schema context
3. **Ensure tools return** full logs (stdout, stderr, exit codes)
4. **Stream output** from agent to console

## Local LLM Setup

### Ollama

```bash
# Install Ollama
brew install ollama  # macOS
# or download from https://ollama.ai

# Pull a model
ollama pull llama3.2
ollama pull codellama

# Run xCode
xcode --local "your task here"
```

### LM Studio

1. Download from https://lmstudio.ai
2. Load a model (e.g., CodeLlama, Mistral)
3. Start the local server (port 1234 by default)
4. Run xCode:
   ```bash
   xcode --llm-endpoint http://localhost:1234/v1 --model <model-name> "your task"
   ```

### llama.cpp Server

```bash
# Start llama.cpp server
./server -m /path/to/model.gguf --port 8080

# Run xCode
xcode --llm-endpoint http://localhost:8080 --model llama "your task"
```

## Roadmap

- [ ] Full la-factoria integration (replace stub)
- [ ] Support for more languages (TypeScript, Go, Rust)
- [ ] Web UI for monitoring agent progress
- [ ] Incremental graph updates (only changed files)
- [ ] Agent conversation history and replay
- [ ] Integration with CI/CD pipelines
- [ ] Custom tool definitions for agents
- [ ] Multi-agent collaboration

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Write tests for your changes
4. Ensure all tests pass (`pytest`)
5. Format code (`black xcode tests`)
6. Commit with structured messages
7. Push and create a Pull Request

## License

MIT License - see LICENSE file for details

## Acknowledgments

- **xgraph**: Codebase knowledge graph builder
- **la-factoria**: Agent orchestration framework
- **Ollama**: Local LLM runtime
- **Neo4j**: Graph database
- **Rich**: Beautiful terminal UI

## Support

- Issues: https://github.com/yourusername/xcode/issues
- Discussions: https://github.com/yourusername/xcode/discussions
- Documentation: https://github.com/yourusername/xcode/wiki

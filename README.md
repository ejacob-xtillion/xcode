# xCode

CLI tool (like Claude Code) that orchestrates a codebase knowledge graph (xgraph) and la-factoria agents with Neo4j MCP to complete coding tasks. Supports local LLMs (Ollama, LM Studio, etc.).

## Install

```bash
cd xcode
pip install -e .
```

Install xgraph (for the knowledge graph). From the xgraph repo:

```bash
pip install -e /path/to/xgraph
```

Or from git:

```bash
pip install git+https://github.com/xtillion/xgraph.git
```

## Usage

```bash
# Task in current directory (Python)
xcode "add retry logic to the payment client"

# Task in another repo
xcode --path /path/to/repo "find and fix flaky tests in auth module"

# Skip rebuilding the knowledge graph
xcode --no-build-graph "refactor the login flow"

# Local LLM (Ollama)
xcode --local "add type hints to utils.py"
xcode --local --model llama3.2 "write unit tests for service layer"

# Custom local endpoint (e.g. LM Studio)
xcode --llm-endpoint http://localhost:1234/v1 --model my-model "explain main.py"
```

## Options

| Option | Description |
|--------|-------------|
| `task` | Task description for the agent (positional) |
| `--path`, `-p` | Path to the repository (default: current directory) |
| `--language`, `-l` | `python` or `csharp` (default: python) |
| `--project-name` | Project name for the knowledge graph (default: basename of path) |
| `--no-build-graph` | Skip building/updating the knowledge graph |
| `--verbose`, `-v` | Verbose output |
| `--model`, `-m` | Model name (e.g. llama3.2, gpt-4o) |
| `--llm-endpoint` | LLM API base URL for local inference |
| `--local` | Use local LLM (default: Ollama at http://localhost:11434/v1) |

## Environment

- **Neo4j** (same instance as xgraph): `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`
- **LLM**: `XCODE_MODEL`, `XCODE_LLM_ENDPOINT` (optional); `OPENAI_API_KEY` or `XCODE_LLM_API_KEY` for cloud

## Local LLM

- **Ollama**: Run `ollama serve`, then `xcode --local` or `xcode --local --model codellama`
- **LM Studio**: Start the local server, then `xcode --llm-endpoint http://localhost:1234/v1 --model <name>`

## Agent loop

xCode closes the agent loop: tools (run_shell, run_tests) return full stdout, stderr, and exit code so the agent can verify task success and iterate. Optional verification step runs tests/linter and injects output back for the agent to fix and retry.

## La-factoria

When la-factoria is integrated, xCode passes task, repo path, project name, Neo4j MCP config, bundled schema, and LLM config (base_url, model) so the agent uses the knowledge graph and optional local LLM.

## License

See LICENSE.

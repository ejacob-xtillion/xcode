# xCode

CLI tool (like Claude Code) that orchestrates a codebase knowledge graph (xgraph) and la-factoria agents with Neo4j MCP to complete coding tasks. Supports local LLMs (Ollama, LM Studio, etc.).

## Usage (planned)

```bash
xcode "add retry logic to the payment client"
xcode --path /path/to/repo "find and fix flaky tests"
xcode --local --model llama3.2 "refactor auth module"
```

## Requirements

- Python 3.11+
- xgraph (for knowledge graph)
- Neo4j (same instance as xgraph)
- la-factoria (for agent runtime)
- Optional: local LLM (Ollama, LM Studio) for `--local`

## License

See LICENSE.

# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2024-01-XX

### Added
- Initial release of xCode CLI tool
- Core orchestration module with graph building and agent execution
- Configuration management with environment variable support
- Graph builder module with xgraph integration (library + subprocess fallback)
- Agent runner with stub showing la-factoria integration points
- Neo4j schema documentation for agents with example Cypher queries
- Verification loop for running tests and linters
- Support for Python (pytest, ruff) and C# (dotnet test, dotnet format)
- Local LLM support (Ollama, LM Studio, llama.cpp)
- Cloud LLM support (OpenAI-compatible APIs)
- Rich CLI with progress indicators and beautiful output
- Comprehensive test suite (60+ tests, high coverage)
- Structured commits with feature branches
- Full documentation and examples

### Features
- Multi-language support (Python, C#)
- Knowledge graph integration via xgraph and Neo4j
- Local and cloud LLM flexibility
- Tool results capture (stdout, stderr, exit codes)
- Verification and iteration loop
- Project scoping for multi-repo scenarios
- Configurable via CLI flags or environment variables

### Development
- Feature branches: orchestrator-module, agent-integration, verification-loop
- Modular testing with pytest
- Code quality tooling (black, ruff, mypy)
- Structured SDLC workflow with proper branching

[0.1.0]: https://github.com/yourusername/xcode/releases/tag/v0.1.0

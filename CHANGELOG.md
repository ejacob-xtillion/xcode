# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Clean architecture implementation with 4 distinct layers (domain, service, repository, infrastructure)
- Domain layer with pure business models and repository interfaces
- Service layer for business logic orchestration
- Repository layer with Neo4j, file system, and agent adapters
- Infrastructure layer with Neo4j and LLM clients
- Comprehensive architecture documentation (ARCHITECTURE.md)
- Performance documentation in docs/performance/
- GitHub Actions CI pipeline with linting, testing, and type checking

### Changed
- **BREAKING**: Migrated to Python 3.10+ type hints (str | None instead of Optional[str])
- Refactored all modules to use modern union syntax and remove typing imports
- Reorganized imports alphabetically across entire codebase
- Moved domain models to xcode.models package
- Updated all imports to use domain layer abstractions
- Improved code formatting and consistency (RCSR pattern)
- Consolidated performance documentation into docs/performance/

### Fixed
- Task classification now correctly identifies questions as requiring tools
- FileTreeCache methods properly integrated into domain models
- Backward compatibility maintained via result.py and config.py aliases

### Performance
- Smart task classification skips graph builds for simple tasks (90% latency reduction)
- File tree caching reduces redundant Neo4j queries
- Optimized agent context generation

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
- Comprehensive test suite (121 tests, 46% coverage)
- Structured commits with feature branches
- Full documentation and examples
- Interactive mode with conversation history

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
